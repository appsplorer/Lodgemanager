from __future__ import annotations

from celery import shared_task
from django.core.mail import EmailMessage, BadHeaderError
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from .models import CommunicationCampaign, DeliveryLog, GeneratedReport, ReportDeliveryLog, ReportSchedule, SecurityAlert, SystemJob, TenantMembership, WebhookEvent
from .services.communications import campaign_members, campaign_actor_is_still_authorized, render_campaign_for_member
from .services.reports import generate_report, canonical_report_id
from .domain.permissions import effective_custom_permissions, has_permission
from .domain.job_policy import retry_delay


def _tenant_actor_is_authorized(tenant, user, permission):
    if not user or not getattr(user, 'is_active', False):
        return False
    membership = TenantMembership.objects.select_related('custom_role').filter(
        tenant=tenant, user=user, is_active=True, tenant__is_active=True
    ).first()
    return bool(membership and has_permission(
        membership.role, permission, effective_custom_permissions(membership)
    ))


def _backoff(attempt, base=30, cap=1800):
    return retry_delay(attempt,base=base,cap=cap)


@shared_task(bind=True, max_retries=5)
def send_campaign(self, campaign_id):
    import smtplib
    from django.conf import settings
    from .services.template_rendering import TemplateRenderError
    try:
        c = CommunicationCampaign.objects.select_related('tenant', 'created_by').get(pk=campaign_id)
    except CommunicationCampaign.DoesNotExist:
        return {'status': 'missing'}
    if c.status not in {'draft', 'scheduled', 'sending', 'failed'}:
        return {'status': 'not_sendable', 'campaign_status': c.status}
    if not campaign_actor_is_still_authorized(c):
        c.status = 'failed'; c.save(update_fields=['status', 'updated_at'])
        return {'status': 'authorization_revoked'}

    c.status = 'sending'; c.save(update_fields=['status', 'updated_at'])
    retryable = 0
    for m in campaign_members(c).iterator(chunk_size=500):
        log,_=DeliveryLog.objects.get_or_create(tenant=c.tenant,campaign=c,member=m,recipient=m.email,defaults={'status':'queued'})
        # Retries revisit only transient recipients. Delivered or terminally failed
        # recipients are immutable within this dispatch cycle.
        if log.status in {'delivered','failed'}:
            continue
        log.attempts += 1; log.last_attempt_at=timezone.now(); log.status='sending'; log.save(update_fields=['attempts','last_attempt_at','status','updated_at'])
        try:
            subject,body=render_campaign_for_member(c,m)
            message_id=log.provider_id or f'<lodgeflow-{c.id}-{log.id}@{c.tenant.slug}.invalid>'
            email=EmailMessage(subject=subject,body=body,from_email=settings.DEFAULT_FROM_EMAIL,to=[m.email],headers={'Message-ID':message_id,'X-LodgeFlow-Campaign':str(c.id)})
            email.send(fail_silently=False)
            log.status='delivered'; log.error=''; log.provider_id=message_id; log.provider_metadata={'backend':settings.EMAIL_BACKEND,'message_id':message_id}; log.delivered_at=timezone.now(); log.save(update_fields=['status','error','provider_id','provider_metadata','delivered_at','updated_at'])
        except (TemplateRenderError,BadHeaderError,ValueError) as exc:
            log.status='failed'; log.error=f'{type(exc).__name__}:{str(exc)[:450]}'; log.save(update_fields=['status','error','updated_at'])
        except Exception as exc:
            permanent=isinstance(exc,smtplib.SMTPRecipientsRefused) or (isinstance(exc,smtplib.SMTPDataError) and int(getattr(exc,'smtp_code',0) or 0)>=500)
            if permanent or self.request.retries >= self.max_retries:
                log.status='failed'
            else:
                log.status='retry_pending'; retryable += 1
            log.error=f'{type(exc).__name__}:{str(exc)[:450]}'; log.save(update_fields=['status','error','updated_at'])

    if retryable and self.request.retries < self.max_retries:
        c.status='sending'; c.save(update_fields=['status','updated_at'])
        raise self.retry(countdown=_backoff(self.request.retries + 1))

    c.deliveries.filter(status='retry_pending').update(status='failed',updated_at=timezone.now())
    delivered=c.deliveries.filter(status='delivered').count(); failed=c.deliveries.filter(status='failed').count()
    c.status = 'sent' if delivered > 0 else 'failed'
    c.save(update_fields=['status', 'updated_at'])
    return {'status': c.status, 'sent': delivered, 'failed': failed}


