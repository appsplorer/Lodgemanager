#!/usr/bin/env python3
"""External LodgeFlow availability/TLS monitor.

Run from a host outside the application stack (cron/systemd/monitoring runner) so
service-down conditions can still be detected. It intentionally sends only
operational metadata, never tenant/user data.
"""
from __future__ import annotations
import json, os, shutil, socket, ssl, sys
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BASE=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
WEBHOOK=os.environ.get('ALERT_WEBHOOK_URL','').strip()
WARN_DAYS=int(os.environ.get('TLS_WARN_DAYS','21'))
TIMEOUT=float(os.environ.get('MONITOR_TIMEOUT_SECONDS','8'))
BACKUP_STATUS_FILE=os.environ.get('BACKUP_STATUS_FILE','/var/lib/lodgeflow-backups/latest-success.json')
BACKUP_MAX_AGE_HOURS=float(os.environ.get('BACKUP_MAX_AGE_HOURS','26'))
DISK_PATH=os.environ.get('DISK_MONITOR_PATH','/')
DISK_WARN_PERCENT=float(os.environ.get('DISK_WARN_PERCENT','85'))


def http_json(path:str):
    req=Request(BASE+path,headers={'User-Agent':'LodgeFlow-External-Monitor/1.0'})
    with urlopen(req,timeout=TIMEOUT) as r:
        body=r.read(131072)
        return r.status,json.loads(body.decode('utf-8'))


def tls_days_remaining():
    parsed=urlparse(BASE)
    if parsed.scheme!='https': return None
    host=parsed.hostname;port=parsed.port or 443
    context=ssl.create_default_context()
    with socket.create_connection((host,port),timeout=TIMEOUT) as raw:
        with context.wrap_socket(raw,server_hostname=host) as sock:
            cert=sock.getpeercert()
    expiry=datetime.strptime(cert['notAfter'],'%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
    return (expiry-datetime.now(timezone.utc)).total_seconds()/86400


def notify(payload):
    if not WEBHOOK:return
    data=json.dumps(payload,separators=(',',':')).encode()
    req=Request(WEBHOOK,data=data,headers={'Content-Type':'application/json','User-Agent':'LodgeFlow-External-Monitor/1.0'},method='POST')
    with urlopen(req,timeout=TIMEOUT) as r:r.read(4096)


def main():
    if not BASE.startswith(('http://','https://')):
        raise SystemExit('PUBLIC_BASE_URL must be an absolute http(s) URL')
    failures=[];result={'service':'lodgeflow','checked_at':datetime.now(timezone.utc).isoformat(),'base_url':BASE}
    for name,path in [('liveness','/api/health/'),('readiness','/api/ready/')]:
        try:
            status,data=http_json(path);result[name]={'http_status':status,'status':data.get('status')}
            if status!=200:failures.append(f'{name}_http_{status}')
            if name=='readiness':
                for component,healthy in (data.get('checks') or {}).items():
                    if not healthy:failures.append(f'readiness_{component}')
        except Exception as exc:
            result[name]={'status':'failed','error_type':type(exc).__name__};failures.append(f'{name}_failed')
    try:
        days=tls_days_remaining();result['tls_days_remaining']=None if days is None else round(days,2)
        if days is not None and days<WARN_DAYS:failures.append('tls_expiring')
    except Exception as exc:
        result['tls']={'status':'failed','error_type':type(exc).__name__};failures.append('tls_check_failed')
    try:
        modified=datetime.fromtimestamp(os.stat(BACKUP_STATUS_FILE).st_mtime,tz=timezone.utc)
        age_hours=(datetime.now(timezone.utc)-modified).total_seconds()/3600
        result['backup']={'status_file':BACKUP_STATUS_FILE,'age_hours':round(age_hours,2),'max_age_hours':BACKUP_MAX_AGE_HOURS}
        if age_hours>BACKUP_MAX_AGE_HOURS:failures.append('backup_stale')
    except OSError as exc:
        result['backup']={'status':'missing','error_type':type(exc).__name__};failures.append('backup_stale')
    try:
        usage=shutil.disk_usage(DISK_PATH);used_percent=(usage.used/usage.total*100) if usage.total else 100.0
        result['disk_capacity']={'path':DISK_PATH,'used_percent':round(used_percent,2),'free_bytes':usage.free,'warn_percent':DISK_WARN_PERCENT}
        if used_percent>=DISK_WARN_PERCENT:failures.append('disk_capacity')
    except OSError as exc:
        result['disk_capacity']={'status':'failed','error_type':type(exc).__name__};failures.append('disk_capacity')
    result['ok']=not failures;result['failures']=failures
    if failures:
        try:notify(result)
        except Exception as exc:result['notification_error']=type(exc).__name__
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if not failures else 2

if __name__=='__main__':sys.exit(main())
