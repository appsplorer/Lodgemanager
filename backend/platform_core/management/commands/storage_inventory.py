from __future__ import annotations

import json

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Emit non-secret private-storage inventory evidence for backup verification."

    def add_arguments(self, parser):
        parser.add_argument("--mode-only", action="store_true")

    def handle(self, *args, **options):
        mode = "s3" if getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") else "local"
        if options["mode_only"]:
            self.stdout.write(mode)
            return
        if mode != "s3":
            raise CommandError("storage inventory is only used for S3 backup mode")
        bucket = getattr(default_storage, "bucket", None)
        if bucket is None:
            raise CommandError("configured storage backend does not expose an S3 bucket")
        objects = []
        total_bytes = 0
        for item in bucket.objects.all().page_size(1000):
            size = int(item.size or 0)
            total_bytes += size
            objects.append({
                "key": item.key,
                "bytes": size,
                "etag": str(item.e_tag or "").strip('"'),
                "last_modified": item.last_modified.isoformat() if item.last_modified else None,
            })
        self.stdout.write(json.dumps({"schema_version": 1, "bucket": bucket.name, "object_count": len(objects), "total_bytes": total_bytes, "objects": objects}, separators=(",", ":"), sort_keys=True))
