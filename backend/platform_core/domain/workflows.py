from dataclasses import dataclass
@dataclass(frozen=True)
class Transition:allowed:bool;reason:str=''
def transition_minutes(current,target):
 order=['draft','review','approved','locked']
 if current not in order or target not in order:return Transition(False,'unknown_state')
 if current=='locked':return Transition(False,'minutes_locked')
 return Transition(target==order[order.index(current)+1],'' if target==order[order.index(current)+1] else 'minutes_must_advance_one_state')
def transition_candidate_pipeline(current,target,stages,allow_regression=False,allow_skip=False):
 if current not in stages or target not in stages:return Transition(False,'unknown_stage')
 a,b=stages.index(current),stages.index(target)
 if b==a+1:return Transition(True)
 if b<a and allow_regression:return Transition(True,'approved_regression')
 if b>a+1 and allow_skip:return Transition(True,'approved_skip')
 return Transition(False,'candidate_stage_order_violation')
