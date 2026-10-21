import json
import sys
from urllib.request import Request,urlopen

BASE='https://api-som-fastapi-production-e66d.up.railway.app'
company=sys.argv[1] if len(sys.argv)>1 else 'MCI-CR'
headers={'X-User':'admin','X-Role':'master','X-Company-Code':company,'Content-Type':'application/json'}
payload=None
endpoint='/portia/context?start=2026-10-01&end=2026-10-16'
if '--ask' in sys.argv:
    endpoint='/portia/ask'
    payload=json.dumps({'question':'Responde por separado: ¿por qué tengo tantos gastos? ¿qué compone mi quincena? ¿dónde he vendido más? Distingue lo que falta y los datos verificables.', 'scope':'erp','start':'2026-10-01','end':'2026-10-16'}).encode()
with urlopen(Request(BASE+endpoint,headers=headers,data=payload),timeout=120) as response:
    result=json.load(response)
context=result.get('data') or result.get('context')
print(json.dumps({'company':context['company'],'warnings':context['warnings'],'sources':{k:{'count':v['count'],'totals':v['totals']} for k,v in context['sections'].items()},'mode':result.get('mode'),'model_warning':result.get('warning')},ensure_ascii=False,indent=2))
if payload:print(result['answer'])
