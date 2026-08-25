from __future__ import annotations

import io
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether

def _now(): return datetime.now(dt_timezone.utc)

NAVY=colors.HexColor('#102a43'); GOLD=colors.HexColor('#b99a4e'); INK=colors.HexColor('#17212b'); MUTED=colors.HexColor('#667085'); LINE=colors.HexColor('#d9dee3'); PAPER=colors.HexColor('#f7f5ef')


def _styles():
    s=getSampleStyleSheet()
    s.add(ParagraphStyle(name='DocTitle',parent=s['Title'],fontName='Helvetica-Bold',fontSize=18,leading=22,textColor=NAVY,spaceAfter=8))
    s.add(ParagraphStyle(name='Lodge',parent=s['Normal'],fontName='Helvetica-Bold',fontSize=10,leading=12,textColor=GOLD,spaceAfter=2))
    s.add(ParagraphStyle(name='Meta',parent=s['Normal'],fontSize=8.2,leading=11,textColor=MUTED))
    s.add(ParagraphStyle(name='Small',parent=s['Normal'],fontSize=8,leading=10,textColor=INK))
    s.add(ParagraphStyle(name='Section',parent=s['Heading2'],fontName='Helvetica-Bold',fontSize=11,leading=14,textColor=NAVY,spaceBefore=8,spaceAfter=5))
    return s


def _header(story,lodge_name,title,subtitle=''):
    st=_styles();story += [Paragraph(lodge_name.upper(),st['Lodge']),Paragraph(title,st['DocTitle'])]
    if subtitle:story.append(Paragraph(subtitle,st['Meta']))
    story.append(Spacer(1,4*mm))


def _footer(canvas,doc,lodge_name,classification='Internal'):
    canvas.saveState();canvas.setStrokeColor(LINE);canvas.line(15*mm,13*mm,A4[0]-15*mm,13*mm);canvas.setFont('Helvetica',7.3);canvas.setFillColor(MUTED)
    canvas.drawString(15*mm,8.5*mm,f'{lodge_name} · {classification} · System generated {_now():%d %b %Y %H:%M %Z}')
    canvas.drawRightString(A4[0]-15*mm,8.5*mm,f'Page {doc.page}');canvas.restoreState()


def _table(data,widths=None,header=True):
    st=_styles();normal=[]
    for r,row in enumerate(data):normal.append([Paragraph(str(v) if v not in (None,'') else '—',st['Small']) for v in row])
    t=Table(normal,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
    styles=[('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.35,LINE),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]
    if header:styles += [('BACKGROUND',(0,0),(-1,0),NAVY),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,PAPER])]
    t.setStyle(TableStyle(styles));return t


def _build(lodge_name,title,story,classification='Internal'):
    buf=io.BytesIO();doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=15*mm,rightMargin=15*mm,topMargin=16*mm,bottomMargin=18*mm,title=title,author='Quill of the Craft',subject='Lodge management generated document')
    doc.build(story,onFirstPage=lambda c,d:_footer(c,d,lodge_name,classification),onLaterPages=lambda c,d:_footer(c,d,lodge_name,classification));return buf.getvalue()


def minutes_pdf(meeting,minute,attendance=None,visitors=None,lodge_name='LodgeFlow'):
    s=[];_header(s,lodge_name,'MEETING MINUTES',f'{meeting.title} · {meeting.starts_at:%d %B %Y, %H:%M} · {meeting.location or "Location not recorded"}')
    st=_styles();s.append(_table([['Status','Version','Meeting type'],[getattr(minute,'state','draft').upper(),getattr(minute,'version','—'),meeting.meeting_type.title()]],header=True));s.append(Spacer(1,4*mm))
    if attendance is not None:
        rows=[['Member','Status']]+[[f'{a.member.first_name} {a.member.last_name}',a.status.title()] for a in attendance]
        s += [Paragraph('Attendance',st['Section']),_table(rows,[120*mm,55*mm])]
    if visitors is not None and list(visitors):
        rows=[['Visitor','Home lodge']]+[[v.name,v.home_lodge or '—'] for v in visitors];s += [Paragraph('Visitors',st['Section']),_table(rows,[90*mm,85*mm])]
    s += [Paragraph('Approved Record',st['Section']),Paragraph((getattr(minute,'body','') or 'No minute narrative recorded.').replace('\n','<br/>'),st['Small']),Spacer(1,5*mm),Paragraph(f'Approval state: {getattr(minute,"state","draft").upper()} · Generated reference: {getattr(minute,"id","")}',st['Meta'])]
    return _build(lodge_name,'Meeting Minutes',s,'Confidential')


