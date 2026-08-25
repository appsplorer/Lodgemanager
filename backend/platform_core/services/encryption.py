import base64,hashlib,json,os
from cryptography.fernet import Fernet,InvalidToken
from django.conf import settings

def _keys():
 raw=str(getattr(settings,'CREDENTIAL_ENCRYPTION_KEYS','') or os.getenv('CREDENTIAL_ENCRYPTION_KEYS','')).strip()
 if raw:return [x.strip().encode() for x in raw.split(',') if x.strip()]
 if settings.DEBUG:
  digest=hashlib.sha256(settings.SECRET_KEY.encode()).digest();return [base64.urlsafe_b64encode(digest)]
 raise RuntimeError('CREDENTIAL_ENCRYPTION_KEYS is required in production')
def encrypt_json(value):return Fernet(_keys()[0]).encrypt(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).decode()
def decrypt_json(token):
 last=None
 for key in _keys():
  try:return json.loads(Fernet(key).decrypt(token.encode()).decode())
  except InvalidToken as exc:last=exc
 raise ValueError('credential_decryption_failed') from last
