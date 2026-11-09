"""Web-only contract matched to the desktop Crane Inspection payload."""
from services.grain_web_fields import field, section

POINTS = {
    'crane_access': 'Crane Access',
    'crane_machinery_space': 'Crane machinery space',
    'crane_operator_cabin': 'Crane operator cabin',
    'crane_jib_head_sheaves': 'Crane jib head sheaves',
    'hoisting_wire_end_pin': 'Hoisting wire end pin',
    'luffing_wire_end_pin': 'Luffing wire end pin',
    'crane_wire_visual': 'Crane wire rope visual inspection',
    'crane_housing_sheaves': 'Crane housing top sheaves',
    'luffing_center_sheave': 'Luffing center sheave visual inspection',
    'cargo_block_sheave': 'Cargo block sheave shaft',
    'slack_hoisting_limit': 'Slack hoisting wire limit',
    'crane_jib_angle_limits': 'Crane jib angle limits',
    'crane_jib_angle_indicator': 'Crane jib angle indicator',
    'crane_hoisting_limits': 'Crane hoisting wire limits',
    'pedestal_light_project': 'Pedestal / Light project',
}
OPTIONS = ['', 'Clean and no obstacles', 'Clean', 'Working', 'Not working', 'Greased',
           'Negative impressions', 'Free to rotate / Unreadable scale', 'No trunnion']
SUFFIXES = ('status', 'status1', 'status2', 'status3')
GROUPS = [section('Service', [field(k,v) for k,v in (
    ('report_number','Report number'), ('vessel','Vessel'), ('client','Client'),
    ('port','Port'), ('country','Country'), ('grt','GRT'), ('nrt','NRT'))]+[field('report_date','Report date','date')]),
    section('Introduction', [field('intro_text','Introduction text','textarea')]+[
        field('intro_inspection_'+p,'Inspection / '+p,'date' if p=='date' else 'text') for p in ('date','hour','minute')]),
    section('Cranes gear survey', [field('gear_'+end+'_'+p, end.title()+' / '+p,'date' if p=='date' else 'text')
        for end in ('start','end') for p in ('date','hour','minute')]+[
        field('gear_'+k,v,'textarea') for k,v in (
            ('condition','Condition'),('wires','Hoisting and luffing wires'),('sheaves','Sheaves'),('operability','Operability'))])]
for key,title in POINTS.items():
    GROUPS.append(section(title, [field(key+'_done','Inspection performed','checkbox')]+[
        {**field(key+'_'+suffix,'Status' if i==0 else f'Additional status {i}','select'), 'options':OPTIONS}
        for i,suffix in enumerate(SUFFIXES)]))
for prefix,title,limit in [(f'crane{i}_remark',f'Crane {i} remarks',10) for i in range(1,5)]+[
        ('recommendation','Recommendations',10),('grabs_condition','Grabs condition survey',10),('conclusion','Conclusion',20)]:
    GROUPS.append({**section(title,[field(f'{prefix}_{i}',f'Text {i}','textarea') for i in range(1,limit+1)]),'repeatable':True})
GROUPS.append(section('Enclosure',[field('link_picture','Picture link')]))
SPEC=dict(title='Crane Inspections',label='Crane Inspections',table='vessel_crane_inspection_reports',
          number='report_number',document='word',sections=GROUPS,
          fields={f['key']:f for g in GROUPS for f in g['fields']})


def validate_period(values):
    from fastapi import HTTPException
    if values.get('gear_start_date') and values.get('gear_end_date'):
        start=tuple(str(values.get('gear_start_'+p) or '00').zfill(2) for p in ('date','hour','minute'))
        end=tuple(str(values.get('gear_end_'+p) or '00').zfill(2) for p in ('date','hour','minute'))
        if end<start:
            raise HTTPException(422,'Survey end precedes survey start')
