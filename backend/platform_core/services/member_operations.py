"""Deterministic duplicate and bulk-operation contracts."""

from __future__ import annotations

import hashlib
import json


def _value(row, key):
    return row.get(key) if isinstance(row, dict) else getattr(row, key, "")


def _text(value):
    return " ".join(str(value or "").strip().lower().split())


def _phone(value):
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return digits[-10:] if len(digits) >= 10 else digits


def duplicate_reasons(candidate, existing) -> list[str]:
    reasons=[]
    email_a=_text(_value(candidate,"email"));email_b=_text(_value(existing,"email"))
    if email_a and email_a==email_b:reasons.append("email")
    phone_a=_phone(_value(candidate,"phone"));phone_b=_phone(_value(existing,"phone"))
    if phone_a and phone_b and phone_a==phone_b:reasons.append("phone")
    name_a=(_text(_value(candidate,"first_name")),_text(_value(candidate,"last_name")))
    name_b=(_text(_value(existing,"first_name")),_text(_value(existing,"last_name")))
    if all(name_a) and name_a==name_b:reasons.append("name")
    return reasons


def bulk_fingerprint(ids, action, parameters) -> str:
    payload={"ids":sorted({str(item) for item in ids}),"action":str(action),"parameters":parameters or {}}
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
