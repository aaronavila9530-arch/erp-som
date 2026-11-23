"""Bunker web contract matching desktop payload keys, with derived fields locked."""
from services.grain_web_fields import field, section
from services.bunker_web_calculations import calculate, number

GROUPS = []
NUMERIC = set()


def group(title, keys, numeric=False):
    fields = []
    for key, label in keys:
        kind = 'date' if key.endswith('_date') or '_date_' in key or key == 'antecedent_arrived_dt' else 'text'
        fields.append(field(key, label, kind))
        if numeric: NUMERIC.add(key)
    GROUPS.append(section(title, fields))


group('Service', [('bunker_cert_no','Report number'),('ship_name','Vessel'),('client','Prepared for'),
    ('port','Port'),('country','Country'),('report_date','Report date'),('port_of_registry','Port of registry'),
    ('gross_tonnage','Gross tonnage'),('report_category','Report category')])
NUMERIC.add('gross_tonnage')
GROUPS[0]['fields'].append({**field('certificate','Survey type','select'), 'options':['ON_HIRE','OFF_HIRE','SPOT']})
group('Survey chronology', [(k,k.replace('_',' ').capitalize()) for k in (
    'berthing_date','berthing_hour','berthing_minute','commenced_date','antecedent_arrived_port',
    'antecedent_arrived_dt','antecedent_survey_date_from','antecedent_survey_hour_from',
    'antecedent_survey_minute_from','antecedent_survey_date_to','antecedent_survey_hour_to',
    'antecedent_survey_minute_to','inspection_with')])
group('Delivery point', [(k,k.replace('_',' ').capitalize()) for k in
    ('dslop_date','dslop_hour','dslop_minute','dslop_port','dslop_country')])
group('Declared figures (MT)', [(k,k.replace('_',' ').capitalize()) for k in
    ('bunker_delivery_declared','rob_diff','plus_consumption','generator_until_aps','cons_dept','me_to_sea_buoy')], True)
group('Draft and list', [(k,k.replace('_',' ').capitalize()) for k in
    ('draft','draft_fwd','draft_aft','trim','list')], True)
for fuel in ('vlsfo','mgo'):
    fields=[]
    for i in range(1,21):
        for suffix,label in [('name','Tank'),('dist_mtrs','Distance (m)'),('gauge_mtrs','Gauge (m)'),
            ('volume_m3','Corrected volume (m3)'),('temp_c','Temperature (C)'),('temp_f','Temperature (F)'),
            ('density_15c','Density at 15 C (t/m3)'),('weight_mt','Weight (MT)')]:
            key=f'{fuel}_tank_{i}_{suffix}'
            fields.append({**field(key,label), 'readonly':suffix in ('temp_f','weight_mt')})
            if suffix in ('volume_m3','temp_c','temp_f','density_15c','weight_mt'):NUMERIC.add(key)
    GROUPS.append({**section(fuel.upper()+' tanks',fields),'tank_fuel':fuel,'row_size':8})
for i in range(1,11):
    group({2:'Generator until DLOSP (signed MT)',3:'Departure M.E. to sea buoy (signed MT)'}.get(i,f'Bunker figure {i}'), [(f'bunker_figure_{i}_{s}',label) for s,label in
        [('name','Figure'),('ifo','IFO (MT)'),('vlsfo','VLSFO (MT)'),('lsmgo','LSMGO (MT)')]])
    NUMERIC.update(f'bunker_figure_{i}_{s}' for s in ('ifo','vlsfo','lsmgo'))
GROUPS[-10:]=[{**section('Bunker figures (signed MT)',[f for g in GROUPS[-10:] for f in g['fields']]),'figure_rows':True,'row_size':4}]
for prefix,title in [('log_eosp','EOSP'),('log_pob','POB'),('log_fwe','FWE'),
                     ('log_bunker','Bunker on log book'),('log_at_survey','At survey')]:
    group(title, [(prefix+'_'+s,s.upper()) for s in ('date','hour','minute','vlsfo','hfso','mdo','lsmgo')])
    NUMERIC.update(prefix+'_'+s for s in ('vlsfo','hfso','mdo','lsmgo'))
