def pct(n,d):return round((float(n)/float(d))*100,1) if d else 0.0
def lodge_energy_score(attendance,dues,candidate_momentum,officer_engagement):return round(.30*attendance+.30*dues+.20*candidate_momentum+.20*officer_engagement,1)


def candidate_conversion_funnel(rows, stages):
    """Return ordered stage-to-stage conversion using historical reach, not current occupancy.

    Each row may be a dict or a model-like object exposing ``stage`` and
    ``stage_history``. A candidate counts as having reached a stage when that
    stage is current or appears as a ``to`` value in its immutable history.
    """
    ordered=[str(x).strip() for x in (stages or []) if str(x).strip()]
    if len(ordered)<2:return []
    reached={stage:0 for stage in ordered}
    for row in rows:
        current=row.get('stage') if isinstance(row,dict) else getattr(row,'stage','')
        history=row.get('stage_history') if isinstance(row,dict) else getattr(row,'stage_history',[])
        seen={str(current)} if current else set()
        for item in history or []:
            if isinstance(item,dict):
                for key in ('from','to'):
                    if item.get(key):seen.add(str(item[key]))
        for stage in ordered:
            if stage in seen:reached[stage]+=1
    result=[]
    for left,right in zip(ordered,ordered[1:]):
        result.append({'from':left,'to':right,'reached_from':reached[left],'reached_to':reached[right],'conversion_pct':pct(reached[right],reached[left])})
    return result
