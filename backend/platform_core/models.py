import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from .querysets import AuditEventQuerySet
from django.utils import timezone

class UUIDModel(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: abstract=True

class Tenant(UUIDModel):
    name=models.CharField(max_length=180)
    slug=models.SlugField(max_length=180,unique=True)
    lodge_number=models.CharField(max_length=80,blank=True)
    jurisdiction=models.CharField(max_length=160,blank=True)
    plan=models.CharField(max_length=40,default='annual')
    locale=models.CharField(max_length=16,default='en')
    timezone=models.CharField(max_length=64,default='UTC')
    is_active=models.BooleanField(default=True)
    settings=models.JSONField(default=dict,blank=True)
    def __str__(self): return self.name

class TenantMembership(UUIDModel):
    ROLE_CHOICES=[(x,x) for x in ['owner','admin','secretary','treasurer','membership','mentor','document_manager','auditor','viewer','custom']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='user_memberships')
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='tenant_memberships')
    role=models.CharField(max_length=40,choices=ROLE_CHOICES,default='viewer')
    custom_permissions=models.JSONField(default=list,blank=True)
    custom_role=models.ForeignKey('CustomRoleDefinition',on_delete=models.PROTECT,null=True,blank=True,related_name='memberships')
    mfa_required=models.BooleanField(default=False)
    is_active=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','user'],name='uniq_user_tenant')]

class LodgeProfile(UUIDModel):
    tenant=models.OneToOneField(Tenant,on_delete=models.CASCADE,related_name='profile')
    address=models.TextField(blank=True)
    meeting_schedule=models.JSONField(default=dict,blank=True)
    letterhead=models.TextField(blank=True)
    signature_blocks=models.JSONField(default=list,blank=True)
    custom_fields=models.JSONField(default=list,blank=True)
    retention_policy=models.JSONField(default=dict,blank=True)

class Member(UUIDModel):
    STATUS=[(x,x) for x in ['active','inactive','demitted','suspended','deceased','candidate']]
    DEGREE=[(x,x) for x in ['none','EA','FC','MM']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='members')
    first_name=models.CharField(max_length=100); last_name=models.CharField(max_length=100)
    email=models.EmailField(blank=True); phone=models.CharField(max_length=40,blank=True)
    address=models.TextField(blank=True); status=models.CharField(max_length=24,choices=STATUS,default='active')
    degree=models.CharField(max_length=8,choices=DEGREE,default='none')
    joined_on=models.DateField(null=True,blank=True); initiated_on=models.DateField(null=True,blank=True)
    passed_on=models.DateField(null=True,blank=True); raised_on=models.DateField(null=True,blank=True)
    date_of_birth=models.DateField(null=True,blank=True)
    tags=models.JSONField(default=list,blank=True); notes=models.TextField(blank=True); custom_data=models.JSONField(default=dict,blank=True); communication_preferences=models.JSONField(default=dict,blank=True)
    is_dues_exempt=models.BooleanField(default=False); custom_dues_amount=models.DecimalField(max_digits=10,decimal_places=2,null=True,blank=True)
    class Meta:
        indexes=[models.Index(fields=['tenant','last_name','first_name'],name='lf_member_name_idx'),models.Index(fields=['tenant','status'],name='lf_member_status_idx'),models.Index(fields=['tenant','email'],name='lf_member_email_idx')]

class OfficerRoleDefinition(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='officer_role_definitions')
    key=models.SlugField(max_length=80); name=models.CharField(max_length=120); sort_order=models.PositiveIntegerField(default=0)
    is_active=models.BooleanField(default=True); permissions=models.JSONField(default=list,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','key'],name='uniq_officer_role_tenant_key')]

class OfficerTerm(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='officer_terms')
    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='officer_terms')
    office=models.CharField(max_length=120); starts_on=models.DateField(); ends_on=models.DateField(null=True,blank=True)
    is_current=models.BooleanField(default=True); successor=models.ForeignKey(Member,on_delete=models.SET_NULL,null=True,blank=True,related_name='successor_terms')
    notes=models.TextField(blank=True)

class Candidate(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='candidates')
    member=models.OneToOneField(Member,on_delete=models.CASCADE,related_name='candidate_profile')
    stage=models.CharField(max_length=80,default='enquiry')
    stage_order=models.PositiveIntegerField(default=0)
    # Legacy primary mentor remains for backwards compatibility; CandidateMentorAssignment is canonical for multi-mentor support.
    mentor=models.ForeignKey(Member,on_delete=models.SET_NULL,null=True,blank=True,related_name='mentees')
    target_degree_date=models.DateField(null=True,blank=True); proficiency_date=models.DateField(null=True,blank=True)
    referred_by=models.CharField(max_length=160,blank=True); status=models.CharField(max_length=40,default='active')
    stage_history=models.JSONField(default=list,blank=True)