for prefix,title in [('cons_sea_loaded','Sea / loaded'),('cons_sea_ballast','Sea / ballast'),
                     ('cons_port_ship_gear','Port / ship gear'),('cons_port_shore_gear','Port / shore gear')]:
    group('Consumption: '+title,[(prefix+'_'+s,s.upper()) for s in ('vlsfo','hfso','mdo','lsmgo')],True)
GROUPS.append(section('Remarks',[field('remarks','Remarks','textarea')]))
group('Representatives',[(k,k.replace('_',' ').capitalize()) for k in
    ('surveyor_name','master_name','chief_engineer_name','owner_name','charterers_name')])
SPEC=dict(title='Bunker Survey',label='Bunker Survey',table='vessel_bunker_reports',number='bunker_cert_no',
          document='excel',sections=GROUPS,fields={f['key']:f for g in GROUPS for f in g['fields']})


def certificate_type(value):
    name=str(value or '').strip().upper().replace('_',' ')
    return {'ON HIRE':'ON_HIRE','ON HIRE CERTIFICATE':'ON_HIRE','OFF HIRE':'OFF_HIRE',
            'OFF HIRE CERTIFICATE':'OFF_HIRE','SPOT':'SPOT','SPOT CERTIFICATE':'SPOT'}.get(name,value)


def normalize(values, strict=False):
    """Normalize measured inputs; always recompute rather than trusting derived values."""
    from fastapi import HTTPException
    values=dict(values)
    if 'certificate' in values:values['certificate']=certificate_type(values['certificate'])
    try:
        for i,title in ((2,'Generator until DLOSP'),(3,'Cons. Departure M.E. to Sea Buoy')):
            if not values.get(f'bunker_figure_{i}_name') and any(values.get(f'bunker_figure_{i}_{s}') not in (None,'') for s in ('ifo','vlsfo','lsmgo')):
                values[f'bunker_figure_{i}_name']=title
        for key in NUMERIC:
            if key in values and not key.endswith(('_weight_mt','_temp_f')):
                value=number(values[key],key)
                values[key]=str(value) if value is not None else None
        for key,value in values.items():
            if value and ('_hour' in key or '_minute' in key):
                maximum=23 if '_hour' in key else 59
                if not str(value).isascii() or not str(value).isdigit() or not 0<=int(value)<=maximum:
                    raise ValueError(f'{key}: invalid time')
                values[key]=str(value).zfill(2)
        for prefix in ('antecedent_survey',):
            if values.get(prefix+'_date_from') and values.get(prefix+'_date_to'):
                stamp=lambda end: tuple(str(values.get(prefix+'_'+p+'_'+end) or '00') for p in ('date','hour','minute'))
                if stamp('to')<stamp('from'):raise ValueError('Survey end precedes survey start')
        result=calculate(values)
        # These rows are SOUNDING results, not independently declared log values.
        for fuel,suffix in (('vlsfo','vlsfo'),('mgo','lsmgo')):
            result['fields']['log_at_survey_'+suffix] = result['totals'][fuel] if result['totals'] and result['tanks'] else None
        fwd=number(values.get('draft_fwd'),'draft_fwd')
        aft=number(values.get('draft_aft'),'draft_aft')
        if any(value is not None and value<0 for value in (fwd,aft)):
            raise ValueError('Draft measurements must be nonnegative')
        result['fields']['trim']=str(aft-fwd) if fwd is not None and aft is not None else None
        if strict and (not result['valid'] or not result['tanks']):
            raise ValueError('; '.join(result['errors']) or 'At least one measured tank is required')
        if strict and any(not tank['name'].strip() for tank in result['tanks']):
            raise ValueError('Every measured tank requires an identifier')
        if strict and values.get('certificate') not in ('ON_HIRE','OFF_HIRE','SPOT'):
            raise ValueError('Select ON HIRE, OFF HIRE or SPOT')
        values.update(result['fields'])
        return values,result
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc
