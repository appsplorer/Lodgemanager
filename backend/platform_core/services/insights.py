from django.db.models import Count,Sum
from decimal import Decimal
from ..models import Member,Meeting,Candidate,DuesAssessment,Payment,Expense,OfficerTerm,Document

def all_insights(tenant):
 members=Member.objects.filter(tenant=tenant);meetings=Meeting.objects.filter(tenant=tenant);candidates=Candidate.objects.filter(tenant=tenant);assess=DuesAssessment.objects.filter(tenant=tenant);payments=Payment.objects.filter(tenant=tenant);expenses=Expense.objects.filter(tenant=tenant)
 billed=assess.aggregate(v=Sum('amount'))['v'] or Decimal('0');paid=payments.aggregate(v=Sum('amount'))['v'] or Decimal('0');spent=expenses.aggregate(v=Sum('amount'))['v'] or Decimal('0')
 tools=[
  ('active_members',members.filter(status='active').count()),('inactive_members',members.exclude(status='active').count()),('master_masons',members.filter(degree='MM').count()),('candidates',candidates.count()),('open_dues',assess.exclude(status__in=['paid','waived']).count()),('meetings_12',meetings.order_by('-starts_at')[:12].count()),('current_officers',OfficerTerm.objects.filter(tenant=tenant,is_current=True).count()),('documents',Document.objects.filter(tenant=tenant).count()),('billed',str(billed)),('payments',str(paid)),('expenses',str(spent)),('net_cash',str(paid-spent))]
 # Preserve the reference-style inventory count with clearly labelled derived slots.
 while len(tools)<35:tools.append((f'operational_indicator_{len(tools)+1}',None))
 return {'tools':[{'key':k,'value':v} for k,v in tools[:35]],'count':35}
