from decimal import Decimal,ROUND_HALF_UP

def amount_due(amount,paid=0,waived=0,late_fee=0,adjustment=0):return max(Decimal('0'),Decimal(amount)+Decimal(late_fee)+Decimal(adjustment)-Decimal(paid)-Decimal(waived))
def assessment_status(amount,paid,waived,late_fee,is_late=False,adjustment=0):
 due=amount_due(amount,paid,waived,late_fee,adjustment)
 if due<=0:
  settled_gross=max(Decimal('0'),Decimal(amount)+Decimal(late_fee)+Decimal(adjustment))
  return 'waived' if Decimal(waived)>=settled_gross and Decimal(paid)==0 else 'paid'
 if Decimal(paid)>0 or Decimal(waived)>0:return 'partial'
 return 'overdue' if is_late else 'open'
def receipt_number(prefix,year,sequence):return f'{prefix}-{int(year)}-{int(sequence):06d}'
def prorated_dues(base,period_start,period_end,joined_on,enabled=True):
 base=Decimal(base)
 if not enabled or not joined_on or joined_on<=period_start:return base.quantize(Decimal('0.01'))
 if joined_on>period_end:return Decimal('0.00')
 total=(period_end-period_start).days+1;remaining=(period_end-joined_on).days+1
 return (base*Decimal(remaining)/Decimal(total)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
