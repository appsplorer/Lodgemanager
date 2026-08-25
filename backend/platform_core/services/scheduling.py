from __future__ import annotations
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def _matches_field(expr: str, value: int, minimum: int, maximum: int) -> bool:
    expr=str(expr).strip()
    for part in expr.split(','):
        part=part.strip()
        if not part: continue
        step=1
        if '/' in part:
            base,step_raw=part.split('/',1)
            try: step=int(step_raw)
            except ValueError: return False
            if step<1:return False
        else: base=part
        if base=='*': start,end=minimum,maximum
        elif '-' in base:
            try:start,end=(int(x) for x in base.split('-',1))
            except ValueError:return False
        else:
            try:start=end=int(base)
            except ValueError:return False
        if start<minimum or end>maximum or start>end:return False
        if start<=value<=end and (value-start)%step==0:return True
    return False


def cron_matches(schedule: str, dt: datetime) -> bool:
    """Match conventional five-field cron (minute hour DOM month DOW).

    DOW accepts 0 or 7 for Sunday. When both day-of-month and day-of-week are
    restricted, standard cron OR semantics are used.
    """
    parts=str(schedule or '').split()
    if len(parts)!=5:return False
    minute,hour,dom,month,dow=parts
    if not _matches_field(minute,dt.minute,0,59) or not _matches_field(hour,dt.hour,0,23) or not _matches_field(month,dt.month,1,12):return False
    dom_ok=_matches_field(dom,dt.day,1,31)
    cron_dow=(dt.weekday()+1)%7
    dow_ok=_matches_field(dow.replace('7','0'),cron_dow,0,6)
    return (dom_ok or dow_ok) if dom!='*' and dow!='*' else dom_ok and dow_ok


def validate_cron(schedule: str) -> bool:
    parts=str(schedule or '').split()
    if len(parts)!=5:return False
    probes=[(parts[0],0,59),(parts[1],0,23),(parts[2],1,31),(parts[3],1,12),(parts[4].replace('7','0'),0,6)]
    # Syntax validation by checking whether each field can match at least one value.
    return all(any(_matches_field(expr,v,lo,hi) for v in range(lo,hi+1)) for expr,lo,hi in probes)


def next_cron_run(schedule: str, timezone_name: str, after: datetime | None=None, max_minutes=527040) -> datetime | None:
    tz=ZoneInfo(timezone_name or 'UTC');start=(after or datetime.now(tz)).astimezone(tz).replace(second=0,microsecond=0)+timedelta(minutes=1)
    current=start
    for _ in range(max_minutes):
        if cron_matches(schedule,current):return current
        current+=timedelta(minutes=1)
    return None
