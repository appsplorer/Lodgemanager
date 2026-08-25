from decimal import Decimal, InvalidOperation
import re

from django.db import transaction
from django.utils import timezone

from ..domain.finance import amount_due, assessment_status, receipt_number
from ..models import BillingEvent, DuesAssessment, Payment, PaymentAllocation, PaymentRequest, Subscription, Tenant, WebhookEvent


class WebhookQuarantined(Exception):
    """Verified provider event that is unsafe to apply automatically."""


SUCCESS_STATES={
    'paymongo':{'paid','succeeded','completed','success'},
    'xendit':{'succeeded','paid','completed','success','captured'},
}
TERMINAL_FAILURE_STATES={'failed','expired','cancelled','canceled','voided'}


def _event_payload(event): return event.payload or {}


def _quarantine(locked, reason):
    locked.status='quarantined';locked.quarantine_reason=str(reason)[:180];locked.last_error='';locked.save(update_fields=['status','quarantine_reason','last_error','attempts','updated_at']);raise WebhookQuarantined(str(reason))


def _next_receipt_number(tenant):
    locked=Tenant.objects.select_for_update().get(pk=tenant.pk);settings=dict(locked.settings or {});seqs=dict(settings.get('receipt_sequences') or {});year=str(timezone.now().year);seq=int(seqs.get(year,0))+1;seqs[year]=seq;settings['receipt_sequences']=seqs;locked.settings=settings;locked.save(update_fields=['settings','updated_at']);prefix=str(settings.get('receipt_prefix') or locked.lodge_number or locked.slug);return locked,receipt_number(prefix,int(year),seq)


def _stripe_subscription_result(locked,data):
    obj=(data.get('data') or {}).get('object') or {};obj_meta=obj.get('metadata') or {};subscription_obj=obj
    payload_tenant=str(obj_meta.get('tenant_id') or data.get('tenant_id') or '').strip()
    # Some invoice events carry tenant metadata on subscription_details.
    if not payload_tenant:
        payload_tenant=str((((obj.get('subscription_details') or {}).get('metadata') or {}).get('tenant_id') or '')).strip()
    if not locked.tenant_id:_quarantine(locked,'stripe_tenant_missing')
    # The signed tenant-scoped callback URL is the primary tenant boundary. If Stripe
    # also supplies tenant metadata, require it to agree; invoice events may omit it.
    if payload_tenant and payload_tenant!=str(locked.tenant_id):_quarantine(locked,'stripe_tenant_mismatch')
    sub,_=Subscription.objects.get_or_create(tenant_id=locked.tenant_id,defaults={'provider':'stripe','status':'pending'})
    event_type=locked.event_type
    if event_type.startswith('customer.subscription.'):
        sub.provider_subscription_id=str(obj.get('id') or sub.provider_subscription_id)[:180];sub.provider_customer_id=str(obj.get('customer') or sub.provider_customer_id)[:180];sub.status=str(obj.get('status') or sub.status)[:40];sub.cancel_at_period_end=bool(obj.get('cancel_at_period_end',sub.cancel_at_period_end));period=obj.get('current_period_end')
        if period:
            try:sub.current_period_end=timezone.datetime.fromtimestamp(int(period),tz=timezone.get_current_timezone())
            except Exception:pass
    elif event_type=='checkout.session.completed':
        sub.provider_customer_id=str(obj.get('customer') or sub.provider_customer_id)[:180];sub.provider_subscription_id=str(obj.get('subscription') or sub.provider_subscription_id)[:180];sub.status='active' if str(obj.get('payment_status') or '').lower() in {'paid','no_payment_required'} else sub.status
    elif event_type in {'invoice.payment_failed','invoice.payment_action_required'}:
        sub.status='past_due'
    elif event_type in {'invoice.paid','invoice.payment_succeeded'} and sub.status in {'past_due','incomplete'}:
        sub.status='active'
    plan=str(obj_meta.get('plan') or (((obj.get('subscription_details') or {}).get('metadata') or {}).get('plan') or '')).strip()
    if plan:sub.plan=plan[:60]
    sub.last_synced_at=timezone.now();sub.save()
    amount=None;currency=str(obj.get('currency') or '').upper()[:3]
    raw_amount=obj.get('amount_paid') or obj.get('amount_total')
    if raw_amount is not None:
        try:amount=Decimal(str(raw_amount))/Decimal('100')
        except Exception:amount=None
    BillingEvent.objects.get_or_create(tenant_id=locked.tenant_id,provider='stripe',provider_reference=locked.event_id,event_type=event_type,defaults={'payload':data,'amount':amount,'currency':currency,'mode':locked.mode,'status':'processed'})
    return {'provider':'stripe','event_type':event_type,'applied':True,'subscription_status':sub.status}


