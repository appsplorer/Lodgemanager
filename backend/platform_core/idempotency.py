from datetime import timedelta
from django.http import HttpResponse,JsonResponse
from django.utils import timezone
from django.db import IntegrityError,transaction
from .models import IdempotencyReceipt
SAFE={'GET','HEAD','OPTIONS'}
class IdempotencyMiddleware:
 def __init__(self,get_response): self.get_response=get_response
 def __call__(self,request):
  if request.method in SAFE:return self.get_response(request)
  key=request.headers.get('Idempotency-Key','').strip()
  if not key:return self.get_response(request)
  if len(key)>80:return JsonResponse({'error':'invalid_idempotency_key'},status=400)
  tenant=getattr(request,'tenant',None);uid=request.user.id if getattr(request,'user',None) and request.user.is_authenticated else None
  now=timezone.now();existing=IdempotencyReceipt.objects.filter(tenant=tenant,user_id=uid,key=key,expires_at__gt=now).first()
  if existing:
   return HttpResponse(bytes(existing.response_body),status=existing.status_code,content_type=existing.content_type or 'application/json')
  response=self.get_response(request)
  if response.status_code<500 and not getattr(response,'streaming',False) and response.get('Content-Type','').startswith('application/json') and len(getattr(response,'content',b''))<=262144:
   try:
    with transaction.atomic():
     IdempotencyReceipt.objects.create(tenant=tenant,user_id=uid,key=key,method=request.method,path=request.path,status_code=response.status_code,content_type=response.get('Content-Type','application/json'),response_body=bytes(response.content),expires_at=now+timedelta(days=2))
   except IntegrityError: pass
  return response
