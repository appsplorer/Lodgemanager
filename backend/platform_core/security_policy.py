import ipaddress
from datetime import datetime,timezone as dt_timezone
from django.contrib.auth import logout
from django.http import JsonResponse
from django.utils import timezone
from .services.client_ip import client_ip

EXEMPT_PREFIXES=('/api/auth/','/api/mfa/','/api/public/','/api/webhooks/','/api/health','/api/csrf')
def _allowed_ip(ip,allowed):
 if not allowed:return True
 try:addr=ipaddress.ip_address(ip);return any(addr in ipaddress.ip_network(str(net),strict=False) for net in allowed)
 except ValueError:return False
class SecurityPolicyMiddleware:
 def __init__(self,get_response):self.get_response=get_response
 def __call__(self,request):
  if not request.path.startswith('/api/') or request.path.startswith(EXEMPT_PREFIXES):return self.get_response(request)
  user=getattr(request,'user',None)
  if not user or not user.is_authenticated:return self.get_response(request)
  membership=getattr(request,'tenant_membership',None);tenant=getattr(request,'tenant',None);security=((tenant.settings or {}).get('security') or {}) if tenant else {}
  if tenant and not _allowed_ip(client_ip(request),security.get('ip_allowlist') or []):return JsonResponse({'error':'network_not_allowed'},status=403)
  timeout=max(5,min(int(security.get('session_timeout_minutes',480) or 480),1440));last=request.session.get('last_activity_at')
  if last:
   try:
    then=datetime.fromisoformat(last)
    if then.tzinfo is None:then=then.replace(tzinfo=dt_timezone.utc)
    if (timezone.now()-then).total_seconds()>timeout*60:
     logout(request);return JsonResponse({'error':'session_expired'},status=401)
   except (ValueError,TypeError):pass
  request.session['last_activity_at']=timezone.now().isoformat()
  # Tenant APIs must never reach view code without an active, authorized tenant
  # membership. Platform and identity endpoints deliberately operate outside a
  # tenant context and are handled by their own permission policies.
  tenant_optional=(request.path=='/api/me' or request.path.startswith(('/api/platform/','/api/ready')))
  if not membership and not tenant_optional:return JsonResponse({'error':'tenant_required'},status=403)
  platform_mfa=request.path.startswith('/api/platform/') and (user.is_superuser or user.platform_roles.filter(is_active=True).exists())
  tenant_mfa=bool(membership and membership.mfa_required) or bool(security.get('mfa_required'))
  if (platform_mfa or tenant_mfa) and not request.session.get('mfa_verified_at'):return JsonResponse({'error':'mfa_required','reauthenticate':True},status=403)
  return self.get_response(request)
