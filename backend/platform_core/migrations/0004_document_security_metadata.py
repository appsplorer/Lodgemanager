from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('platform_core', '0003_custom_role_membership')]

    operations = [
        migrations.AddField(
            model_name='document',
            name='original_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='document',
            name='file_size',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='document',
            name='sha256',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='document',
            name='scan_status',
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
