from __future__ import annotations

import base64
import hashlib
import hmac
import time
from collections import defaultdict
from decimal import Decimal, InvalidOperation


class _RequestsTransport:
 def post(self,url,**kwargs):
  import requests
  response=requests.post(url,timeout=(5,20),**kwargs);response.raise_for_status();return response.json()


class _HTTP:
 def __init__(self,secret_key,*,transport=None):self.secret_key=str(secret_key or '');self.transport=transport or _RequestsTransport()
 def post(self,url,**kwargs):return self.transport.post(url,**kwargs)
 def basic_auth_headers(self):
  token=base64.b64encode((self.secret_key+':').encode()).decode();return {'Authorization':f'Basic {token}','Content-Type':'application/json','Accept':'application/json'}


class StripeAdapter(_HTTP):
 @staticmethod
 def parse_webhook(payload,signature,secret,tolerance=300,*,sdk=None):
  """Verify and construct a Stripe event using Stripe's official SDK."""
  if not secret or not signature:raise ValueError('stripe_signature_required')
  if sdk is None:import stripe as sdk
  event=sdk.Webhook.construct_event(payload,signature,secret,tolerance=tolerance)
  return event.to_dict_recursive() if hasattr(event,'to_dict_recursive') else dict(event)
 @staticmethod
 def verify_signature(payload,signature,secret,tolerance=300,*,sdk=None):
  try:StripeAdapter.parse_webhook(payload,signature,secret,tolerance,sdk=sdk);return True
  except Exception:return False
 def create_checkout_session(self,encoded,idempotency_key):return self.post('https://api.stripe.com/v1/checkout/sessions',data=encoded,headers={'Authorization':f'Bearer {self.secret_key}','Content-Type':'application/x-www-form-urlencoded','Idempotency-Key':idempotency_key})
 def create_customer_portal_session(self,encoded,idempotency_key):return self.post('https://api.stripe.com/v1/billing_portal/sessions',data=encoded,headers={'Authorization':f'Bearer {self.secret_key}','Content-Type':'application/x-www-form-urlencoded','Idempotency-Key':idempotency_key})


class PayMongoAdapter(_HTTP):
 @staticmethod
 def verify_signature(payload,signature,secret,*,mode='live',tolerance=300,now=None):
  if not secret or not signature or mode not in {'test','live'}:return False
  values=defaultdict(list)
  for part in str(signature).split(','):
   if '=' in part:key,value=part.strip().split('=',1);values[key].append(value)
  timestamp=(values.get('t') or [''])[0];signature_key='te' if mode=='test' else 'li'
  try:
   signed_at=int(timestamp)
   if abs(float(time.time() if now is None else now)-signed_at)>max(1,int(tolerance)):return False
  except (TypeError,ValueError):return False
  expected=hmac.new(str(secret).encode(),timestamp.encode()+b'.'+payload,hashlib.sha256).hexdigest();return any(hmac.compare_digest(expected,candidate) for candidate in values.get(signature_key,[]))
 def create_link(self,amount,description,remarks,*,currency='PHP'):
  try:minor_amount=int(amount)
  except (TypeError,ValueError) as exc:raise ValueError('invalid_paymongo_amount') from exc
  currency=str(currency or '').upper()
  if minor_amount<100 or len(currency)!=3:raise ValueError('invalid_paymongo_payment_link')
  reference=str(remarks or '')[:255]
  return self.post('https://api.paymongo.com/v1/payment_links',json={'amount':minor_amount,'currency':currency,'description':str(description)[:255],'remarks':reference,'metadata':{'internal_reference':reference}},headers=self.basic_auth_headers())


class XenditAdapter(_HTTP):
 @staticmethod
 def verify_callback_token(expected,received):return bool(expected and received and hmac.compare_digest(str(expected),str(received)))
 def create_payment_request(self,reference_id,amount,currency='PHP',country='PH'):
  try:request_amount=Decimal(str(amount))
  except (InvalidOperation,TypeError,ValueError) as exc:raise ValueError('invalid_xendit_amount') from exc
  currency=str(currency or '').upper();country=str(country or '').upper();reference=str(reference_id or '')
  if request_amount<=0 or len(currency)!=3 or len(country)!=2 or not reference:raise ValueError('invalid_xendit_payment_request')
  headers={**self.basic_auth_headers(),'api-version':'2024-11-11','Idempotency-key':reference};payload={'reference_id':reference,'type':'PAY','country':country,'currency':currency,'request_amount':float(request_amount),'capture_method':'AUTOMATIC'}
  return self.post('https://api.xendit.co/v3/payment_requests',json=payload,headers=headers)
