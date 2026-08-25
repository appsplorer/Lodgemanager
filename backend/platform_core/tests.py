import json
import tempfile
from unittest import skipUnless
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase,override_settings
from .models import Tenant,TenantMembership,Member,Expense,CustomRoleDefinition


@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class PlatformMediaRegressionTests(TestCase):
 @classmethod
 def setUpClass(cls):
  cls._media_dir=tempfile.TemporaryDirectory()
  cls._storage_override=override_settings(STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage','OPTIONS':{'location':cls._media_dir.name}},'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}})
  cls._storage_override.enable();super().setUpClass()
 @classmethod
 def tearDownClass(cls):
  super().tearDownClass();cls._storage_override.disable();cls._media_dir.cleanup()
 def setUp(self):
  U=get_user_model();self.admin=U.objects.create_superuser(username='media@example.test',email='media@example.test',password='Media-test-pass-123!');self.client.force_login(self.admin)
  from django.utils import timezone
  session=self.client.session;session['mfa_verified_at']=timezone.now().isoformat();session.save()
 def upload(self,**fields):
  payload=b'\x89PNG\r\n\x1a\nvalid-test-body'
  data={'title':'Portrait','visibility':'private','alt_text':'Member portrait','file':SimpleUploadedFile('portrait.png',payload,content_type='image/png'),**fields}
  return self.client.post('/api/platform/media',data=data)
 def test_private_asset_has_security_metadata_and_authorized_preview(self):
  response=self.upload();self.assertEqual(response.status_code,201);row=response.json()
  self.assertEqual(row['original_name'],'portrait.png');self.assertEqual(row['file_size'],23);self.assertEqual(len(row['sha256']),64);self.assertEqual(row['visibility'],'private')
  self.assertEqual(self.client.get(f"/api/platform/media/{row['id']}/download").status_code,200)
  self.client.logout();self.assertEqual(self.client.get(f"/api/public/media/{row['id']}").status_code,404)
 def test_public_asset_requires_alt_text_and_clean_scan(self):
  missing=self.upload(visibility='public',alt_text='');self.assertEqual(missing.status_code,400)
  unavailable=self.upload(visibility='public');self.assertEqual(unavailable.status_code,409)
  with patch('platform_core.services.file_security._clamav',return_value='clean'):
   clean=self.upload(visibility='public')
  self.assertEqual(clean.status_code,201);self.client.logout();self.assertEqual(self.client.get(f"/api/public/media/{clean.json()['id']}").status_code,200)

@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class TenantSafetyTests(TestCase):
 def setUp(self):
  U=get_user_model();self.user=U.objects.create_user(username='owner@example.test',email='owner@example.test',password='Strong-test-pass-123!')
  self.a=Tenant.objects.create(name='Alpha Lodge',slug='alpha');self.b=Tenant.objects.create(name='Beta Lodge',slug='beta')
  TenantMembership.objects.create(user=self.user,tenant=self.a,role='owner');TenantMembership.objects.create(user=self.user,tenant=self.b,role='owner')
  self.client.force_login(self.user)
 def hdr(self,tenant):return {'HTTP_X_LODGE_ID':str(tenant.id)}
 def test_member_crud_is_tenant_isolated(self):
  r=self.client.post('/api/members',data=json.dumps({'first_name':'Ada','last_name':'Mason','email':'ada@example.test'}),content_type='application/json',**self.hdr(self.a));self.assertEqual(r.status_code,201)
  self.assertEqual(Member.objects.filter(tenant=self.a).count(),1);self.assertEqual(Member.objects.filter(tenant=self.b).count(),0)
  r=self.client.get('/api/members',**self.hdr(self.b));self.assertEqual(r.status_code,200);self.assertEqual(r.json()['count'],0)
 def test_offline_stale_edit_returns_conflict(self):
  m=Member.objects.create(tenant=self.a,first_name='Grace',last_name='Stone');base=m.updated_at.isoformat();m.notes='server change';m.save()
  r=self.client.patch(f'/api/members/{m.id}',data=json.dumps({'notes':'offline change'}),content_type='application/json',HTTP_X_LODGEFLOW_BASE_UPDATED_AT=base,**self.hdr(self.a));self.assertEqual(r.status_code,409);self.assertEqual(r.json()['error'],'offline_conflict')
 def test_idempotency_prevents_duplicate_expense(self):
  body=json.dumps({'category':'Supplies','description':'Paper','amount':'12.00','currency':'PHP','incurred_on':'2026-08-23'})
  h={**self.hdr(self.a),'HTTP_IDEMPOTENCY_KEY':'same-expense-key'}
  r1=self.client.post('/api/expenses',data=body,content_type='application/json',**h);r2=self.client.post('/api/expenses',data=body,content_type='application/json',**h)
  self.assertEqual(r1.status_code,201);self.assertEqual(r2.status_code,201);self.assertEqual(Expense.objects.filter(tenant=self.a).count(),1);self.assertEqual(r1.content,r2.content)
 def test_workspace_bootstrap_never_exposes_other_tenant_as_current(self):
  r=self.client.get('/api/workspace/bootstrap',**self.hdr(self.a));self.assertEqual(r.status_code,200);self.assertEqual(r.json()['tenant']['id'],str(self.a.id))

