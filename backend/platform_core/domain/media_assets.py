"""Dependency-free media metadata and publication rules."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePath


VISIBILITIES = frozenset({"public", "private"})


def _storage_name(original_name: str) -> str:
    suffix = PurePath(original_name).suffix
    stem = PurePath(original_name).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    safe_suffix = re.sub(r"[^A-Za-z0-9.]", "", suffix)
    return f"{safe_stem or 'asset'}{safe_suffix}"[-180:]


def build_media_metadata(
    *,
    original_name: str,
    content_type: str,
    payload: bytes,
    visibility: str,
    decorative: bool,
) -> dict[str, object]:
    """Build the immutable security metadata captured at upload time."""
    normalized_visibility = str(visibility or "").strip().lower()
    if normalized_visibility not in VISIBILITIES:
        raise ValueError("visibility must be public or private")
    normalized_original_name = PurePath(str(original_name or "asset.bin").replace("\\", "/")).name
    return {
        "original_name": normalized_original_name[:255],
        "storage_name": _storage_name(normalized_original_name),
        "mime_type": str(content_type or "").strip().lower()[:120],
        "file_size": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "visibility": normalized_visibility,
        "decorative": bool(decorative),
    }


def public_download_allowed(visibility: str, scan_status: str) -> bool:
    """Fail closed: only explicitly public, clean content may be anonymous."""
    return visibility == "public" and scan_status == "clean"
