# Generated for Quill of the Craft Final Baseline v1.0 reporting completion.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies=[('platform_core','0007_finance_workflow_completion'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.AlterField(model_name='generatedreport',name='file_path',field=models.CharField(blank=True,max_length=500)),
        migrations.AlterField(model_name='generatedreport',name='sha256',field=models.CharField(blank=True,max_length=64)),
        migrations.AddField(model_name='generatedreport',name='status',field=models.CharField(choices=[('queued','queued'),('running','running'),('completed','completed'),('failed','failed'),('approval_required','approval_required')],db_index=True,default='completed',max_length=24)),
        migrations.AddField(model_name='generatedreport',name='progress',field=models.PositiveSmallIntegerField(default=100)),
        migrations.AddField(model_name='generatedreport',name='error',field=models.TextField(blank=True)),
        migrations.AddField(model_name='generatedreport',name='job_id',field=models.CharField(blank=True,max_length=80)),
        migrations.AddField(model_name='reportschedule',name='attachments',field=models.JSONField(blank=True,default=list)),
        migrations.AddField(model_name='reportschedule',name='next_run_at',field=models.DateTimeField(blank=True,null=True)),
        migrations.CreateModel(
            name='ReportDeliveryLog',
            fields=[
                ('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ('created_at',models.DateTimeField(auto_now_add=True)),('updated_at',models.DateTimeField(auto_now=True)),
                ('recipient',models.EmailField(max_length=254)),
                ('status',models.CharField(choices=[('queued','queued'),('sending','sending'),('delivered','delivered'),('retry_pending','retry_pending'),('failed','failed')],default='queued',max_length=24)),
                ('attempts',models.PositiveIntegerField(default=0)),('provider_reference',models.CharField(blank=True,max_length=180)),('error',models.TextField(blank=True)),
                ('last_attempt_at',models.DateTimeField(blank=True,null=True)),('delivered_at',models.DateTimeField(blank=True,null=True)),
                ('generated_report',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='delivery_logs',to='platform_core.generatedreport')),
                ('schedule',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='delivery_logs',to='platform_core.reportschedule')),
                ('tenant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='report_delivery_logs',to='platform_core.tenant')),
            ],
        ),
    ]