class IdentityRbacRegressionTests(TestCase):
 def setUp(self):
  U=get_user_model()
  self.owner=U.objects.create_user(username='owner2@example.test',email='owner2@example.test',password='Strong-test-pass-123!')
  self.member_user=U.objects.create_user(username='custom@example.test',email='custom@example.test',password='Strong-test-pass-123!')
  self.a=Tenant.objects.create(name='Gamma Lodge',slug='gamma')
  self.b=Tenant.objects.create(name='Delta Lodge',slug='delta')
  TenantMembership.objects.create(user=self.owner,tenant=self.a,role='owner')
  TenantMembership.objects.create(user=self.owner,tenant=self.b,role='owner')
  self.client.force_login(self.owner)
 def hdr(self,tenant=None):return {'HTTP_X_LODGE_ID':str((tenant or self.a).id)}
 def test_custom_role_assignment_is_tenant_scoped_and_updates_dynamically(self):
  role_resp=self.client.post('/api/settings/custom-roles',data=json.dumps({'name':'Records clerk','permissions':['members.view'],'approval_requirements':{}}),content_type='application/json',**self.hdr())
  self.assertEqual(role_resp.status_code,201); role_id=role_resp.json()['id']
  assign=self.client.post('/api/settings/users',data=json.dumps({'user_id':self.member_user.id,'role':'custom','custom_role_id':role_id,'mfa_required':False,'is_active':True}),content_type='application/json',**self.hdr())
  self.assertIn(assign.status_code,(200,201))
  membership=TenantMembership.objects.get(user=self.member_user,tenant=self.a)
  self.assertEqual(str(membership.custom_role_id),role_id); self.assertEqual(membership.custom_permissions,[])
  self.client.force_login(self.member_user)
  self.assertEqual(self.client.get('/api/members',**self.hdr()).status_code,200)
  self.client.force_login(self.owner)
  changed=self.client.patch(f'/api/settings/custom-roles/{role_id}',data=json.dumps({'permissions':['dashboard.view']}),content_type='application/json',**self.hdr())
  self.assertEqual(changed.status_code,200)
  self.client.force_login(self.member_user)
  self.assertEqual(self.client.get('/api/members',**self.hdr()).status_code,403)
 def test_cross_tenant_custom_role_assignment_is_rejected(self):
  foreign=CustomRoleDefinition.objects.create(tenant=self.b,name='Foreign role',permissions=['members.view'])
  r=self.client.post('/api/settings/users',data=json.dumps({'user_id':self.member_user.id,'role':'custom','custom_role_id':str(foreign.id)}),content_type='application/json',**self.hdr(self.a))
  self.assertEqual(r.status_code,400); self.assertEqual(r.json()['error'],'invalid_or_cross_tenant_custom_role')
 def test_suspended_tenant_is_not_resolved_as_active_workspace(self):
  self.a.is_active=False;self.a.save(update_fields=['is_active','updated_at'])
  r=self.client.get('/api/members',**self.hdr(self.a))
  self.assertEqual(r.status_code,403)
 def test_cross_tenant_object_existence_is_not_leaked(self):
  outsider=Member.objects.create(tenant=self.b,first_name='Hidden',last_name='Member')
  # Remove the owner's Delta membership so the request cannot legitimately resolve that tenant.
  TenantMembership.objects.filter(user=self.owner,tenant=self.b).delete()
  r=self.client.get(f'/api/members/{outsider.id}',**self.hdr(self.a))
  self.assertEqual(r.status_code,404)
 def test_invitation_password_token_is_single_use(self):
  from .services.account_tokens import issue_account_token
  invited=get_user_model().objects.create(username='invitee@example.test',email='invitee@example.test',is_active=False)
  invited.set_unusable_password(); invited.save(update_fields=['password'])
  membership=TenantMembership.objects.create(user=invited,tenant=self.a,role='viewer',is_active=True)
  _,token=issue_account_token(user=invited,purpose='invitation',tenant=self.a,issued_by=self.owner)
  payload=json.dumps({'token':token,'password':'Invitation-Strong-Pass-123!'})
  first=self.client.post('/api/auth/invitation',data=payload,content_type='application/json')
  self.assertEqual(first.status_code,200,first.content);invited.refresh_from_db();membership.refresh_from_db();self.assertTrue(invited.is_active);self.assertTrue(membership.is_active)
  self.client.logout()
  second=self.client.post('/api/auth/invitation',data=payload,content_type='application/json')
  self.assertEqual(second.status_code,400);self.assertEqual(second.json()['error'],'token_already_used')
 def test_step_up_requires_valid_password_and_refreshes_recent_auth(self):
  bad=self.client.post('/api/auth/step-up',data=json.dumps({'password':'not-the-password'}),content_type='application/json')
  self.assertEqual(bad.status_code,401);self.assertEqual(bad.json()['error'],'invalid_credentials')
  good=self.client.post('/api/auth/step-up',data=json.dumps({'password':'Strong-test-pass-123!'}),content_type='application/json')
  self.assertEqual(good.status_code,200);self.assertTrue(good.json()['ok']);self.assertFalse(good.json()['mfa_used'])
  session=self.client.session;self.assertTrue(session.get('password_verified_at'))

