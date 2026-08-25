#!/usr/bin/env python3
"""Create and verify tamper-evident LodgeFlow backup bundle manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


MANIFEST = "manifest.json"
MANIFEST_CHECKSUM = "manifest.sha256"
REQUIRED = {"local": {"database", "media", "sentinel"}, "s3": {"database", "s3_inventory", "sentinel"}}
ALLOWED_TYPES = {"database", "media", "s3_inventory", "sentinel"}


class ManifestError(ValueError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_artifact_path(bundle: Path, raw: str) -> Path:
    relative = PurePosixPath(str(raw))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ManifestError(f"unsafe artifact path: {raw}")
    path = bundle.joinpath(*relative.parts)
    if path.is_symlink() or not path.is_file():
        raise ManifestError(f"artifact is missing or not a regular file: {raw}")
    if os.path.commonpath((str(bundle.resolve()), str(path.resolve()))) != str(bundle.resolve()):
        raise ManifestError(f"artifact escapes bundle: {raw}")
    return path


def parse_artifacts(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        kind, separator, filename = value.partition("=")
        if not separator or kind not in ALLOWED_TYPES or not filename:
            raise ManifestError(f"invalid artifact declaration: {value}")
        if kind in result:
            raise ManifestError(f"duplicate artifact type: {kind}")
        result[kind] = filename
    return result


def create(bundle: Path, media_mode: str, declarations: list[str]) -> dict[str, object]:
    bundle = bundle.resolve()
    if media_mode not in REQUIRED:
        raise ManifestError("media mode must be local or s3")
    artifacts = parse_artifacts(declarations)
    missing = REQUIRED[media_mode] - artifacts.keys()
    if missing:
        raise ManifestError(f"missing required {media_mode} media backup evidence: {', '.join(sorted(missing))}")
    rows = []
    for kind, filename in sorted(artifacts.items()):
        path = safe_artifact_path(bundle, filename)
        rows.append({"type": kind, "filename": filename, "bytes": path.stat().st_size, "sha256": sha256(path)})
    payload: dict[str, object] = {
        "schema_version": 1,
        "backup_id": bundle.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "media_mode": media_mode,
        "artifacts": rows,
    }
    manifest_path = bundle / MANIFEST
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    checksum_path = bundle / MANIFEST_CHECKSUM
    checksum_path.write_text(f"{sha256(manifest_path)}  {MANIFEST}\n", encoding="ascii")
    checksum_path.chmod(0o600)
    return payload


def verify(bundle: Path) -> dict[str, object]:
    bundle = bundle.resolve()
    manifest_path = bundle / MANIFEST
    checksum_path = bundle / MANIFEST_CHECKSUM
    if manifest_path.is_symlink() or checksum_path.is_symlink() or not manifest_path.is_file() or not checksum_path.is_file():
        raise ManifestError("manifest and manifest checksum are required regular files")
    checksum_parts = checksum_path.read_text(encoding="ascii").strip().split()
    if len(checksum_parts) != 2 or checksum_parts[1] != MANIFEST or checksum_parts[0] != sha256(manifest_path):
        raise ManifestError("manifest checksum mismatch")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ManifestError("invalid backup manifest JSON") from exc
    if payload.get("schema_version") != 1 or payload.get("media_mode") not in REQUIRED:
        raise ManifestError("unsupported backup manifest schema or media mode")
    rows = payload.get("artifacts")
    if not isinstance(rows, list):
        raise ManifestError("manifest artifacts must be a list")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("type") not in ALLOWED_TYPES or row.get("type") in seen:
            raise ManifestError("invalid or duplicate artifact entry")
        seen.add(row["type"])
        path = safe_artifact_path(bundle, str(row.get("filename") or ""))
        if path.stat().st_size != row.get("bytes"):
            raise ManifestError(f"artifact checksum/size mismatch: {row.get('filename')}")
        if sha256(path) != row.get("sha256"):
            raise ManifestError(f"artifact checksum mismatch: {row.get('filename')}")
    missing = REQUIRED[payload["media_mode"]] - seen
    if missing:
        raise ManifestError(f"missing required media backup evidence: {', '.join(sorted(missing))}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    create_parser = subparsers.add_parser("create")
    create_parser.add_argument("--bundle", type=Path, required=True)
    create_parser.add_argument("--media-mode", choices=sorted(REQUIRED), required=True)
    create_parser.add_argument("--artifact", action="append", default=[])
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--bundle", type=Path, required=True)
    artifact_parser = subparsers.add_parser("artifact")
    artifact_parser.add_argument("--bundle", type=Path, required=True)
    artifact_parser.add_argument("--type", choices=sorted(ALLOWED_TYPES), required=True)
    args = parser.parse_args()
    try:
        if args.command == "create":
            result = create(args.bundle, args.media_mode, args.artifact)
        else:
            result = verify(args.bundle)
            if args.command == "artifact":
                row = next((item for item in result["artifacts"] if item["type"] == args.type), None)
                if not row:
                    raise ManifestError(f"artifact type not present: {args.type}")
                print(args.bundle.resolve() / row["filename"])
                return 0
        print(json.dumps({"ok": True, "backup_id": result["backup_id"], "media_mode": result["media_mode"]}, sort_keys=True))
        return 0
    except (ManifestError, OSError) as exc:
        print(f"backup manifest error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
