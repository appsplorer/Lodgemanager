class ApiCacheControlMiddleware:
 def __init__(self,get_response):self.get_response=get_response
 def __call__(self,request):
  response=self.get_response(request)
  if request.path.startswith('/api/public/'):
   response.setdefault('Cache-Control','public, max-age=60, stale-while-revalidate=300')
  elif request.path.startswith('/api/'):
   response['Cache-Control']='private, no-store, max-age=0';response['Pragma']='no-cache'
  return response