@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class OperationalObservabilityRegressionTests(TestCase):
 def setUp(self):
  U=get_user_model();self.admin=U.objects.create_superuser(username='ops@example.test',email='ops@example.test',password='Strong-ops-pass-123!');self.client.force_login(self.admin)
  from django.utils import timezone
  session=self.client.session;session['mfa_verified_at']=timezone.now().isoformat();session.save()
 def test_security_alert_can_be_acknowledged_and_is_auditable(self):
  from .models import SecurityAlert,AuditEvent
  alert=SecurityAlert.objects.create(kind='test_high_risk',severity='high',message='Synthetic QA alert')
  r=self.client.post(f'/api/platform/security-alerts/{alert.id}/acknowledge',data='{}',content_type='application/json')
  self.assertEqual(r.status_code,200);alert.refresh_from_db();self.assertIsNotNone(alert.acknowledged_at);self.assertEqual(alert.acknowledged_by_id,self.admin.id)
  self.assertTrue(AuditEvent.objects.filter(action='platform.security_alert.acknowledged',object_id=str(alert.id)).exists())
 def test_repeated_job_failure_monitor_is_deduplicated(self):
  from .models import SecurityAlert,SystemJob
  from .tasks import monitor_operational_health
  for i in range(3):SystemJob.objects.create(kind=f'qa-{i}',status='failed')
  first=monitor_operational_health();second=monitor_operational_health()
  self.assertEqual(len(first['raised']),1);self.assertEqual(len(second['raised']),0)
  self.assertEqual(SecurityAlert.objects.filter(kind='repeated_job_failures',acknowledged_at__isnull=True).count(),1)


@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class MeetingWorkflowRegressionTests(TestCase):
 def setUp(self):
  from django.utils import timezone
  U=get_user_model();self.user=U.objects.create_user(username='secretary@example.test',email='secretary@example.test',password='Meeting-pass-123!')
  self.tenant=Tenant.objects.create(name='Meeting Lodge',slug='meeting-lodge');TenantMembership.objects.create(user=self.user,tenant=self.tenant,role='owner');self.client.force_login(self.user);self.h={'HTTP_X_LODGE_ID':str(self.tenant.id)}
  self.member=Member.objects.create(tenant=self.tenant,first_name='Meeting',last_name='Member')
  self.meeting=__import__('platform_core.models',fromlist=['Meeting']).Meeting.objects.create(tenant=self.tenant,title='Stated',starts_at=timezone.now()+timezone.timedelta(days=1),recurrence_rule='FREQ=WEEKLY;INTERVAL=1')
 def test_agenda_reordering_is_server_persisted(self):
  a=self.client.post(f'/api/meetings/{self.meeting.id}/agenda',data=json.dumps({'title':'Opening','kind':'standard'}),content_type='application/json',**self.h).json()
  b=self.client.post(f'/api/meetings/{self.meeting.id}/agenda',data=json.dumps({'title':'Business','kind':'custom'}),content_type='application/json',**self.h).json()
  r=self.client.post(f'/api/meetings/{self.meeting.id}/agenda/reorder',data=json.dumps({'ids':[b['id'],a['id']]}),content_type='application/json',**self.h);self.assertEqual(r.status_code,200);self.assertEqual(r.json()['results'][0]['title'],'Business')
 def test_recurring_generation_is_idempotent(self):
  first=self.client.post(f'/api/meetings/{self.meeting.id}/generate-occurrences',data=json.dumps({'horizon_days':30}),content_type='application/json',**self.h).json();second=self.client.post(f'/api/meetings/{self.meeting.id}/generate-occurrences',data=json.dumps({'horizon_days':30}),content_type='application/json',**self.h).json()
  self.assertGreater(first['created'],0);self.assertEqual(second['created'],0);self.assertGreaterEqual(second['existing'],first['created'])
 def test_locked_minutes_require_controlled_reopen_reason(self):
  from platform_core.models import MinuteVersion
  minute=MinuteVersion.objects.create(tenant=self.tenant,meeting=self.meeting,version=1,state='locked',body='Approved record',changed_by=self.user,locked_by=self.user)
  edit=self.client.post(f'/api/meetings/{self.meeting.id}/minutes',data=json.dumps({'body':'Silent edit'}),content_type='application/json',**self.h);self.assertEqual(edit.status_code,409)
  bad=self.client.post(f'/api/meetings/{self.meeting.id}/minutes/1/reopen',data=json.dumps({'reason':'x'}),content_type='application/json',**self.h);self.assertEqual(bad.status_code,400)
  good=self.client.post(f'/api/meetings/{self.meeting.id}/minutes/1/reopen',data=json.dumps({'reason':'Correct a recorded motion'}),content_type='application/json',**self.h);self.assertEqual(good.status_code,201);self.assertEqual(good.json()['version'],2);self.assertEqual(good.json()['state'],'draft')