@shared_task
def dispatch_due_campaigns():
    """Atomically claim due campaigns so overlapping Beat ticks cannot double-send."""
    now=timezone.now();queued=[];failed=[]
    due=CommunicationCampaign.objects.filter(status='scheduled',scheduled_for__lte=now).values_list('id',flat=True)[:500]
    for campaign_id in due:
        claimed=CommunicationCampaign.objects.filter(pk=campaign_id,status='scheduled',scheduled_for__lte=now).update(status='sending',updated_at=now)
        if not claimed:continue
        try:task=send_campaign.delay(str(campaign_id));queued.append({'campaign_id':str(campaign_id),'task_id':task.id})
        except Exception as exc:CommunicationCampaign.objects.filter(pk=campaign_id,status='sending').update(status='failed',updated_at=timezone.now());failed.append({'campaign_id':str(campaign_id),'error':type(exc).__name__})
    return {'queued':queued,'failed':failed,'checked_at':now.isoformat()}


@shared_task(bind=True,max_retries=3)
def import_members_job(self,job_id):
    """Commit a validated large member import atomically and idempotently."""
    from django.contrib.auth import get_user_model
    from .models import Member
    from .services.audit import append_audit
    try:job=SystemJob.objects.select_related('tenant').get(pk=job_id,kind='member_import')
    except SystemJob.DoesNotExist:return {'status':'missing'}
    if job.status=='completed':return {'status':'already_completed','job_id':str(job.id),**dict(job.result or {})}
    actor=get_user_model().objects.filter(pk=(job.payload or {}).get('actor_id'),is_active=True).first()
    if not _tenant_actor_is_authorized(job.tenant,actor,'members.create'):
        job.status='failed';job.finished_at=timezone.now();job.last_error='authorization_revoked';job.save(update_fields=['status','finished_at','last_error','updated_at']);return {'status':'authorization_revoked','job_id':str(job.id)}
    rows=list((job.payload or {}).get('rows') or []);job.status='running';job.started_at=job.started_at or timezone.now();job.attempts=max(job.attempts,self.request.retries+1);job.last_error='';job.save(update_fields=['status','started_at','attempts','last_error','updated_at'])
    allowed={'first_name','last_name','email','phone','address','status','degree','joined_on','initiated_on','passed_on','raised_on','date_of_birth','tags','notes','custom_data','communication_preferences','is_dues_exempt','custom_dues_amount'}
    try:
        created=[]
        with transaction.atomic():
            for row in rows:
                values={key:value for key,value in dict(row.get('data') or {}).items() if key in allowed};member=Member(tenant=job.tenant,**values);member.full_clean();member.save();created.append(str(member.id))
        result={'created':len(created),'member_ids':created[:1000]};job.status='completed';job.finished_at=timezone.now();job.result=result;job.save(update_fields=['status','finished_at','result','updated_at']);append_audit(actor=actor,tenant=job.tenant,action='members.imported',object_type='SystemJob',object_id=job.id,metadata={'count':len(created),'async':True,'mapping':(job.payload or {}).get('mapping',{}),'duplicate_policy':(job.payload or {}).get('duplicate_policy','none')});return {'status':'completed','job_id':str(job.id),**result}
    except Exception as exc:
        job.status='failed';job.finished_at=timezone.now();job.last_error=f'{type(exc).__name__}:{str(exc)[:500]}';job.save(update_fields=['status','finished_at','last_error','updated_at'])
        if self.request.retries<self.max_retries:job.status='queued';job.save(update_fields=['status','updated_at']);raise self.retry(exc=exc,countdown=_backoff(self.request.retries+1,base=45))
        return {'status':'failed','job_id':str(job.id),'error':type(exc).__name__}


@shared_task(bind=True, max_retries=5)
def process_webhook_event(self, event_id):
    """Background reconciliation for an already signature-verified webhook."""
    from .services.webhook_processing import process_verified_webhook, WebhookQuarantined
    try:
        event=WebhookEvent.objects.get(pk=event_id)
    except WebhookEvent.DoesNotExist:
        return {'status':'missing'}
    try:
        return process_verified_webhook(event)
    except WebhookQuarantined as exc:
        return {'status':'quarantined','reason':str(exc)}
    except Exception as exc:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc,countdown=_backoff(self.request.retries + 1, base=20))
        return {'status':'failed','error':type(exc).__name__}