def receipt_pdf(payment,lodge_name='LodgeFlow'):
    s=[];_header(s,lodge_name,'PAYMENT RECEIPT',f'Receipt No. {payment.receipt_number}')
    member=f'{payment.member.first_name} {payment.member.last_name}' if getattr(payment,'member',None) else 'Unallocated payer'
    purpose=f'Dues assessment {payment.assessment_id}' if getattr(payment,'assessment_id',None) else (payment.notes or 'Payment')
    rows=[['Receipt detail','Value'],['Date / time',payment.paid_at.strftime('%d %b %Y %H:%M %Z')],['Member',member],['Payment for',purpose],['Method / reference',f'{payment.method.title()} / {payment.provider_reference or "—"}'],['Amount',f'{payment.currency} {Decimal(payment.amount):,.2f}'],['Status','REVERSED' if getattr(payment,'is_reversed',False) else 'PAID'],['Audit reference',str(payment.id)]]
    s.append(_table(rows,[60*mm,115*mm]));s.append(Spacer(1,8*mm));st=_styles();s.append(Paragraph('Treasurer / authorised signature: ______________________________',st['Small']))
    return _build(lodge_name,'Payment Receipt',s,'Member Financial Record')


def member_statement_pdf(member,assessments,payments,balance,lodge_name='LodgeFlow',period='All activity',adjustments=None):
    s=[];_header(s,lodge_name,'MEMBER STATEMENT',f'{member.first_name} {member.last_name} · Statement period: {period}')
    rows=[['Cycle / Date','Description','Charge / Credit','Payment','Outstanding']]
    for a in assessments:
        total=Decimal(a.amount)+Decimal(a.late_fee)+Decimal(a.adjustment_amount)-Decimal(a.waived_amount);out=max(Decimal('0'),total-Decimal(a.paid_amount));rows.append([a.cycle.name,f'Dues / assessment · {a.currency}',f'{total:,.2f}',f'{Decimal(a.paid_amount):,.2f}',f'{out:,.2f}'])
    for p in payments:rows.append([p.paid_at.strftime('%d %b %Y'),f'Payment · {p.receipt_number} · {p.currency}' + (' · REVERSED' if getattr(p,'is_reversed',False) else ''),'—',f'{Decimal(p.amount):,.2f}','—'])
    for x in adjustments or []:rows.append([x.created_at.strftime('%d %b %Y'),f'{x.kind.replace("_"," " ).title()} · {x.reason[:60]}',f'{Decimal(x.amount):,.2f}','—','—'])
    s.append(_table(rows,[35*mm,60*mm,28*mm,28*mm,30*mm]));s.append(Spacer(1,5*mm));st=_styles();s.append(Paragraph(f'Closing / outstanding balance: <b>{balance:,.2f}</b>',st['Section']))
    return _build(lodge_name,'Member Statement',s,'Member Financial Record')


def officer_roster_pdf(terms,lodge_name='LodgeFlow',effective_date=None):
    s=[];_header(s,lodge_name,'OFFICER ROSTER',f'Effective date: {effective_date or _now().date()}')
    rows=[['Office','Officer','Term start','Term end']]+[[x.office,f'{x.member.first_name} {x.member.last_name}',x.starts_on,x.ends_on or 'Current'] for x in terms]
    s.append(_table(rows,[52*mm,65*mm,30*mm,30*mm]));return _build(lodge_name,'Officer Roster',s,'Internal')