@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class FinanceWorkflowRegressionTests(TestCase):
 def setUp(self):
  from datetime import date,timedelta
  from decimal import Decimal
  from .models import DuesCycle
  U=get_user_model();self.user=U.objects.create_user(username='treasurer@example.test',email='treasurer@example.test',password='Finance-pass-123!')
  self.tenant=Tenant.objects.create(name='Finance Lodge',slug='finance-lodge',settings={'default_currency':'GBP','finance':{'payment_methods':['cash','bank_transfer','cheque']}});TenantMembership.objects.create(user=self.user,tenant=self.tenant,role='owner');self.client.force_login(self.user);self.h={'HTTP_X_LODGE_ID':str(self.tenant.id)}
  self.member=Member.objects.create(tenant=self.tenant,first_name='Paying',last_name='Member',status='active',joined_on=date.today()-timedelta(days=365))
  self.cycle=DuesCycle.objects.create(tenant=self.tenant,name='Annual dues',period_start=date.today()-timedelta(days=365),period_end=date.today()+timedelta(days=1),due_on=date.today()-timedelta(days=20),standard_amount=Decimal('100.00'),late_fee=Decimal('5.00'),currency='GBP',status='active',is_open=True)
 def _generate(self):
  r=self.client.post(f'/api/dues/cycles/{self.cycle.id}/generate',data='{}',content_type='application/json',**self.h);self.assertEqual(r.status_code,200);return r
 def test_generation_is_idempotent_and_cycle_terms_lock_after_generation(self):
  from .models import DuesAssessment
  first=self._generate();second=self._generate();self.assertEqual(first.json()['created'],1);self.assertEqual(second.json()['created'],0);self.assertEqual(second.json()['existing'],1);self.assertEqual(DuesAssessment.objects.filter(tenant=self.tenant,cycle=self.cycle,member=self.member).count(),1)
  locked=self.client.patch(f'/api/dues/cycles/{self.cycle.id}',data=json.dumps({'standard_amount':'125.00'}),content_type='application/json',**self.h);self.assertEqual(locked.status_code,409)
 def test_waiver_requires_reason_and_creates_immutable_adjustment_evidence(self):
  from .models import DuesAssessment,FinancialAdjustment
  self._generate();a=DuesAssessment.objects.get(tenant=self.tenant,member=self.member,cycle=self.cycle)
  bad=self.client.post(f'/api/dues/assessments/{a.id}/waive',data=json.dumps({'amount':'10.00'}),content_type='application/json',**self.h);self.assertEqual(bad.status_code,400)
  good=self.client.post(f'/api/dues/assessments/{a.id}/waive',data=json.dumps({'amount':'10.00','reason':'Approved hardship waiver'}),content_type='application/json',**self.h);self.assertEqual(good.status_code,200);self.assertTrue(FinancialAdjustment.objects.filter(tenant=self.tenant,assessment=a,kind='waiver',amount='10.00',created_by=self.user).exists())
 def test_manual_payment_allocates_once_uses_configured_method_and_can_be_reversed(self):
  from .models import DuesAssessment,Payment,PaymentAllocation,FinancialAdjustment
  self._generate();a=DuesAssessment.objects.get(tenant=self.tenant,member=self.member,cycle=self.cycle)
  wrong=self.client.post('/api/dues/record-payment',data=json.dumps({'assessment_id':str(a.id),'amount':'25.00','currency':'USD','method':'cash'}),content_type='application/json',**self.h);self.assertEqual(wrong.status_code,409)
  disabled=self.client.post('/api/dues/record-payment',data=json.dumps({'assessment_id':str(a.id),'amount':'25.00','currency':'GBP','method':'crypto'}),content_type='application/json',**self.h);self.assertEqual(disabled.status_code,400)
  paid=self.client.post('/api/dues/record-payment',data=json.dumps({'assessment_id':str(a.id),'amount':'25.00','currency':'GBP','method':'bank_transfer','provider_reference':'BANK-1'}),content_type='application/json',HTTP_IDEMPOTENCY_KEY='finance-manual-payment-1',**self.h);self.assertEqual(paid.status_code,201);pid=paid.json()['payment']['id']
  self.assertEqual(Payment.objects.filter(pk=pid,tenant=self.tenant).count(),1);self.assertEqual(PaymentAllocation.objects.filter(payment_id=pid,assessment=a,amount='25.00').count(),1);self.assertTrue(Payment.objects.get(pk=pid).receipt_number)
  rev=self.client.post(f'/api/dues/payments/{pid}/reverse',data=json.dumps({'reason':'Bank transfer was returned'}),content_type='application/json',**self.h);self.assertEqual(rev.status_code,200);p=Payment.objects.get(pk=pid);self.assertTrue(p.is_reversed);a.refresh_from_db();self.assertEqual(str(a.paid_amount),'0.00');self.assertTrue(FinancialAdjustment.objects.filter(related_payment=p,kind='payment_reversal').exists())
  again=self.client.post(f'/api/dues/payments/{pid}/reverse',data=json.dumps({'reason':'Duplicate reversal attempt'}),content_type='application/json',**self.h);self.assertEqual(again.status_code,409)
 def test_arrears_report_has_aging_currency_totals_and_member_drilldown_identity(self):
  self._generate();r=self.client.get('/api/dues/arrears',**self.h);self.assertEqual(r.status_code,200);data=r.json();self.assertEqual(data['count'],1);self.assertEqual(data['results'][0]['member_id'],str(self.member.id));self.assertEqual(data['results'][0]['currency'],'GBP');self.assertIn(data['results'][0]['aging_bucket'],{'1-30','31-60','61-90','90+'});self.assertEqual(data['totals_by_currency']['GBP'],data['results'][0]['outstanding'])
 def test_expense_category_attachment_and_approval_become_immutable_after_approval(self):
  from .models import Document,Expense
  doc=Document.objects.create(tenant=self.tenant,title='Supplier receipt',file_path='private/receipt.pdf')
  cat=self.client.post('/api/expenses/categories',data=json.dumps({'name':'Supplies','requires_approval':True}),content_type='application/json',**self.h);self.assertEqual(cat.status_code,201)
  expense=self.client.post('/api/expenses',data=json.dumps({'category_definition':cat.json()['id'],'description':'Paper stock','amount':'15.25','currency':'GBP','incurred_on':self.cycle.due_on.isoformat(),'vendor':'Stationer','attachment_document':str(doc.id)}),content_type='application/json',**self.h);self.assertEqual(expense.status_code,201);eid=expense.json()['id'];self.assertEqual(expense.json()['approval_status'],'pending')
  approved=self.client.post(f'/api/expenses/{eid}/approve',data=json.dumps({'decision':'approved','reason':'Invoice and receipt checked'}),content_type='application/json',**self.h);self.assertEqual(approved.status_code,200);self.assertEqual(approved.json()['approval_status'],'approved')
  edit=self.client.patch(f'/api/expenses/{eid}',data=json.dumps({'amount':'1.00'}),content_type='application/json',**self.h);self.assertEqual(edit.status_code,409);self.assertEqual(Expense.objects.get(pk=eid).attachment_document_id,doc.id)

 def test_member_statement_reconciles_adjustments_waivers_payments_and_late_fee(self):
  from .models import DuesAssessment
  self._generate();a=DuesAssessment.objects.get(tenant=self.tenant,member=self.member,cycle=self.cycle)
  late=self.client.post(f'/api/dues/cycles/{self.cycle.id}/late-fees',data='{}',content_type='application/json',**self.h);self.assertEqual(late.status_code,200)
  self.client.post(f'/api/dues/assessments/{a.id}/waive',data=json.dumps({'amount':'10.00','reason':'Approved ten pound waiver'}),content_type='application/json',**self.h)
  self.client.post(f'/api/dues/assessments/{a.id}/adjust',data=json.dumps({'kind':'charge','amount':'5.00','reason':'Replacement card charge'}),content_type='application/json',**self.h)
  self.client.post('/api/dues/record-payment',data=json.dumps({'assessment_id':str(a.id),'amount':'20.00','currency':'GBP','method':'cash'}),content_type='application/json',HTTP_IDEMPOTENCY_KEY='statement-payment-1',**self.h)
  r=self.client.get(f'/api/members/{self.member.id}/statement?currency=GBP',**self.h);self.assertEqual(r.status_code,200);data=r.json();self.assertEqual(data['balance'],'80.00');self.assertEqual(data['balances_by_currency']['GBP'],'80.00');self.assertGreaterEqual(len(data['adjustments']),2);self.assertEqual(len(data['payments']),1)
 def test_finance_export_preserves_decimal_and_currency_metadata(self):
  from .models import DuesAssessment
  self._generate();a=DuesAssessment.objects.get(tenant=self.tenant,member=self.member,cycle=self.cycle)
  self.client.post('/api/dues/record-payment',data=json.dumps({'assessment_id':str(a.id),'amount':'10.25','currency':'GBP','method':'cash'}),content_type='application/json',HTTP_IDEMPOTENCY_KEY='export-payment-1',**self.h)
  r=self.client.get('/api/exports/finance?format=csv',**self.h);self.assertEqual(r.status_code,200);body=r.content.decode();self.assertIn('10.25',body);self.assertIn('Default currency,GBP',body);self.assertIn('receipt_number',body);self.assertIn('is_reversed',body)

