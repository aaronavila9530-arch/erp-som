"""One synthetic, non-persistent PORTIA request; no real questionnaire data."""
import requests
base='https://api-som-fastapi-production-e66d.up.railway.app'
headers={'X-User':'admin','X-Role':'master','X-Company-Code':'MCI-CR'}
response=requests.post(base+'/informes/logra/improve',headers=headers,json={
    'form_slug':'agencias_navieras_y_agentes','section':'critical_questions','item_key':'1',
    'text':'La informacion sobre el buque de mayor porte aun esta pendiente de confirmacion documental.',
    'language':'ES'},timeout=90)
print('PORTIA HTTP',response.status_code)
response.raise_for_status()
print(response.json()['text'])
