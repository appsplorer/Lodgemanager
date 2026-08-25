from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('platform_core', '0004_document_security_metadata')]

    operations = [
        migrations.AddField(
            model_name='member',
            name='communication_preferences',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='communicationcampaign',
            name='template_key',
            field=models.SlugField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='communicationcampaign',
            name='administrative_notice',
            field=models.BooleanField(default=False),
        ),
    ]
