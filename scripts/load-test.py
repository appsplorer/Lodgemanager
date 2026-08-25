#!/usr/bin/env python3
"""Authenticated LodgeFlow reference-load runner.

Designed for the protected reference-performance runner described in the SRS. The
reported latency includes HTTP/network overhead, making the 700 ms gate conservative.
"""
from __future__ import annotations
import json, math, os, statistics, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import requests

BASE=os.environ.get('LOAD_BASE_URL','http://127.0.0.1:8080').rstrip('/')
USERNAME=os.environ.get('LOAD_TEST_USERNAME','loadtest@example.test')
PASSWORD=os.environ.get('LOAD_TEST_PASSWORD','')
LODGE=os.environ.get('LOAD_LODGE_ID','')
CONCURRENCY=max(1,int(os.environ.get('LOAD_CONCURRENCY','100')))
DURATION=max(5,int(os.environ.get('LOAD_DURATION_SECONDS','60')))
P95_LIMIT=float(os.environ.get('LOAD_P95_LIMIT_MS','700'))
ERROR_LIMIT=float(os.environ.get('LOAD_ERROR_RATE_LIMIT','0.005'))
RESULT=Path(os.environ.get('LOAD_RESULT_PATH','artifacts/reference-load.json'))
ENDPOINTS=['/api/dashboard','/api/members?limit=100','/api/meetings?limit=100','/api/dues/assessments?limit=100','/api/documents?limit=100','/api/reports/summary']
_thread=threading.local()


def authenticated_session():
    s=requests.Session();s.headers.update({'User-Agent':'LodgeFlow-Reference-Load/1.0','X-Requested-With':'LodgeFlow'})
    r=s.get(BASE+'/api/csrf/',timeout=15);r.raise_for_status();csrf=s.cookies.get('csrftoken')
    r=s.post(BASE+'/api/auth/login',json={'username':USERNAME,'password':PASSWORD},headers={'X-CSRFToken':csrf or ''},timeout=15);r.raise_for_status()
    if LODGE:s.headers['X-Lodge-ID']=LODGE
    return s


def session():
    if not hasattr(_thread,'session'):_thread.session=authenticated_session()
    return _thread.session


def worker(worker_id,deadline):
    lat=[];errors=0;requests_count=0;idx=worker_id%len(ENDPOINTS);s=session()
    while time.monotonic()<deadline:
        path=ENDPOINTS[idx%len(ENDPOINTS)];idx+=1;started=time.perf_counter()
        try:
            r=s.get(BASE+path,timeout=15);elapsed=(time.perf_counter()-started)*1000;requests_count+=1
            if r.status_code>=400:errors+=1
            else:lat.append(elapsed)
        except requests.RequestException:
            requests_count+=1;errors+=1
    return lat,errors,requests_count


def percentile(values,p):
    if not values:return math.inf
    xs=sorted(values);pos=max(0,min(len(xs)-1,math.ceil(p*len(xs))-1));return xs[pos]


def main():
    if len(PASSWORD)<16 or not LODGE:
        print('LOAD_TEST_PASSWORD (>=16 chars) and LOAD_LODGE_ID are required.',file=sys.stderr);return 2
    # Warm the authenticated path before the measured concurrent window.
    warm=authenticated_session()
    for path in ENDPOINTS:
        r=warm.get(BASE+path,timeout=15);r.raise_for_status()
    deadline=time.monotonic()+DURATION;latencies=[];errors=total=0
    started=time.time()
    with ThreadPoolExecutor(max_workers=CONCURRENCY,thread_name_prefix='lodgeflow-load') as pool:
        futures=[pool.submit(worker,i,deadline) for i in range(CONCURRENCY)]
        for f in as_completed(futures):
            lat,err,count=f.result();latencies.extend(lat);errors+=err;total+=count
    elapsed=max(time.time()-started,0.001);error_rate=errors/max(total,1)
    result={'base_url':BASE,'concurrency':CONCURRENCY,'duration_seconds':DURATION,'requests':total,'successful_samples':len(latencies),'errors':errors,'error_rate':error_rate,'requests_per_second':total/elapsed,'latency_ms':{'p50':percentile(latencies,.50),'p95':percentile(latencies,.95),'p99':percentile(latencies,.99),'mean':statistics.mean(latencies) if latencies else math.inf,'max':max(latencies) if latencies else math.inf},'gates':{'p95_limit_ms':P95_LIMIT,'error_rate_limit':ERROR_LIMIT}}
    result['passed']=result['latency_ms']['p95']<=P95_LIMIT and error_rate<=ERROR_LIMIT
    RESULT.parent.mkdir(parents=True,exist_ok=True);RESULT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['passed'] else 1

if __name__=='__main__':sys.exit(main())
