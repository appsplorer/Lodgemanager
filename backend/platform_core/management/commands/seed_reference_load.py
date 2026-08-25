from __future__ import annotations
import math, os
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from platform_core.models import Attendance, Document, DuesAssessment, DuesCycle, Meeting, Member, Payment, Tenant, TenantMembership


def quota(total,index,count):
    base,extra=divmod(total,count)
    return base+(1 if index<extra else 0)


class Command(BaseCommand):
    help='Seed the SRS reference-scale performance dataset. Never enabled implicitly.'

    def add_arguments(self,parser):
        parser.add_argument('--tenants',type=int,default=100)
        parser.add_argument('--members',type=int,default=50_000)
        parser.add_argument('--attendance',type=int,default=250_000)
        parser.add_argument('--finance',type=int,default=100_000,help='Creates this many assessments and this many matched payments.')
        parser.add_argument('--documents',type=int,default=20_000)
        parser.add_argument('--reset',action='store_true')
        parser.add_argument('--prefix',default='loadref')

    def handle(self,*args,**o):
        if os.getenv('ALLOW_REFERENCE_LOAD_SEED','').lower()!='true':
            raise CommandError('Set ALLOW_REFERENCE_LOAD_SEED=true explicitly before seeding benchmark data.')
        n=max(1,o['tenants']);prefix=str(o['prefix']).strip() or 'loadref'
        targets={k:max(0,int(o[k])) for k in ('members','attendance','finance','documents')}
        if o['reset']:
            deleted=Tenant.objects.filter(slug__startswith=f'{prefix}-').delete()[0]
            self.stdout.write(f'Removed {deleted} benchmark records through tenant cascade.')
        password=os.getenv('LOAD_TEST_PASSWORD','')
        if len(password)<16:raise CommandError('LOAD_TEST_PASSWORD must be at least 16 characters.')
        User=get_user_model();username=os.getenv('LOAD_TEST_USERNAME','loadtest@example.test')
        user,_=User.objects.get_or_create(username=username,defaults={'email':username})
        user.set_password(password);user.is_active=True;user.save(update_fields=['password','is_active'])
        now=timezone.now();today=now.date()
        totals={'tenants':0,'members':0,'attendance':0,'assessments':0,'payments':0,'documents':0}
        for i in range(n):
            with transaction.atomic():
                tenant,_=Tenant.objects.update_or_create(slug=f'{prefix}-{i+1:03d}',defaults={'name':f'Reference Lodge {i+1:03d}','lodge_number':f'R{i+1:04d}','jurisdiction':'Performance QA','plan':'enterprise','is_active':True})
                TenantMembership.objects.update_or_create(tenant=tenant,user=user,defaults={'role':'owner','is_active':True,'mfa_required':False})
                mc=quota(targets['members'],i,n);ac=quota(targets['attendance'],i,n);fc=quota(targets['finance'],i,n);dc=quota(targets['documents'],i,n)
                existing=list(Member.objects.filter(tenant=tenant).order_by('id'))
                if len(existing)<mc:
                    start=len(existing)
                    Member.objects.bulk_create([Member(tenant=tenant,first_name=f'Member{j+1}',last_name=f'Ref{i+1:03d}',email=f'{prefix}-{i+1:03d}-{j+1}@example.test',status='active',degree='MM',joined_on=today-timedelta(days=(j%3650))) for j in range(start,mc)],batch_size=2000)
                members=list(Member.objects.filter(tenant=tenant).order_by('id')[:mc])
                if not members and (ac or fc):raise CommandError('Attendance/finance targets require member rows.')
                # Attendance: enough meetings to preserve the unique meeting/member invariant.
                meet_count=max(1,math.ceil(ac/max(1,len(members)))) if ac else 0
                Meeting.objects.filter(tenant=tenant,title__startswith='Reference Meeting ').delete()
                meetings=[Meeting(tenant=tenant,title=f'Reference Meeting {j+1}',meeting_type='stated',starts_at=now-timedelta(days=j*7),location='Reference Hall',status='completed') for j in range(meet_count)]
                Meeting.objects.bulk_create(meetings,batch_size=500)
                attendance=[]
                remaining=ac
                for meeting in meetings:
                    take=min(remaining,len(members));attendance.extend(Attendance(tenant=tenant,meeting=meeting,member=m,status='present',checked_in_at=meeting.starts_at) for m in members[:take]);remaining-=take
                    if remaining<=0:break
                Attendance.objects.bulk_create(attendance,batch_size=5000)
                # Finance: create as many cycles as required for unique member/cycle assessments.
                DuesCycle.objects.filter(tenant=tenant,name__startswith='Reference Cycle ').delete()
                cycle_count=max(1,math.ceil(fc/max(1,len(members)))) if fc else 0
                cycles=[DuesCycle(tenant=tenant,name=f'Reference Cycle {j+1}',period_start=today-timedelta(days=365*(j+1)),period_end=today-timedelta(days=365*j+1),due_on=today-timedelta(days=365*j),standard_amount=Decimal('100.00'),late_fee=Decimal('0.00'),status='closed',is_open=False) for j in range(cycle_count)]
                DuesCycle.objects.bulk_create(cycles,batch_size=500)
                assessments=[];remaining=fc
                for cycle in cycles:
                    take=min(remaining,len(members));assessments.extend(DuesAssessment(tenant=tenant,member=m,cycle=cycle,amount=Decimal('100.00'),paid_amount=Decimal('100.00'),status='paid') for m in members[:take]);remaining-=take
                    if remaining<=0:break
                DuesAssessment.objects.bulk_create(assessments,batch_size=5000)
                payments=[Payment(tenant=tenant,member=a.member,assessment=a,amount=a.amount,currency='PHP',method='benchmark',receipt_number=f'PERF-{i+1:03d}-{j+1:06d}',paid_at=now) for j,a in enumerate(assessments)]
                Payment.objects.bulk_create(payments,batch_size=5000)
                Document.objects.filter(tenant=tenant,title__startswith='Reference Document ').delete()
                Document.objects.bulk_create([Document(tenant=tenant,title=f'Reference Document {j+1}',folder='Performance QA',tags=['reference-load'],mime_type='text/plain',content='Synthetic performance-test metadata record.',created_by=user) for j in range(dc)],batch_size=5000)
                totals['tenants']+=1;totals['members']+=len(members);totals['attendance']+=len(attendance);totals['assessments']+=len(assessments);totals['payments']+=len(payments);totals['documents']+=dc
            self.stdout.write(f'[{i+1}/{n}] {tenant.slug}: members={mc} attendance={ac} finance={fc} documents={dc}')
        self.stdout.write(self.style.SUCCESS(f'Reference seed complete: {totals}'))
        self.stdout.write(f'Load-test tenant id: {Tenant.objects.get(slug=f"{prefix}-001").id}')
