from difflib import SequenceMatcher

def completeness(row):
 vals=list(row.values()) if hasattr(row,'values') else []
 return round(100*sum(v not in (None,'',[],{}) for v in vals)/max(len(vals),1),1)
def _norm(v):return ''.join(c for c in str(v or '').lower() if c.isalnum())
def likely_duplicate(a,b):
 ae,be=_norm(a.get('email')), _norm(b.get('email'));ap,bp=_norm(a.get('phone')), _norm(b.get('phone'))
 if ae and ae==be:return True
 if ap and ap==bp:return True
 an=_norm(f"{a.get('first_name','')} {a.get('last_name','')}");bn=_norm(f"{b.get('first_name','')} {b.get('last_name','')}")
 return bool(an and bn and SequenceMatcher(None,an,bn).ratio()>=.92)