class CandidateMentorAssignment(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='candidate_mentor_assignments')
    candidate=models.ForeignKey(Candidate,on_delete=models.CASCADE,related_name='mentor_assignments')
    mentor=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='candidate_mentor_assignments')
    role=models.CharField(max_length=80,default='mentor'); assigned_at=models.DateTimeField(default=timezone.now); ended_at=models.DateTimeField(null=True,blank=True)
    is_active=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['candidate','mentor','role'],name='uniq_candidate_mentor_role')]

class CandidateTask(UUIDModel):
    STATUS=[(x,x) for x in ['todo','in_progress','blocked','completed','cancelled']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE)
    candidate=models.ForeignKey(Candidate,on_delete=models.CASCADE,related_name='tasks')
    title=models.CharField(max_length=200); due_on=models.DateField(null=True,blank=True)
    assignee=models.ForeignKey(Member,on_delete=models.SET_NULL,null=True,blank=True,related_name='candidate_tasks_assigned')
    status=models.CharField(max_length=24,choices=STATUS,default='todo'); required_for_stage=models.BooleanField(default=False)
    completed_at=models.DateTimeField(null=True,blank=True); notes=models.TextField(blank=True)

class Meeting(UUIDModel):
    TYPE=[(x,x) for x in ['stated','special','degree','social','committee','other']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='meetings')
    title=models.CharField(max_length=180); meeting_type=models.CharField(max_length=30,choices=TYPE,default='stated')
    starts_at=models.DateTimeField(); ends_at=models.DateTimeField(null=True,blank=True); location=models.CharField(max_length=240,blank=True)
    agenda=models.JSONField(default=list,blank=True); business_items=models.JSONField(default=list,blank=True)
    communications=models.JSONField(default=list,blank=True); approved_bills=models.JSONField(default=list,blank=True)
    status=models.CharField(max_length=30,default='scheduled'); recurrence_rule=models.CharField(max_length=255,blank=True)
    education_minutes=models.PositiveIntegerField(default=0); business_minutes=models.PositiveIntegerField(default=0); fellowship_minutes=models.PositiveIntegerField(default=0)
    recurrence_source=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='generated_occurrences')
    occurrence_key=models.CharField(max_length=180,blank=True)
    class Meta:
        constraints=[models.UniqueConstraint(fields=['tenant','occurrence_key'],condition=~models.Q(occurrence_key=''),name='uniq_tenant_meeting_occurrence_key')]

class AgendaItem(UUIDModel):
    KIND=[(x,x) for x in ['standard','custom']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='agenda_items')
    meeting=models.ForeignKey(Meeting,on_delete=models.CASCADE,related_name='agenda_items')
    kind=models.CharField(max_length=20,choices=KIND,default='custom')
    standard_key=models.SlugField(max_length=80,blank=True)
    title=models.CharField(max_length=240)
    notes=models.TextField(blank=True)
    sort_order=models.PositiveIntegerField(default=0)
    is_hidden=models.BooleanField(default=False)
    class Meta:
        ordering=['sort_order','created_at']
        indexes=[models.Index(fields=['tenant','meeting','sort_order'],name='lf_agenda_order_idx')]

class Attendance(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE)
    meeting=models.ForeignKey(Meeting,on_delete=models.CASCADE,related_name='attendance')
    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='attendance')
    status=models.CharField(max_length=24,default='present'); checked_in_at=models.DateTimeField(null=True,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['meeting','member'],name='uniq_meeting_member_attendance')]

class Visitor(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='visitors')
    meeting=models.ForeignKey(Meeting,on_delete=models.CASCADE,related_name='visitors')
    name=models.CharField(max_length=180); home_lodge=models.CharField(max_length=180,blank=True)
    lodge_number=models.CharField(max_length=80,blank=True); jurisdiction=models.CharField(max_length=160,blank=True)
    email=models.EmailField(blank=True); notes=models.TextField(blank=True)

class MinuteVersion(UUIDModel):
    STATE=[(x,x) for x in ['draft','review','approved','locked']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE)
    meeting=models.ForeignKey(Meeting,on_delete=models.CASCADE,related_name='minute_versions')
    version=models.PositiveIntegerField(default=1); state=models.CharField(max_length=20,choices=STATE,default='draft')
    body=models.TextField(blank=True); changed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    reviewer_comments=models.TextField(blank=True); reopen_reason=models.TextField(blank=True)
    reopened_from=models.ForeignKey('self',on_delete=models.SET_NULL,null=True,blank=True,related_name='reopened_versions')
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='minutes_approved')
    approved_at=models.DateTimeField(null=True,blank=True)
    locked_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='minutes_locked')
    locked_at=models.DateTimeField(null=True,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['meeting','version'],name='uniq_meeting_minute_version')]

