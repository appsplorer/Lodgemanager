from __future__ import annotations

import threading
import time


class LocalRateLimiter:
    """Bounded fallback used when the shared cache is unavailable."""

    def __init__(self, max_keys=10000):
        self.max_keys=max(100,int(max_keys));self._rows={};self._lock=threading.Lock()

    def allow(self,key,limit,window,now=None):
        current=time.monotonic() if now is None else float(now);window=max(1,int(window));limit=max(1,int(limit))
        with self._lock:
            row=self._rows.get(key)
            if row is None or current-row[0]>=window:
                if len(self._rows)>=self.max_keys:
                    oldest=min(self._rows,key=lambda item:self._rows[item][0]);self._rows.pop(oldest,None)
                self._rows[key]=(current,1);return True
            started,count=row;count+=1;self._rows[key]=(started,count);return count<=limit


_fallback=LocalRateLimiter()


def allow(key,limit,window,*,critical=False,cache_backend=None,fallback=None,now=None):
    ck='rl:'+str(key);fallback=fallback or _fallback
    try:
        if cache_backend is None:
            from django.core.cache import cache as cache_backend
        if cache_backend.add(ck,1,timeout=window):return True
        value=cache_backend.incr(ck);return int(value)<=int(limit)
    except Exception:
        # A bounded local limiter keeps authentication and public ingress protected
        # during Redis failure. Non-critical endpoints use the same conservative path.
        return fallback.allow(ck,limit,window,now=now)
