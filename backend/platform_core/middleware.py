from __future__ import annotations

import uuid
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone

from .models import ImpersonationSession, TenantMembership
from .services.client_ip import client_ip, client_ip_key


class RequestSecurityHeadersMiddleware:
    """Attach a request id and deliberate browser-security/CORS headers.

    CORS is deny-by-default. Only configured same-origin/explicit origins receive
    Access-Control-Allow-Origin; credentials are never exposed to wildcard origins.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.client_ip = client_ip(request)
        request.ip_hash = client_ip_key(request)
        incoming = (request.headers.get('X-Request-ID') or '').strip()
        request.request_id = incoming[:80] if incoming else str(uuid.uuid4())
        if request.method == 'OPTIONS' and request.path.startswith('/api/'):
            response = JsonResponse({'ok': True})
        else:
            response = self.get_response(request)
        response['X-Request-ID'] = request.request_id
        response['X-Frame-Options'] = 'DENY'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=(self)'
        response['Content-Security-Policy'] = getattr(
            settings,
            'CONTENT_SECURITY_POLICY',
            "default-src 'self'; base-uri 'self'; frame-ancestors 'none'; object-src 'none'; "
            "img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:; "
            "style-src 'self' 'unsafe-inline'; script-src 'self'; form-action 'self'",
        )
        origin = (request.headers.get('Origin') or '').strip()
        allowed = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []))
        if origin and origin in allowed:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Vary'] = 'Origin'
            response['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRFToken, X-Lodge-ID, Idempotency-Key, X-LodgeFlow-Base-Updated-At, X-Request-ID'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        return response


class ImpersonationMiddleware:
    """Apply an audited, time-bounded support impersonation session.

    The original authenticated operator is retained on request.real_user so audit
    records can preserve who initiated the action. Stop is deliberately evaluated
    as the real operator rather than the target user.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.real_user = getattr(request, 'user', None)
        request.impersonation = None
        if request.path == '/api/platform/impersonation/stop':
            return self.get_response(request)
        raw = request.session.get('impersonation_id') if hasattr(request, 'session') else None
        if raw and request.real_user and request.real_user.is_authenticated:
            session = ImpersonationSession.objects.select_related('actor', 'target_user', 'tenant').filter(
                pk=raw, actor=request.real_user, is_active=True, ended_at__isnull=True
            ).first()
            if session:
                if session.expires_at <= timezone.now():
                    session.is_active = False
                    session.ended_at = timezone.now()
                    session.save(update_fields=['is_active', 'ended_at', 'updated_at'])
                    request.session.pop('impersonation_id', None)
                    request.session.pop('impersonated_user_id', None)
                else:
                    request.impersonation = session
                    request.user = session.target_user
        return self.get_response(request)


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.tenant_membership = None
        if request.user.is_authenticated:
            lodge = request.headers.get('X-Lodge-ID')
            qs = TenantMembership.objects.select_related('tenant','custom_role').filter(
                user=request.user, is_active=True, tenant__is_active=True
            )
            # An impersonation session is scoped to exactly one tenant and may not
            # be used to pivot into another membership owned by the target account.
            if getattr(request, 'impersonation', None):
                qs = qs.filter(tenant=request.impersonation.tenant)
                lodge = str(request.impersonation.tenant_id)
            membership = qs.filter(tenant_id=lodge).first() if lodge else qs.first()
            if membership:
                request.tenant = membership.tenant
                request.tenant_membership = membership
        return self.get_response(request)