class DuesCycle(UUIDModel):
    STATUS=[(x,x) for x in ['draft','active','closed']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='dues_cycles')
    name=models.CharField(max_length=120); period_start=models.DateField(); period_end=models.DateField(); due_on=models.DateField()
    standard_amount=models.DecimalField(max_digits=10,decimal_places=2); late_fee=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    currency=models.CharField(max_length=3,default='PHP'); status=models.CharField(max_length=20,choices=STATUS,default='draft')
    proration_enabled=models.BooleanField(default=False); is_open=models.BooleanField(default=False)
    class Meta:
        constraints=[models.CheckConstraint(condition=models.Q(period_end__gte=models.F('period_start')),name='dues_cycle_period_valid'),models.CheckConstraint(condition=models.Q(due_on__gte=models.F('period_start')),name='dues_cycle_due_valid')]

class DuesAssessment(UUIDModel):
    STATUS=[(x,x) for x in ['open','partial','paid','waived','overdue']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE)
    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='dues_assessments')
    cycle=models.ForeignKey(DuesCycle,on_delete=models.CASCADE,related_name='assessments')
    amount=models.DecimalField(max_digits=10,decimal_places=2); late_fee=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    adjustment_amount=models.DecimalField(max_digits=10,decimal_places=2,default=0); currency=models.CharField(max_length=3,default='PHP')
    waived_amount=models.DecimalField(max_digits=10,decimal_places=2,default=0); paid_amount=models.DecimalField(max_digits=10,decimal_places=2,default=0)
    status=models.CharField(max_length=20,choices=STATUS,default='open')
    class Meta: constraints=[models.UniqueConstraint(fields=['member','cycle'],name='uniq_member_dues_cycle'),models.CheckConstraint(condition=models.Q(amount__gte=0),name='dues_assessment_amount_nonnegative'),models.CheckConstraint(condition=models.Q(late_fee__gte=0),name='dues_assessment_late_fee_nonnegative'),models.CheckConstraint(condition=models.Q(waived_amount__gte=0),name='dues_assessment_waived_nonnegative'),models.CheckConstraint(condition=models.Q(paid_amount__gte=0),name='dues_assessment_paid_nonnegative')]

class PaymentRequest(UUIDModel):
    STATUS=[(x,x) for x in ['created','pending','paid','failed','cancelled','expired']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='payment_requests')
    assessment=models.ForeignKey(DuesAssessment,on_delete=models.SET_NULL,null=True,blank=True,related_name='payment_requests')
    member=models.ForeignKey(Member,on_delete=models.SET_NULL,null=True,blank=True,related_name='payment_requests')
    provider=models.CharField(max_length=40); mode=models.CharField(max_length=10,default='test')
    internal_reference=models.CharField(max_length=180); provider_reference=models.CharField(max_length=180,blank=True)
    amount=models.DecimalField(max_digits=12,decimal_places=2); currency=models.CharField(max_length=3,default='PHP')
    status=models.CharField(max_length=20,choices=STATUS,default='created'); request_payload=models.JSONField(default=dict,blank=True); response_payload=models.JSONField(default=dict,blank=True)
    expires_at=models.DateTimeField(null=True,blank=True); settled_at=models.DateTimeField(null=True,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','internal_reference'],name='uniq_payment_request_internal_ref')]

class Payment(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='payments')
    member=models.ForeignKey(Member,on_delete=models.SET_NULL,null=True,blank=True,related_name='payments')
    assessment=models.ForeignKey(DuesAssessment,on_delete=models.SET_NULL,null=True,blank=True,related_name='payments')
    amount=models.DecimalField(max_digits=12,decimal_places=2); currency=models.CharField(max_length=3,default='PHP')
    method=models.CharField(max_length=40,default='manual'); provider=models.CharField(max_length=40,blank=True)
    provider_reference=models.CharField(max_length=180,blank=True); receipt_number=models.CharField(max_length=80)
    paid_at=models.DateTimeField(default=timezone.now); notes=models.TextField(blank=True)
    is_reversed=models.BooleanField(default=False); reversed_at=models.DateTimeField(null=True,blank=True); reversal_reason=models.TextField(blank=True)
    reversed_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='payments_reversed')
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','receipt_number'],name='uniq_tenant_receipt'),models.UniqueConstraint(fields=['tenant','provider','provider_reference'],condition=~models.Q(provider_reference=''),name='uniq_payment_provider_reference'),models.CheckConstraint(condition=models.Q(amount__gt=0),name='payment_amount_positive')]