@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class FinanceReceiptConcurrencyTests(__import__('django.test',fromlist=['TransactionTestCase']).TransactionTestCase):
 reset_sequences=True
 def setUp(self):
  from datetime import date,timedelta
  from decimal import Decimal
  from .models import DuesCycle,DuesAssessment
  U=get_user_model();self.user=U.objects.create_user(username='race-treasurer@example.test',email='race-treasurer@example.test',password='Finance-race-pass-123!')
  self.tenant=Tenant.objects.create(name='Receipt Race Lodge',slug='receipt-race',settings={'default_currency':'GBP','finance':{'payment_methods':['cash']}});TenantMembership.objects.create(user=self.user,tenant=self.tenant,role='owner')
  cycle=DuesCycle.objects.create(tenant=self.tenant,name='Race cycle',period_start=date.today()-timedelta(days=30),period_end=date.today()+timedelta(days=30),due_on=date.today()+timedelta(days=10),standard_amount=Decimal('100.00'),currency='GBP',status='active',is_open=True)
  self.assessments=[]
  for i in range(2):
   m=Member.objects.create(tenant=self.tenant,first_name='Race',last_name=f'Member{i}',status='active');self.assessments.append(DuesAssessment.objects.create(tenant=self.tenant,member=m,cycle=cycle,amount=Decimal('100.00'),currency='GBP'))
 @skipUnless(connection.vendor=='postgresql','PostgreSQL row-lock semantics are not available in SQLite')
 def test_concurrent_manual_payments_receive_distinct_tenant_receipts(self):
  import threading
  from django.test import Client
  from .models import Payment
  barrier=threading.Barrier(2);results=[];errors=[];lock=threading.Lock()
  def worker(assessment,index):
   try:
    c=Client();c.force_login(self.user);barrier.wait(timeout=10)
    r=c.post('/api/dues/record-payment',data=json.dumps({'assessment_id':str(assessment.id),'amount':'10.00','currency':'GBP','method':'cash'}),content_type='application/json',HTTP_X_LODGE_ID=str(self.tenant.id),HTTP_IDEMPOTENCY_KEY=f'race-payment-{index}')
    with lock:results.append((r.status_code,r.json() if r.headers.get('Content-Type','').startswith('application/json') else {}))
   except Exception as exc:
    with lock:errors.append(exc)
  threads=[threading.Thread(target=worker,args=(assessment,i)) for i,assessment in enumerate(self.assessments)];[t.start() for t in threads];[t.join(timeout=20) for t in threads]
  self.assertFalse(errors);self.assertEqual(sorted(x[0] for x in results),[201,201]);receipts=list(Payment.objects.filter(tenant=self.tenant).values_list('receipt_number',flat=True));self.assertEqual(len(receipts),2);self.assertEqual(len(set(receipts)),2)

