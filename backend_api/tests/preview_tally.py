"""Local UI fixture only. No production DB or customer records."""
import sys
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routers.tally import router, SheetInput, ProjectInput, export_workbook

app=FastAPI()
projects=[dict(id=1,name="MV DEMO - Tally",holds=[1,3,5],service_id=100,revision=0)]
sheets={}
drivers=[dict(plate="AB123",driver="CHOFER DEMO")]
companies=["TRANSPORTE DEMO"]

@app.get("/")
def home():
    return HTMLResponse('''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <link rel="stylesheet" href="/som/tally-assets/tabulator.min.css"><link rel="stylesheet" href="/som/tally-assets/tally.css">
    <style>body{margin:20px;font-family:Arial}*{box-sizing:border-box}</style><main id="app"></main>
    <script src="/som/tally-assets/tabulator.min.js"></script><script src="/som/tally-assets/papaparse.min.js"></script><script src="/som/tally-assets/tally.js?v=2"></script>
    <script>async function request(path,method='GET',body){const r=await fetch(path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:JSON.stringify(d.detail));return d;}
    SOMTally.mount(document.querySelector('#app'),{company:'TEST',user:'test',headers:()=>({'Content-Type':'application/json'}),getJSON:p=>request(p),postJSON:(p,b)=>request(p,'POST',b),sendJSON:(m,p,b)=>request(p,m,b)});</script>''')

@app.get("/tally/bootstrap")
def bootstrap():
    return dict(projects=projects,drivers=drivers,companies=companies,services=[dict(consec=100,buque_contenedor="MV DEMO",cliente="TEST")],editable=True)

@app.post("/tally/projects")
def create(body:ProjectInput):
    row=dict(id=len(projects)+1,**body.model_dump());projects.append(row);return row

@app.put("/tally/projects/{pid}")
def update(pid:int,body:ProjectInput):
    row=next(p for p in projects if p['id']==pid);row.update(body.model_dump());row['revision']+=1;return row

@app.get("/tally/projects/{pid}/sheets/{hold}")
def read(pid:int,hold:int):
    return sheets.get((pid,hold),dict(revision=0,rows=[]))

@app.put("/tally/projects/{pid}/sheets/{hold}")
def save(pid:int,hold:int,body:SheetInput):
    old=read(pid,hold)
    if old['revision']!=body.revision:raise HTTPException(409,'Otra persona modifico esta bodega. Sus cambios no se sobrescribieron.')
    rows=[r.model_dump(mode='json') for r in body.rows]
    for r in rows:r['driver']=next((d['driver'] for d in drivers if d['plate']==r['plate']),'')
    sheets[(pid,hold)]=dict(revision=body.revision+1,rows=rows)
    return dict(revision=body.revision+1,count=len(rows))

@app.get("/tally/projects/{pid}/excel")
def excel(pid:int):
    p=next(p for p in projects if p['id']==pid)
    return StreamingResponse(export_workbook(p,{h:read(pid,h)['rows'] for h in p['holds']}),headers={'Content-Disposition':'attachment; filename="demo.xlsx"'})

app.include_router(router)

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8801)