class PaymentAllocation(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='payment_allocations')
    payment=models.ForeignKey(Payment,on_delete=models.PROTECT,related_name='allocations')
    assessment=models.ForeignKey(DuesAssessment,on_delete=models.PROTECT,related_name='payment_allocations')
    amount=models.DecimalField(max_digits=12,decimal_places=2)
    class Meta: constraints=[models.UniqueConstraint(fields=['payment','assessment'],name='uniq_payment_assessment_allocation'),models.CheckConstraint(condition=models.Q(amount__gt=0),name='payment_allocation_amount_positive')]

class FinancialAdjustment(UUIDModel):
    KIND=[(x,x) for x in ['waiver','charge','credit','payment_reversal']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='financial_adjustments')
    assessment=models.ForeignKey(DuesAssessment,on_delete=models.PROTECT,related_name='adjustments')
    kind=models.CharField(max_length=30,choices=KIND); amount=models.DecimalField(max_digits=12,decimal_places=2)
    reason=models.TextField(); created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='financial_adjustments_created')
    related_payment=models.ForeignKey(Payment,on_delete=models.PROTECT,null=True,blank=True,related_name='reversal_adjustments')
    class Meta: constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name='financial_adjustment_amount_positive')]

class ExpenseCategory(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='expense_categories')
    name=models.CharField(max_length=100); is_active=models.BooleanField(default=True); requires_approval=models.BooleanField(default=False)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','name'],name='uniq_tenant_expense_category')]

class Expense(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='expenses')
    meeting=models.ForeignKey(Meeting,on_delete=models.SET_NULL,null=True,blank=True,related_name='expenses')
    category=models.CharField(max_length=100); category_definition=models.ForeignKey(ExpenseCategory,on_delete=models.PROTECT,null=True,blank=True,related_name='expenses'); description=models.CharField(max_length=255)
    amount=models.DecimalField(max_digits=12,decimal_places=2); currency=models.CharField(max_length=3,default='PHP')
    incurred_on=models.DateField(); vendor=models.CharField(max_length=180,blank=True); receipt_path=models.CharField(max_length=500,blank=True)
    attachment_document=models.ForeignKey('Document',on_delete=models.PROTECT,null=True,blank=True,related_name='expense_attachments')
    is_charity=models.BooleanField(default=False)
    approval_status=models.CharField(max_length=20,default='draft'); approval_reason=models.TextField(blank=True); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='approved_expenses'); approved_at=models.DateTimeField(null=True,blank=True)
    class Meta: constraints=[models.CheckConstraint(condition=models.Q(amount__gt=0),name='expense_amount_positive')]

class Document(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='documents')
    title=models.CharField(max_length=240); folder=models.CharField(max_length=240,blank=True); tags=models.JSONField(default=list,blank=True)
    file_path=models.CharField(max_length=500,blank=True); mime_type=models.CharField(max_length=120,blank=True)
    original_name=models.CharField(max_length=255,blank=True); file_size=models.PositiveBigIntegerField(default=0); sha256=models.CharField(max_length=64,blank=True); scan_status=models.CharField(max_length=32,blank=True)
    content=models.TextField(blank=True); permissions=models.JSONField(default=dict,blank=True); template_key=models.CharField(max_length=80,blank=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)

class MeetingAttachment(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='meeting_attachments')
    meeting=models.ForeignKey(Meeting,on_delete=models.CASCADE,related_name='pack_attachments')
    document=models.ForeignKey(Document,on_delete=models.CASCADE,related_name='meeting_pack_links')
    label=models.CharField(max_length=180,blank=True)
    sort_order=models.PositiveIntegerField(default=0)
    include_in_pack=models.BooleanField(default=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='meeting_attachments_created')
    class Meta:
        ordering=['sort_order','created_at']
        constraints=[models.UniqueConstraint(fields=['meeting','document'],name='uniq_meeting_pack_document')]
        indexes=[models.Index(fields=['tenant','meeting','sort_order'],name='lf_meeting_attach_idx')]

class CommunicationCampaign(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='campaigns')
    name=models.CharField(max_length=180); channel=models.CharField(max_length=20,default='email')
    subject=models.CharField(max_length=240,blank=True); body=models.TextField(); segment=models.JSONField(default=dict,blank=True)
    template_key=models.SlugField(max_length=120,blank=True); administrative_notice=models.BooleanField(default=False)
    scheduled_for=models.DateTimeField(null=True,blank=True); status=models.CharField(max_length=30,default='draft')
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)

