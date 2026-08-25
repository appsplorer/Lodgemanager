from __future__ import annotations

import re


TOKEN = re.compile(r'\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}')
ALLOWED_MERGE_FIELDS = {
    'member.first_name', 'member.last_name', 'member.email', 'member.phone',
    'member.address', 'member.status', 'member.degree', 'member.joined_on',
    'lodge.name', 'lodge.number', 'lodge.jurisdiction', 'lodge.locale',
    'document.generated_date', 'document.generated_at',
}


class TemplateRenderError(ValueError):
    def __init__(self, code, fields=None):
        self.code = code
        self.fields = sorted(set(fields or []))
        super().__init__(code)


def extract_merge_fields(*parts: str):
    fields = set()
    for part in parts:
        fields.update(TOKEN.findall(str(part or '')))
    return sorted(fields)


def validate_merge_fields(declared, *parts):
    if declared is None:
        declared = []
    if not isinstance(declared, list) or any(not isinstance(x, str) for x in declared):
        raise TemplateRenderError('merge_fields_must_be_string_list')
    used = extract_merge_fields(*parts)
    unknown = [x for x in used if x not in ALLOWED_MERGE_FIELDS]
    if unknown:
        raise TemplateRenderError('unknown_or_unsafe_merge_fields', unknown)
    declared_clean = sorted(set(x.strip() for x in declared if x.strip()))
    undeclared = [x for x in used if x not in declared_clean]
    if declared_clean and undeclared:
        raise TemplateRenderError('template_uses_undeclared_merge_fields', undeclared)
    invalid_declared = [x for x in declared_clean if x not in ALLOWED_MERGE_FIELDS]
    if invalid_declared:
        raise TemplateRenderError('unknown_or_unsafe_declared_merge_fields', invalid_declared)
    return used if not declared_clean else declared_clean


def render_template(text: str, context: dict, declared=None):
    fields = validate_merge_fields(declared or [], text)
    missing = [x for x in fields if x not in context]
    if missing:
        raise TemplateRenderError('missing_merge_context', missing)
    return TOKEN.sub(lambda match: str(context.get(match.group(1), '')), str(text or ''))
