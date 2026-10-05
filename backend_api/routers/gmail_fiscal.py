from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.routing import APIRoute
from fastapi.responses import HTMLResponse
from html import escape
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

from database import get_db
from security.gmail_access import issue_session, require_gmail_admin
from services.gmail_fiscal_service import (
    complete_oauth,
    create_oauth_url,
    ensure_schema,
    oauth_configured,
    start_scheduler,
    sync_mailbox,
    _configured_account_profiles,
)


class PrivateRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()
        async def private_response(request):
            response = await handler(request)
            response.headers["Cache-Control"] = "no-store"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Content-Type-Options"] = "nosniff"
            return response
        return private_response


router=APIRouter(prefix="/accounting/tax/gmail",tags=["Gmail Fiscal Inbox"],route_class=PrivateRoute)


class GmailSession(BaseModel):
    usuario: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)
    codigo: str = Field(pattern=r"^\d{6}$")


@router.post("/session")
def gmail_session(payload: GmailSession, request: Request,
                  x_company_code: str = Header(default="MSL-CR"), conn=Depends(get_db)):
    company = x_company_code.strip().upper()
    if company not in {p["company_code"] for p in _configured_account_profiles()}:
        raise HTTPException(403, "Empresa no configurada para Gmail")
    return issue_session(conn, payload.usuario, payload.password, payload.codigo, company,
                         request.client.host if request.client else "unknown")


class OAuthStart(BaseModel):
    user:str="ERP_USER"
    account_email:str|None=None


class AutomationUpdate(BaseModel):
    enabled:bool
    interval_minutes:int=Field(default=10,ge=5,le=1440)
    search_query:str|None=None
    user:str="ERP_USER"
    account_email:str|None=None


def _accounts(principal):
    return [p["account_email"] for p in _configured_account_profiles()
            if p["company_code"] == principal["company"]]


def _account(value, principal):
    allowed = _accounts(principal)
    account = str(value or (allowed[0] if allowed else "")).strip().lower()
    if account not in allowed:
        raise HTTPException(403, "Buzon no autorizado para esta empresa")
    return account


@router.get("/status")
def connection_status(account_email:str|None=None,principal=Depends(require_gmail_admin),conn=Depends(get_db)):
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if account_email:
            cur.execute("""SELECT account_email,status,scopes,auto_enabled,interval_minutes,search_query,last_sync_at,
          next_sync_at,last_error,connected_by,connected_at,updated_at,
          encrypted_refresh_token IS NOT NULL authorized FROM gmail_fiscal_connections WHERE account_email=%s""",(_account(account_email,principal),))
            rows=[cur.fetchone()]
        else:
            cur.execute("""SELECT account_email,status,scopes,auto_enabled,interval_minutes,search_query,last_sync_at,
          next_sync_at,last_error,connected_by,connected_at,updated_at,
          encrypted_refresh_token IS NOT NULL authorized FROM gmail_fiscal_connections
          WHERE account_email=ANY(%s) ORDER BY account_email""", (_accounts(principal),))
            rows=cur.fetchall()
        accounts=[row for row in rows if row]
        counts={}
        for row in accounts:
            cur.execute("""SELECT status,COUNT(*) count FROM gmail_fiscal_messages WHERE account_email=%s GROUP BY status""",(row["account_email"],))
            counts[row["account_email"]]={r["status"]:r["count"] for r in cur.fetchall()}
    return {"connection":accounts[0] if len(accounts)==1 else None,"connections":accounts,"oauth_configured":oauth_configured(),"message_counts":counts}


@router.post("/oauth/start")
def oauth_start(payload:OAuthStart,principal=Depends(require_gmail_admin),conn=Depends(get_db)):
    account = _account(payload.account_email,principal)
    try: url=create_oauth_url(conn,principal["user"],account_email=account)
    except Exception: raise HTTPException(409,"No se pudo iniciar la autorizacion Gmail")
    return {"authorization_url":url,"expires_in_minutes":15,"account":account}


@router.get("/oauth/callback",response_class=HTMLResponse)
def oauth_callback(state:str|None=None,code:str|None=None,error:str|None=None,conn=Depends(get_db)):
    if error: return HTMLResponse(f"<h2>Autorización cancelada</h2><p>{escape(error)}</p>",status_code=400)
    if not state or not code: return HTMLResponse("<h2>Autorización incompleta</h2>",status_code=400)
    try: account=complete_oauth(conn,state,code)
    except Exception:
        conn.rollback()
        return HTMLResponse("<h2>No se pudo conectar Gmail</h2><p>La autorizacion no es valida, vencio o no corresponde al buzon solicitado. Inicie una nueva desde SOM.</p>",status_code=400)
    return HTMLResponse(f"<h2>Gmail conectado correctamente</h2><p>{escape(account)}</p><p>Puede cerrar esta ventana y regresar al ERP.</p>")