class DeliveryLog(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE)
    campaign=models.ForeignKey(CommunicationCampaign,on_delete=models.CASCADE,related_name='deliveries')
    member=models.ForeignKey(Member,on_delete=models.SET_NULL,null=True,blank=True)
    recipient=models.CharField(max_length=255); status=models.CharField(max_length=30,default='queued')
    provider_id=models.CharField(max_length=180,blank=True); error=models.TextField(blank=True); delivered_at=models.DateTimeField(null=True,blank=True)
    attempts=models.PositiveIntegerField(default=0); last_attempt_at=models.DateTimeField(null=True,blank=True); provider_metadata=models.JSONField(default=dict,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','campaign','recipient'],name='uniq_campaign_recipient_delivery')]

class EmailTemplate(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,null=True,blank=True,related_name='email_templates')
    key=models.SlugField(max_length=120); name=models.CharField(max_length=180); subject=models.CharField(max_length=240); body=models.TextField()
    merge_fields=models.JSONField(default=list,blank=True); is_active=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','key'],name='uniq_template_tenant_key',nulls_distinct=False)]

class SavedReport(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='saved_reports')
    owner=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='saved_reports')
    name=models.CharField(max_length=160); report_type=models.CharField(max_length=80); filters=models.JSONField(default=dict,blank=True)
    columns=models.JSONField(default=list,blank=True); grouping=models.JSONField(default=list,blank=True); sorting=models.JSONField(default=list,blank=True); is_shared=models.BooleanField(default=False)

class GeneratedReport(UUIDModel):
    STATUS=[(x,x) for x in ['queued','running','completed','failed','approval_required']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='generated_reports')
    report_type=models.CharField(max_length=80); format=models.CharField(max_length=10,default='pdf'); filters=models.JSONField(default=dict,blank=True)
    reporting_period=models.CharField(max_length=160,blank=True); file_path=models.CharField(max_length=500,blank=True); sha256=models.CharField(max_length=64,blank=True); row_count=models.PositiveIntegerField(default=0)
    generated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='generated_reports'); metadata=models.JSONField(default=dict,blank=True)
    status=models.CharField(max_length=24,choices=STATUS,default='completed',db_index=True); progress=models.PositiveSmallIntegerField(default=100); error=models.TextField(blank=True); job_id=models.CharField(max_length=80,blank=True)

class ReportSchedule(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='report_schedules')
    report_type=models.CharField(max_length=80); format=models.CharField(max_length=10,default='pdf'); schedule=models.CharField(max_length=120)
    recipients=models.JSONField(default=list,blank=True); filters=models.JSONField(default=dict,blank=True); attachments=models.JSONField(default=list,blank=True); is_active=models.BooleanField(default=True)
    created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='report_schedules')
    last_run_at=models.DateTimeField(null=True,blank=True); last_status=models.CharField(max_length=30,blank=True); next_run_at=models.DateTimeField(null=True,blank=True)

class ReportDeliveryLog(UUIDModel):
    STATUS=[(x,x) for x in ['queued','sending','delivered','retry_pending','failed']]
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='report_delivery_logs')
    schedule=models.ForeignKey(ReportSchedule,on_delete=models.SET_NULL,null=True,blank=True,related_name='delivery_logs')
    generated_report=models.ForeignKey(GeneratedReport,on_delete=models.SET_NULL,null=True,blank=True,related_name='delivery_logs')
    recipient=models.EmailField(); status=models.CharField(max_length=24,choices=STATUS,default='queued'); attempts=models.PositiveIntegerField(default=0)
    provider_reference=models.CharField(max_length=180,blank=True); error=models.TextField(blank=True); last_attempt_at=models.DateTimeField(null=True,blank=True); delivered_at=models.DateTimeField(null=True,blank=True)

class GeneratedDocument(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='generated_documents')
    kind=models.CharField(max_length=80); source_type=models.CharField(max_length=80); source_id=models.CharField(max_length=80)
    template_key=models.CharField(max_length=120,blank=True); template_version=models.CharField(max_length=40,default='1')
    file_path=models.CharField(max_length=500); sha256=models.CharField(max_length=64); generated_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='generated_documents')
    metadata=models.JSONField(default=dict,blank=True)


