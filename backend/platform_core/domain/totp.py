import base64,hmac,hashlib,secrets,struct,time

def generate_secret():return base64.b32encode(secrets.token_bytes(20)).decode().rstrip('=')
def _code(secret,counter):
 padded=secret+'='*((8-len(secret)%8)%8);key=base64.b32decode(padded,casefold=True);msg=struct.pack('>Q',counter);digest=hmac.new(key,msg,hashlib.sha1).digest();off=digest[-1]&15;num=(struct.unpack('>I',digest[off:off+4])[0]&0x7fffffff)%1000000;return f'{num:06d}'
def verify_totp(secret,code,last_counter=None,window=1,step=30):
 now=int(time.time()//step)
 for counter in range(now-window,now+window+1):
  if last_counter is not None and counter<=last_counter:continue
  if hmac.compare_digest(_code(secret,counter),str(code).zfill(6)):return True,counter
 return False,None