@router.put("/automation")
def update_automation(payload:AutomationUpdate,principal=Depends(require_gmail_admin),conn=Depends(get_db)):
    account = _account(payload.account_email,principal)
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if payload.enabled:
            cur.execute("SELECT encrypted_refresh_token FROM gmail_fiscal_connections WHERE account_email=%s",(account,))
            current=cur.fetchone()
            if not current or not current.get("encrypted_refresh_token"):
                raise HTTPException(409,"Autorice la cuenta Gmail antes de activar la revisión automática")
        cur.execute("""UPDATE gmail_fiscal_connections SET auto_enabled=%s,interval_minutes=%s,
          search_query=COALESCE(%s,search_query),next_sync_at=CASE WHEN %s THEN NOW() ELSE NULL END,updated_at=NOW()
          WHERE account_email=%s RETURNING account_email,status,auto_enabled,interval_minutes,search_query,next_sync_at""",
                    (payload.enabled,payload.interval_minutes,payload.search_query,payload.enabled,account)); row=cur.fetchone()
        cur.execute("INSERT INTO gmail_fiscal_audit(account_email,action,detail,performed_by) VALUES(%s,'AUTOMATION_UPDATED',jsonb_build_object('enabled',%s,'interval',%s),%s)",
                    (account,payload.enabled,payload.interval_minutes,principal["user"]))
    conn.commit(); return row


@router.post("/sync")
def run_sync(max_messages:int=Query(50,ge=1,le=100),account_email:str|None=None,principal=Depends(require_gmail_admin),conn=Depends(get_db)):
    account = _account(account_email,principal)
    try: return sync_mailbox(conn,triggered_by=principal["user"],max_messages=max_messages,account_email=account)
    except Exception: raise HTTPException(409,"No se pudo completar la sincronizacion Gmail")


@router.get("/messages")
def list_messages(status:str|None=None,account_email:str|None=None,limit:int=Query(100,ge=1,le=500),principal=Depends(require_gmail_admin),conn=Depends(get_db)):
    ensure_schema(conn); where=["account_email=%s"]; params=[_account(account_email,principal)]
    if status: where.append("status=%s"); params.append(status.upper())
    params.append(limit)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""SELECT * FROM gmail_fiscal_messages WHERE {' AND '.join(where)}
          ORDER BY received_at DESC NULLS LAST,id DESC LIMIT %s""",params); rows=cur.fetchall()
    return {"data":rows,"count":len(rows)}


@router.get("/messages/{message_id}/attachments")
def message_attachments(message_id:int,principal=Depends(require_gmail_admin),conn=Depends(get_db)):
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT id,message_id,gmail_attachment_id,filename,mime_type,content_hash,size_bytes,status,
          tax_document_id,error_detail,created_at FROM gmail_fiscal_attachments
          WHERE message_id=%s AND message_id IN (SELECT id FROM gmail_fiscal_messages
          WHERE account_email=ANY(%s)) ORDER BY id""",(message_id,_accounts(principal))); rows=cur.fetchall()
    return {"data":rows}


@router.delete("/connection")
def disconnect(account_email:str|None=None,principal=Depends(require_gmail_admin),conn=Depends(get_db)):
    account = _account(account_email,principal)
    ensure_schema(conn)
    with conn.cursor() as cur:
        cur.execute("""UPDATE gmail_fiscal_connections SET encrypted_refresh_token=NULL,status='PENDING_AUTH',auto_enabled=FALSE,
          next_sync_at=NULL,last_error=NULL,updated_at=NOW() WHERE account_email=%s""",(account,))
        cur.execute("UPDATE gmail_fiscal_oauth_states SET consumed_at=NOW() WHERE account_email=%s AND consumed_at IS NULL", (account,))
        cur.execute("INSERT INTO gmail_fiscal_audit(account_email,action,performed_by) VALUES(%s,'DISCONNECTED',%s)",(account,principal["user"]))
    conn.commit(); return {"message":"Conexión local eliminada; revoque también el acceso en Google si corresponde"}


def start_gmail_fiscal_scheduler():
    start_scheduler()