class AuditEvent(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    occurred_at=models.DateTimeField(default=timezone.now,db_index=True)
    tenant=models.ForeignKey(Tenant,on_delete=models.SET_NULL,null=True,blank=True,related_name='audit_events')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True)
    action=models.CharField(max_length=120); object_type=models.CharField(max_length=120,blank=True); object_id=models.CharField(max_length=80,blank=True)
    request_id=models.CharField(max_length=80,blank=True); ip_hash=models.CharField(max_length=128,blank=True); user_agent=models.CharField(max_length=255,blank=True)
    before=models.JSONField(default=dict,blank=True); after=models.JSONField(default=dict,blank=True); metadata=models.JSONField(default=dict,blank=True)
    prev_hash=models.CharField(max_length=64,blank=True); event_hash=models.CharField(max_length=64,blank=True)
    objects=AuditEventQuerySet.as_manager()
    class Meta: ordering=['-occurred_at']; indexes=[models.Index(fields=['tenant','occurred_at'],name='lf_audit_tenant_time_idx'),models.Index(fields=['action','occurred_at'],name='lf_audit_action_time_idx')]
    def save(self,*args,**kwargs):
        if not self._state.adding:
            raise ValidationError('audit_events_are_append_only')
        return super().save(*args,**kwargs)
    def delete(self,*args,**kwargs):
        raise ValidationError('audit_events_are_append_only')

class ExportEvent(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='export_events')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
    export_type=models.CharField(max_length=80); format=models.CharField(max_length=12); filters=models.JSONField(default=dict,blank=True)
    row_count=models.PositiveIntegerField(default=0); approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='approved_exports')
    approval_request=models.ForeignKey('ExportApprovalRequest',on_delete=models.SET_NULL,null=True,blank=True,related_name='export_events')
    result=models.CharField(max_length=30,default='completed'); sha256=models.CharField(max_length=64,blank=True); error=models.TextField(blank=True)

class FeatureFlag(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,null=True,blank=True,related_name='feature_flags')
    key=models.SlugField(max_length=120); enabled=models.BooleanField(default=False); config=models.JSONField(default=dict,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','key'],name='uniq_feature_flag_tenant',nulls_distinct=False)]

class EncryptedCredential(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,null=True,blank=True,related_name='credentials')
    provider=models.CharField(max_length=60); mode=models.CharField(max_length=10,default='test'); ciphertext=models.TextField()
    key_version=models.PositiveIntegerField(default=1); health_status=models.CharField(max_length=40,default='unchecked'); last_checked_at=models.DateTimeField(null=True,blank=True)
    is_enabled=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','provider','mode'],name='uniq_provider_credential',nulls_distinct=False)]

class WebhookEvent(UUIDModel):
    provider=models.CharField(max_length=60); event_id=models.CharField(max_length=180); tenant=models.ForeignKey(Tenant,on_delete=models.SET_NULL,null=True,blank=True)
    event_type=models.CharField(max_length=120,blank=True); mode=models.CharField(max_length=10,default='live'); payload=models.JSONField(default=dict); status=models.CharField(max_length=30,default='received',db_index=True)
    attempts=models.PositiveIntegerField(default=0); last_error=models.TextField(blank=True); quarantine_reason=models.CharField(max_length=180,blank=True); processed_at=models.DateTimeField(null=True,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['provider','event_id','mode'],name='uniq_provider_event_mode')]

class CMSPage(UUIDModel):
    slug=models.SlugField(max_length=180); title=models.CharField(max_length=240); status=models.CharField(max_length=20,default='draft')
    blocks=models.JSONField(default=list,blank=True); meta_title=models.CharField(max_length=240,blank=True); meta_description=models.TextField(blank=True)
    canonical_url=models.URLField(blank=True); og=models.JSONField(default=dict,blank=True); schema=models.JSONField(default=dict,blank=True)
    robots_index=models.BooleanField(default=True); locale=models.CharField(max_length=16,default='en')
    class Meta: constraints=[models.UniqueConstraint(fields=['slug','locale'],name='uniq_cms_slug_locale')]

class RedirectRule(UUIDModel):
    source=models.CharField(max_length=300,unique=True); destination=models.CharField(max_length=500); status_code=models.PositiveSmallIntegerField(default=301); is_active=models.BooleanField(default=True)

class PlatformAnnouncement(UUIDModel):
    kind=models.CharField(max_length=30,default='banner'); title=models.CharField(max_length=180); body=models.TextField(blank=True)
    starts_at=models.DateTimeField(null=True,blank=True); ends_at=models.DateTimeField(null=True,blank=True); is_active=models.BooleanField(default=True)

class ABExperiment(UUIDModel):
    key=models.SlugField(max_length=120,unique=True); variants=models.JSONField(default=list); weights=models.JSONField(default=list); is_active=models.BooleanField(default=True)

