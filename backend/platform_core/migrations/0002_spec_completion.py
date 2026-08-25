# Generated for Final Baseline v1.0 completion hardening (24 Aug 2026).
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [('platform_core', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='OfficerRoleDefinition',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('key', models.SlugField(max_length=80)), ('name', models.CharField(max_length=120)),
                ('sort_order', models.PositiveIntegerField(default=0)), ('is_active', models.BooleanField(default=True)),
                ('permissions', models.JSONField(blank=True, default=list)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='officer_role_definitions', to='platform_core.tenant')),
            ],
        ),
        migrations.AddConstraint(model_name='officerroledefinition', constraint=models.UniqueConstraint(fields=('tenant','key'), name='uniq_officer_role_tenant_key')),
        migrations.CreateModel(
            name='CandidateMentorAssignment',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('role', models.CharField(default='mentor', max_length=80)), ('assigned_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('ended_at', models.DateTimeField(blank=True, null=True)), ('is_active', models.BooleanField(default=True)),
                ('candidate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mentor_assignments', to='platform_core.candidate')),
                ('mentor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='candidate_mentor_assignments', to='platform_core.member')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='candidate_mentor_assignments', to='platform_core.tenant')),
            ],
        ),
        migrations.AddConstraint(model_name='candidatementorassignment', constraint=models.UniqueConstraint(fields=('candidate','mentor','role'), name='uniq_candidate_mentor_role')),
        migrations.AddField(model_name='candidatetask', name='assignee', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='candidate_tasks_assigned', to='platform_core.member')),
        migrations.AddField(model_name='candidatetask', name='status', field=models.CharField(choices=[('todo','todo'),('in_progress','in_progress'),('blocked','blocked'),('completed','completed'),('cancelled','cancelled')], default='todo', max_length=24)),
        migrations.AddField(model_name='candidatetask', name='required_for_stage', field=models.BooleanField(default=False)),
        migrations.CreateModel(
            name='PaymentRequest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('provider', models.CharField(max_length=40)), ('mode', models.CharField(default='test', max_length=10)),
                ('internal_reference', models.CharField(max_length=180)), ('provider_reference', models.CharField(blank=True, max_length=180)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)), ('currency', models.CharField(default='PHP', max_length=3)),
                ('status', models.CharField(choices=[('created','created'),('pending','pending'),('paid','paid'),('failed','failed'),('cancelled','cancelled'),('expired','expired')], default='created', max_length=20)),
                ('request_payload', models.JSONField(blank=True, default=dict)), ('response_payload', models.JSONField(blank=True, default=dict)),
                ('expires_at', models.DateTimeField(blank=True, null=True)), ('settled_at', models.DateTimeField(blank=True, null=True)),
                ('assessment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_requests', to='platform_core.duesassessment')),
                ('member', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_requests', to='platform_core.member')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_requests', to='platform_core.tenant')),
            ],
        ),
        migrations.AddConstraint(model_name='paymentrequest', constraint=models.UniqueConstraint(fields=('tenant','internal_reference'), name='uniq_payment_request_internal_ref')),
        migrations.AddField(model_name='expense', name='approval_status', field=models.CharField(default='draft', max_length=20)),
        migrations.AddField(model_name='expense', name='approved_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_expenses', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='expense', name='approved_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='deliverylog', name='attempts', field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name='deliverylog', name='last_attempt_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='deliverylog', name='provider_metadata', field=models.JSONField(blank=True, default=dict)),
        migrations.CreateModel(
            name='SavedReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=160)), ('report_type', models.CharField(max_length=80)), ('filters', models.JSONField(blank=True, default=dict)),
                ('columns', models.JSONField(blank=True, default=list)), ('grouping', models.JSONField(blank=True, default=list)), ('sorting', models.JSONField(blank=True, default=list)), ('is_shared', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_reports', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_reports', to='platform_core.tenant')),
            ],
        ),
        migrations.CreateModel(
            name='GeneratedReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('report_type', models.CharField(max_length=80)), ('format', models.CharField(default='pdf', max_length=10)), ('filters', models.JSONField(blank=True, default=dict)),
                ('reporting_period', models.CharField(blank=True, max_length=160)), ('file_path', models.CharField(max_length=500)), ('sha256', models.CharField(max_length=64)), ('row_count', models.PositiveIntegerField(default=0)), ('metadata', models.JSONField(blank=True, default=dict)),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_reports', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='generated_reports', to='platform_core.tenant')),
            ],
        ),
        migrations.AddField(model_name='reportschedule', name='created_by', field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='report_schedules', to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name='reportschedule', name='last_run_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='reportschedule', name='last_status', field=models.CharField(blank=True, max_length=30)),
        migrations.CreateModel(
            name='GeneratedDocument',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(max_length=80)), ('source_type', models.CharField(max_length=80)), ('source_id', models.CharField(max_length=80)),
                ('template_key', models.CharField(blank=True, max_length=120)), ('template_version', models.CharField(default='1', max_length=40)), ('file_path', models.CharField(max_length=500)), ('sha256', models.CharField(max_length=64)), ('metadata', models.JSONField(blank=True, default=dict)),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_documents', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='generated_documents', to='platform_core.tenant')),
            ],
        ),
        migrations.AddField(model_name='impersonationsession', name='expires_at', field=models.DateTimeField(default=django.utils.timezone.now)),
        migrations.AddField(model_name='exportapprovalrequest', name='expires_at', field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(
            name='SecurityAlert',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
                ('kind', models.CharField(max_length=80)), ('severity', models.CharField(default='medium', max_length=20)), ('message', models.CharField(max_length=500)), ('metadata', models.JSONField(blank=True, default=dict)), ('acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('acknowledged_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='security_alerts_acknowledged', to=settings.AUTH_USER_MODEL)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='security_alerts', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='security_alerts', to='platform_core.tenant')),
            ],
        ),
    ]
