from __future__ import annotations
from datetime import datetime, timezone as dt_timezone
from django.utils import timezone
from ..models import SecurityAlert


def has_recent_step_up(request, minutes=10):
    raw=request.session.get('mfa_verified_at') or request.session.get('password_verified_at')
    if not raw:
        return False
    try:
        when=datetime.fromisoformat(raw)
        if when.tzinfo is None:
            when=when.replace(tzinfo=dt_timezone.utc)
        return (timezone.now()-when).total_seconds() <= minutes*60
    except (TypeError, ValueError):
        return False


def security_alert(*, kind, message, tenant=None, actor=None, severity='medium', metadata=None):
    return SecurityAlert.objects.create(
        tenant=tenant, actor=actor, kind=kind, severity=severity,
        message=str(message)[:500], metadata=metadata or {},
    )
