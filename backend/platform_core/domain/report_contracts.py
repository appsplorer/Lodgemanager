"""Appendix C minimum-content contracts for the commercial report catalogue."""

REPORT_REQUIRED_COLUMNS = {
    'R-001': {'Section','Metric','Value'},
    'R-002': {'Year','Section','Metric','Value'},
    'R-003': {'Metric','Value'},
    'R-010': {'Member ID','Name','Status','Degree','Tags / groups','Custom fields'},
    'R-011': {'Date','Member ID','Action','Previous status','New status','Actor'},
    'R-012': {'Month','Opening','Joined','Exited','Closing','Growth','Churn %','Retention %'},
    'R-013': {'Field','Value'},
    'R-014': {'Member ID','Name','Status','Email','Phone'},
    'R-020': {'Office','Officer','Start','End','Current'},
    'R-021': {'Office','Officer','Start','End','Current'},
    'R-030': {'Candidate','Stage','Status','Target degree'},
    'R-031': {'Candidate','Stage','Entered','Exited','Days','Threshold','Exception'},
    'R-032': {'Candidate','Task','Status','Due','Overdue','Assignee / mentor'},
    'R-033': {'Mentor','Active candidates','Open tasks','Overdue tasks'},
    'R-040': {'Meeting','Date','Member','Status','Check-in'},
    'R-041': {'Meeting','Date','Present','Recorded','Attendance %'},
    'R-042': {'Member','Meetings attended','Attendance records','Participation points'},
    'R-043': {'Meeting','Date','Visitor','Home lodge','Lodge no.','Jurisdiction','Notes'},
    'R-044': {'Section','Item','Status','Reference'},
    'R-050': {'Cycle','Period','Currency','Assessments','Base amount','Adjustments','Late fees','Paid','Waived','Outstanding','Collection %'},
    'R-051': {'Member','Cycle','Due date','Currency','Outstanding','Aging bucket','Status'},
    'R-052': {'Cycle','Period','Currency','Assessed','Collected','Collection %'},
    'R-053': {'Receipt','Paid at','Member','Assessment','Amount','Currency','Method','Reference'},
    'R-054': {'Date','Type','Reference','Currency','Charge','Payment','Waiver / adjustment','Balance'},
    'R-055': {'Field','Value'},
    'R-056': {'Date','Category','Payee','Description','Amount','Currency','Approval','Attachment'},
    'R-057': {'Section','Metric','Currency','Amount'},
    'R-060': {'Campaign','Recipient','Status','Attempts','Provider reference','Delivered'},
    'R-061': {'Campaign','Created','Status','Recipients','Delivered','Failed'},
    'R-070': {'Time','Actor','Action','Object type','Object ID','Request ID','Hash'},
    'R-071': {'Time','Requester','Export','Format','Records','Approver','Result','Hash'},
    'R-072': {'Requested','Requester','Export','Format','Status','Approver','Reason','Expires'},
    'R-073': {'Time','Actor','Action','Object type','Object ID','Request ID','Hash'},
    'R-080': {'Tenant ID','Tenant','Status','Plan','Active users','Members','Features','Failed jobs','Stored bytes'},
    'R-081': {'Tenant','Record type','Provider','Reference','Plan / event','Status','Amount','Currency','Occurred'},
    'R-082': {'Tenant','Provider','Event','Type','Mode','Status','Attempts','Error'},
    'R-083': {'Tenant','Job','Created','Age minutes','Attempts','Terminal','Finished','Error'},
    'R-084': {'Tenant','Campaign','Recipient','Status','Attempts','Last attempt','Error'},
}


def validate_report_output(report_id, columns, rows):
    report_id=str(report_id).upper()
    required=REPORT_REQUIRED_COLUMNS.get(report_id)
    if required is None:
        raise ValueError(f'report_contract_unknown:{report_id}')
    column_list=[str(value) for value in columns]
    missing=sorted(required-set(column_list))
    if missing:
        raise ValueError(f'report_contract_missing_columns:{report_id}:{",".join(missing)}')
    width=len(column_list)
    for index,row in enumerate(rows):
        if not isinstance(row,(list,tuple)) or len(row)!=width:
            raise ValueError(f'report_contract_row_width:{report_id}:{index}')
