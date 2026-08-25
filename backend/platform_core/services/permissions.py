from functools import wraps
from django.http import JsonResponse
from ..domain.permissions import has_permission, effective_custom_permissions

def permission_required(permission):
 def deco(fn):
  @wraps(fn)
  def wrapped(request,*args,**kwargs):
   if not getattr(request,'user',None) or not request.user.is_authenticated:return JsonResponse({'error':'authentication_required'},status=401)
   membership=getattr(request,'tenant_membership',None)
   if not membership or not getattr(request,'tenant',None):return JsonResponse({'error':'tenant_required'},status=403)
   if not has_permission(membership.role,permission,effective_custom_permissions(membership)):return JsonResponse({'error':'forbidden','permission':permission},status=403)
   return fn(request,*args,**kwargs)
  return wrapped
 return deco
