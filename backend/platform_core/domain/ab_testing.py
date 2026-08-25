import hashlib

def assign_variant(experiment_key,subject_key,variants,weights=None):
 variants=list(variants or ['control']);weights=list(weights or [])
 if not variants:return 'control'
 if len(weights)!=len(variants) or sum(float(x) for x in weights)<=0:weights=[1/len(variants)]*len(variants)
 total=sum(float(x) for x in weights);point=int(hashlib.sha256(f'{experiment_key}|{subject_key}'.encode()).hexdigest()[:16],16)/(16**16-1)
 cursor=0.0
 for v,w in zip(variants,weights):
  cursor+=float(w)/total
  if point<cursor:return str(v)
 return str(variants[-1])
