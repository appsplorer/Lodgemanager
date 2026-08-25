import hashlib
from django.core.cache import cache
from django.http import HttpResponse

CACHEABLE=('/api/dashboard','/api/reports/summary','/api/reports/insights','/api/workspace/bootstrap')
TTL=30

def _version(tenant_id):
    if not tenant_id:return 1
    return int(cache.get(f'lf:tenant-version:{tenant_id}',1) or 1)

def _bump(tenant_id):
    if not tenant_id:return
    key=f'lf:tenant-version:{tenant_id}'
    try:cache.incr(key)
    except ValueError:cache.set(key,2,None)

class ApiReadCacheMiddleware:
    def __init__(self,get_response):self.get_response=get_response
    def __call__(self,request):
        tenant=getattr(request,'tenant',None);user=getattr(request,'user',None);tenant_id=str(tenant.id) if tenant else ''
        eligible=request.method=='GET' and any(request.path.startswith(p) for p in CACHEABLE) and bool(user and user.is_authenticated)
        key=None
        if eligible:
            raw=f'{tenant_id}|{user.id}|{_version(tenant_id)}|{request.get_full_path()}'.encode();key='lf:read:'+hashlib.sha256(raw).hexdigest();hit=cache.get(key)
            if hit:
                status,content_type,body=hit;response=HttpResponse(body,status=status,content_type=content_type);response['X-LodgeFlow-Cache']='HIT';return response
        response=self.get_response(request)
        if key and response.status_code==200 and not getattr(response,'streaming',False) and response.get('Content-Type','').startswith('application/json'):
            cache.set(key,(response.status_code,response.get('Content-Type','application/json'),bytes(response.content)),TTL);response['X-LodgeFlow-Cache']='MISS'
        elif request.method not in {'GET','HEAD','OPTIONS'} and response.status_code<400:
            _bump(tenant_id)
        return response