@shared_task(bind=True, max_retries=3)
def generate_report_async(self, generated_report_id):
    """Generate a persisted large report outside the web request thread."""
    try:
        report=GeneratedReport.objects.select_related('tenant','generated_by').get(pk=generated_report_id)
    except GeneratedReport.DoesNotExist:
        return {'status':'missing'}
    if report.status=='completed':
        return {'status':'already_completed','generated_report_id':str(report.id)}
    if not _tenant_actor_is_authorized(report.tenant, report.generated_by, 'reports.export'):
        report.status='failed';report.progress=100;report.error='authorization_revoked';report.save(update_fields=['status','progress','error','updated_at'])
        return {'status':'authorization_revoked','generated_report_id':str(report.id)}
    report.status='running';report.progress=15;report.error='';report.save(update_fields=['status','progress','error','updated_at'])
    try:
        report,_,_=generate_report(report.tenant,report.report_type,report.format,report.filters,report.generated_by,existing=report)
        return {'status':'completed','generated_report_id':str(report.id),'sha256':report.sha256,'row_count':report.row_count}
    except Exception as exc:
        report.status='failed';report.progress=100;report.error=f'{type(exc).__name__}:{str(exc)[:500]}';report.save(update_fields=['status','progress','error','updated_at'])
        if self.request.retries<self.max_retries:
            report.status='queued';report.progress=5;report.save(update_fields=['status','progress','updated_at'])
            raise self.retry(exc=exc,countdown=_backoff(self.request.retries+1,base=45))
        return {'status':'failed','generated_report_id':str(report.id),'error':type(exc).__name__}


