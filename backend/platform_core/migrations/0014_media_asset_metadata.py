from django.db import migrations, models


def migrate_legacy_tags(apps, schema_editor):
    MediaAsset = apps.get_model("platform_core", "MediaAsset")
    for asset in MediaAsset.objects.all().iterator():
        tags = set(asset.accessibility_tags or [])
        asset.visibility = "private" if "visibility:private" in tags else "public"
        asset.decorative = "decorative" in tags
        asset.original_name = asset.file_path.rsplit("/", 1)[-1][:255]
        asset.save(update_fields=["visibility", "decorative", "original_name"])


class Migration(migrations.Migration):
    dependencies = [("platform_core", "0013_member_operations")]
    operations = [
        migrations.AddField(model_name="mediaasset", name="original_name", field=models.CharField(blank=True, max_length=255)),
        migrations.AddField(model_name="mediaasset", name="file_size", field=models.PositiveBigIntegerField(default=0)),
        migrations.AddField(model_name="mediaasset", name="sha256", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="mediaasset", name="scan_status", field=models.CharField(blank=True, max_length=32)),
        migrations.AddField(model_name="mediaasset", name="visibility", field=models.CharField(choices=[("public", "public"), ("private", "private")], default="private", max_length=16)),
        migrations.AddField(model_name="mediaasset", name="decorative", field=models.BooleanField(default=False)),
        migrations.RunPython(migrate_legacy_tags, migrations.RunPython.noop),
    ]
