import hashlib
import json
from copy import deepcopy

from django.conf import settings
from django.db import connection, transaction

from ..models import AuditEvent
from .client_ip import client_ip

SECRET_TOKENS={'password','secret','secret_key','webhook_secret','callback_token','api_key','private_key','token','access_token','refresh_token','authorization','credential','ciphertext'}


def _json(v): return json.dumps(v or {},sort_keys=True,separators=(',',':'),default=str)

def _ip(request):
    if request is None:return ''
    raw=client_ip(request)
    return hashlib.sha256((settings.SECRET_KEY+'|'+raw).encode()).hexdigest() if raw else ''


def scrub_sensitive(value):
    """Recursively redact secret-bearing values before durable audit persistence."""
    if isinstance(value,dict):
        clean={}
        for key,item in value.items():
            lower=str(key).lower().replace('-','_')
            clean[key]='[REDACTED]' if any(token in lower for token in SECRET_TOKENS) else scrub_sensitive(item)
        return clean
    if isinstance(value,list):return [scrub_sensitive(x) for x in value]
    if isinstance(value,tuple):return [scrub_sensitive(x) for x in value]
    return value


def append_audit(request=None,actor=None,tenant=None,action='',object_type='',object_id='',before=None,after=None,metadata=None):
    actor=actor or (getattr(request,'user',None) if request is not None and getattr(request,'user',None) and request.user.is_authenticated else None)
    tenant=tenant or (getattr(request,'tenant',None) if request is not None else None)
    tenant_key=str(getattr(tenant,'id','platform'))
    clean_before=scrub_sensitive(deepcopy(before or {}));clean_after=scrub_sensitive(deepcopy(after or {}));clean_metadata=scrub_sensitive(deepcopy(metadata or {}))
    with transaction.atomic():
        if connection.vendor=='postgresql':
            with connection.cursor() as c:c.execute('SELECT pg_advisory_xact_lock(hashtext(%s))',[f'lodgeflow:audit:{tenant_key}'])
        previous=AuditEvent.objects.filter(tenant=tenant).order_by('-occurred_at','-id').first();prev_hash=previous.event_hash if previous else ''
        payload={'tenant':tenant_key,'actor':getattr(actor,'id',None),'action':action,'object_type':object_type,'object_id':str(object_id or ''),'before':clean_before,'after':clean_after,'metadata':clean_metadata,'prev_hash':prev_hash}
        event_hash=hashlib.sha256((prev_hash+'|'+_json(payload)).encode()).hexdigest()
        return AuditEvent.objects.create(tenant=tenant,actor=actor,action=action,object_type=object_type or '',object_id=str(object_id or ''),request_id=(request.headers.get('X-Request-ID','')[:80] if request is not None else ''),ip_hash=_ip(request),user_agent=((request.headers.get('User-Agent','')[:255]) if request is not None else ''),before=clean_before,after=clean_after,metadata=clean_metadata,prev_hash=prev_hash,event_hash=event_hash)


def verify_audit_chain(tenant=None):
    """Verify the append-only tenant chain by stored hash links, independent of wall-clock ordering."""
    events=list(AuditEvent.objects.filter(tenant=tenant).only(
        'id','tenant_id','actor_id','action','object_type','object_id','before','after','metadata','prev_hash','event_hash'
    ))
    if not events:return {'valid':True,'checked':0,'head_hash':''}
    by_prev={}
    by_hash={}
    for event in events:
        if not event.event_hash:
            return {'valid':False,'checked':0,'broken_event_id':str(event.id),'reason':'missing_event_hash'}
        by_hash[event.event_hash]=event
        by_prev.setdefault(event.prev_hash or '',[]).append(event)
    roots=by_prev.get('',[])
    if len(roots)!=1:
        return {'valid':False,'checked':0,'reason':'invalid_chain_root_count','root_count':len(roots)}
    previous='';checked=0;seen=set();event=roots[0]
    while event:
        if str(event.id) in seen:
            return {'valid':False,'checked':checked,'broken_event_id':str(event.id),'reason':'cycle_detected'}
        seen.add(str(event.id));tenant_key=str(event.tenant_id or 'platform')
        payload={'tenant':tenant_key,'actor':event.actor_id,'action':event.action,'object_type':event.object_type,'object_id':str(event.object_id or ''),'before':event.before or {},'after':event.after or {},'metadata':event.metadata or {},'prev_hash':previous}
        expected=hashlib.sha256((previous+'|'+_json(payload)).encode()).hexdigest()
        if event.prev_hash!=previous or event.event_hash!=expected:
            return {'valid':False,'checked':checked,'broken_event_id':str(event.id),'reason':'hash_mismatch','expected_previous':previous,'stored_previous':event.prev_hash}
        previous=event.event_hash;checked+=1
        children=by_prev.get(previous,[])
        if len(children)>1:
            return {'valid':False,'checked':checked,'broken_event_id':str(event.id),'reason':'chain_branch_detected','child_count':len(children)}
        event=children[0] if children else None
    if checked!=len(events):
        return {'valid':False,'checked':checked,'reason':'orphaned_events','total_events':len(events)}
    return {'valid':True,'checked':checked,'head_hash':previous}