@shared_task(bind=True, max_retries=4)
def run_report_schedule(self, schedule_id):
    """Generate and deliver a scheduled report idempotently with recipient evidence."""
    try:
        schedule=ReportSchedule.objects.select_related('tenant','created_by').get(pk=schedule_id,is_active=True)
    except ReportSchedule.DoesNotExist:
        return {'status':'missing_or_disabled'}
    if not _tenant_actor_is_authorized(schedule.tenant, schedule.created_by, 'reports.admin'):
        schedule.last_run_at=timezone.now();schedule.last_status='authorization_revoked';schedule.save(update_fields=['last_run_at','last_status','updated_at'])
        return {'status':'authorization_revoked'}
    if not schedule.recipients:return {'status':'no_recipients'}
    task_id=str(self.request.id or f'manual-{schedule.id}')
    job=SystemJob.objects.filter(tenant=schedule.tenant,kind='scheduled_report',payload__task_id=task_id).order_by('-created_at').first()
    if not job:
        job=SystemJob.objects.create(tenant=schedule.tenant,kind='scheduled_report',status='running',attempts=1,payload={'task_id':task_id,'schedule_id':str(schedule.id),'report_type':schedule.report_type,'format':schedule.format,'filters':schedule.filters,'recipients':schedule.recipients,'attachments':schedule.attachments},started_at=timezone.now(),result={})
    else:
        job.status='running';job.attempts=max(job.attempts,self.request.retries+1);job.started_at=job.started_at or timezone.now();job.save(update_fields=['status','attempts','started_at','updated_at'])
    try:
        result=dict(job.result or {})
        report=None
        if result.get('generated_report_id'):
            report=GeneratedReport.objects.filter(pk=result['generated_report_id'],tenant=schedule.tenant,status='completed').first()
        if report:
            with default_storage.open(report.file_path,'rb') as handle:data=handle.read()
            mime=(report.metadata or {}).get('mime_type') or 'application/octet-stream'
        else:
            report,data,mime=generate_report(schedule.tenant,schedule.report_type,schedule.format,schedule.filters,schedule.created_by)
            result['generated_report_id']=str(report.id);result['sha256']=report.sha256;job.result=result;job.save(update_fields=['result','updated_at'])
        filename=report.metadata.get('filename') or report.file_path.rsplit('/',1)[-1]
        attachment_payload=[];attachment_ids=[]
        for attachment_type in list(schedule.attachments or []):
            cached=(result.get('attachment_reports') or {}).get(attachment_type)
            attachment=GeneratedReport.objects.filter(pk=cached,tenant=schedule.tenant,status='completed').first() if cached else None
            if attachment:
                with default_storage.open(attachment.file_path,'rb') as handle:attachment_data=handle.read()
                attachment_mime=(attachment.metadata or {}).get('mime_type') or 'application/octet-stream'
            else:
                definition=__import__('platform_core.services.reports',fromlist=['REPORT_CATALOG']).REPORT_CATALOG[canonical_report_id(attachment_type)]
                attachment_format='pdf' if 'pdf' in definition['formats'] else definition['formats'][0]
                attachment,attachment_data,attachment_mime=generate_report(schedule.tenant,attachment_type,attachment_format,schedule.filters,schedule.created_by)
                amap=dict(result.get('attachment_reports') or {});amap[attachment_type]=str(attachment.id);result['attachment_reports']=amap;job.result=result;job.save(update_fields=['result','updated_at'])
            attachment_payload.append(((attachment.metadata or {}).get('filename') or attachment.file_path.rsplit('/',1)[-1],attachment_data,attachment_mime));attachment_ids.append(str(attachment.id))
        delivered=[];failed=[]
        for recipient in list(schedule.recipients):
            log,_=ReportDeliveryLog.objects.get_or_create(tenant=schedule.tenant,schedule=schedule,generated_report=report,recipient=recipient,defaults={'status':'queued','attempts':0})
            if log.status=='delivered':delivered.append(recipient);continue
            log.status='sending';log.attempts+=1;log.last_attempt_at=timezone.now();log.save(update_fields=['status','attempts','last_attempt_at','updated_at'])
            try:
                message_ref=log.provider_reference or f'<lodgeflow-report-{schedule.id}-{report.id}-{log.id}@{schedule.tenant.slug}.invalid>'
                email=EmailMessage(subject=f'{schedule.tenant.name}: {report.metadata.get("report_name",schedule.report_type)}',body='Your scheduled Quill of the Craft report is attached. This message contains an authorized tenant-scoped report.',to=[recipient],headers={'Message-ID':message_ref,'X-LodgeFlow-Report':str(report.id)})
                email.attach(filename,data,mime)
                for extra_name,extra_data,extra_mime in attachment_payload:email.attach(extra_name,extra_data,extra_mime)
                email.send(fail_silently=False)
                log.status='delivered';log.provider_reference=message_ref;log.delivered_at=timezone.now();log.error='';log.save(update_fields=['status','provider_reference','delivered_at','error','updated_at']);delivered.append(recipient)
            except Exception as exc:
                log.status='retry_pending' if self.request.retries<self.max_retries else 'failed';log.error=f'{type(exc).__name__}:{str(exc)[:450]}';log.save(update_fields=['status','error','updated_at']);failed.append(recipient)
        result.update({'generated':True,'generated_report_id':str(report.id),'sha256':report.sha256,'attachment_report_ids':attachment_ids,'delivered_to':delivered,'failed_to':failed})
        job.result=result
        if failed and self.request.retries<self.max_retries:
            job.status='failed';job.last_error=f'delivery_failed:{len(failed)}';job.finished_at=timezone.now();job.save(update_fields=['status','last_error','result','finished_at','updated_at'])
            schedule.last_run_at=timezone.now();schedule.last_status='retry_pending';schedule.save(update_fields=['last_run_at','last_status','updated_at'])
            raise self.retry(countdown=_backoff(self.request.retries+1,base=60))
        job.status='completed' if not failed else 'failed';job.finished_at=timezone.now();job.last_error='' if not failed else f'delivery_failed:{len(failed)}';job.save(update_fields=['status','result','last_error','finished_at','updated_at'])
        schedule.last_run_at=timezone.now();schedule.last_status=job.status;schedule.save(update_fields=['last_run_at','last_status','updated_at'])
        return {'status':job.status,'job_id':str(job.id),**result}
    except self.MaxRetriesExceededError:
        raise
    except Exception as exc:
        job.status='failed';job.last_error=f'{type(exc).__name__}:{str(exc)[:500]}';job.finished_at=timezone.now();job.save(update_fields=['status','last_error','finished_at','updated_at'])
        schedule.last_run_at=timezone.now();schedule.last_status='failed';schedule.save(update_fields=['last_run_at','last_status','updated_at'])
        if self.request.retries<self.max_retries:raise self.retry(exc=exc,countdown=_backoff(self.request.retries+1,base=60))
        return {'status':'failed','job_id':str(job.id),'error':type(exc).__name__}