class ABAssignment(UUIDModel):
    experiment=models.ForeignKey(ABExperiment,on_delete=models.CASCADE,related_name='assignments')
    subject_key=models.CharField(max_length=180); variant=models.CharField(max_length=80); tenant=models.ForeignKey(Tenant,on_delete=models.SET_NULL,null=True,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['experiment','subject_key'],name='uniq_ab_assignment')]

class ABExposure(UUIDModel):
    assignment=models.ForeignKey(ABAssignment,on_delete=models.CASCADE,related_name='exposures')
    event=models.CharField(max_length=80,default='view'); metadata=models.JSONField(default=dict,blank=True)

class PlatformRoleAssignment(UUIDModel):
    ROLE=[(x,x) for x in ['super_admin','support_admin','billing_admin','compliance_auditor','operator_devops']]
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='platform_roles')
    role=models.CharField(max_length=40,choices=ROLE)
    is_active=models.BooleanField(default=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['user','role'],name='uniq_platform_user_role')]

class CustomRoleDefinition(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='custom_roles')
    name=models.CharField(max_length=120); permissions=models.JSONField(default=list); approval_requirements=models.JSONField(default=dict,blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['tenant','name'],name='uniq_custom_role_name')]

class SiteSetting(UUIDModel):
    key=models.SlugField(max_length=120,unique=True); value=models.JSONField(default=dict); is_public=models.BooleanField(default=False)

class NavigationMenu(UUIDModel):
    key=models.SlugField(max_length=80); items=models.JSONField(default=list); locale=models.CharField(max_length=16,default='en')
    class Meta: constraints=[models.UniqueConstraint(fields=['key','locale'],name='uniq_nav_key_locale')]

class MediaAsset(UUIDModel):
    title=models.CharField(max_length=180); file_path=models.CharField(max_length=500); mime_type=models.CharField(max_length=120,blank=True)
    original_name=models.CharField(max_length=255,blank=True); file_size=models.PositiveBigIntegerField(default=0); sha256=models.CharField(max_length=64,blank=True); scan_status=models.CharField(max_length=32,blank=True)
    visibility=models.CharField(max_length=16,choices=[('public','public'),('private','private')],default='private'); decorative=models.BooleanField(default=False)
    alt_text=models.CharField(max_length=300,blank=True); accessibility_tags=models.JSONField(default=list,blank=True)

class LeadForm(UUIDModel):
    key=models.SlugField(max_length=120,unique=True); name=models.CharField(max_length=180); fields=models.JSONField(default=list); routing=models.JSONField(default=dict,blank=True); is_active=models.BooleanField(default=True)

class LeadSubmission(UUIDModel):
    form=models.ForeignKey(LeadForm,on_delete=models.PROTECT,related_name='submissions'); data=models.JSONField(default=dict); status=models.CharField(max_length=30,default='new'); source=models.CharField(max_length=240,blank=True)

class Subscription(UUIDModel):
    tenant=models.OneToOneField(Tenant,on_delete=models.CASCADE,related_name='subscription')
    provider=models.CharField(max_length=30,default='stripe'); provider_customer_id=models.CharField(max_length=180,blank=True); provider_subscription_id=models.CharField(max_length=180,blank=True)
    plan=models.CharField(max_length=60,default='annual'); status=models.CharField(max_length=40,default='active'); current_period_end=models.DateTimeField(null=True,blank=True); trial_ends_at=models.DateTimeField(null=True,blank=True)
    cancel_at_period_end=models.BooleanField(default=False); last_synced_at=models.DateTimeField(null=True,blank=True)

class BillingEvent(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.SET_NULL,null=True,blank=True,related_name='billing_events'); provider=models.CharField(max_length=30); event_type=models.CharField(max_length=120)
    provider_reference=models.CharField(max_length=180,blank=True); amount=models.DecimalField(max_digits=12,decimal_places=2,null=True,blank=True); currency=models.CharField(max_length=3,blank=True); mode=models.CharField(max_length=10,default='live'); status=models.CharField(max_length=30,default='recorded'); payload=models.JSONField(default=dict,blank=True)

class ImpersonationSession(UUIDModel):
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='impersonations_started'); target_user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='impersonations_received')
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE); reason=models.TextField(); started_at=models.DateTimeField(default=timezone.now); expires_at=models.DateTimeField(); ended_at=models.DateTimeField(null=True,blank=True); is_active=models.BooleanField(default=True)

