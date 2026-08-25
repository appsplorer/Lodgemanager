import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('platform_core', '0002_spec_completion')]

    operations = [
        migrations.AddField(
            model_name='tenantmembership',
            name='custom_role',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='memberships',
                to='platform_core.customroledefinition',
            ),
        ),
    ]
