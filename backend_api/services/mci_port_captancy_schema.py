"""MCI layout with the complete Port Captancy data, not the MSL letterhead."""
from services.port_captancy_web_fields import EVENTS

TITLES = {
    'instructions': 'INSTRUCTIONS, SCOPE AND METHODOLOGY', 'work': 'Work performed',
    'limitations': 'Main limitations of this report', 'chronology': 'Extract time sheet',
    'representatives': 'Representatives', 'particulars': 'VESSEL PARTICULARS',
    'operation_summary': 'OPERATION SUMMARY', 'remarks': 'REMARKS',
    'conclusion': 'CONCLUSION', 'enclosure': 'ENCLOSURE',
}
GROUPS = {'instructions': ('work', 'limitations', 'chronology', 'representatives'),
          'particulars': (), 'operation_summary': (), 'remarks': (), 'conclusion': (), 'enclosure': ()}
FIELDS = {
    'report_type': 'Survey scope / report type', 'imo': 'IMO',
    'length_and_tonnage': 'Length overall and tonnage', 'cargo': 'Cargo',
    'flag_port_registry': 'Flag / port of registry', 'grt': 'GRT', 'nrt': 'NRT', 'build_year': 'Year built',
    'period_start': 'Period investigated - from', 'period_end': 'Period investigated - to',
    'issue_date': 'Date of issue', 'report_status': 'Report status',
    'arrival_date': 'Arrival date', 'arrival_time': 'Arrival time (LT)',
    'inspection_date': 'Inspection date', 'inspection_time': 'Inspection time (LT)',
    'master': 'Master', 'chief_officer': 'Chief officer', 'surveyor': 'Surveyor / signatory',
}
for i, label in enumerate(EVENTS):
    FIELDS[f'ts_date_{i}'] = label+' / date'
    FIELDS[f'ts_time_{i}'] = label+' / time (LT)'

