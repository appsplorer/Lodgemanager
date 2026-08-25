from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def text(p): return (ROOT/p).read_text()
def test_sw_never_caches_private_api():
 s=text('frontend/public/sw.js');assert "url.pathname.startsWith('/api/')" in s and "!url.pathname.startsWith('/api/public/')" in s
 assert 'private API lives in encrypted IndexedDB' in s
def test_private_cache_is_encrypted():
 s=text('frontend/lib/offline.ts');assert "AES-GCM" in s and 'extractable' not in s.lower();assert 'generateKey' in s and 'crypto.subtle.encrypt' in s
def test_queue_uses_idempotency():
 a=text('frontend/lib/api.ts');b=text('backend/platform_core/idempotency.py');m=text('backend/platform_core/models.py')
 assert "Idempotency-Key" in a and 'idempotencyKey' in a
 assert 'IdempotencyReceipt' in b and 'IdempotencyReceipt' in m
def test_high_risk_actions_blocked_offline():
 s=text('frontend/lib/api.ts')
 for token in ['billing','credentials','mfa','payment-link','transition','impersonat','checkout','portal','waive','adjust','reverse','approve','late-fees']: assert token in s
def test_uploads_are_online_only():
 s=text('frontend/lib/api.ts');assert 'File uploads require an internet connection' in s
def test_cache_is_bounded_and_ttl_based():
 s=text('frontend/lib/offline.ts');assert 'MAX_CACHE_RECORDS' in s and 'MAX_QUEUE_RECORDS' in s and 'DEFAULT_TTL' in s and 'expiresAt' in s
def test_accessible_reduced_motion_present():
 s=text('frontend/app/globals.css');assert 'prefers-reduced-motion' in s and ':focus-visible' in s
def test_hover_microinteractions_present():
 s=text('frontend/app/globals.css');assert '.panel:hover' in s and '.console-row:hover' in s and '.feature-grid article:hover' in s
def test_landing_has_reveal_and_parallax():
 p=text('frontend/app/page.tsx');b=text('frontend/components/PublicCmsBlocks.tsx');assert 'MarketingMotion' in p and 'data-reveal' in b and 'data-parallax' in b
def test_service_worker_versioning_and_update():
 s=text('frontend/public/sw.js');assert 'VERSION' in s and 'skipWaiting' in s and 'clients.claim' in s
def test_next_build_is_standalone_and_compressed():
 s=text('frontend/next.config.mjs');assert "output: 'standalone'" in s and 'compress: true' in s
def test_idempotency_receipts_expire():
 s=text('backend/platform_core/idempotency.py');assert 'timedelta(days=2)' in s and 'expires_at__gt=now' in s
def test_offline_status_ui_present():
 s=text('frontend/components/OfflineSyncProvider.tsx');assert 'Sync now' in s and 'queued' in s and "window.addEventListener('online'" in s
def test_dashboard_uses_live_api_not_hardcoded_kpis():
 s=text('frontend/app/dashboard/page.tsx');assert "api<DashboardData>('/dashboard')" in s and 'Loading dashboard' in s and 'Dashboard unavailable' in s

def test_next_proxies_api_to_django():
 s=text('frontend/next.config.mjs');assert "source: '/api/:path*'" in s and 'backend:8000/api/:path*' in s

def test_mutations_bootstrap_csrf():
 s=text('frontend/lib/api.ts');assert "url('/csrf/')" in s and 'await ensureCsrf()' in s and 'X-CSRFToken' in s

def test_offline_conflict_version_is_carried_end_to_end():
 a=text('frontend/lib/api.ts');o=text('frontend/lib/offline.ts');v=text('backend/platform_core/views.py')
 assert 'X-LodgeFlow-Base-Updated-At' in a and 'baseUpdatedAt' in o and 'offline_conflict' in v

def test_offline_queue_never_silently_evicts_changes():
 s=text('frontend/lib/offline.ts');assert 'Offline change queue is full' in s;assert 'trimQueue' not in s

def test_offline_data_is_bound_to_authenticated_principal():
 s=text('frontend/lib/offline.ts');assert 'bindOfflinePrincipal' in s and "'principal-id'" in s
 assert 'clearOfflinePrincipal' in s

def test_logout_warns_before_unsynced_discard_with_branded_dialog():
 s=text('frontend/components/LogoutButton.tsx');assert 'queuedCount' in s and 'unsynced offline change' in s and 'useConfirmDialog' in s and 'confirm(' not in s

def test_mfa_page_and_enrollment_guard_exist():
 f=text('frontend/app/mfa/page.tsx');v=text('backend/platform_core/views.py')
 assert '/mfa/verify' in f and '/mfa/setup' in f and 'one-time-code' in f
 assert 'mfa_already_enrolled' in v and 'password_verification_expired' in v

def test_workspace_identity_uses_server_bootstrap():
 s=text('frontend/components/WorkspaceIdentity.tsx');assert '/workspace/bootstrap' in s and 'Switch lodge' in s and 'setSelectedLodge' in s

def test_server_read_cache_is_scoped_and_invalidated():
 s=text('backend/platform_core/read_cache.py');assert 'tenant_id' in s and 'user.id' in s and '_version(tenant_id)' in s and '_bump(tenant_id)' in s

def test_production_settings_fail_closed():
 s=text('backend/lodgeflow/settings.py')
 for token in ['DJANGO_SECRET_KEY must be a strong','POSTGRES_PASSWORD is required','CREDENTIAL_ENCRYPTION_KEYS is required','CSRF_TRUSTED_ORIGINS is required']:assert token in s

