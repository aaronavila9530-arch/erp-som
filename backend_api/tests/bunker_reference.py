"""Measured inputs from the supplied AQUITANIA workbook (2026-07-04).

Source SHA256: 01df343749a8f81aca809549f91026628f889eb76878693f4a5aa9efe4560cc1.
Metadata is deliberately marked QA; these fixtures are never stored in SOM.
"""
def aquitania():
    data=dict(company_code='MSL-CR',bunker_cert_no='QA-AQUITANIA',certificate='OFF_HIRE',
        ship_name='AQUITANIA',client='QA CLIENT',port='Puerto Caldera',country='Costa Rica',
        report_date='2026-07-04',port_of_registry='SINGAPORE',gross_tonnage='24166',
        surveyor_name='QA SURVEYOR',master_name='QA MASTER',chief_engineer_name='QA ENGINEER',
        owner_name='QA OWNER',charterers_name='QA CHARTERER',draft_fwd='4.5',draft_aft='6.25',list='0',
        antecedent_arrived_port='Puerto Caldera',antecedent_arrived_dt='2026-06-16',
        berthing_hour='08',berthing_minute='00',antecedent_survey_date_from='2026-07-04',
        antecedent_survey_hour_from='19',antecedent_survey_minute_from='30',
        antecedent_survey_date_to='2026-07-04',antecedent_survey_hour_to='21',antecedent_survey_minute_to='30',
        inspection_with='Chief Engineer and Third Engineer',dslop_date='2026-07-05',
        dslop_hour='03',dslop_minute='00',dslop_port='Puerto Caldera',dslop_country='Costa Rica',
        bunker_figure_2_vlsfo='-0.4',bunker_figure_3_vlsfo='-1.2',
        bunker_figure_2_lsmgo='0',bunker_figure_3_lsmgo='0')
    rows={
        'vlsfo':[
            ('No 1P','13.73','4.83','157.44','39','.9415'),
            ('No 1S','13.61','EMPTY','.745','34','.9483'),
            ('No 2P','13.34','.03','.22','34','.9415'),
            ('No 2S','8.31','7.64','88.945','50','.9415'),
            ('HFO SETT TK 1','7.1','5.95','29.575','81','.9415'),
            ('HFO SETT TK 2','7.1','6.35','31.74','76','.9415'),
            ('No 1 HFO SERV TK','7.4','7.4','37.415','95','.9415'),
            ('No 2 HFO SERV TK','7.1','7','35.265','94','.9415'),
            ('FO Overflow','4.3','.52','4.844','55','.9415')],
        'mgo':[
            ('DEEP TK','4.43','.33','13.22','37','.825'),
            ('3P DO','3.02','2.05','91.05','37','.8758'),
            ('SETT','2.78','1.83','6.51','37','.825'),
            ('SERV 1','4.54','3.37','12.901','37','.8855'),
            ('SERV 2','4.43','3.95','15.355','37','.825'),
            ('OVERFLOW','4.4','.41','3.569','37','.8855')]}
    for fuel,tanks in rows.items():
        for i,row in enumerate(tanks,1):
            for key,value in zip(('name','dist_mtrs','gauge_mtrs','volume_m3','temp_c','density_15c'),row):
                data[f'{fuel}_tank_{i}_{key}']=value
    return data
