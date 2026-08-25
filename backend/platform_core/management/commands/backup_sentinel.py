from __future__ import annotations

import hashlib
import json

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from platform_core.models import SystemJob


class Command(BaseCommand):
    help = "Create or verify the database-and-storage sentinel used by recovery drills."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=("create", "verify"))
        parser.add_argument("--token", required=True)

    def handle(self, *args, **options):
        token = str(options["token"]).strip()
        if not token or len(token) > 120 or not all(character.isalnum() or character in "-_" for character in token):
            raise CommandError("invalid sentinel token")
        payload = f"lodgeflow-backup-sentinel:{token}\n".encode()
        digest = hashlib.sha256(payload).hexdigest()
        path = f"backup-sentinels/{token}.txt"
        if options["action"] == "create":
            if default_storage.exists(path):
                default_storage.delete(path)
            stored_path = default_storage.save(path, ContentFile(payload))
            SystemJob.objects.update_or_create(
                kind="backup_sentinel",
                payload={"token": token},
                defaults={"status": "completed", "result": {"storage_path": stored_path, "sha256": digest, "bytes": len(payload)}},
            )
            self.stdout.write(json.dumps({"ok": True, "token": token, "storage_path": stored_path, "sha256": digest}, sort_keys=True))
            return
        job = SystemJob.objects.filter(kind="backup_sentinel", status="completed", payload__token=token).order_by("-created_at").first()
        if not job:
            raise CommandError("database sentinel is missing")
        result = job.result or {}
        stored_path = str(result.get("storage_path") or "")
        if not stored_path or not default_storage.exists(stored_path):
            raise CommandError("storage sentinel is missing")
        with default_storage.open(stored_path, "rb") as handle:
            restored = handle.read(len(payload) + 1)
        if restored != payload or hashlib.sha256(restored).hexdigest() != result.get("sha256"):
            raise CommandError("storage sentinel checksum mismatch")
        self.stdout.write(json.dumps({"ok": True, "token": token, "storage_path": stored_path, "sha256": result["sha256"]}, sort_keys=True))
