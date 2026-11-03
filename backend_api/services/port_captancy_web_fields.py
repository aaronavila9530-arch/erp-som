"""Web contract audited against PortCaptancyForm; desktop remains untouched."""
from services.grain_web_fields import field, section

EVENTS = ('Vessel arrival', 'NOR tendered', 'All fast', 'Supervision commenced', 'Supervision completed')
GROUPS = [
    section('Service', [field(k, label) for k, label in (
        ('report_number', 'Report number'), ('continent', 'Continent'), ('country', 'Country'),
        ('port', 'Port'), ('operation', 'Operation'), ('requested_by', 'Requested by'), ('vessel', 'Vessel'))]),
    section('Introduction', [field('report_type', 'Survey scope / report type')] + [
        field(k+'_'+part, label+' / '+part, 'date' if part == 'date' else 'text')
        for k, label in (('arrival', 'Arrival'), ('inspection', 'Inspection'))
        for part in ('date', 'hour', 'minute')]),
    section('Representatives', [field('master', 'Master'), field('chief', 'Chief officer')]),
    section('Vessel particulars', [field(k, label) for k, label in (
        ('flag', 'Flag / port of registry'), ('grt', 'GRT'), ('nrt', 'NRT'), ('imo', 'IMO'), ('year_built', 'Year built'))]),
    section('Extract time sheet', [field(f'ts_{part}_{i}', label+' / '+part,
        'date' if part == 'date' else 'text') for i, label in enumerate(EVENTS) for part in ('date', 'hour', 'min')]),
]
for key, title in (('operation_summary', 'Operation summary'), ('remarks', 'Remarks'), ('conclusion', 'Conclusion')):
    group = section(title, [field(f'{key}_{i}', f'{title} {i}', 'textarea') for i in range(1, 16)])
    group['repeatable'] = True
    GROUPS.append(group)
GROUPS.append(section('Enclosure', [field('link_picture', 'Picture link')]))
SPEC = dict(title='Port Captancy', label='Port Captancy', table='port_captancy_reports',
            number='report_number', document='word', sections=GROUPS,
            fields={f['key']: f for group in GROUPS for f in group['fields']})

