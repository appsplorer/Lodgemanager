from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from ..models import AgendaItem, Meeting

WEEKDAYS={'MO':0,'TU':1,'WE':2,'TH':3,'FR':4,'SA':5,'SU':6}


def parse_rrule(value: str) -> dict:
    """Parse a conservative RFC5545-style recurrence subset used by LodgeFlow.

    Supported: FREQ=DAILY|WEEKLY|MONTHLY, INTERVAL, BYDAY for weekly rules,
    COUNT, and UNTIL (YYYYMMDD or YYYYMMDDTHHMMSSZ). Unknown keys are ignored,
    but malformed supported values fail closed.
    """
    raw=(value or '').strip().upper()
    if not raw:
        return {}
    if raw.startswith('RRULE:'):
        raw=raw[6:]
    out={}
    for part in raw.split(';'):
        if not part:
            continue
        if '=' not in part:
            raise ValueError('invalid_recurrence_rule')
        key,val=part.split('=',1);out[key.strip()]=val.strip()
    freq=out.get('FREQ')
    if freq not in {'DAILY','WEEKLY','MONTHLY'}:
        raise ValueError('unsupported_recurrence_frequency')
    try: interval=int(out.get('INTERVAL','1'))
    except ValueError as exc: raise ValueError('invalid_recurrence_interval') from exc
    if interval<1 or interval>365: raise ValueError('invalid_recurrence_interval')
    result={'freq':freq,'interval':interval}
    if out.get('BYDAY'):
        days=[x for x in out['BYDAY'].split(',') if x]
        if freq!='WEEKLY' or any(x not in WEEKDAYS for x in days): raise ValueError('invalid_recurrence_byday')
        result['byday']=days
    if out.get('COUNT'):
        try: count=int(out['COUNT'])
        except ValueError as exc: raise ValueError('invalid_recurrence_count') from exc
        if count<1 or count>1000: raise ValueError('invalid_recurrence_count')
        result['count']=count
    if out.get('UNTIL'):
        token=out['UNTIL']; parsed=None
        for fmt in ('%Y%m%dT%H%M%SZ','%Y%m%d'):
            try: parsed=datetime.strptime(token,fmt);break
            except ValueError: pass
        if parsed is None: raise ValueError('invalid_recurrence_until')
        result['until']=parsed.replace(tzinfo=timezone.utc if hasattr(timezone,'utc') else ZoneInfo('UTC'))
    return result


def _add_months(dt: datetime, months: int) -> datetime:
    month_index=(dt.year*12 + (dt.month-1)) + months
    year,month=divmod(month_index,12);month+=1
    day=min(dt.day,calendar.monthrange(year,month)[1])
    return dt.replace(year=year,month=month,day=day)


def recurrence_datetimes(start: datetime, rule: str, horizon: datetime, *, max_occurrences: int=400):
    cfg=parse_rrule(rule)
    if not cfg: return []
    interval=cfg['interval'];freq=cfg['freq'];until=cfg.get('until');count=cfg.get('count')
    results=[]
    # The template meeting is occurrence #1; generated occurrences begin after it.
    if freq=='DAILY':
        cursor=start+timedelta(days=interval)
        while cursor<=horizon:
            if until and cursor>until: break
            results.append(cursor)
            if count and len(results)+1>=count: break
            if until and cursor>=until: break
            if len(results)>=max_occurrences: break
            cursor += timedelta(days=interval)
    elif freq=='MONTHLY':
        n=1
        while len(results)<max_occurrences:
            cursor=_add_months(start,n*interval);n+=1
            if cursor>horizon or (until and cursor>until): break
            results.append(cursor)
            if count and len(results)+1>=count: break
    else:
        bydays=cfg.get('byday') or [list(WEEKDAYS)[start.weekday()]]
        wanted=sorted(WEEKDAYS[x] for x in bydays)
        week0=(start-timedelta(days=start.weekday())).replace(hour=start.hour,minute=start.minute,second=start.second,microsecond=start.microsecond)
        n=0
        while len(results)<max_occurrences:
            week=week0+timedelta(weeks=n*interval);n+=1
            for weekday in wanted:
                cursor=week+timedelta(days=weekday)
                if cursor<=start: continue
                if cursor>horizon or (until and cursor>until): return results
                results.append(cursor)
                if count and len(results)+1>=count: return results
                if len(results)>=max_occurrences: return results
    return results


def sync_meeting_agenda_json(meeting: Meeting):
    meeting.agenda=[{'id':str(x.id),'kind':x.kind,'standard_key':x.standard_key,'title':x.title,'notes':x.notes,'sort_order':x.sort_order,'hidden':x.is_hidden} for x in meeting.agenda_items.order_by('sort_order','created_at')]
    meeting.save(update_fields=['agenda','updated_at'])


def generate_recurring_occurrences(template: Meeting, *, horizon_days: int=180):
    if template.recurrence_source_id or not template.recurrence_rule:
        return {'created':0,'existing':0}
    tz_name=getattr(template.tenant,'timezone','UTC') or 'UTC'
    try: zone=ZoneInfo(tz_name)
    except Exception: zone=ZoneInfo('UTC')
    start=timezone.localtime(template.starts_at,zone) if timezone.is_aware(template.starts_at) else template.starts_at.replace(tzinfo=zone)
    horizon=timezone.now().astimezone(zone)+timedelta(days=max(1,min(int(horizon_days),730)))
    duration=(template.ends_at-template.starts_at) if template.ends_at else None
    created=existing=0
    with transaction.atomic():
        for dt in recurrence_datetimes(start,template.recurrence_rule,horizon):
            aware=dt.astimezone(ZoneInfo('UTC'))
            key=f'{template.id}:{aware.isoformat()}'
            defaults={
                'title':template.title,'meeting_type':template.meeting_type,'starts_at':aware,
                'ends_at':aware+duration if duration else None,'location':template.location,
                'agenda':template.agenda,'business_items':template.business_items,'communications':template.communications,
                'approved_bills':template.approved_bills,'status':'scheduled','recurrence_rule':'',
                'education_minutes':0,'business_minutes':0,'fellowship_minutes':0,'recurrence_source':template,
            }
            meeting,is_created=Meeting.objects.get_or_create(tenant=template.tenant,occurrence_key=key,defaults=defaults)
            created+=int(is_created);existing+=int(not is_created)
            if is_created:
                items=list(template.agenda_items.order_by('sort_order','created_at'))
                AgendaItem.objects.bulk_create([AgendaItem(tenant=template.tenant,meeting=meeting,kind=x.kind,standard_key=x.standard_key,title=x.title,notes=x.notes,sort_order=x.sort_order,is_hidden=x.is_hidden) for x in items])
    return {'created':created,'existing':existing}
