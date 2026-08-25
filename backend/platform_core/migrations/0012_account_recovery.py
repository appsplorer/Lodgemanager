import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("platform_core", "0011_meeting_pack_attachments"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AccountActionToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("purpose", models.CharField(choices=[("invitation", "invitation"), ("password_reset", "password_reset")], max_length=32)),
                ("digest", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("issued_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="account_action_tokens_issued", to=settings.AUTH_USER_MODEL)),
                ("tenant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="account_action_tokens", to="platform_core.tenant")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="account_action_tokens", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(model_name="accountactiontoken", index=models.Index(fields=["purpose", "expires_at"], name="lf_account_token_exp_idx")),
        migrations.AddIndex(model_name="accountactiontoken", index=models.Index(fields=["user", "purpose", "consumed_at"], name="lf_account_token_user_idx")),
    ]