def test_migration_graph_covers_all_models_and_has_concrete_choices():
 import ast,re
 models=ast.parse(text('backend/platform_core/models.py'))
 expected={x.name for x in models.body if isinstance(x,ast.ClassDef) and x.name!='UUIDModel'}
 created=set(); combined=[]
 migrations=sorted((ROOT/'backend/platform_core/migrations').glob('[0-9][0-9][0-9][0-9]_*.py'))
 assert migrations, 'No application migrations found'
 for migration in migrations:
  source=migration.read_text(); combined.append(source); tree=ast.parse(source)
  mc=next((x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Migration'),None)
  if not mc: continue
  ops=next((x for x in mc.body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='operations'),None)
  if not ops: continue
  for op in ops.value.elts:
   if isinstance(op,ast.Call) and isinstance(op.func,ast.Attribute) and op.func.attr=='CreateModel':
    kw=next(k for k in op.keywords if k.arg=='name'); created.add(ast.literal_eval(kw.value))
 all_migrations='\n'.join(combined)
 assert created==expected, f'Migration graph missing/extraneous models: missing={expected-created}, extra={created-expected}'
 assert not re.search(r'choices=[A-Z_]+\b',all_migrations), 'Migrations must freeze concrete choice values'
 assert all_migrations.count('models.ForeignKey(')+all_migrations.count('models.OneToOneField(')>=60

def test_all_url_view_references_exist():
 import ast,re
 funcs={x.name for x in ast.parse(text('backend/platform_core/views.py')).body if isinstance(x,ast.FunctionDef)}
 refs=set(re.findall(r'v\.([A-Za-z_][A-Za-z0-9_]*)',text('backend/lodgeflow/urls.py')))
 assert refs<=funcs

def test_deployment_scripts_are_present_and_checksum_restore():
 assert 'check --deploy' in text('scripts/deploy-production.sh') and 'makemigrations --check --dry-run' in text('scripts/deploy-production.sh')
 assert 'sha256sum' in text('scripts/backup.sh') and 'sha256sum -c' in text('scripts/restore.sh')

def test_production_compose_migrates_before_backend():
 s=text('docker-compose.prod.yml');assert 'migrate:' in s and 'service_completed_successfully' in s and 'clamav:' in s

def test_local_docker_stack_and_windows_helpers_present():
    compose=text('docker-compose.local.yml')
    for service in ['db:','redis:','clamav:','mailpit:','migrate:','seed:','backend:','worker:','beat:','frontend:']:
        assert service in compose
    assert 'seed_local_demo' in compose
    assert text('.env.local.example').count('LOCAL_ADMIN_') >= 3
    assert 'docker compose --env-file .env.local -f docker-compose.local.yml' in text('scripts/local-up.ps1')
    assert 'python manage.py test platform_core' in text('scripts/local-qa.ps1')

def test_local_seed_is_debug_guarded_and_creates_full_access_demo():
    s=text('backend/platform_core/management/commands/seed_local_demo.py')
    assert 'DEBUG' in s and 'disabled unless DEBUG=true' in s
    assert 'is_superuser = True' in s
    assert '"role": "owner"' in s
    assert 'role="super_admin"' in s
    assert 'CMSPage.objects.update_or_create' in s
    assert 'DuesCycle.objects.update_or_create' in s

def test_local_guide_covers_offline_conflict_qa():
    s=text('docs/LOCAL_PYCHARM_DOCKER_QA.md')
    for token in ['Service Workers','IndexedDB','Conflict QA','Sync now','makemigrations --check --dry-run','npm run build']:
        assert token in s

def test_production_proxy_is_loopback_only_and_datastores_are_private():
 s=text('docker-compose.prod.yml');n=text('deploy/nginx.conf')
 assert 'proxy:' in s and '127.0.0.1:${APP_HTTP_PORT:-8080}:8080' in s
 # PostgreSQL and Redis production services use expose/internal networking only: no host port mappings.
 db=s.split('  db:',1)[1].split('  redis:',1)[0];redis=s.split('  redis:',1)[1].split('  clamav:',1)[0]
 assert 'ports:' not in db and 'ports:' not in redis
 assert 'location /api/' in n and 'proxy_pass http://backend:8000' in n and 'proxy_pass http://frontend:3000' in n

def test_staging_overlay_proves_email_storage_and_malware_contracts():
 c=text('docker-compose.staging.yml');s=text('scripts/staging-e2e.sh')
 for token in ['minio:','minio-init:','mailpit:','AWS_STORAGE_BUCKET_NAME','EMAIL_HOST: mailpit']:
  assert token in c
 for token in ['S3-compatible storage probe: ok','SMTP probe: ok','ClamAV upload probe: ok','Celery worker probe: ok']:
  assert token in s

def test_backup_restore_is_encrypted_checksum_verified_and_destructive_drilled():
 b=text('scripts/backup.sh');r=text('scripts/restore.sh');v=text('scripts/verify-backup-restore.sh')
 assert 'aes-256-cbc' in b and 'pbkdf2' in b and '.dump.enc' in b and 'sha256sum' in b
 assert 'sha256sum -c' in r and 'openssl enc -d' in r and 'RESTORE_CONFIRM' in r
 assert 'Representative restored record verified' in v and 'Member.objects.filter' in v

def test_browser_runtime_contract_uses_playwright_and_axe_desktop_mobile():
 package=text('frontend/package.json');config=text('frontend/playwright.config.ts');spec=text('frontend/e2e/core.spec.ts');ci=text('.github/workflows/ci.yml')
 assert '@playwright/test' in package and '@axe-core/playwright' in package and 'test:e2e' in package
 assert 'desktop-chromium' in config and 'mobile-chromium' in config
 assert 'AxeBuilder' in spec and 'authentication reaches a tenant-scoped live dashboard' in spec
 assert 'Desktop/mobile Playwright + axe' in ci and 'runtime-e2e-evidence' in ci

def test_ci_contains_contractual_runtime_release_gates():
 s=text('.github/workflows/ci.yml')
 for token in ['makemigrations --check --dry-run','check --deploy --fail-level WARNING','docker build -t lodgeflow-backend:ci','pip-audit','trivy-action','gitleaks','playwright install','verify-backup-restore.sh']:
  assert token in s

def test_step_up_auth_is_wired_for_sensitive_platform_actions():
    views=(ROOT/'backend/platform_core/views.py').read_text()
    urls=(ROOT/'backend/lodgeflow/urls.py').read_text()
    dialog=(ROOT/'frontend/components/AppDialog.tsx').read_text()
    admin=(ROOT/'frontend/app/platform-admin/page.tsx').read_text()
    assert "def step_up_auth" in views and "api/auth/step-up" in urls
    assert "password_verified_at" in views and "mfa_verified_at" in views
    assert "useStepUpDialog" in dialog and "step_up_required" in admin and "/auth/step-up" in admin


def test_custom_roles_are_reusable_tenant_scoped_and_dynamic():
 m=text('backend/platform_core/models.py');p=text('backend/platform_core/domain/permissions.py');v=text('backend/platform_core/views.py');u=text('backend/lodgeflow/urls.py');f=text('frontend/app/settings/page.tsx')
 assert "custom_role=models.ForeignKey('CustomRoleDefinition'" in m
 assert 'def effective_custom_permissions' in p and "role',None)=='custom'" in p
 assert 'invalid_or_cross_tenant_custom_role' in v and 'custom_role_in_use' in v and 'authorization_refresh' in v
 assert "api/settings/custom-roles/<uuid:pk>" in u
 assert 'Custom role for ${u.username}' in f and 'deleteCustomRole' in f

def test_observability_alerting_and_reference_performance_contract():
    settings=(ROOT/'backend/lodgeflow/settings.py').read_text()
    views=(ROOT/'backend/platform_core/views.py').read_text()
    tasks=(ROOT/'backend/platform_core/tasks.py').read_text()
    req=(ROOT/'backend/requirements.txt').read_text()
    prod=(ROOT/'.env.production.example').read_text()
    ops=(ROOT/'scripts/ops-monitor.py').read_text()
    load=(ROOT/'scripts/load-test.py').read_text()
    seed=(ROOT/'backend/platform_core/management/commands/seed_reference_load.py').read_text()
    perf=(ROOT/'.github/workflows/reference-load.yml').read_text()
    assert 'sentry-sdk[django]' in req and 'send_default_pii=False' in settings and 'SENTRY_DSN' in prod
    assert "'storage':False" in views and "'malware_scanner':False" in views and 'clamav_readiness' in views
    assert 'operational-health-watch' in settings and 'monitor_operational_health' in tasks
    assert "kind=='security'" in views and 'acknowledge_security_alert' in views
    assert 'PUBLIC_BASE_URL' in ops and 'tls_days_remaining' in ops and 'ALERT_WEBHOOK_URL' in ops
    assert 'LOAD_CONCURRENCY' in load and "'100'" in load and 'LOAD_P95_LIMIT_MS' in load
    assert 'ALLOW_REFERENCE_LOAD_SEED' in seed and '50_000' in seed and '250_000' in seed and '100_000' in seed and '20_000' in seed
    assert 'lodgeflow-reference' in perf and '--members 50000' in perf and '--attendance 250000' in perf and '--finance 100000' in perf and '--documents 20000' in perf

def test_document_security_module_enforces_mime_acl_download_and_template_allowlist():
    import importlib.util
    fs_path=ROOT/'backend/platform_core/services/file_security.py'
    spec=importlib.util.spec_from_file_location('lf_file_security',fs_path);fs=importlib.util.module_from_spec(spec);spec.loader.exec_module(fs)
    class Upload:
        name='invoice.jpg';content_type='application/pdf';size=9
        def __init__(self):self._data=b'%PDF-1.7\n';self.pos=0
        def read(self,n=-1):return self._data[:n] if n>=0 else self._data
        def seek(self,n):self.pos=n
    try:
        fs.validate_upload(Upload())
        assert False,'extension/MIME mismatch must be rejected'
    except fs.FileValidationError as exc:
        assert exc.code=='file_extension_mime_mismatch'
    v=text('backend/platform_core/views.py');u=text('backend/lodgeflow/urls.py');m=text('backend/platform_core/models.py');settings=text('backend/lodgeflow/settings.py')
    assert 'def document_download' in v and "api/documents/<uuid:pk>/download" in u
    assert "FileResponse(handle,as_attachment=True" in v and "Cache-Control']='private, no-store'" in v
    assert 'original_name=models.CharField' in m and 'sha256=models.CharField' in m and 'scan_status=models.CharField' in m
    assert "'default_acl':'private'" in settings and "'querystring_auth':True" in settings
    tr_path=ROOT/'backend/platform_core/services/template_rendering.py';tspec=importlib.util.spec_from_file_location('lf_template_rendering',tr_path);tr=importlib.util.module_from_spec(tspec);tspec.loader.exec_module(tr)
    assert tr.render_template('Dear {{member.first_name}}',{'member.first_name':'Ada'})=='Dear Ada'
    try:
        tr.render_template('{{unsafe.secret}}',{'unsafe.secret':'x'})
        assert False,'unsafe merge field must fail'
    except tr.TemplateRenderError as exc:
        assert exc.code=='unknown_or_unsafe_merge_fields'
    assert 'missing_merge_context' in tr_path.read_text() and 'template_version=hashlib.sha256' in v

def test_communications_module_has_consent_preview_lifecycle_idempotent_delivery_and_test_send():
    m=text('backend/platform_core/models.py');c=text('backend/platform_core/services/communications.py');t=text('backend/platform_core/tasks.py');v=text('backend/platform_core/views.py');u=text('backend/lodgeflow/urls.py');f=text('frontend/components/WorkflowTools.tsx')
    assert 'communication_preferences=models.JSONField' in m and 'administrative_notice=models.BooleanField' in m and 'template_key=models.SlugField' in m
    assert "communication_preferences__email='opt_out'" in c and 'required_administrative_notices' in c
    assert 'render_campaign_for_member' in c and 'validate_merge_fields' in c
    assert "if log.status in {'delivered','failed'}" in t and "log.status='retry_pending'" in t and "Message-ID" in t and 'provider_metadata' in t
    assert 'def campaign_delivery_logs' in v and 'def campaign_cancel' in v and 'select_for_update' in v
    assert 'def email_template_preview' in v and 'def email_template_test_send' in v and 'test_recipient_must_be_authorized_tenant_user' in v
    assert "api/communications/<uuid:pk>/deliveries" in u and "api/communications/templates/<uuid:pk>/test-send" in u
    assert 'Recipient preview & dispatch' in f and 'Queue reviewed campaign' in f and 'Delivery outcomes' in f and 'Send controlled test' in f

def test_meeting_workflow_completion_is_implemented():
    m=text('backend/platform_core/models.py');v=text('backend/platform_core/views.py');svc=text('backend/platform_core/services/meetings.py');t=text('backend/platform_core/tasks.py');u=text('backend/lodgeflow/urls.py');f=text('frontend/components/WorkflowTools.tsx');pdf=text('backend/platform_core/services/pdfs.py')
    assert 'class AgendaItem' in m and 'recurrence_source=models.ForeignKey' in m and 'occurrence_key=models.CharField' in m
    assert 'reviewer_comments=models.TextField' in m and "reopened_from=models.ForeignKey('self'" in m and 'locked_by=models.ForeignKey' in m
    assert 'def parse_rrule' in svc and 'def generate_recurring_occurrences' in svc and 'occurrence_key=key' in svc and 'get_or_create' in svc
    assert 'def meeting_agenda' in v and 'def agenda_reorder' in v and 'def meeting_generate_occurrences' in v and 'def minutes_reopen' in v
    assert "controlled_reopen_required" in v and "reopen_reason_required" in v and "target=='approved'" in v
    assert 'def generate_recurring_meetings' in t and 'recurring-meeting-generation' in text('backend/lodgeflow/settings.py')
    assert "api/meetings/<uuid:meeting_id>/agenda" in u and "minutes/<int:version>/reopen" in u
    assert 'Visual agenda builder' in f and 'Sync recurring dates' in f and 'Controlled reopen' in f and 'Attendance & visitors' in f
    assert "if kind=='pack'" in v and 'Prior / Current Minutes' in pdf

def test_finance_workflow_completion_is_governed_and_currency_safe():
    models=text('backend/platform_core/models.py');views=text('backend/platform_core/views.py');domain=text('backend/platform_core/domain/finance.py')
    migration=text('backend/platform_core/migrations/0007_finance_workflow_completion.py');webhooks=text('backend/platform_core/services/webhook_processing.py')
    exports=text('backend/platform_core/services/exports.py');reports=text('backend/platform_core/services/reports.py');ui=text('frontend/components/WorkflowTools.tsx');finance_ui=text('frontend/app/finance/page.tsx');offline=text('frontend/lib/api.ts')
    for token in ['class PaymentAllocation','class FinancialAdjustment','class ExpenseCategory','adjustment_amount','is_reversed','dues_cycle_period_valid','payment_amount_positive']:
        assert token in models
    for token in ['def dues_cycle_preview','def dues_cycle_transition','get_or_create(','def waive_dues_assessment','def adjust_dues_assessment','def reverse_payment','def dues_arrears','totals_by_currency','select_for_update().get(pk=request.tenant.pk)','PaymentAllocation.objects.create','payment_currency_must_match_assessment','approved_expense_is_immutable']:
        assert token in views
    assert "status='draft',is_open=False" in views and "status='active'" in views
    assert 'ROUND_HALF_UP' in domain and "f'{prefix}-{int(year)}-{int(sequence):06d}'" in domain
    assert 'dues_cycle_period_valid' in migration and 'payment_allocation_amount_positive' in migration
    assert 'PaymentAllocation.objects.create' in webhooks and 'provider_amount_mismatch' in webhooks and 'provider_currency_mismatch' in webhooks
    assert "isinstance(v,Decimal)" in exports and "format(v,'f')" in exports and 'export_date_format' in exports and 'Default currency' in exports
    assert 'outstanding_by_currency' in reports and 'paid_by_currency' in reports and 'is_reversed=False' in reports
    for token in ['Preview → activate → generate','Idempotent assessment generation','Record non-destructive adjustment','Reverse latest recorded payment','Arrears aging & member drill-down','totals remain separated by currency']:
        assert token.lower() in ui.lower()
    for token in ['Expense categories','Receipt / supporting document','approval required','Approve','Reject']:
        assert token in finance_ui
    for token in ['waive','adjust','reverse','approve','late-fees','transition']:
        assert token in offline


def test_finance_proration_and_status_fixtures_are_deterministic():
    import importlib.util
    from datetime import date
    from decimal import Decimal
    spec=importlib.util.spec_from_file_location('finance_domain',ROOT/'backend/platform_core/domain/finance.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    assert mod.prorated_dues(Decimal('120.00'),date(2026,1,1),date(2026,12,31),date(2026,7,1),True)==Decimal('60.49')
    assert mod.prorated_dues(Decimal('120.00'),date(2026,1,1),date(2026,12,31),date(2025,12,1),True)==Decimal('120.00')
    assert mod.amount_due('100.00','20.00','10.00','5.00','-2.00')==Decimal('73.00')
    assert mod.assessment_status('100.00','0','0','5.00',True,'0')=='overdue'
    assert mod.assessment_status('100.00','50','0','0',False,'0')=='partial'
    assert mod.assessment_status('100.00','0','100','0',False,'0')=='waived'

def test_report_catalog_async_scheduling_and_premium_accessible_ui_completion():
    reports=text('backend/platform_core/services/reports.py');views=text('backend/platform_core/views.py');tasks=text('backend/platform_core/tasks.py');models=text('backend/platform_core/models.py');urls=text('backend/lodgeflow/urls.py');ui=text('frontend/components/PremiumReports.tsx');css=text('frontend/app/globals.css');settings=text('backend/lodgeflow/settings.py')
    for rid in ['R-001','R-002','R-003','R-010','R-014','R-020','R-030','R-040','R-044','R-050','R-057','R-060','R-070','R-073','R-080','R-084']:
        assert rid in reports
    for token in ['def report_catalog','def report_preview','def estimate_report_rows','No data for selected filters','repeatRows=1','Page {self._pageNumber} of {count}','safe_report_filename','freeze_panes','_safe_text']:
        assert token in reports
    for token in ['def report_catalog_view','def report_preview_view','def generated_reports','def generated_report_download','report_approval_required','async_threshold_rows','generate_report_async.delay','Cache-Control']:
        assert token in views
    for token in ['def generate_report_async','def run_report_schedule','ReportDeliveryLog.objects.get_or_create','attachment_reports','def dispatch_due_report_schedules']:
        assert token in tasks
    assert 'report-schedule-dispatch' in settings and 'dispatch_due_report_schedules' in settings
    assert 'class ReportDeliveryLog' in models and "status=models.CharField(max_length=24,choices=STATUS" in models
    for route in ['api/reports/catalog','api/reports/preview/<str:report_type>','api/reports/generated','api/reports/generated/<uuid:pk>/download','api/reports/schedules/<uuid:pk>/run']:
        assert route in urls
    for token in ['Decision intelligence','Professional reporting, without spreadsheet guesswork.','Commercial catalogue','Reconciled preview','Accessible trend visualization','Values are printed as text; meaning does not rely on color.','Generated vault','Scheduled report packs','Sensitive approvals']:
        assert token in ui
    assert '.report-hero' in css and '.report-library' in css and '.report-trend' in css and '.report-bottom-grid' in css


def test_generated_report_formats_are_branded_searchable_paginated_and_formula_safe():
    s=text('backend/platform_core/services/reports.py')
    for token in ['tenant.name','classification','SimpleDocTemplate','Paragraph(','Table(','repeatRows=1','NumberedCanvas','Page {self._pageNumber} of {count}','application/pdf','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','utf-8-sig']:
        assert token in s
    assert "text[:1] in {'=','+','-','@'}" in s
    assert "landscape(base) if wide else base" in s
    assert "str(tenant.slug).lower()" in s and "report_id=canonical_report_id(report_type).lower()" in s


def test_audit_compliance_completion_is_append_only_redacted_dual_control_and_uses_premium_dialogs():
    models=text('backend/platform_core/models.py');querysets=text('backend/platform_core/querysets.py');audit=text('backend/platform_core/services/audit.py');exports=text('backend/platform_core/services/exports.py');views=text('backend/platform_core/views.py');ui=text('frontend/app/compliance/page.tsx');css=text('frontend/app/globals.css')
    assert 'objects=AuditEventQuerySet.as_manager()' in models and 'audit_events_are_append_only' in models
    for token in ['AuditEventQuerySet','audit_events_are_append_only','def update(self','def delete(self']:
        assert token in querysets
    for token in ['scrub_sensitive','SECRET_TOKENS','verify_audit_chain','chain_branch_detected','orphaned_events']:
        assert token in audit
    for token in ['approval_request=approval','result=\'completed\'','sha256=digest','approver_id']:
        assert token in exports
    for token in ['self_approval_not_allowed','decision_reason_required_min_5_chars','approved_filters_do_not_match_request','def compliance_exports']:
        assert token in views
    assert 'useTextPromptDialog' in ui and 'promptDialog.ask' in ui
    assert 'window.prompt' not in ui and 'confirm(' not in ui
    assert 'promptDialog.dialog' in ui
    for token in ['Compliance command centre','Hash chain verified','Export evidence ledger','Dual-control queue']:
        assert token in ui
    assert '.compliance-hero' in css and '.compliance-kpis' in css and '.approval-layout' in css


def test_provider_billing_completion_uses_billing_control_plane_step_up_safe_replay_and_no_native_confirm():
    models=text('backend/platform_core/models.py');views=text('backend/platform_core/views.py');webhooks=text('backend/platform_core/services/webhook_processing.py');tasks=text('backend/platform_core/tasks.py');migration=text('backend/platform_core/migrations/0009_audit_billing_completion.py');ui=text('frontend/components/PremiumBillingOps.tsx');css=text('frontend/app/globals.css')
    for token in ["fields=('provider','event_id','mode')",'quarantine_reason','cancel_at_period_end','last_synced_at','decision_reason']:
        assert token in migration or token in models
    for token in ['tenant_scoped_webhook_url_required','invalid_signature','event_tenant_or_mode_conflict','accepted_for_retry','configure_checkout','approved_return_origins','return_url_origin_not_approved']:
        assert token in views
    assert "user_has_platform_permission(request.user,'billing.edit')" in views and "user_has_platform_permission(request.user,'logs.view')" in views
    replay_start=views.index('def replay_webhook')
    replay_slice=views[replay_start:replay_start+2400]
    assert 'has_recent_step_up(request)' in replay_slice and 'step_up_required' in replay_slice
    for token in ['WebhookQuarantined','provider_amount_mismatch','provider_currency_mismatch','provider_mode_mismatch','payment_request_not_found_or_tenant_mismatch','duplicate_payment']:
        assert token in webhooks
    assert 'process_webhook_event' in tasks and 'self.retry' in tasks
    assert "api('/platform/billing'" in ui and "action:'configure_checkout'" in ui
    assert 'useConfirmDialog' in ui and 'confirmDialog.ask' in ui and 'confirmDialog.dialog' in ui
    assert 'confirm(' not in ui and '/platform/site-settings' not in ui
    for token in ['Revenue operations','Encrypted provider vault','Quarantine queue','Payment request lifecycle','Billing evidence']:
        assert token in ui
    assert '.billing-hero' in css and '.provider-readiness' in css and '.billing-kpis' in css


def test_provider_credential_resolution_prefers_tenant_specific_and_compliance_queue_shows_actor_evidence():
    views=text('backend/platform_core/views.py');ui=text('frontend/app/compliance/page.tsx')
    assert 'def _tenant_or_global_credential' in views
    assert views.count('_tenant_or_global_credential(')>=4
    assert "requester_name" in views and "approver_name" in views
    assert 'requester_name' in ui and 'approver_name' in ui
    platform_ui=text('frontend/app/platform-admin/page.tsx')
    billing_effect=platform_ui[platform_ui.index("if(tab==='billing')"):platform_ui.index("if(tab==='operations')")]
    assert '/platform/site-settings' not in billing_effect

def test_provider_vault_enable_disable_and_financial_delivery_uniqueness_controls():
    models=text('backend/platform_core/models.py');views=text('backend/platform_core/views.py');migration=text('backend/platform_core/migrations/0010_integrity_controls.py');ui=text('frontend/app/platform-admin/page.tsx')
    assert 'is_enabled=models.BooleanField(default=True)' in models
    assert "condition=~models.Q(provider_reference='')" in models
    assert "fields=['tenant','provider','provider_reference']" in models
    assert "fields=['tenant','campaign','recipient']" in models
    assert "is_enabled=True" in views
    assert "def credential_toggle" in views and "credential_disabled" in views
    assert "platform/credentials/${c.id}/toggle" in ui and 'is_enabled' in ui
    assert 'uniq_payment_provider_reference' in migration and 'uniq_campaign_recipient_delivery' in migration

def test_candidate_pipeline_reports_conversion_funnel():
    analytics=text('backend/platform_core/domain/analytics.py');views=text('backend/platform_core/views.py')
    assert 'def candidate_conversion_funnel' in analytics
    assert "'conversion':candidate_conversion" in views
    assert "candidate_stages" in views


def test_candidate_conversion_funnel_fixture():
    import importlib.util
    spec=importlib.util.spec_from_file_location('analytics_domain',ROOT/'backend/platform_core/domain/analytics.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    rows=[
      {'stage':'application','stage_history':[{'to':'enquiry'},{'to':'application'}]},
      {'stage':'ballot','stage_history':[{'to':'enquiry'},{'to':'application'},{'to':'investigation'},{'to':'ballot'}]},
      {'stage':'enquiry','stage_history':[]},
    ]
    result=mod.candidate_conversion_funnel(rows,['enquiry','application','investigation','ballot'])
    assert result[0]=={'from':'enquiry','to':'application','reached_from':3,'reached_to':2,'conversion_pct':66.7}
    assert result[1]['conversion_pct']==50.0

def test_tenant_custom_fields_and_candidate_stage_history_are_validated():
    domain=text('backend/platform_core/domain/tenant_config.py');views=text('backend/platform_core/views.py');ui=text('frontend/app/settings/page.tsx')
    for token in ['def normalize_member_custom_fields','display_order','def normalize_candidate_stages','candidate_stages_in_use']:
        assert token in domain
    assert 'normalize_member_custom_fields' in views and 'normalize_candidate_stages' in views
    assert "Candidate.objects.filter(tenant=request.tenant)" in views and "stage_history" in views
    assert 'custom_fields' in ui and 'Custom member fields' in ui


def test_tenant_config_domain_fixtures():
    import importlib.util
    spec=importlib.util.spec_from_file_location('tenant_config_domain',ROOT/'backend/platform_core/domain/tenant_config.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    fields=mod.normalize_member_custom_fields([{'key':'shirt_size','label':'Shirt size','type':'select','required':True,'display_order':2,'options':['S','M','L']},{'key':'nickname','label':'Nickname','type':'text','display_order':1}])
    assert [x['key'] for x in fields]==['nickname','shirt_size']
    assert fields[1]['required'] is True and fields[1]['options']==['S','M','L']
    try:mod.normalize_candidate_stages(['enquiry','application'],{'ballot'})
    except ValueError as exc:assert str(exc).startswith('candidate_stages_in_use:')
    else:raise AssertionError('Removing a used stage must fail')

def test_public_analytics_are_consent_gated_and_configuration_is_allowlisted():
    domain=text('backend/platform_core/domain/public_config.py');views=text('backend/platform_core/views.py');client=text('frontend/components/PublicAnalytics.tsx');home=text('frontend/app/page.tsx');slug=text('frontend/app/[slug]/page.tsx');settings=text('backend/lodgeflow/settings.py');admin=text('frontend/app/platform-admin/page.tsx')
    assert 'def normalize_analytics_config' in domain and 'google_measurement_id' in domain and 'meta_pixel_id' in domain
    assert "key=='analytics'" in views and 'normalize_analytics_config' in views
    for token in ['lodgeflow:analytics-consent','requires_consent','www.googletagmanager.com','connect.facebook.net','Grant analytics','Decline analytics']:
        assert token in client
    assert 'PublicAnalytics' in home and 'PublicAnalytics' in slug
    assert 'www.googletagmanager.com' in settings and 'connect.facebook.net' in settings
    assert 'saveAnalytics' in admin and "key:'analytics'" in admin


def test_public_analytics_config_fixture():
    import importlib.util
    spec=importlib.util.spec_from_file_location('public_config_domain',ROOT/'backend/platform_core/domain/public_config.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    cfg=mod.normalize_analytics_config({'enabled':True,'requires_consent':True,'google_measurement_id':'G-ABC123XYZ9','meta_pixel_id':'1234567890'})
    assert cfg['enabled'] is True and cfg['requires_consent'] is True
    try:mod.normalize_analytics_config({'enabled':True,'google_measurement_id':'<script>'})
    except ValueError as exc:assert str(exc)=='invalid_google_measurement_id'
    else:raise AssertionError('unsafe analytics identifier must be rejected')

def test_meeting_pack_combines_notices_and_acl_checked_pdf_attachments():
    models=text('backend/platform_core/models.py');views=text('backend/platform_core/views.py');urls=text('backend/lodgeflow/urls.py');pdfs=text('backend/platform_core/services/pdfs.py');merge=text('backend/platform_core/services/pdf_merge.py');migration=text('backend/platform_core/migrations/0011_meeting_pack_attachments.py');ui=text('frontend/components/WorkflowTools.tsx')
    for token in ['class MeetingAttachment','meeting=models.ForeignKey(Meeting','document=models.ForeignKey(Document','include_in_pack','sort_order','uniq_meeting_pack_document']:
        assert token in models or token in migration
    for token in ['def meeting_attachments','def meeting_attachment_detail','_document_allowed','application/pdf','scan_status','merge_pdf_documents','meeting.communications']:
        assert token in views or token in pdfs
    assert 'api/meetings/<uuid:meeting_id>/attachments' in urls
    assert 'Notices / communications' in pdfs and 'Configured attachments' in pdfs
    for token in ['def merge_pdf_documents','PdfReader','PdfWriter','PDFMergeError','max_total_pages','encrypted_pdf_not_supported']:
        assert token in merge
    for token in ['/attachments','Meeting pack attachments','include_in_pack']:
        assert token in ui


def test_pdf_merge_rejects_encrypted_or_invalid_payloads_and_preserves_page_order():
    import importlib.util, io
    from reportlab.pdfgen import canvas
    from pypdf import PdfReader, PdfWriter
    spec=importlib.util.spec_from_file_location('pdf_merge',ROOT/'backend/platform_core/services/pdf_merge.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    def one_page(label):
        out=io.BytesIO();c=canvas.Canvas(out);c.drawString(72,720,label);c.save();return out.getvalue()
    base=one_page('BASE');a=one_page('ATTACHMENT A');b=one_page('ATTACHMENT B')
    merged=mod.merge_pdf_documents(base,[('A',a),('B',b)],max_total_pages=10)
    assert len(PdfReader(io.BytesIO(merged)).pages)==3
    try:mod.merge_pdf_documents(base,[('bad',b'not a pdf')])
    except mod.PDFMergeError as exc:assert exc.code=='invalid_pdf'
    else:raise AssertionError('invalid attachment must fail closed')
    writer=PdfWriter();writer.add_blank_page(width=100,height=100);writer.encrypt('secret');encrypted=io.BytesIO();writer.write(encrypted)
    try:mod.merge_pdf_documents(base,[('secret',encrypted.getvalue())])
    except mod.PDFMergeError as exc:assert exc.code=='encrypted_pdf_not_supported'
    else:raise AssertionError('encrypted PDF must fail closed')

def test_campaign_retries_only_transient_recipient_failures_with_bounded_backoff():
    tasks=text('backend/platform_core/tasks.py');ui=text('frontend/components/WorkflowTools.tsx')
    start=tasks.index('def send_campaign')
    block=tasks[start:tasks.index('@shared_task',start+20)]
    assert "if log.status in {'delivered','failed'}" in block
    assert "log.status='retry_pending'" in block
    assert 'raise self.retry(countdown=_backoff(' in block
    assert 'max_retries=5' in tasks
    assert 'permanent=isinstance(exc,smtplib.SMTPRecipientsRefused)' in block
    assert 'Delivery outcomes' in ui and 'retry_pending' in ui

def test_member_import_dry_run_executes_model_validation_and_commit_is_atomic():
    views=text('backend/platform_core/views.py');ui=text('frontend/components/WorkflowTools.tsx')
    start=views.index('def member_import')
    end=views.index('def member_duplicates',start)
    block=views[start:end]
    assert "validated_rows=[]" in block
    assert "candidate=Member(tenant=request.tenant)" in block
    assert "candidate.full_clean()" in block
    assert "validated_rows.append((i,mapped))" in block
    assert "with transaction.atomic():" in block and "transaction.set_rollback(True)" in block
    assert "request.GET.get('commit')!='true'" in block
    assert "preview=[row for _,row in validated_rows[:100]]" in block
    assert 'Validation complete:' in ui and '/members/import?commit=true' in ui

def test_integrity_migration_reconciles_legacy_duplicates_before_unique_constraints():
    migration=text('backend/platform_core/migrations/0010_integrity_controls.py')
    assert 'def reconcile_legacy_duplicates' in migration
    assert 'migrations.RunPython(reconcile_legacy_duplicates' in migration
    assert 'duplicate_provider_reference_preserved' in migration
    assert 'migration_merged_delivery_log_ids' in migration
    run=migration.index('migrations.RunPython(reconcile_legacy_duplicates')
    assert run < migration.index("name='uniq_payment_provider_reference'")
    assert run < migration.index("name='uniq_campaign_recipient_delivery'")

def test_delivery_package_contains_api_data_model_admin_security_sbom_and_risk_documents():
    required={
      'docs/openapi.yaml':['openapi: 3.1.0','X-Lodge-ID','/api/auth/login','/api/meetings/{meeting_id}/attachments','/api/reports/catalog'],
      'docs/DATA_MODEL.md':['Tenant isolation','MeetingAttachment','PaymentAllocation','AuditEvent','GeneratedReport'],
      'docs/ADMIN_OPERATOR_GUIDE.md':['Platform operator','Tenant administrator','Provider credentials','Backup','Incident'],
      'docs/SECURITY_AND_KNOWN_RISKS.md':['Threat model','Known release risks','Secrets','Tenant isolation','Provider sandbox'],
      'docs/THIRD_PARTY_LICENSES.md':['Django','Next.js','pypdf','ReportLab'],
      'docs/RELEASE_NOTES_2026-08-24.md':['LodgeFlow','Migration','Acceptance','Not production-approved'],
      'docs/SBOM.json':['"bomFormat": "CycloneDX"','"components"'],
    }
    for path,tokens in required.items():
        content=text(path)
        for token in tokens: assert token in content, f'{path} missing {token}'

def test_playwright_records_warmed_lcp_budget_for_primary_navigation():
    e2e=text('frontend/e2e/core.spec.ts')
    for token in ['largest-contentful-paint','LCP_BUDGET_MS','2500','warmed primary page LCP','testInfo.attach']:
        assert token in e2e

def test_pdf_service_can_render_representative_documents_without_django_runtime():
    import importlib.util, types
    spec=importlib.util.spec_from_file_location('pdf_service',ROOT/'backend/platform_core/services/pdfs.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    meeting=types.SimpleNamespace(title='Stated Meeting',starts_at=__import__('datetime').datetime(2026,8,24,19,30),location='Lodge Hall',meeting_type='stated',agenda=[{'title':'Opening'}],communications=['Secretary notice'])
    minute=types.SimpleNamespace(id='m1',body='Approved prior minutes',state='approved',version=2)
    member=types.SimpleNamespace(first_name='Ada',last_name='Mason')
    attendance=[types.SimpleNamespace(member=member,status='present')]
    visitors=[types.SimpleNamespace(name='Guest Mason',home_lodge='Example Lodge')]
    assert mod.minutes_pdf(meeting,minute,attendance,visitors).startswith(b'%PDF-')
    assert mod.meeting_pack_pdf(meeting,minute,attendance,visitors,attachment_labels=['By-laws']).startswith(b'%PDF-')

def test_delivery_includes_eight_readable_representative_pdf_samples_and_manifest():
    from pypdf import PdfReader
    names=['receipt.pdf','member-statement.pdf','officer-roster.pdf','minutes.pdf','summons.pdf','attendance-sheet.pdf','meeting-pack.pdf','monthly-management-pack.pdf']
    for name in names:
        path=ROOT/'docs/samples'/name
        assert path.exists() and path.stat().st_size>700, name
        reader=PdfReader(str(path));assert len(reader.pages)>=1,name
        assert (reader.metadata.title or '').strip(),name
    manifest=text('docs/PDF_SAMPLE_APPROVAL.md')
    for name in names:assert name in manifest
    assert 'SHA-256' in manifest and 'visual qa' in manifest.lower()
    generator=text('scripts/generate-pdf-samples.py')
    assert 'receipt_pdf' in generator and 'meeting_pack_pdf' in generator and 'merge_pdf_documents' in generator

def test_ci_does_not_use_deprecated_node20_checkout_action_or_corrupted_sync_workflow():
    workflows=list((ROOT/'.github/workflows').glob('*.yml'))
    assert workflows
    combined='\n'.join(p.read_text() for p in workflows)
    assert 'actions/checkout@v4' not in combined
    assert 'actions/checkout@v5' in combined
    assert not (ROOT/'.github/workflows/finalize-source-sync.yml').exists()
    for staging in ['.patch-sync-v1','.source-sync','.source-sync-v2','.source-sync-v3']:
        assert not (ROOT/staging).exists()

def test_ci_generates_resolved_container_sboms_and_uploads_security_evidence():
    ci=text('.github/workflows/ci.yml')
    for token in [
        'format: cyclonedx',
        'security-artifacts/backend-sbom.cdx.json',
        'security-artifacts/frontend-sbom.cdx.json',
        'name: security-evidence',
        'path: security-artifacts',
    ]:
        assert token in ci
