"""Opaque, expiring, single-use tokens for invitation and password recovery."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Callable


class AccountTokenError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def new_raw_token() -> str:
    return secrets.token_urlsafe(32)


def digest_token(raw_token: str) -> str:
    return hashlib.sha256(str(raw_token).encode("utf-8")).hexdigest()


def validate_token_record(
    record,
    raw_token: str,
    purpose: str,
    *,
    now: datetime,
    digest: Callable[[str], str] = digest_token,
):
    if record.consumed_at is not None:
        raise AccountTokenError("token_already_used")
    if record.expires_at <= now:
        raise AccountTokenError("token_expired")
    if record.purpose != purpose:
        raise AccountTokenError("token_purpose_mismatch")
    if not hmac.compare_digest(str(record.digest), digest(raw_token)):
        raise AccountTokenError("invalid_token")
    return record


def issue_account_token(*, user, purpose: str, tenant=None, issued_by=None, ttl_seconds: int | None = None, metadata=None):
    from django.conf import settings
    from django.utils import timezone

    from ..models import AccountActionToken

    if purpose not in {"invitation", "password_reset"}:
        raise AccountTokenError("invalid_token_purpose")
    if ttl_seconds is None:
        ttl_seconds = (
            settings.INVITATION_TOKEN_TTL_SECONDS
            if purpose == "invitation"
            else settings.PASSWORD_RESET_TOKEN_TTL_SECONDS
        )
    ttl = max(300, min(int(ttl_seconds), 60 * 60 * 24 * 30))
    raw_token = new_raw_token()
    now = timezone.now()
    AccountActionToken.objects.filter(
        user=user,
        tenant=tenant,
        purpose=purpose,
        consumed_at__isnull=True,
    ).update(consumed_at=now)
    record = AccountActionToken.objects.create(
        user=user,
        tenant=tenant,
        purpose=purpose,
        digest=digest_token(raw_token),
        expires_at=now + timezone.timedelta(seconds=ttl),
        issued_by=issued_by,
        metadata=metadata or {},
    )
    return record, raw_token


def consume_account_token(*, raw_token: str, purpose: str):
    from django.db import transaction
    from django.utils import timezone

    from ..models import AccountActionToken

    token_digest = digest_token(raw_token)
    with transaction.atomic():
        try:
            record = AccountActionToken.objects.select_for_update().select_related("user", "tenant").get(digest=token_digest)
        except AccountActionToken.DoesNotExist as exc:
            raise AccountTokenError("invalid_token") from exc
        validate_token_record(record, raw_token, purpose, now=timezone.now())
        record.consumed_at = timezone.now()
        record.save(update_fields=["consumed_at", "updated_at"])
        return record
