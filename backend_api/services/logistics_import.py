"""Lossless narrative mapping for explicitly authorized legacy MCI copies."""
from services.mci_survey_schema import SurveyContent

def content_from_legacy(row):
    sections = {k:dict(enabled=True,blocks=[]) for k in ('instructions','chronology','representatives','particulars','findings')}
    for key, old in (('process','process_text'), ('documentary','findings_documental_text'),
                     ('operational','findings_operational_text'), ('incidents','incidents_text'),
                     ('conclusion','conclusion_text')):
        text=row.get(old) or ''
        sections[key]=dict(enabled=bool(text.strip()),blocks=[dict(text=text)] if text else [])
    return SurveyContent(hierarchy_version=2, imo=row.get('imo_no') or '',
        flag_port_registry=row.get('flag_port_registry') or '', grt=row.get('grt') or '',
        nrt=row.get('nrt') or '', build_year=row.get('build_year') or '',
        master=row.get('captain') or '',chief_officer=row.get('chief_officer') or '',
        issue_date=row.get('report_date'),arrival_date=row.get('arrival_date'),
        inspection_date=row.get('inspection_date'),supervision_completed_date=row.get('supervision_completed_date'),
        report_status='Draft', sections=sections)
