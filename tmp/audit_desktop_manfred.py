import requests
from collections import Counter

base='https://api-som-fastapi-production-e66d.up.railway.app'
headers={'X-User':'admin','X-Role':'master','X-User-Role':'master','X-Company-Code':'MSL-CR'}
import sys
if '--surveyor' in sys.argv:
    headers.update({'X-User': 'surveyor01', 'X-Role': 'user', 'X-User-Role': 'user'})
if '--laura' in sys.argv:
    for company in ('MSL-CR','MCI-CR'):
        r=requests.get(base+'/comercial/board',headers={**headers,'X-Company-Code':company},params={'year':2026},timeout=40)
        print(company,'HTTP',r.status_code)
        if r.ok:
            for row in r.json():
                if 'LAURA' in str(row.get('buque_contenedor','')).upper():
                    print({k:row.get(k) for k in ('consec','num_informe','buque_contenedor','estado','operacion','surveyor','fecha_inicio','fecha_fin')})
    sys.exit()
for params in ({'estados':['Confirmado','En Operación']},{'estados':['FINALIZADO'],'year':2026}):
    r=requests.get(base+'/comercial/board',headers=headers,params=params,timeout=40)
    print('BOARD',params,'HTTP',r.status_code)
    if r.ok:
        rows=r.json();print('count',len(rows),'states',dict(Counter(x.get('estado') for x in rows)))
        print('Manfred services',[{'report':x.get('num_informe'),'vessel':x.get('buque_contenedor'),'state':x.get('estado'),'operation':x.get('operacion')} for x in rows if 'manfred' in str(x.get('surveyor','')).lower() or 'surveyor01' in str(x.get('surveyor','')).lower()])
    else:print(r.text[:500])
r=requests.get(base+'/hr/events/',headers=headers,timeout=40)
print('HR HTTP',r.status_code)
if r.ok:print('Manfred requests',[{'id':x['id'],'status':x['status'],'event_type':x['event_type'],'date':x['event_date']} for x in r.json() if x.get('created_by')=='surveyor01'])
else:print(r.text[:500])