def _local_payment_result(locked,data,provider):
    raw=data.get('data') or data;attrs=raw.get('attributes') or raw
    reference=str(attrs.get('reference_id') or attrs.get('remarks') or attrs.get('description') or attrs.get('external_id') or '')
    match=re.search(r'(?:lfpr:|lfpr-)([0-9a-fA-F-]{32,36})',reference)
    payment_request=None
    if match and locked.tenant_id:
        payment_request=PaymentRequest.objects.select_for_update().filter(pk=match.group(1),tenant_id=locked.tenant_id,provider=provider).select_related('assessment__cycle','member','tenant').first()
    if not payment_request:_quarantine(locked,'payment_request_not_found_or_tenant_mismatch')
    if payment_request.mode!=locked.mode:_quarantine(locked,'provider_mode_mismatch')
    provider_state=str(attrs.get('status') or attrs.get('payment_status') or attrs.get('event') or locked.event_type).lower()
    # Non-success terminal callbacks update the persisted request but never credit finance.
    if any(state in provider_state for state in TERMINAL_FAILURE_STATES):
        payment_request.status='expired' if 'expired' in provider_state else 'cancelled' if 'cancel' in provider_state else 'failed';payment_request.response_payload=data;payment_request.save(update_fields=['status','response_payload','updated_at']);return {'provider':provider,'event_type':locked.event_type,'applied':False,'payment_request_status':payment_request.status}
    if not any(state in provider_state for state in SUCCESS_STATES[provider]):
        return {'provider':provider,'event_type':locked.event_type,'applied':False,'ignored_state':provider_state or 'unknown'}
    try:
        if provider=='paymongo':
            # PayMongo API amounts are minor currency units (centavos). Never use a threshold heuristic.
            raw_amount=attrs.get('amount') if attrs.get('amount') is not None else attrs.get('paid_amount')
            amount=(Decimal(str(raw_amount or '0'))/Decimal('100')).quantize(Decimal('0.01'))
        else:
            amount=Decimal(str(attrs.get('amount') or attrs.get('request_amount') or attrs.get('paid_amount') or '0')).quantize(Decimal('0.01'))
    except (InvalidOperation,ValueError):amount=Decimal('0')
    currency=str(attrs.get('currency') or payment_request.currency).upper()[:3]
    if amount!=payment_request.amount:_quarantine(locked,'provider_amount_mismatch')
    if currency!=payment_request.currency.upper():_quarantine(locked,'provider_currency_mismatch')
    assessment=payment_request.assessment
    if not assessment:_quarantine(locked,'payment_request_missing_assessment')
    due=amount_due(assessment.amount,assessment.paid_amount,assessment.waived_amount,assessment.late_fee,assessment.adjustment_amount)
    if amount>due:_quarantine(locked,'provider_amount_exceeds_balance')
    provider_ref=str(attrs.get('payment_request_id') or attrs.get('payment_id') or attrs.get('id') or locked.event_id)[:180]
    if not provider_ref:_quarantine(locked,'provider_reference_missing')
    existing=Payment.objects.filter(tenant=assessment.tenant,provider=provider,provider_reference=provider_ref).first()
    if not existing:
        locked_tenant,rec=_next_receipt_number(assessment.tenant);payment=Payment.objects.create(tenant=locked_tenant,member=assessment.member,assessment=assessment,amount=amount,currency=currency,method='online',provider=provider,provider_reference=provider_ref,receipt_number=rec);PaymentAllocation.objects.create(tenant=locked_tenant,payment=payment,assessment=assessment,amount=amount);assessment.paid_amount+=amount;assessment.status=assessment_status(assessment.amount,assessment.paid_amount,assessment.waived_amount,assessment.late_fee,timezone.now().date()>assessment.cycle.due_on,assessment.adjustment_amount);assessment.save(update_fields=['paid_amount','status','updated_at'])
    payment_request.status='paid';payment_request.provider_reference=provider_ref;payment_request.settled_at=timezone.now();payment_request.response_payload=data;payment_request.save(update_fields=['status','provider_reference','settled_at','response_payload','updated_at'])
    BillingEvent.objects.get_or_create(tenant=assessment.tenant,provider=provider,provider_reference=locked.event_id,event_type=locked.event_type,defaults={'amount':amount,'currency':currency,'mode':locked.mode,'status':'processed','payload':data})
    return {'provider':provider,'event_type':locked.event_type,'applied':True,'duplicate_payment':bool(existing),'provider_reference':provider_ref}


def process_verified_webhook(event:WebhookEvent):
    """Apply a signature-verified provider event inside its persisted tenant/mode boundary.

    Quarantine decisions are committed before the exception is surfaced to the task/console.
    """
    if event.status=='processed':return {'status':'already_processed'}
    data=_event_payload(event);provider=event.provider;quarantined=None;result=None
    with transaction.atomic():
        locked=WebhookEvent.objects.select_for_update().get(pk=event.pk)
        if locked.status=='processed':return {'status':'already_processed'}
        locked.attempts+=1
        try:
            if provider=='stripe':result=_stripe_subscription_result(locked,data)
            elif provider in {'paymongo','xendit'}:result=_local_payment_result(locked,data,provider)
            else:_quarantine(locked,'unsupported_provider')
        except WebhookQuarantined as exc:
            # _quarantine has persisted the reason. Catch inside atomic so that evidence is committed.
            quarantined=exc
        except Exception as exc:
            locked.status='failed';locked.last_error=f'{type(exc).__name__}:{str(exc)[:300]}';locked.save(update_fields=['status','attempts','last_error','updated_at']);raise
        if quarantined is None:
            locked.status='processed';locked.processed_at=timezone.now();locked.last_error='';locked.quarantine_reason='';locked.save(update_fields=['status','processed_at','attempts','last_error','quarantine_reason','updated_at'])
    if quarantined is not None:raise quarantined
    return result