@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class ReportEngineRegressionTests(TestCase):
 def setUp(self):
  from datetime import date
  U=get_user_model();self.user=U.objects.create_user(username='report-owner@example.test',email='report-owner@example.test',password='Report-Strong-Pass-123!')
  self.viewer=U.objects.create_user(username='report-viewer@example.test',email='report-viewer@example.test',password='Report-Viewer-Pass-123!')
  self.tenant=Tenant.objects.create(name='Reporting Lodge',slug='reporting-lodge',lodge_number='77',timezone='Europe/London',settings={'reports':{'page_size':'A4','classification':'Confidential','async_threshold_rows':5000}});TenantMembership.objects.create(user=self.user,tenant=self.tenant,role='owner')
  TenantMembership.objects.create(user=self.viewer,tenant=self.tenant,role='viewer')
  self.other=Tenant.objects.create(name='Other Reporting Lodge',slug='other-reporting');Member.objects.create(tenant=self.other,first_name='Hidden',last_name='Person',email='hidden@example.test',status='active')
  Member.objects.create(tenant=self.tenant,first_name='Alice',last_name='Member',email='alice@example.test',status='active',joined_on=date(2026,1,1))
  Member.objects.create(tenant=self.tenant,first_name='Bob',last_name='Member',email='bob@example.test',status='inactive',joined_on=date(2025,5,1))
  self.client.force_login(self.user);self.h={'HTTP_X_LODGE_ID':str(self.tenant.id)}
 def test_catalog_preview_is_tenant_scoped_and_discloses_metadata(self):
  c=self.client.get('/api/reports/catalog',**self.h);self.assertEqual(c.status_code,200);ids={x['id'] for x in c.json()['results']};self.assertIn('R-001',ids);self.assertIn('R-070',ids);self.assertNotIn('R-080',ids)
  p=self.client.get('/api/reports/preview/R-010?status=active',**self.h);self.assertEqual(p.status_code,200);body=p.json();self.assertEqual(body['report_id'],'R-010');self.assertEqual(body['total_rows'],1);self.assertEqual(body['metadata']['tenant'],'Reporting Lodge');self.assertEqual(body['filters']['status'],'active');self.assertNotIn('Hidden',json.dumps(body))
 def test_inline_xlsx_generation_persists_hash_and_private_download(self):
  from .models import GeneratedReport
  r=self.client.get('/api/reports/generate/R-010?format=xlsx',**self.h);self.assertEqual(r.status_code,200);self.assertIn('private',r['Cache-Control']);self.assertIn('no-store',r['Cache-Control']);self.assertTrue(r['X-Report-SHA256']);obj=GeneratedReport.objects.filter(tenant=self.tenant,report_type='R-010',status='completed').latest('created_at');self.assertEqual(obj.sha256,r['X-Report-SHA256']);d=self.client.get(f'/api/reports/generated/{obj.id}/download',**self.h);self.assertEqual(d.status_code,200);self.assertIn('private',d['Cache-Control']);self.assertIn('no-store',d['Cache-Control'])
 def test_view_permission_does_not_grant_generation_or_download(self):
  from .models import GeneratedReport
  self.client.force_login(self.viewer)
  self.assertEqual(self.client.get('/api/reports/preview/R-010',**self.h).status_code,200)
  denied=self.client.get('/api/reports/generate/R-010?format=pdf',**self.h);self.assertEqual(denied.status_code,403);self.assertEqual(denied.json()['permission'],'reports.export')
  self.client.force_login(self.user);created=self.client.get('/api/reports/generate/R-010?format=pdf',**self.h);self.assertEqual(created.status_code,200);report=GeneratedReport.objects.latest('created_at')
  self.client.force_login(self.viewer);download=self.client.get(f'/api/reports/generated/{report.id}/download',**self.h);self.assertEqual(download.status_code,403);self.assertEqual(download.json()['permission'],'reports.export')
 def test_background_generation_is_persisted_before_enqueue(self):
  from unittest.mock import patch
  from .models import GeneratedReport
  with patch('platform_core.tasks.generate_report_async.delay') as delay:
   delay.return_value.id='report-task-1';r=self.client.get('/api/reports/generate/R-010?format=xlsx&async=1',**self.h)
  self.assertEqual(r.status_code,202);obj=GeneratedReport.objects.get(pk=r.json()['id']);self.assertEqual(obj.status,'queued');self.assertEqual(obj.job_id,'report-task-1');self.assertEqual(obj.tenant,self.tenant)
 def test_schedule_rejects_invalid_cron_and_accepts_valid_cron(self):
  bad=self.client.post('/api/reports/schedules',data=json.dumps({'report_type':'R-001','format':'pdf','schedule':'not cron','recipients':['report-owner@example.test']}),content_type='application/json',**self.h);self.assertEqual(bad.status_code,400)
  good=self.client.post('/api/reports/schedules',data=json.dumps({'report_type':'R-001','format':'pdf','schedule':'0 8 1 * *','recipients':['report-owner@example.test'],'attachments':['R-050','R-051']}),content_type='application/json',**self.h);self.assertEqual(good.status_code,201);self.assertEqual(good.json()['report_type'],'R-001');self.assertEqual(good.json()['attachments'],['R-050','R-051']);self.assertTrue(good.json()['next_run_at'])
 def test_sensitive_report_requires_governed_approval_by_default(self):
  r=self.client.get('/api/reports/generate/R-070?format=pdf',**self.h);self.assertEqual(r.status_code,428);self.assertEqual(r.json()['error'],'report_approval_required');self.assertEqual(r.json()['export_type'],'report:R-070')