@shared_task
def dispatch_due_report_schedules():
    """Celery Beat minute dispatcher for validated five-field cron schedules."""
    from zoneinfo import ZoneInfo
    from .services.scheduling import cron_matches, next_cron_run
    now=timezone.now();queued=[];skipped=[]
    for schedule in ReportSchedule.objects.filter(is_active=True).select_related('tenant').iterator(chunk_size=200):
        try: local_now=now.astimezone(ZoneInfo(schedule.tenant.timezone or 'UTC'))
        except Exception: local_now=now
        minute_floor=local_now.replace(second=0,microsecond=0)
        if schedule.last_run_at and schedule.last_run_at>=now-timezone.timedelta(seconds=59):continue
        if not cron_matches(schedule.schedule,minute_floor):continue
        # Update a run marker before enqueueing to prevent Beat overlap from duplicating the same minute.
        updated=ReportSchedule.objects.filter(pk=schedule.pk,is_active=True).filter(last_run_at__lt=now-timezone.timedelta(seconds=59)).update(last_run_at=now,last_status='queued') if schedule.last_run_at else ReportSchedule.objects.filter(pk=schedule.pk,is_active=True,last_run_at__isnull=True).update(last_run_at=now,last_status='queued')
        if not updated:skipped.append(str(schedule.id));continue
        task=run_report_schedule.delay(str(schedule.id));queued.append({'schedule_id':str(schedule.id),'task_id':task.id})
        next_run=next_cron_run(schedule.schedule,schedule.tenant.timezone or 'UTC',after=local_now)
        if next_run:ReportSchedule.objects.filter(pk=schedule.pk).update(next_run_at=next_run.astimezone(timezone.utc) if hasattr(timezone,'utc') else next_run)
    return {'queued':queued,'skipped':skipped,'checked_at':now.isoformat()}


@shared_task
def monitor_operational_health():
    """Raise deduplicated operational alerts for repeated asynchronous failures.

    Service-down/TLS/disk checks are intentionally performed by the external monitor
    (scripts/ops-monitor.py) because an unavailable application cannot alert on itself.
    """
    from datetime import timedelta
    from .services.security import security_alert
    now=timezone.now(); window=now-timedelta(minutes=15); dedupe=now-timedelta(hours=1)
    checks=[
        ('repeated_job_failures',SystemJob.objects.filter(status='failed',updated_at__gte=window).count(),3,'high'),
        ('repeated_webhook_failures',WebhookEvent.objects.filter(status='failed',updated_at__gte=window).count(),3,'high'),
        ('repeated_delivery_failures',DeliveryLog.objects.filter(status='failed',updated_at__gte=window).count(),10,'medium'),
    ]
    raised=[]
    for kind,count,threshold,severity in checks:
        if count<threshold or SecurityAlert.objects.filter(kind=kind,created_at__gte=dedupe,acknowledged_at__isnull=True).exists():
            continue
        alert=security_alert(kind=kind,message=f'{count} failures detected in the last 15 minutes',severity=severity,metadata={'count':count,'window_minutes':15,'threshold':threshold})
        raised.append(str(alert.id))
    return {'status':'ok','raised':raised,'checked_at':now.isoformat()}


