"""Local-only UI harness. Synthetic credentials, no database or Google calls."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from routers.som_web import som_web_home

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
def preview():
    html = som_web_home().body.decode()
    helpers = html.split("    let gmailAdminSession = null;", 1)[1].split("    async function getJSON", 1)[0]
    return '''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <style>body{font-family:system-ui}label{display:block;margin:16px 0}input{display:block;width:100%;box-sizing:border-box;padding:8px}button{padding:8px}.error{color:#b42318}</style>
    <button id="start">Estado Gmail</button><p id="result"></p><script>
    const session={usuario:'test-admin'};
    const esc = x => String(x);
    const selectedCompany=()=> 'MSL-CR';
    const headers=()=>({'Content-Type':'application/json','X-Company-Code':'MSL-CR'});
    let gmailAdminSession = null;
    ''' + helpers + '''
    document.getElementById('start').onclick=async()=>{
      try { const r=await secureFetch('/accounting/tax/gmail/status',{headers:headers()}); document.getElementById('result').textContent=r.ok?'Authorized':'Denied'; }
      catch(e){document.getElementById('result').textContent=e.message;}
    };
    </script></html>'''


@app.post("/accounting/tax/gmail/session")
def session(payload: dict):
    if payload.get("password") != "demo-only" or payload.get("codigo") != "123456":
        return JSONResponse({"detail": "Credenciales o permisos no validos"}, status_code=401)
    return {"access_token": "synthetic-test-token", "expires_in": 900}


@app.get("/accounting/tax/gmail/status")
def status():
    return {"status": "TEST"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8799)
