from functools import wraps
from django.http import JsonResponse
from ..models import PlatformRoleAssignment
ROLE_PERMISSIONS={
 'super_admin':{'*'},
 'support_admin':{'tenants.view','tenants.edit','users.view','users.edit','logs.view','features.view','features.edit','impersonation.create'},
 'billing_admin':{'tenants.view','billing.view','billing.edit','credentials.billing'},
 'compliance_auditor':{'tenants.view','logs.view','billing.view','users.view'},
 'operator_devops':{'tenants.view','logs.view','features.view','features.edit','credentials.infrastructure'},
}
def user_has_platform_permission(user,permission):
 if not user or not user.is_authenticated:return False
 if user.is_superuser:return True
 roles=PlatformRoleAssignment.objects.filter(user=user,is_active=True).values_list('role',flat=True)
 return any('*' in ROLE_PERMISSIONS.get(r,set()) or permission in ROLE_PERMISSIONS.get(r,set()) for r in roles)
def platform_permission_required(permission):
 def deco(fn):
  @wraps(fn)
  def wrapped(request,*args,**kwargs):
   if not getattr(request,'user',None) or not request.user.is_authenticated:return JsonResponse({'error':'authentication_required'},status=401)
   if not user_has_platform_permission(request.user,permission):return JsonResponse({'error':'platform_forbidden','permission':permission},status=403)
   return fn(request,*args,**kwargs)
  return wrapped
 return deco