@shared_task
def enforce_retention_policies(dry_run=False):
    """Apply tenant lifecycle policy while preserving audit and financial evidence."""
    from .domain.retention import normalize_retention_policy,retention_cutoff
    from .models import DeliveryLog,Document,GeneratedDocument,LodgeProfile,Member,Tenant
    from .services.audit import append_audit
    now=timezone.now();summary={'tenants':0,'documents':0,'generated_documents':0,'generated_reports':0,'delivery_logs':0,'members_anonymized':0,'storage_failures':0,'dry_run':bool(dry_run)}
    job=SystemJob.objects.create(kind='retention_enforcement',status='running',started_at=now,payload={'dry_run':bool(dry_run)},attempts=1)
    try:
        for tenant in Tenant.objects.filter(is_active=True).iterator(chunk_size=100):
            profile,_=LodgeProfile.objects.get_or_create(tenant=tenant);policy=normalize_retention_policy(profile.retention_policy);summary['tenants']+=1
            document_cutoff=retention_cutoff(now.date(),policy['documents_years']);documents=Document.objects.filter(tenant=tenant,created_at__date__lt=document_cutoff)
            for document in documents.iterator(chunk_size=200):
                summary['documents']+=1
                if dry_run:continue
                if document.file_path:
                    try:default_storage.delete(document.file_path)
                    except Exception:summary['storage_failures']+=1;continue
                append_audit(tenant=tenant,action='retention.document.deleted',object_type='Document',object_id=document.id,metadata={'created_at':document.created_at.isoformat(),'policy_years':policy['documents_years']});document.delete()
            generated_documents=GeneratedDocument.objects.filter(tenant=tenant,created_at__date__lt=document_cutoff)
            for generated_document in generated_documents.iterator(chunk_size=200):
                summary['generated_documents']+=1
                if dry_run:continue
                if generated_document.file_path:
                    try:default_storage.delete(generated_document.file_path)
                    except Exception:summary['storage_failures']+=1;continue
                append_audit(tenant=tenant,action='retention.generated_document.deleted',object_type='GeneratedDocument',object_id=generated_document.id,metadata={'kind':generated_document.kind,'sha256':generated_document.sha256,'policy_years':policy['documents_years']});generated_document.delete()
            report_cutoff=retention_cutoff(now.date(),policy['generated_reports_years']);reports=GeneratedReport.objects.filter(tenant=tenant,created_at__date__lt=report_cutoff)
            for report in reports.iterator(chunk_size=200):
                summary['generated_reports']+=1
                if dry_run:continue
                if report.file_path:
                    try:default_storage.delete(report.file_path)
                    except Exception:summary['storage_failures']+=1;continue
                append_audit(tenant=tenant,action='retention.generated_report.deleted',object_type='GeneratedReport',object_id=report.id,metadata={'report_type':report.report_type,'sha256':report.sha256,'policy_years':policy['generated_reports_years']});report.delete()
            communication_cutoff=retention_cutoff(now.date(),policy['communications_years']);logs=DeliveryLog.objects.filter(tenant=tenant,created_at__date__lt=communication_cutoff);log_count=logs.count();summary['delivery_logs']+=log_count
            if log_count and not dry_run:append_audit(tenant=tenant,action='retention.communication_delivery.deleted',object_type='DeliveryLog',metadata={'count':log_count,'policy_years':policy['communications_years']});logs.delete()
            member_cutoff=retention_cutoff(now.date(),policy['inactive_members_years']);members=Member.objects.filter(tenant=tenant,updated_at__date__lt=member_cutoff).exclude(status='active').exclude(first_name='Anonymized')
            for member in members.iterator(chunk_size=200):
                summary['members_anonymized']+=1
                if dry_run:continue
                token=str(member.id).split('-')[0];member.first_name='Anonymized';member.last_name=f'Member {token}';member.email='';member.phone='';member.address='';member.date_of_birth=None;member.notes='';member.tags=[];member.custom_data={'anonymized_at':now.isoformat(),'retention_policy_years':policy['inactive_members_years']};member.communication_preferences={};member.save();append_audit(tenant=tenant,action='retention.member.anonymized',object_type='Member',object_id=member.id,metadata={'policy_years':policy['inactive_members_years']})
        job.status='completed';job.finished_at=timezone.now();job.result=summary;job.save(update_fields=['status','finished_at','result','updated_at']);return summary
    except Exception as exc:
        job.status='failed';job.finished_at=timezone.now();job.last_error=f'{type(exc).__name__}:{str(exc)[:500]}';job.result=summary;job.save(update_fields=['status','finished_at','last_error','result','updated_at']);raise


@shared_task
def generate_recurring_meetings():
    """Celery Beat recurrence expansion. get_or_create occurrence keys make retries safe."""
    from .models import Meeting
    from .services.meetings import generate_recurring_occurrences
    created=existing=templates=failed=0
    for meeting in Meeting.objects.filter(recurrence_source__isnull=True).exclude(recurrence_rule='').select_related('tenant').iterator(chunk_size=200):
        templates+=1
        try:
            result=generate_recurring_occurrences(meeting,horizon_days=180);created+=result['created'];existing+=result['existing']
        except Exception:
            failed+=1
    return {'templates':templates,'created':created,'existing':existing,'failed':failed,'generated_at':timezone.now().isoformat()}
