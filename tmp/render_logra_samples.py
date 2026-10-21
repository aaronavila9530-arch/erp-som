"""Generate deterministic export fixtures, never connected to production."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend_api'))
from services.logra_web_export import build
from routers.logra_web import CATALOG
form=CATALOG[0]
payload={'report':{'id':'QA','title':'LOGRA Agencias navieras','status':'Pending','version':2,'created_by':'QA',
    'agenda_items':[{'date_iso':'2026-10-19','start_time':'09:01','end_time':'10:00','place':'Puerto de prueba',
                     'person':'Persona de prueba','company':'Empresa de prueba','topic':'Revision de requisitos operativos','status':'Pendiente','priority':'Alta'}],
    'agenda_notes':'Confirmar documentos pendientes y registrar las fuentes de cada respuesta.'},
    'answers':[{'form_slug':form['slug'],'form_title':form['title'],'section':'critical_questions','item_key':str(q['number']),
        'question_text':q['question'],'bullets':['Observacion de prueba para validar el formato. No representa un hallazgo real.',
        'Pendiente de confirmar con evidencia documental. Se conserva el texto completo sin cambiar su significado.']} for q in form['critical_questions'][:3]],'attachments':[]}
folder=root/'tmp/logra-qa';folder.mkdir(exist_ok=True)
for kind in ('pdf','docx','xlsx'):
    (folder/f'export-sample.{kind}').write_bytes(build(payload,kind))
print(folder)
