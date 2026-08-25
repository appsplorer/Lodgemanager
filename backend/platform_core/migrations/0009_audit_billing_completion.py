# Generated for Quill of the Craft Final Baseline v1.0 audit/provider billing completion.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[('platform_core','0008_reports_completion')]
    operations=[
        migrations.AddField(model_name='exportevent',name='approval_request',field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name='export_events',to='platform_core.exportapprovalrequest')),
        migrations.AddField(model_name='exportevent',name='result',field=models.CharField(default='completed',max_length=30)),
        migrations.AddField(model_name='exportevent',name='sha256',field=models.CharField(blank=True,max_length=64)),
        migrations.AddField(model_name='exportevent',name='error',field=models.TextField(blank=True)),
        migrations.AddField(model_name='webhookevent',name='mode',field=models.CharField(default='live',max_length=10)),
        migrations.RemoveConstraint(model_name='webhookevent',name='uniq_provider_event'),
        migrations.AddConstraint(model_name='webhookevent',constraint=models.UniqueConstraint(fields=('provider','event_id','mode'),name='uniq_provider_event_mode')),
        migrations.AddField(model_name='webhookevent',name='quarantine_reason',field=models.CharField(blank=True,max_length=180)),
        migrations.AlterField(model_name='webhookevent',name='status',field=models.CharField(db_index=True,default='received',max_length=30)),
        migrations.AddField(model_name='subscription',name='cancel_at_period_end',field=models.BooleanField(default=False)),
        migrations.AddField(model_name='subscription',name='last_synced_at',field=models.DateTimeField(blank=True,null=True)),
        migrations.AddField(model_name='billingevent',name='mode',field=models.CharField(default='live',max_length=10)),
        migrations.AddField(model_name='billingevent',name='status',field=models.CharField(default='recorded',max_length=30)),
        migrations.AddField(model_name='exportapprovalrequest',name='decision_reason',field=models.TextField(blank=True)),
    ]
