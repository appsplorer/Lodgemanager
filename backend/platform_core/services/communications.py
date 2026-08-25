from __future__ import annotations

from django.db.models import Q

from ..models import Member, TenantMembership
from ..domain.permissions import has_permission, effective_custom_permissions
from .template_rendering import render_template, validate_merge_fields


def _administrative_notice_bypasses_opt_out(campaign) -> bool:
    policy = ((campaign.tenant.settings or {}).get('communications') or {})
    return bool(campaign.administrative_notice and policy.get('required_administrative_notices', False))


def campaign_members(campaign):
    """Resolve campaign recipients server-side from the persisted segment definition and consent state."""
    segment = campaign.segment or {}
    qs = Member.objects.filter(tenant=campaign.tenant).exclude(email='')
    statuses = segment.get('member_status') or segment.get('status')
    if statuses:
        if not isinstance(statuses, list):
            statuses = [statuses]
        qs = qs.filter(status__in=[str(x) for x in statuses])
    else:
        qs = qs.filter(status='active')

    tags = segment.get('tags') or segment.get('groups') or []
    if not isinstance(tags, list):
        tags = [tags]
    for tag in [str(x).strip() for x in tags if str(x).strip()]:
        qs = qs.filter(tags__contains=[tag])

    arrears_state = str(segment.get('dues_state') or '').strip().lower()
    if arrears_state in {'arrears', 'overdue', 'open'}:
        qs = qs.filter(dues_assessments__status__in=['open', 'partial', 'overdue'])
    elif arrears_state in {'clear', 'paid'}:
        qs = qs.exclude(dues_assessments__status__in=['open', 'partial', 'overdue'])

    candidate_status = str(segment.get('candidate_status') or '').strip()
    if candidate_status:
        qs = qs.filter(candidate_profile__status=candidate_status)

    search = str(segment.get('search') or '').strip()
    if search:
        qs = qs.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search))

    if not _administrative_notice_bypasses_opt_out(campaign):
        # Explicit consent/preferences are server-side filters, never a UI-only warning.
        qs = qs.exclude(communication_preferences__email='opt_out')
        qs = qs.exclude(communication_preferences__email=False)
        qs = qs.exclude(communication_preferences__marketing='opt_out')
        qs = qs.exclude(communication_preferences__marketing=False)

    return qs.distinct().order_by('last_name', 'first_name', 'id')


def campaign_actor_is_still_authorized(campaign) -> bool:
    if not campaign.created_by_id or not campaign.created_by or not campaign.created_by.is_active:
        return False
    membership = TenantMembership.objects.filter(
        tenant=campaign.tenant, user=campaign.created_by, is_active=True, tenant__is_active=True
    ).select_related('custom_role').first()
    if not membership:
        return False
    return has_permission(membership.role, 'communications.edit', effective_custom_permissions(membership))


def member_message_context(member, tenant):
    return {
        'member.first_name': member.first_name,
        'member.last_name': member.last_name,
        'member.email': member.email,
        'member.phone': member.phone,
        'member.address': member.address,
        'member.status': member.status,
        'member.degree': member.degree,
        'member.joined_on': member.joined_on.isoformat() if member.joined_on else '',
        'lodge.name': tenant.name,
        'lodge.number': tenant.lodge_number,
        'lodge.jurisdiction': tenant.jurisdiction,
        'lodge.locale': tenant.locale,
    }


def render_campaign_for_member(campaign, member):
    context = member_message_context(member, campaign.tenant)
    validate_merge_fields([], campaign.subject, campaign.body)
    return render_template(campaign.subject, context), render_template(campaign.body, context)
