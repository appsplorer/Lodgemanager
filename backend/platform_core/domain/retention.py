"""Validated lifecycle policy that never purges protected audit or finance records."""

from datetime import date


CONFIGURABLE_CATEGORIES={
    'documents_years':7,
    'generated_reports_years':7,
    'communications_years':7,
    'inactive_members_years':7,
}


def _years(value, default):
    if value in (None,''):return default
    try:parsed=int(value)
    except (TypeError,ValueError) as exc:raise ValueError('invalid_retention_years') from exc
    if parsed<1 or parsed>50:raise ValueError('invalid_retention_years')
    return parsed


def normalize_retention_policy(policy):
    if policy in (None,''):policy={}
    if not isinstance(policy,dict):raise ValueError('retention_policy_must_be_object')
    incoming=dict(policy)
    if 'inactive_members_years' not in incoming and 'members_years' in incoming:
        incoming['inactive_members_years']=incoming['members_years']
    normalized={key:_years(incoming.get(key),default) for key,default in CONFIGURABLE_CATEGORIES.items()}
    normalized.update({'audit':'preserve','finance':'preserve'})
    return normalized


def retention_cutoff(today, years):
    try:return today.replace(year=today.year-int(years))
    except ValueError:return today.replace(year=today.year-int(years),day=28)
