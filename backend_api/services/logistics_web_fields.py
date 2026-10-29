"""Audited desktop Logistics Supervision contract, exposed only to MSL web."""
from services.grain_web_fields import field, section

GROUPS = [
    section('Report header', [field(k, label, typ) for k, label, typ in (
        ('cert_no','Report number','text'), ('customer','Customer','text'),
        ('port','Port','text'), ('country','Country','text'), ('report_date','Report date','date'))]),
    section('Vessel particulars', [field(k, label) for k, label in (
        ('vessel_name','Vessel'), ('flag_port_registry','Flag / port of registry'),
        ('grt','GRT'), ('nrt','NRT'), ('imo_no','IMO number'), ('build_year','Year built'))]),
    section('Representatives', [field('captain','Master'), field('chief_officer','Chief officer')]),
    section('Time sheet', [field(k,label,'date') for k,label in (
        ('arrival_date','Arrival'), ('inspection_date','Inspection'),
        ('supervision_completed_date','Supervision completed'))]),
    section('Supervision process', [field('process_text','Supervision process','textarea')]),
    section('Findings', [field(k,label,'textarea') for k,label in (
        ('findings_documental_text','Documentary findings'),
        ('findings_operational_text','Operational control findings'), ('incidents_text','Incidents'))]),
    section('Conclusion', [field('conclusion_text','Conclusion','textarea')]),
]
SPEC = dict(title='Logistics Supervision', label='Logistics Supervision',
            table='vessel_truck_supervision_reports', number='cert_no', document='word',
            sections=GROUPS, fields={f['key']:f for g in GROUPS for f in g['fields']})