@override_settings(ALLOWED_HOSTS=['testserver','localhost'])
class AuditBillingRegressionTests(TestCase):
 def setUp(self):
  from .models import PlatformRoleAssignment
  U=get_user_model();self.billing=U.objects.create_user(username='billing-admin@example.test',email='billing-admin@example.test',password='Billing-Strong-Pass-123!')
  self.owner=U.objects.create_user(username='audit-owner@example.test',email='audit-owner@example.test',password='Audit-Strong-Pass-123!')
  self.approver=U.objects.create_user(username='audit-approver@example.test',email='audit-approver@example.test',password='Audit-Approver-Pass-123!')
  self.tenant=Tenant.objects.create(name='Compliance Lodge',slug='compliance-lodge')
  TenantMembership.objects.create(user=self.owner,tenant=self.tenant,role='owner');TenantMembership.objects.create(user=self.approver,tenant=self.tenant,role='owner')
  PlatformRoleAssignment.objects.create(user=self.billing,role='billing_admin')
  self.h={'HTTP_X_LODGE_ID':str(self.tenant.id)}
 def _step_up(self,user):
  self.client.force_login(user);session=self.client.session
  from django.utils import timezone
  now=timezone.now().isoformat();session['mfa_verified_at']=now;session['password_verified_at']=now;session.save()
 def _mfa_login(self,user):
  self.client.force_login(user);session=self.client.session
  from django.utils import timezone
  session['mfa_verified_at']=(timezone.now()-timezone.timedelta(minutes=11)).isoformat();session.save()
 def test_platform_report_catalog_and_generation_follow_role_permissions(self):
  self._mfa_login(self.billing)
  catalog=self.client.get('/api/platform/reports/catalog');self.assertEqual(catalog.status_code,200);ids={x['id'] for x in catalog.json()['results']};self.assertIn('R-080',ids);self.assertIn('R-081',ids);self.assertNotIn('R-082',ids)
  generated=self.client.get('/api/platform/reports/generate/R-081?format=xlsx');self.assertEqual(generated.status_code,200);self.assertTrue(generated['X-Report-SHA256']);self.assertIn('private',generated['Cache-Control']);self.assertIn('no-store',generated['Cache-Control'])
  forbidden=self.client.get('/api/platform/reports/generate/R-082?format=pdf');self.assertEqual(forbidden.status_code,403);self.assertEqual(forbidden.json()['permission'],'logs.view')
 def test_audit_records_are_append_only_and_secret_values_are_redacted(self):
  from django.core.exceptions import ValidationError
  from .models import AuditEvent
  from .services.audit import append_audit,verify_audit_chain
  event=append_audit(actor=self.owner,tenant=self.tenant,action='settings.security.updated',metadata={'api_key':'super-secret','nested':{'password':'hidden','safe':'visible'}})
  self.assertEqual(event.metadata['api_key'],'[REDACTED]');self.assertEqual(event.metadata['nested']['password'],'[REDACTED]');self.assertEqual(event.metadata['nested']['safe'],'visible')
  with self.assertRaises(ValidationError):AuditEvent.objects.filter(pk=event.pk).update(action='tampered')
  with self.assertRaises(ValidationError):AuditEvent.objects.filter(pk=event.pk).delete()
  event.action='tampered'
  with self.assertRaises(ValidationError):event.save()
  self.assertTrue(verify_audit_chain(self.tenant)['valid'])
 def test_sensitive_export_requires_dual_control_and_records_decision_reason(self):
  from .models import ExportApprovalRequest
  self.client.force_login(self.owner)
  created=self.client.post('/api/exports/approvals',data=json.dumps({'export_type':'members','format':'xlsx','reason':'Quarterly compliance evidence','filters':{'status':'active'}}),content_type='application/json',**self.h)
  self.assertEqual(created.status_code,201);approval_id=created.json()['id']
  self_approve=self.client.post(f'/api/exports/approvals/{approval_id}',data=json.dumps({'decision':'approved','reason':'Self approval attempt'}),content_type='application/json',**self.h)
  self.assertEqual(self_approve.status_code,409);self.assertEqual(self_approve.json()['error'],'self_approval_not_allowed')
  self.client.force_login(self.approver)
  approved=self.client.post(f'/api/exports/approvals/{approval_id}',data=json.dumps({'decision':'approved','reason':'Validated legitimate purpose'}),content_type='application/json',**self.h)
  self.assertEqual(approved.status_code,200);obj=ExportApprovalRequest.objects.get(pk=approval_id);self.assertEqual(obj.approved_by,self.approver);self.assertEqual(obj.decision_reason,'Validated legitimate purpose')
 def test_billing_admin_can_govern_checkout_policy_after_step_up(self):
  from .models import SiteSetting
  self._step_up(self.billing)
  payload={'action':'configure_checkout','policy':{'annual':{'stripe_price_id':'price_annual_123'},'success_url':'/settings?billing=success','cancel_url':'/settings?billing=cancelled','portal_return_url':'/settings','approved_return_origins':['https://app.example.test']}}
  r=self.client.post('/api/platform/billing',data=json.dumps(payload),content_type='application/json')
  self.assertEqual(r.status_code,201);policy=SiteSetting.objects.get(key='billing_plans').value;self.assertEqual(policy['annual']['stripe_price_id'],'price_annual_123');self.assertEqual(policy['approved_return_origins'],['https://app.example.test'])
 def test_billing_admin_webhook_replay_requires_step_up(self):
  from .models import WebhookEvent
  event=WebhookEvent.objects.create(provider='stripe',event_id='evt-replay-1',tenant=self.tenant,event_type='invoice.payment_failed',mode='test',payload={'data':{'object':{'customer':'cus_123'}}},status='received')
  self._mfa_login(self.billing)
  denied=self.client.post(f'/api/platform/webhooks/{event.id}/replay',data='{}',content_type='application/json');self.assertEqual(denied.status_code,403);self.assertEqual(denied.json()['error'],'step_up_required')
  self._step_up(self.billing)
  replayed=self.client.post(f'/api/platform/webhooks/{event.id}/replay',data='{}',content_type='application/json');self.assertEqual(replayed.status_code,200);event.refresh_from_db();self.assertEqual(event.status,'processed')
 def test_stripe_tenant_scoped_event_does_not_require_duplicate_tenant_metadata(self):
  from .models import Subscription,WebhookEvent
  from .services.webhook_processing import process_verified_webhook
  event=WebhookEvent.objects.create(provider='stripe',event_id='evt-no-meta',tenant=self.tenant,event_type='invoice.payment_failed',mode='test',payload={'data':{'object':{'customer':'cus_456'}}},status='received')
  result=process_verified_webhook(event);event.refresh_from_db();sub=Subscription.objects.get(tenant=self.tenant)
  self.assertTrue(result['applied']);self.assertEqual(event.status,'processed');self.assertEqual(sub.status,'past_due')
 def test_stripe_explicit_mismatched_tenant_metadata_is_quarantined(self):
  from .models import WebhookEvent
  from .services.webhook_processing import WebhookQuarantined,process_verified_webhook
  event=WebhookEvent.objects.create(provider='stripe',event_id='evt-bad-meta',tenant=self.tenant,event_type='customer.subscription.updated',mode='test',payload={'data':{'object':{'id':'sub_bad','customer':'cus_bad','metadata':{'tenant_id':'00000000-0000-0000-0000-000000000001'}}}},status='received')
  with self.assertRaises(WebhookQuarantined):process_verified_webhook(event)
  event.refresh_from_db();self.assertEqual(event.status,'quarantined');self.assertEqual(event.quarantine_reason,'stripe_tenant_mismatch')
 def test_tenant_specific_provider_credential_precedes_platform_default(self):
  from .models import EncryptedCredential
  from .services.encryption import encrypt_json,decrypt_json
  from .views import _tenant_or_global_credential
  EncryptedCredential.objects.create(tenant=None,provider='stripe',mode='test',ciphertext=encrypt_json({'secret_key':'global','webhook_secret':'global-hook'}))
  specific=EncryptedCredential.objects.create(tenant=self.tenant,provider='stripe',mode='test',ciphertext=encrypt_json({'secret_key':'tenant','webhook_secret':'tenant-hook'}))
  selected=_tenant_or_global_credential(self.tenant,'stripe','test');self.assertEqual(selected.id,specific.id);self.assertEqual(decrypt_json(selected.ciphertext)['secret_key'],'tenant')
