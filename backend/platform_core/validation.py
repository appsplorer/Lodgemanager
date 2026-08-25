from __future__ import annotations

import ipaddress
import re
from decimal import Decimal
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from .services.safe_urls import UnsafeURLError, validate_public_url

ALLOWED_REDIRECT_CODES = {301, 302}
CMS_BLOCK_TYPES = {
    'hero', 'rich_text', 'features', 'feature_grid', 'statistics', 'image_text',
    'image_text_split', 'pricing', 'testimonials', 'faq', 'lead_form', 'cta', 'security',
}
CMS_URL_FIELDS={'href','url','primary_href','secondary_href','image','image_url','logo_url','background_image','video_url'}


def _validate_content_urls(value, *, location='content'):
    if isinstance(value,dict):
        clean={}
        for key,item in value.items():
            if key in CMS_URL_FIELDS and item:
                try:clean[key]=validate_public_url(item)
                except UnsafeURLError as exc:raise ValidationError({location:f'Unsafe URL in {key}: {exc}'}) from exc
            else:clean[key]=_validate_content_urls(item,location=location)
        return clean
    if isinstance(value,list):return [_validate_content_urls(item,location=location) for item in value]
    return value


def _clean_int(value, *, name: str, minimum: int, maximum: int, default: int) -> int:
    if value in (None, ''):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError({name: f'{name} must be an integer.'}) from exc
    if parsed < minimum or parsed > maximum:
        raise ValidationError({name: f'{name} must be between {minimum} and {maximum}.'})
    return parsed


def validate_security_settings(settings: dict | None) -> dict:
    """Normalize tenant security policy with production-safe bounds.

    The caller may merge this return value back into Tenant.settings['security'].
    """
    raw = dict(settings or {})
    normalized = dict(raw)
    normalized['session_timeout_minutes'] = _clean_int(
        raw.get('session_timeout_minutes'), name='session_timeout_minutes', minimum=5, maximum=1440, default=480
    )
    normalized['password_min_length'] = _clean_int(
        raw.get('password_min_length'), name='password_min_length', minimum=12, maximum=128, default=12
    )
    normalized['password_history'] = _clean_int(
        raw.get('password_history'), name='password_history', minimum=0, maximum=24, default=5
    )
    normalized['max_failed_attempts'] = _clean_int(
        raw.get('max_failed_attempts'), name='max_failed_attempts', minimum=3, maximum=20, default=8
    )
    normalized['lockout_minutes'] = _clean_int(
        raw.get('lockout_minutes'), name='lockout_minutes', minimum=1, maximum=1440, default=15
    )
    allowlist = raw.get('ip_allowlist') or []
    if not isinstance(allowlist, list):
        raise ValidationError({'ip_allowlist': 'IP allowlist must be a list of CIDR/network values.'})
    clean_networks = []
    for value in allowlist:
        candidate = str(value).strip()
        if not candidate:
            continue
        try:
            clean_networks.append(str(ipaddress.ip_network(candidate, strict=False)))
        except ValueError as exc:
            raise ValidationError({'ip_allowlist': f'Invalid IP/CIDR value: {candidate}'}) from exc
    normalized['ip_allowlist'] = clean_networks
    for flag in ('mfa_required', 'export_requires_approval', 'export_dual_control', 'allow_external_report_recipients'):
        if flag in raw:
            normalized[flag] = bool(raw.get(flag))
    return normalized


def validate_redirect_rule(source: str, destination: str, status_code: int | str) -> tuple[str, str, int]:
    source = str(source or '').strip()
    destination = str(destination or '').strip()
    try:
        code = int(status_code)
    except (TypeError, ValueError) as exc:
        raise ValidationError({'status_code': 'Redirect status must be 301 or 302.'}) from exc
    if code not in ALLOWED_REDIRECT_CODES:
        raise ValidationError({'status_code': 'Redirect status must be 301 or 302.'})
    if not source.startswith('/') or source.startswith('//') or '\\' in source or any(c in source for c in ('\r', '\n')):
        raise ValidationError({'source': 'Redirect source must be a safe same-site absolute path.'})
    if not destination.startswith('/') or destination.startswith('//') or '\\' in destination or any(c in destination for c in ('\r', '\n')):
        raise ValidationError({'destination': 'Redirect destination must be a safe same-site absolute path.'})
    parsed = urlsplit(destination)
    if parsed.scheme or parsed.netloc:
        raise ValidationError({'destination': 'External/protocol redirects are not permitted.'})
    if source == destination:
        raise ValidationError({'destination': 'Redirect source and destination cannot be identical.'})
    return source, destination, code


def validate_report_recipients(tenant, recipients) -> list[str]:
    if not isinstance(recipients, list):
        raise ValidationError({'recipients': 'Recipients must be an array.'})
    clean: list[str] = []
    for raw in recipients:
        value = str(raw or '').strip().lower()
        if not value or len(value) > 254 or not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', value):
            raise ValidationError({'recipients': f'Invalid email recipient: {raw}'})
        if value not in clean:
            clean.append(value)
    if not clean:
        raise ValidationError({'recipients': 'At least one recipient is required.'})
    security = ((tenant.settings or {}).get('security') or {})
    if bool(security.get('allow_external_report_recipients', False)):
        return clean
    permitted = set(
        tenant.user_memberships.filter(is_active=True, user__is_active=True)
        .exclude(user__email='')
        .values_list('user__email', flat=True)
    )
    permitted = {str(x).strip().lower() for x in permitted if x}
    # Member delivery addresses are deliberately not accepted for privileged report packs.
    blocked = [x for x in clean if x not in permitted]
    if blocked:
        raise ValidationError({'recipients': 'External report recipients are disabled by tenant security policy.'})
    return clean


