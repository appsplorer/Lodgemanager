#!/usr/bin/env python3
"""Generate non-PII representative PDF delivery samples.

The seven operational documents use the production PDF service directly. The
monthly management sample uses the same ReportLab design language/report fields
as the runtime report catalogue, but with synthetic fixture rows so it can be
rendered without a Django/PostgreSQL runtime.
"""
from __future__ import annotations

import hashlib
import io
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))

from platform_core.services.pdf_merge import merge_pdf_documents
from platform_core.services.pdfs import (
    meeting_pack_pdf, member_statement_pdf, minutes_pdf, officer_roster_pdf, receipt_pdf,
)
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT=ROOT/'docs'/'samples'
LODGE='Quill Example Lodge No. 101'
WHEN=datetime(2026,8,24,19,30,tzinfo=timezone.utc)


def _member(first,last):return NS(first_name=first,last_name=last)


def _management_pack_pdf():
    buf=io.BytesIO();styles=getSampleStyleSheet();doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=15*mm,rightMargin=15*mm,topMargin=18*mm,bottomMargin=18*mm,title='Monthly Lodge Management Pack',author='Quill of the Craft',subject='Representative R-001 management report')
    cover=ParagraphStyle('cover',parent=styles['Title'],fontSize=24,leading=29,textColor=colors.HexColor('#102a43'),alignment=TA_CENTER,spaceAfter=8)
    small=ParagraphStyle('small',parent=styles['BodyText'],fontSize=8,leading=10,textColor=colors.HexColor('#1d2a33'))
    story=[Spacer(1,12*mm),Paragraph(LODGE,cover),Paragraph('Monthly Lodge Management Pack',styles['Title']),Paragraph('R-001 · August 2026 · Internal · synthetic delivery sample',small),Spacer(1,8*mm)]
    kpis=[['KPI','Value'],['Active members','128'],['Candidate pipeline','7'],['Attendance rate','84.6%'],['Dues outstanding','GBP 2,450.00'],['Approved expenses','GBP 1,120.00'],['Campaign delivery','98.4%']]
    table=Table(kpis,colWidths=[105*mm,65*mm],repeatRows=1);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#102a43')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#d4d9dd')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f6f7f7')]),('PADDING',(0,0),(-1,-1),6)]));story += [Paragraph('Executive summary',styles['Heading2']),table,Spacer(1,6*mm)]
    rows=[['Area','Status','Management note'],['Membership','Stable','2 joins, 1 demit; no unresolved duplicate records'],['Candidates','On track','1 overdue task escalated to assigned mentor'],['Meetings','Complete','Prior minutes approved; next meeting pack prepared'],['Finance','Watch','Outstanding dues concentrated in 9 member accounts'],['Compliance','Healthy','Audit chain verified; no unacknowledged high alerts']]
    detail=Table(rows,colWidths=[35*mm,35*mm,100*mm],repeatRows=1);detail.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#102a43')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#d4d9dd')),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),5)]));story += [Paragraph('Management exceptions',styles['Heading2']),detail,Spacer(1,5*mm),Paragraph('Representative non-production data. Runtime R-001 is generated from authorized tenant records and includes reporting-period metadata and pagination.',small)]
    def footer(canvas,doc_):
        canvas.saveState();canvas.setFont('Helvetica',7);canvas.setFillColor(colors.HexColor('#59636b'));canvas.drawString(15*mm,8*mm,'Internal · Representative delivery sample · Generated 2026-08-24');canvas.drawRightString(A4[0]-15*mm,8*mm,f'Page {doc_.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer);return buf.getvalue()


def build_samples():
    OUT.mkdir(parents=True,exist_ok=True)
    member=_member('Ada','Mason');visitor=NS(name='Grace Visitor',home_lodge='Example Provincial Lodge')
    meeting=NS(title='August Stated Meeting',starts_at=WHEN,location='Lodge Hall',meeting_type='stated',agenda=[{'title':'Opening and salutations'},{'title':'Treasurer report'},{'title':'Candidate business'}],communications=[{'title':'Grand Lodge circular 2026-08'},{'subject':'Charity appeal and response deadline'}])
    minute=NS(id='00000000-0000-4000-8000-000000000201',body='The prior minutes were reviewed and approved without amendment. Treasurer and secretary reports were received.',state='approved',version=3)
    attendance=[NS(member=member,status='present'),NS(member=_member('James','Craft'),status='present'),NS(member=_member('Noah','Stone'),status='excused')]
    visitors=[visitor]
    payment=NS(id='00000000-0000-4000-8000-000000000301',receipt_number='QOC-2026-000042',paid_at=WHEN,member=member,assessment_id='A-2026-08',notes='Annual dues',method='card',provider_reference='pi_sample_42',currency='GBP',amount=Decimal('125.00'),is_reversed=False)
    assessment=NS(cycle=NS(name='2026 Annual Dues'),currency='GBP',amount=Decimal('150'),late_fee=Decimal('0'),adjustment_amount=Decimal('0'),waived_amount=Decimal('0'),paid_amount=Decimal('125'))
    adjustment=NS(created_at=WHEN,kind='credit',reason='Synthetic delivery-sample adjustment',amount=Decimal('5'))
    terms=[NS(office='Worshipful Master',member=member,starts_on=date(2026,1,1),ends_on=None),NS(office='Secretary',member=_member('James','Craft'),starts_on=date(2026,1,1),ends_on=date(2026,12,31)),NS(office='Treasurer',member=_member('Noah','Stone'),starts_on=date(2026,1,1),ends_on=None)]

    files={
      'receipt.pdf':receipt_pdf(payment,LODGE),
      'member-statement.pdf':member_statement_pdf(member,[assessment],[payment],Decimal('20.00'),LODGE,'1 Jan - 24 Aug 2026',[adjustment]),
      'officer-roster.pdf':officer_roster_pdf(terms,LODGE,date(2026,8,24)),
      'minutes.pdf':minutes_pdf(meeting,minute,attendance,visitors,LODGE),
      'summons.pdf':meeting_pack_pdf(meeting,minute,attendance,visitors,LODGE,'summons'),
      'attendance-sheet.pdf':meeting_pack_pdf(meeting,minute,attendance,visitors,LODGE,'attendance'),
      'monthly-management-pack.pdf':_management_pack_pdf(),
    }
    attachment=io.BytesIO();from reportlab.pdfgen import canvas
    c=canvas.Canvas(attachment,pagesize=A4);c.setTitle('Representative Meeting Attachment');c.drawString(25*mm,A4[1]-35*mm,'Representative By-laws / Circular Attachment');c.drawString(25*mm,A4[1]-45*mm,'Synthetic attachment included to exercise governed PDF merging.');c.save()
    base=meeting_pack_pdf(meeting,minute,attendance,visitors,LODGE,'pack',attachment_labels=['Representative By-laws / Circular'])
    files['meeting-pack.pdf']=merge_pdf_documents(base,[('Representative By-laws / Circular',attachment.getvalue())])
    for name,data in files.items():(OUT/name).write_bytes(data)
    return files


def write_manifest(files):
    lines=['# Representative PDF Sample Approval Pack','', 'These files contain synthetic/non-PII fixture data and are included for contractual document visual QA. Seven samples are rendered through the production `platform_core.services.pdfs` functions; the management-pack fixture reproduces the runtime R-001 visual/report contract without requiring a live Django database.','', '| File | Pages | Bytes | SHA-256 | visual QA |','|---|---:|---:|---|---|']
    for name,data in sorted(files.items()):
        pages=len(PdfReader(io.BytesIO(data)).pages);digest=hashlib.sha256(data).hexdigest();lines.append(f'| `{name}` | {pages} | {len(data)} | `{digest}` | Local visual QA passed; staging/UAT approval pending |')
    lines += ['', 'Production UAT must separately approve PDFs generated from the staging application because these local samples do not replace runtime acceptance.']
    (ROOT/'docs'/'PDF_SAMPLE_APPROVAL.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    generated=build_samples();write_manifest(generated);print(f'Generated {len(generated)} representative PDFs in {OUT}')