class SystemJob(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.SET_NULL,null=True,blank=True,related_name='jobs'); kind=models.CharField(max_length=80); status=models.CharField(max_length=30,default='queued')
    payload=models.JSONField(default=dict,blank=True); result=models.JSONField(default=dict,blank=True); attempts=models.PositiveIntegerField(default=0); scheduled_for=models.DateTimeField(null=True,blank=True); started_at=models.DateTimeField(null=True,blank=True); finished_at=models.DateTimeField(null=True,blank=True); last_error=models.TextField(blank=True)

class AccountActionToken(UUIDModel):
    PURPOSE_CHOICES=[('invitation','invitation'),('password_reset','password_reset')]
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='account_action_tokens')
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,null=True,blank=True,related_name='account_action_tokens')
    purpose=models.CharField(max_length=32,choices=PURPOSE_CHOICES)
    digest=models.CharField(max_length=64,unique=True)
    expires_at=models.DateTimeField()
    consumed_at=models.DateTimeField(null=True,blank=True)
    issued_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='account_action_tokens_issued')
    metadata=models.JSONField(default=dict,blank=True)
    class Meta:
        indexes=[models.Index(fields=['purpose','expires_at'],name='lf_account_token_exp_idx'),models.Index(fields=['user','purpose','consumed_at'],name='lf_account_token_user_idx')]

class BulkActionConfirmation(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='bulk_action_confirmations')
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='bulk_action_confirmations')
    token_digest=models.CharField(max_length=64,unique=True)
    fingerprint=models.CharField(max_length=64)
    action=models.CharField(max_length=80)
    impacted_count=models.PositiveIntegerField()
    expires_at=models.DateTimeField()
    consumed_at=models.DateTimeField(null=True,blank=True)
    class Meta:indexes=[models.Index(fields=['tenant','user','expires_at'],name='lf_bulk_confirm_exp_idx')]

class MFADevice(UUIDModel):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='mfa_devices')
    name=models.CharField(max_length=120,default='Authenticator'); secret_ciphertext=models.TextField(); backup_codes_hash=models.JSONField(default=list,blank=True)
    is_confirmed=models.BooleanField(default=False); last_used_counter=models.BigIntegerField(default=-1); confirmed_at=models.DateTimeField(null=True,blank=True)

class ExportApprovalRequest(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='export_approvals'); requester=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='export_requests')
    export_type=models.CharField(max_length=80); format=models.CharField(max_length=12); filters=models.JSONField(default=dict,blank=True); status=models.CharField(max_length=20,default='pending')
    approved_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='export_approvals_given'); decided_at=models.DateTimeField(null=True,blank=True); reason=models.TextField(blank=True); decision_reason=models.TextField(blank=True); expires_at=models.DateTimeField(null=True,blank=True)

class Milestone(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='milestones')
    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='milestones',null=True,blank=True)
    kind=models.CharField(max_length=80); title=models.CharField(max_length=180); milestone_date=models.DateField(); notes=models.TextField(blank=True); recurring_yearly=models.BooleanField(default=False)

class ParticipationRecord(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,related_name='participation_records')
    member=models.ForeignKey(Member,on_delete=models.CASCADE,related_name='participation_records'); meeting=models.ForeignKey(Meeting,on_delete=models.SET_NULL,null=True,blank=True,related_name='participation_records')
    kind=models.CharField(max_length=60); points=models.PositiveIntegerField(default=1); notes=models.CharField(max_length=255,blank=True)


class SecurityAlert(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.SET_NULL,null=True,blank=True,related_name='security_alerts')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='security_alerts')
    kind=models.CharField(max_length=80); severity=models.CharField(max_length=20,default='medium'); message=models.CharField(max_length=500); metadata=models.JSONField(default=dict,blank=True)
    acknowledged_at=models.DateTimeField(null=True,blank=True); acknowledged_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='security_alerts_acknowledged')

class IdempotencyReceipt(UUIDModel):
    tenant=models.ForeignKey(Tenant,on_delete=models.CASCADE,null=True,blank=True,related_name='idempotency_receipts')
    user_id=models.BigIntegerField(null=True,blank=True)
    key=models.CharField(max_length=80)
    method=models.CharField(max_length=12)
    path=models.CharField(max_length=500)
    status_code=models.PositiveSmallIntegerField(default=200)
    content_type=models.CharField(max_length=120,blank=True)
    response_body=models.BinaryField(blank=True,default=bytes)
    expires_at=models.DateTimeField()
    class Meta:
        constraints=[models.UniqueConstraint(fields=['tenant','user_id','key'],name='uniq_tenant_user_idem_key',nulls_distinct=False)]
        indexes=[models.Index(fields=['expires_at'],name='lf_idem_expiry_idx'),models.Index(fields=['tenant','key'],name='lf_idem_tenant_key_idx')]
