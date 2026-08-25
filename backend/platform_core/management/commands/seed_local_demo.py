import os
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from platform_core.models import (
    CMSPage,
    Candidate,
    DuesAssessment,
    DuesCycle,
    LeadForm,
    LodgeProfile,
    Meeting,
    Member,
    NavigationMenu,
    OfficerTerm,
    PlatformRoleAssignment,
    SiteSetting,
    Tenant,
    TenantMembership,
)


class Command(BaseCommand):
    help = "Create/update a safe local QA tenant, administrator and representative demo records."

    def handle(self, *args, **options):
        if os.getenv("DEBUG", "false").lower() != "true":
            self.stderr.write(self.style.ERROR("seed_local_demo is intentionally disabled unless DEBUG=true"))
            return

        username = os.getenv("LOCAL_ADMIN_USERNAME", "admin")
        email = os.getenv("LOCAL_ADMIN_EMAIL", "admin@lodgeflow.local")
        password = os.getenv("LOCAL_ADMIN_PASSWORD", "LodgeFlowLocal123!")
        tenant_name = os.getenv("LOCAL_TENANT_NAME", "Harmony Lodge")
        tenant_slug = os.getenv("LOCAL_TENANT_SLUG", "harmony-lodge")
        tenant_number = os.getenv("LOCAL_TENANT_NUMBER", "1001")
        jurisdiction = os.getenv("LOCAL_TENANT_JURISDICTION", "Local QA")

        User = get_user_model()
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        tenant, _ = Tenant.objects.update_or_create(
            slug=tenant_slug,
            defaults={
                "name": tenant_name,
                "lodge_number": tenant_number,
                "jurisdiction": jurisdiction,
                "timezone": "Europe/London",
                "locale": "en",
                "plan": "annual",
                "is_active": True,
                "settings": {
                    "base_currency": "PHP",
                    "enabled_currencies": ["PHP", "USD", "GBP", "EUR", "SGD", "AUD", "CAD", "JPY"],
                    "branding": {"brand_name": "LodgeFlow", "tagline": "Private Lodge Office"},
                },
            },
        )
        TenantMembership.objects.update_or_create(
            tenant=tenant,
            user=user,
            defaults={"role": "owner", "mfa_required": False, "is_active": True},
        )
        role_password = os.getenv("LOCAL_ROLE_PASSWORD", password)
        for role in ("secretary", "treasurer", "membership", "mentor", "auditor", "viewer"):
            role_user, _ = User.objects.get_or_create(username=f"local-{role}", defaults={"email": f"{role}@lodgeflow.local"})
            role_user.email = f"{role}@lodgeflow.local"
            role_user.is_active = True
            role_user.is_staff = False
            role_user.is_superuser = False
            role_user.set_password(role_password)
            role_user.save()
            TenantMembership.objects.update_or_create(
                tenant=tenant,
                user=role_user,
                defaults={"role": role, "mfa_required": False, "is_active": True},
            )
        LodgeProfile.objects.get_or_create(
            tenant=tenant,
            defaults={
                "address": "Local QA Lodge Hall",
                "meeting_schedule": {"summary": "Second Thursday · 19:00"},
            },
        )
        PlatformRoleAssignment.objects.update_or_create(
            user=user,
            role="super_admin",
            defaults={"is_active": True},
        )

        members = []
        demo_people = [
            ("Arthur", "Bennett", "mentor@lodgeflow.local", "MM"),
            ("James", "Carter", "james@example.test", "MM"),
            ("Michael", "Davies", "michael@example.test", "FC"),
            ("Daniel", "Evans", "daniel@example.test", "EA"),
            ("Samuel", "Foster", "samuel@example.test", "MM"),
            ("Oliver", "Grant", "oliver@example.test", "none"),
        ]
        for index, (first, last, member_email, degree) in enumerate(demo_people, start=1):
            member, _ = Member.objects.update_or_create(
                tenant=tenant,
                email=member_email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "status": "candidate" if degree == "none" else "active",
                    "degree": degree,
                    "phone": f"+44 7700 900{index:03d}",
                    "joined_on": timezone.localdate() - timedelta(days=365 * (index + 1)),
                    "tags": ["local-demo"],
                    "notes": "Synthetic record created only for local LodgeFlow QA.",
                },
            )
            members.append(member)

        OfficerTerm.objects.update_or_create(
            tenant=tenant,
            member=members[0],
            office="Worshipful Master",
            starts_on=timezone.localdate().replace(month=1, day=1),
            defaults={"is_current": True, "successor": members[1]},
        )
        OfficerTerm.objects.update_or_create(
            tenant=tenant,
            member=members[1],
            office="Secretary",
            starts_on=timezone.localdate().replace(month=1, day=1),
            defaults={"is_current": True, "successor": members[2]},
        )
        Candidate.objects.update_or_create(
            tenant=tenant,
            member=members[-1],
            defaults={
                "stage": "enquiry",
                "stage_order": 1,
                "mentor": members[0],
                "target_degree_date": timezone.localdate() + timedelta(days=45),
                "status": "active",
            },
        )

        start = timezone.now() + timedelta(days=7)
        Meeting.objects.update_or_create(
            tenant=tenant,
            title="September Stated Meeting",
            defaults={
                "meeting_type": "stated",
                "starts_at": start,
                "ends_at": start + timedelta(hours=2),
                "location": "Local QA Lodge Hall",
                "agenda": ["Opening", "Minutes", "Correspondence", "Treasurer report", "Closing"],
                "status": "scheduled",
            },
        )

        year = timezone.localdate().year
        cycle, _ = DuesCycle.objects.update_or_create(
            tenant=tenant,
            name=f"Annual Dues {year}",
            defaults={
                "period_start": timezone.localdate().replace(month=1, day=1),
                "period_end": timezone.localdate().replace(month=12, day=31),
                "due_on": timezone.localdate().replace(month=3, day=31),
                "standard_amount": Decimal("5000.00"),
                "late_fee": Decimal("250.00"),
                "proration_enabled": True,
                "is_open": True,
                "status": "active",
            },
        )
        for member in members[:-1]:
            DuesAssessment.objects.get_or_create(
                tenant=tenant,
                member=member,
                cycle=cycle,
                defaults={"amount": Decimal("5000.00"), "status": "open"},
            )

        SiteSetting.objects.update_or_create(
            key="workspace_theme",
            defaults={
                "is_public": True,
                "value": {
                    "preset": "heritage",
                    "brand_name": "LodgeFlow",
                    "tagline": "Private Lodge Office",
                    "primary": "#0c2830",
                    "primary_alt": "#123841",
                    "accent": "#c49a54",
                    "radius": 18,
                    "density": "comfortable",
                },
            },
        )
        CMSPage.objects.update_or_create(
            slug="home",
            locale="en",
            defaults={
                "title": "LodgeFlow",
                "status": "published",
                "meta_title": "LodgeFlow · Private Lodge Administration",
                "meta_description": "Secure lodge administration for members, meetings, candidates, dues, finance, documents, communications and reporting.",
                "blocks": [
                    {
                        "type": "hero",
                        "eyebrow": "Private lodge administration",
                        "title": "Run the Lodge office with clarity, continuity and control.",
                        "body": "One secure workspace for members, officers, candidates, meetings, dues, finance, documents, communications and reporting.",
                        "primary_label": "Open workspace",
                        "primary_href": "/login",
                        "secondary_label": "Explore features",
                        "secondary_href": "#features",
                    },
                    {
                        "type": "features",
                        "eyebrow": "Built around lodge work",
                        "title": "Everything officers need, without spreadsheet sprawl.",
                        "items": [
                            {"title": "Member records", "body": "Profiles, degrees, dates, custom fields, notes and governed import/export."},
                            {"title": "Meetings & minutes", "body": "Agenda, attendance, visitors and controlled minutes approval."},
                            {"title": "Dues & finance", "body": "Assessments, receipts, arrears, expenses and finance reporting."},
                            {"title": "Offline continuity", "body": "Encrypted cached records and conflict-aware queued routine edits."},
                        ],
                    },
                    {
                        "type": "security",
                        "eyebrow": "Private by design",
                        "title": "Your Lodge records stay inside your Lodge.",
                        "items": [
                            {"title": "Tenant isolation", "body": "Server-side tenant scoping for authenticated Lodge work."},
                            {"title": "Granular RBAC", "body": "Purpose-specific officer and platform permissions."},
                            {"title": "MFA & audit", "body": "TOTP MFA and tamper-evident audit history for privileged actions."},
                        ],
                    },
                    {
                        "type": "cta",
                        "eyebrow": "Ready for continuity",
                        "title": "One system the next Secretary can actually inherit.",
                        "primary_label": "Enter LodgeFlow",
                        "primary_href": "/login",
                    },
                ],
            },
        )
        NavigationMenu.objects.update_or_create(
            key="main",
            locale="en",
            defaults={
                "items": [
                    {"label": "Features", "href": "#features"},
                    {"label": "Security", "href": "#security"},
                    {"label": "Sign in", "href": "/login"},
                ]
            },
        )
        LeadForm.objects.update_or_create(
            key="demo-request",
            defaults={
                "name": "Demo request",
                "is_active": True,
                "fields": [
                    {"key": "name", "label": "Name", "type": "text", "required": True},
                    {"key": "email", "label": "Email", "type": "email", "required": True},
                    {"key": "message", "label": "Message", "type": "textarea", "required": False},
                ],
                "routing": {"to": email},
            },
        )

        self.stdout.write(self.style.SUCCESS("Local LodgeFlow demo data is ready."))
        self.stdout.write(f"Frontend: http://localhost:3000")
        self.stdout.write(f"Django API: http://localhost:8000/api/health/")
        self.stdout.write(f"Mailpit: http://localhost:8025")
        self.stdout.write(f"Login: {email} / {password}")
        self.stdout.write(self.style.WARNING("These credentials are LOCAL QA defaults only. Never reuse them on a server."))
