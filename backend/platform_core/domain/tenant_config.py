from __future__ import annotations

import re

MEMBER_CUSTOM_FIELD_TYPES={'text','textarea','email','phone','number','date','select','checkbox'}
_FIELD_KEY=re.compile(r'^[a-z][a-z0-9_]{0,63}$')
_STAGE=re.compile(r'^[A-Za-z0-9][A-Za-z0-9 _./-]{0,79}$')


def _bounded_int(value, *, default: int, minimum: int, maximum: int, code: str) -> int:
    if value in (None,''):
        return default
    try:
        parsed=int(value)
    except (TypeError,ValueError) as exc:
        raise ValueError(code) from exc
    if parsed<minimum or parsed>maximum:
        raise ValueError(code)
    return parsed


def normalize_member_custom_fields(fields):
    if fields in (None,''):
        return []
    if not isinstance(fields,list) or len(fields)>100:
        raise ValueError('custom_fields_must_be_list_max_100')
    clean=[];keys=set()
    for index,raw in enumerate(fields):
        if not isinstance(raw,dict):
            raise ValueError(f'custom_field_{index+1}_must_be_object')
        key=str(raw.get('key') or raw.get('name') or '').strip().lower()
        if not _FIELD_KEY.match(key):
            raise ValueError(f'invalid_custom_field_key:{key or index+1}')
        if key in keys:
            raise ValueError(f'duplicate_custom_field_key:{key}')
        keys.add(key)
        field_type=str(raw.get('type') or 'text').strip().lower()
        if field_type not in MEMBER_CUSTOM_FIELD_TYPES:
            raise ValueError(f'unsupported_custom_field_type:{field_type}')
        label=str(raw.get('label') or key.replace('_',' ').title()).strip()
        if not label or len(label)>120:
            raise ValueError(f'invalid_custom_field_label:{key}')
        row={
            'key':key,
            'label':label,
            'type':field_type,
            'required':bool(raw.get('required',False)),
            'display_order':_bounded_int(raw.get('display_order'),default=index,minimum=0,maximum=10000,code=f'invalid_custom_field_display_order:{key}'),
        }
        if field_type=='select':
            options=raw.get('options') or []
            if not isinstance(options,list) or not options or len(options)>100:
                raise ValueError(f'invalid_custom_field_options:{key}')
            normalized=[]
            for option in options:
                value=str(option).strip()
                if not value or len(value)>120:
                    raise ValueError(f'invalid_custom_field_options:{key}')
                if value not in normalized:
                    normalized.append(value)
            row['options']=normalized
        clean.append(row)
    return sorted(clean,key=lambda x:(x['display_order'],x['key']))


def normalize_candidate_stages(stages, used_stages=()):
    if not isinstance(stages,list) or len(stages)<2 or len(stages)>50:
        raise ValueError('candidate_stages_must_have_2_to_50_items')
    clean=[]
    for raw in stages:
        stage=str(raw or '').strip()
        if not _STAGE.match(stage):
            raise ValueError(f'invalid_candidate_stage:{stage}')
        if stage in clean:
            raise ValueError(f'duplicate_candidate_stage:{stage}')
        clean.append(stage)
    used={str(x).strip() for x in (used_stages or ()) if str(x).strip()}
    missing=sorted(used-set(clean))
    if missing:
        raise ValueError('candidate_stages_in_use:'+','.join(missing))
    return clean