def meeting_pack_pdf(meeting,minute,attendance,visitors,lodge_name='LodgeFlow',kind='pack',attachment_labels=None):
    from xml.sax.saxutils import escape
    st=_styles();s=[]
    title={'pack':'MEETING PACK','summons':'SUMMONS / NOTICE','attendance':'ATTENDANCE SHEET'}[kind];_header(s,lodge_name,title,f'{escape(str(meeting.title))} · {meeting.starts_at:%d %B %Y, %H:%M} · {escape(str(meeting.location or "Location not recorded"))}')
    if kind in ('pack','summons'):
        s.append(Paragraph('Agenda',st['Section']));agenda=list(meeting.agenda or []);rows=[['#','Agenda item']]+[[i+1,escape(str(x.get('title') if isinstance(x,dict) else x))] for i,x in enumerate(agenda) if not (isinstance(x,dict) and x.get('hidden'))];s.append(_table(rows if len(rows)>1 else [['#','Agenda item'],['—','No agenda items recorded']],[15*mm,160*mm]))
        notices=list(meeting.communications or [])
        notice_rows=[['#','Notice / communication']]
        for i,item in enumerate(notices,1):
            if isinstance(item,dict):
                value=item.get('title') or item.get('subject') or item.get('body') or item.get('text') or str(item)
            else:value=item
            notice_rows.append([i,escape(str(value))])
        s.append(Paragraph('Notices / communications',st['Section']));s.append(_table(notice_rows if len(notice_rows)>1 else [['#','Notice / communication'],['—','No notices or communications recorded']],[15*mm,160*mm]))
        if kind=='pack':
            labels=[escape(str(x)) for x in (attachment_labels or []) if str(x).strip()]
            attachment_rows=[['#','Configured attachment']]+[[i,label] for i,label in enumerate(labels,1)]
            s.append(Paragraph('Configured attachments',st['Section']));s.append(_table(attachment_rows if len(attachment_rows)>1 else [['#','Configured attachment'],['—','No PDF attachments configured']],[15*mm,160*mm]))
    if kind=='pack':s.append(PageBreak())
    if kind in ('pack','attendance'):
        s.append(Paragraph('Members',st['Section']));s.append(_table([['Member','Status','Signature / notes']]+[[escape(f'{a.member.first_name} {a.member.last_name}'),a.status.title(),''] for a in attendance],[75*mm,35*mm,65*mm]));
        s.append(Paragraph('Visitors',st['Section']));s.append(_table([['Visitor','Home lodge','Signature']]+[[escape(str(v.name)),escape(str(v.home_lodge or '—')),''] for v in visitors],[65*mm,65*mm,45*mm]))
    if kind=='pack' and minute:
        s.append(PageBreak());s.append(Paragraph('Prior / Current Minutes',st['Section']));s.append(Paragraph(escape(str(minute.body or 'No narrative recorded.')).replace('\n','<br/>'),st['Small']));s.append(Spacer(1,4*mm));s.append(Paragraph(f'Approval state: {minute.state.upper()} · Version {minute.version}',st['Meta']))
    return _build(lodge_name,title,s,'Confidential' if kind=='pack' else 'Internal')


def candidate_progress_pdf(candidate,lodge_name='LodgeFlow'):
    st=_styles();s=[];m=candidate.member;_header(s,lodge_name,'CANDIDATE PROGRESS SUMMARY',f'{m.first_name} {m.last_name} · Current stage: {candidate.stage}')
    mentors=', '.join(f'{x.mentor.first_name} {x.mentor.last_name}' for x in candidate.mentor_assignments.filter(is_active=True)) or 'Not assigned';s.append(_table([['Field','Value'],['Status',candidate.status],['Mentors',mentors],['Target degree date',candidate.target_degree_date or '—']],[55*mm,120*mm]));
    rows=[['Task','Status','Due','Required']]+[[x.title,x.status,x.due_on or '—','Yes' if x.required_for_stage else 'No'] for x in candidate.tasks.all()];s += [Paragraph('Tasks and milestones',st['Section']),_table(rows,[80*mm,35*mm,30*mm,30*mm])];return _build(lodge_name,'Candidate Progress Summary',s,'Confidential')


def text_document_pdf(title,body,header=''):
    lodge_name=(header or 'LodgeFlow').split('\n')[0][:100];s=[];_header(s,lodge_name,title);st=_styles();s.append(Paragraph(str(body).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('\n','<br/>'),st['Small']));return _build(lodge_name,title,s,'Internal')
