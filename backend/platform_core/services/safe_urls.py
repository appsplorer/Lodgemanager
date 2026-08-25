"""URL validation shared by CMS, navigation, media and billing boundaries."""

from __future__ import annotations

from urllib.parse import urlsplit


class UnsafeURLError(ValueError):
    pass


def validate_public_url(value, *, allow_relative: bool = True, https_required: bool = False) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if any(ord(character) < 32 or ord(character) == 127 for character in raw) or "\\" in raw:
        raise UnsafeURLError("url_contains_unsafe_characters")
    if raw.startswith("#"):
        if not allow_relative or len(raw) == 1:
            raise UnsafeURLError("relative_url_not_allowed")
        return raw
    if raw.startswith("/"):
        if not allow_relative or raw.startswith("//"):
            raise UnsafeURLError("relative_url_not_allowed")
        parsed = urlsplit(raw)
        if parsed.scheme or parsed.netloc:
            raise UnsafeURLError("invalid_relative_url")
        return raw
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise UnsafeURLError("http_or_https_url_required")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeURLError("url_credentials_not_allowed")
    if https_required and parsed.scheme != "https":
        raise UnsafeURLError("https_url_required")
    return raw
