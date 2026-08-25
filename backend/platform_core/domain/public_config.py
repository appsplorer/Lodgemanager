from __future__ import annotations

import re

_GA4=re.compile(r'^G-[A-Z0-9]{6,20}$')
_META=re.compile(r'^[0-9]{5,30}$')


def normalize_analytics_config(value):
    raw=dict(value or {}) if isinstance(value,dict) else {}
    enabled=bool(raw.get('enabled',False))
    requires_consent=bool(raw.get('requires_consent',True))
    google=str(raw.get('google_measurement_id') or '').strip().upper()
    meta=str(raw.get('meta_pixel_id') or '').strip()
    if google and not _GA4.fullmatch(google):
        raise ValueError('invalid_google_measurement_id')
    if meta and not _META.fullmatch(meta):
        raise ValueError('invalid_meta_pixel_id')
    if enabled and not (google or meta):
        raise ValueError('analytics_provider_identifier_required')
    return {
        'enabled':enabled,
        'requires_consent':requires_consent,
        'google_measurement_id':google,
        'meta_pixel_id':meta,
    }
