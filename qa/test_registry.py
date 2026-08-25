"""Stable requirement-test metadata shared by local and CI runners."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import wraps
from typing import Any, TypeVar


F = TypeVar("F", bound=Callable[..., Any])
ALLOWED_EVIDENCE_KINDS = {
    "unit",
    "integration",
    "api",
    "component",
    "e2e",
    "security",
    "performance",
    "recovery",
    "visual",
    "uat",
}


def requirement_test(
    test_id: str,
    requirement_ids: Iterable[str],
    evidence_kind: str,
) -> Callable[[F], F]:
    """Attach immutable acceptance metadata to an executable test callable."""

    normalized_id = str(test_id).strip()
    normalized_requirements = tuple(dict.fromkeys(str(item).strip() for item in requirement_ids if str(item).strip()))
    normalized_kind = str(evidence_kind).strip().lower()
    if not normalized_id:
        raise ValueError("test_id_required")
    if not normalized_requirements:
        raise ValueError("requirement_ids_required")
    if normalized_kind not in ALLOWED_EVIDENCE_KINDS:
        raise ValueError("invalid_evidence_kind")

    def decorate(function: F) -> F:
        @wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return function(*args, **kwargs)

        wrapped.requirement_test_id = normalized_id  # type: ignore[attr-defined]
        wrapped.requirement_ids = normalized_requirements  # type: ignore[attr-defined]
        wrapped.evidence_kind = normalized_kind  # type: ignore[attr-defined]
        return wrapped  # type: ignore[return-value]

    return decorate
