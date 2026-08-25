import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

def backfill_cycle_status(apps,schema_editor):
    Cycle=apps.get_model('platform_core','DuesCycle');Assessment=apps.get_model('platform_core','DuesAssessment')
    for c in Cycle.objects.all().iterator():
        c.status='active' if c.is_open else 'closed';c.currency='PHP';c.save(update_fields=['status','currency'])
    for a in Assessment.objects.select_related('cycle').all().iterator():
        a.currency=a.cycle.currency or 'PHP';a.save(update_fields=['currency'])

class Migration(migrations.Migration):
 dependencies=[('platform_core','0006_meeting_workflow_completion'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
 operations=[
  migrations.AlterField(model_name='duescycle',name='is_open',field=models.BooleanField(default=False)),
  migrations.AddField(model_name='duescycle',name='currency',field=models.CharField(default='PHP',max_length=3)),
  migrations.AddField(model_name='duescycle',name='status',field=models.CharField(choices=[('draft','draft'),('active','active'),('closed','closed')],default='draft',max_length=20)),
  migrations.AddField(model_name='duesassessment',name='adjustment_amount',field=models.DecimalField(decimal_places=2,default=0,max_digits=10)),
  migrations.AddField(model_name='duesassessment',name='currency',field=models.CharField(default='PHP',max_length=3)),
  migrations.AddField(model_name='payment',name='is_reversed',field=models.BooleanField(default=False)),
  migrations.AddField(model_name='payment',name='reversed_at',field=models.DateTimeField(blank=True,null=True)),
  migrations.AddField(model_name='payment',name='reversal_reason',field=models.TextField(blank=True)),
  migrations.AddField(model_name='payment',name='reversed_by',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='payments_reversed',to=settings.AUTH_USER_MODEL)),
  migrations.CreateModel(name='ExpenseCategory',fields=[('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('name',models.CharField(max_length=100)),('is_active',models.BooleanField(default=True)),('requires_approval',models.BooleanField(default=False)),('tenant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='expense_categories',to='platform_core.tenant'))]),
  migrations.AddConstraint(model_name='expensecategory',constraint=models.UniqueConstraint(fields=('tenant','name'),name='uniq_tenant_expense_category')),
  migrations.AddField(model_name='expense',name='approval_reason',field=models.TextField(blank=True)),
  migrations.AddField(model_name='expense',name='category_definition',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='expenses',to='platform_core.expensecategory')),
  migrations.AddField(model_name='expense',name='attachment_document',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='expense_attachments',to='platform_core.document')),
  migrations.CreateModel(name='PaymentAllocation',fields=[('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('amount',models.DecimalField(decimal_places=2,max_digits=12)),('assessment',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='payment_allocations',to='platform_core.duesassessment')),('payment',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='allocations',to='platform_core.payment')),('tenant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='payment_allocations',to='platform_core.tenant'))]),
  migrations.AddConstraint(model_name='paymentallocation',constraint=models.UniqueConstraint(fields=('payment','assessment'),name='uniq_payment_assessment_allocation')),
  migrations.CreateModel(name='FinancialAdjustment',fields=[('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),('kind',models.CharField(choices=[('waiver','waiver'),('charge','charge'),('credit','credit'),('payment_reversal','payment_reversal')],max_length=30)),('amount',models.DecimalField(decimal_places=2,max_digits=12)),('reason',models.TextField()),('assessment',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='adjustments',to='platform_core.duesassessment')),('created_by',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='financial_adjustments_created',to=settings.AUTH_USER_MODEL)),('related_payment',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name='reversal_adjustments',to='platform_core.payment')),('tenant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='financial_adjustments',to='platform_core.tenant'))]),
  migrations.AddConstraint(model_name='duescycle',constraint=models.CheckConstraint(condition=models.Q(period_end__gte=models.F('period_start')),name='dues_cycle_period_valid')),
  migrations.AddConstraint(model_name='duescycle',constraint=models.CheckConstraint(condition=models.Q(due_on__gte=models.F('period_start')),name='dues_cycle_due_valid')),
  migrations.AddConstraint(model_name='duesassessment',constraint=models.CheckConstraint(condition=models.Q(amount__gte=0),name='dues_assessment_amount_nonnegative')),
  migrations.AddConstraint(model_name='duesassessment',constraint=models.CheckConstraint(condition=models.Q(late_fee__gte=0),name='dues_assessment_late_fee_nonnegative')),
  migrations.AddConstraint(model_name='duesassessment',constraint=models.CheckConstraint(condition=models.Q(waived_amount__gte=0),name='dues_assessment_waived_nonnegative')),
  migrations.AddConstraint(model_name='duesassessment',constraint=models.CheckConstraint(condition=models.Q(paid_amount__gte=0),name='dues_assessment_paid_nonnegative')),
  migrations.AddConstraint(model_name='payment',constraint=models.CheckConstraint(condition=models.Q(amount__gt=0),name='payment_amount_positive')),
  migrations.AddConstraint(model_name='paymentallocation',constraint=models.CheckConstraint(condition=models.Q(amount__gt=0),name='payment_allocation_amount_positive')),
  migrations.AddConstraint(model_name='financialadjustment',constraint=models.CheckConstraint(condition=models.Q(amount__gt=0),name='financial_adjustment_amount_positive')),
  migrations.AddConstraint(model_name='expense',constraint=models.CheckConstraint(condition=models.Q(amount__gt=0),name='expense_amount_positive')),
  migrations.RunPython(backfill_cycle_status,migrations.RunPython.noop),
 ]
