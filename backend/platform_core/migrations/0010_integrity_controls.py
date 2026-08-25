# Generated for Quill of the Craft Final Baseline v1.0 integrity controls.
from django.db import migrations, models
from django.db.models import Count


def reconcile_legacy_duplicates(apps, schema_editor):
    """Make pre-existing rows safe for the new idempotency constraints.

    Financial rows are never deleted: duplicate provider references are cleared
    only on later duplicate payments and the original reference is preserved in
    the payment notes. Duplicate delivery-log rows are operational evidence, so
    they are consolidated into the earliest row while preserving attempts,
    terminal outcome, provider identifiers, errors, timestamps and the IDs of
    the rows merged by this migration.
    """
    Payment=apps.get_model('platform_core','Payment')
    DeliveryLog=apps.get_model('platform_core','DeliveryLog')

    payment_groups=(Payment.objects.exclude(provider_reference='')
        .values('tenant_id','provider','provider_reference')
        .annotate(total=Count('id')).filter(total__gt=1))
    for group in payment_groups.iterator():
        rows=list(Payment.objects.filter(
            tenant_id=group['tenant_id'],provider=group['provider'],
            provider_reference=group['provider_reference'],
        ).order_by('created_at','id'))
        for duplicate in rows[1:]:
            evidence=(
                '[migration duplicate_provider_reference_preserved '
                f"provider={group['provider']} reference={group['provider_reference']}]"
            )
            duplicate.notes=((duplicate.notes or '').rstrip()+'\n'+evidence).strip()
            duplicate.provider_reference=''
            duplicate.save(update_fields=['provider_reference','notes','updated_at'])

    status_rank={'queued':0,'sending':1,'retry_pending':2,'failed':3,'delivered':4}
    delivery_groups=(DeliveryLog.objects.values('tenant_id','campaign_id','recipient')
        .annotate(total=Count('id')).filter(total__gt=1))
    for group in delivery_groups.iterator():
        rows=list(DeliveryLog.objects.filter(
            tenant_id=group['tenant_id'],campaign_id=group['campaign_id'],recipient=group['recipient'],
        ).order_by('created_at','id'))
        keeper=rows[0];duplicates=rows[1:]
        keeper.attempts=sum(int(row.attempts or 0) for row in rows)
        keeper.status=max(rows,key=lambda row:status_rank.get(row.status,0)).status
        keeper.member_id=keeper.member_id or next((row.member_id for row in rows if row.member_id),None)
        keeper.provider_id=next((row.provider_id for row in rows if row.provider_id),'')
        keeper.last_attempt_at=max((row.last_attempt_at for row in rows if row.last_attempt_at),default=None)
        keeper.delivered_at=max((row.delivered_at for row in rows if row.delivered_at),default=None)
        errors=[]
        for row in rows:
            value=(row.error or '').strip()
            if value and value not in errors:errors.append(value)
        keeper.error=' | '.join(errors)[:2000]
        metadata=dict(keeper.provider_metadata or {})
        metadata['migration_merged_delivery_log_ids']=[str(row.id) for row in duplicates]
        keeper.provider_metadata=metadata
        keeper.save(update_fields=['attempts','status','member','provider_id','last_attempt_at','delivered_at','error','provider_metadata','updated_at'])
        DeliveryLog.objects.filter(id__in=[row.id for row in duplicates]).delete()


def reverse_reconcile(apps, schema_editor):
    # Consolidation is intentionally irreversible; the preserved evidence fields
    # document what was changed and why. Recreating duplicate operational rows
    # would violate the idempotency guarantee this migration establishes.
    pass


class Migration(migrations.Migration):
    dependencies=[('platform_core','0009_audit_billing_completion')]
    operations=[
        migrations.AddField(model_name='encryptedcredential',name='is_enabled',field=models.BooleanField(default=True)),
        migrations.RunPython(reconcile_legacy_duplicates,reverse_reconcile),
        migrations.AddConstraint(model_name='payment',constraint=models.UniqueConstraint(fields=('tenant','provider','provider_reference'),condition=~models.Q(provider_reference=''),name='uniq_payment_provider_reference')),
        migrations.AddConstraint(model_name='deliverylog',constraint=models.UniqueConstraint(fields=('tenant','campaign','recipient'),name='uniq_campaign_recipient_delivery')),
    ]
