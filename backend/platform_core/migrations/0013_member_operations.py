import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies=[('platform_core','0012_account_recovery'),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
        migrations.CreateModel(
            name='BulkActionConfirmation',
            fields=[
                ('id',models.UUIDField(default=uuid.uuid4,editable=False,primary_key=True,serialize=False)),
                ('created_at',models.DateTimeField(auto_now_add=True)),
                ('updated_at',models.DateTimeField(auto_now=True)),
                ('token_digest',models.CharField(max_length=64,unique=True)),
                ('fingerprint',models.CharField(max_length=64)),
                ('action',models.CharField(max_length=80)),
                ('impacted_count',models.PositiveIntegerField()),
                ('expires_at',models.DateTimeField()),
                ('consumed_at',models.DateTimeField(blank=True,null=True)),
                ('tenant',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='bulk_action_confirmations',to='platform_core.tenant')),
                ('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='bulk_action_confirmations',to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(model_name='bulkactionconfirmation',index=models.Index(fields=['tenant','user','expires_at'],name='lf_bulk_confirm_exp_idx')),
    ]
