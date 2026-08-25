"""Dependency-free retry controls shared by workers and control-plane APIs."""

from __future__ import annotations


def retry_delay(attempt: int, *, base: int = 30, cap: int = 1800) -> int:
    normalized_attempt = max(1, int(attempt))
    normalized_base = max(1, int(base))
    normalized_cap = max(normalized_base, int(cap))
    return min(normalized_cap, normalized_base * (2 ** (normalized_attempt - 1)))


def retryable_job(kind: str, payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    if kind == "member_import":
        return bool(payload.get("actor_id")) and isinstance(payload.get("rows"), list)
    if kind == "scheduled_report":
        return bool(str(payload.get("schedule_id") or "").strip())
    if kind == "retention_enforcement":
        return isinstance(payload.get("dry_run"), bool)
    return False