def validate_cms_blocks(blocks) -> list[dict]:
    if not isinstance(blocks, list):
        raise ValidationError({'blocks': 'CMS blocks must be an array.'})
    if len(blocks) > 100:
        raise ValidationError({'blocks': 'A page may contain at most 100 blocks.'})
    clean: list[dict] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict):
            raise ValidationError({'blocks': f'Block {index + 1} must be an object.'})
        item = dict(block)
        block_type = str(item.get('type') or '').strip().lower()
        aliases = {'feature_grid': 'features', 'image_text_split': 'image_text'}
        block_type = aliases.get(block_type, block_type)
        if block_type not in CMS_BLOCK_TYPES:
            raise ValidationError({'blocks': f'Unsupported CMS block type: {block_type or "(missing)"}.'})
        item=_validate_content_urls(item,location='blocks')
        item['type'] = block_type
        item['hidden'] = bool(item.get('hidden', False))
        clean.append(item)
    return clean


def validate_navigation_items(items, *, depth: int = 0) -> list[dict]:
    if depth > 3:
        raise ValidationError({'items': 'Navigation nesting cannot exceed three levels.'})
    if not isinstance(items, list) or len(items) > 100:
        raise ValidationError({'items': 'Navigation items must be an array with at most 100 entries.'})
    clean = []
    for item in items:
        if not isinstance(item, dict):
            raise ValidationError({'items': 'Each navigation item must be an object.'})
        row = dict(item)
        label = str(row.get('label') or '').strip()
        href = str(row.get('href') or '').strip()
        if not label:
            raise ValidationError({'items': 'Navigation items require a label.'})
        if href:
            try:href=validate_public_url(href)
            except UnsafeURLError as exc:raise ValidationError({'items':f'Unsafe navigation target for {label}: {exc}'}) from exc
        row['label'] = label[:120]
        row['href'] = href[:500]
        row['visible'] = bool(row.get('visible', True))
        if 'children' in row:
            row['children'] = validate_navigation_items(row.get('children') or [], depth=depth + 1)
        clean.append(row)
    return clean

LEAD_FIELD_TYPES={'text','email','phone','textarea','select','checkbox','number'}

def validate_lead_form_fields(fields) -> list[dict]:
    if not isinstance(fields,list) or not fields or len(fields)>50:
        raise ValidationError({'fields':'Lead form fields must contain between 1 and 50 field definitions.'})
    names=set();clean=[]
    for index,raw in enumerate(fields,1):
        if not isinstance(raw,dict):raise ValidationError({'fields':f'Field {index} must be an object.'})
        name=str(raw.get('name') or '').strip()
        if not re.match(r'^[A-Za-z][A-Za-z0-9_]{0,63}$',name):raise ValidationError({'fields':f'Field {index} has an invalid name.'})
        if name in names:raise ValidationError({'fields':f'Duplicate field name: {name}'})
        names.add(name)
        field_type=str(raw.get('type') or 'text').strip().lower()
        if field_type not in LEAD_FIELD_TYPES:raise ValidationError({'fields':f'Unsupported field type: {field_type}'})
        label=str(raw.get('label') or name.replace('_',' ').title()).strip()[:120]
        row={'name':name,'label':label,'type':field_type,'required':bool(raw.get('required',False))}
        max_length=_clean_int(raw.get('max_length'),name='max_length',minimum=1,maximum=5000,default=500)
        row['max_length']=max_length
        if field_type=='select':
            options=raw.get('options') or []
            if not isinstance(options,list) or not options or len(options)>100:raise ValidationError({'fields':f'Select field {name} requires 1-100 options.'})
            row['options']=[str(x).strip()[:120] for x in options if str(x).strip()]
            if not row['options']:raise ValidationError({'fields':f'Select field {name} requires options.'})
        clean.append(row)
    return clean


def validate_lead_submission(fields, payload) -> dict:
    if not isinstance(payload,dict):raise ValidationError({'submission':'Submission must be an object.'})
    definitions={x['name']:x for x in validate_lead_form_fields(fields)}
    clean={}
    errors={}
    for name,definition in definitions.items():
        value=payload.get(name)
        if definition['type']=='checkbox':
            value=bool(value)
            if definition['required'] and not value:errors[name]='This field is required.'
            clean[name]=value;continue
        value='' if value is None else str(value).strip()
        if definition['required'] and not value:errors[name]='This field is required.';continue
        if not value:clean[name]='';continue
        if len(value)>definition['max_length']:errors[name]=f'Maximum length is {definition["max_length"]}.';continue
        if definition['type']=='email' and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$',value):errors[name]='Enter a valid email address.';continue
        if definition['type']=='phone' and not re.match(r'^[+()0-9 .-]{5,40}$',value):errors[name]='Enter a valid phone number.';continue
        if definition['type']=='number':
            try: Decimal(value)
            except Exception:errors[name]='Enter a valid number.';continue
        if definition['type']=='select' and value not in definition.get('options',[]):errors[name]='Select a valid option.';continue
        clean[name]=value
    if errors:raise ValidationError(errors)
    return clean
