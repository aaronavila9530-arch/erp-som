from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from html import escape
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, Field

from database import get_db
from services.gmail_fiscal_service import (
    ACCOUNT,
    complete_oauth,
    create_oauth_url,
    ensure_schema,
    oauth_configured,
    start_scheduler,
    sync_mailbox,
)


router=APIRouter(prefix="/accounting/tax/gmail",tags=["Gmail Fiscal Inbox"])


class OAuthStart(BaseModel):
    user:str="ERP_USER"


class AutomationUpdate(BaseModel):
    enabled:bool
    interval_minutes:int=Field(default=10,ge=5,le=1440)
    search_query:str|None=None
    user:str="ERP_USER"


@router.get("/status")
def connection_status(conn=Depends(get_db)):
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT account_email,status,scopes,auto_enabled,interval_minutes,search_query,last_sync_at,
          next_sync_at,last_error,connected_by,connected_at,updated_at,
          encrypted_refresh_token IS NOT NULL authorized FROM gmail_fiscal_connections WHERE account_email=%s""",(ACCOUNT,))
        row=cur.fetchone()
        cur.execute("""SELECT status,COUNT(*) count FROM gmail_fiscal_messages WHERE account_email=%s GROUP BY status""",(ACCOUNT,))
        counts={r["status"]:r["count"] for r in cur.fetchall()}
    return {"connection":row,"oauth_configured":oauth_configured(),"message_counts":counts}


@router.post("/oauth/start")
def oauth_start(payload:OAuthStart,conn=Depends(get_db)):
    try: url=create_oauth_url(conn,payload.user)
    except Exception as exc: raise HTTPException(409,str(exc))
    return {"authorization_url":url,"expires_in_minutes":15,"account":ACCOUNT}


@router.get("/oauth/callback",response_class=HTMLResponse)
def oauth_callback(state:str|None=None,code:str|None=None,error:str|None=None,conn=Depends(get_db)):
    if error: return HTMLResponse(f"<h2>Autorización cancelada</h2><p>{escape(error)}</p>",status_code=400)
    if not state or not code: return HTMLResponse("<h2>Autorización incompleta</h2>",status_code=400)
    try: account=complete_oauth(conn,state,code)
    except Exception as exc: return HTMLResponse(f"<h2>No se pudo conectar Gmail</h2><p>{escape(str(exc))}</p>",status_code=400)
    return HTMLResponse(f"<h2>Gmail conectado correctamente</h2><p>{account}</p><p>Puede cerrar esta ventana y regresar al ERP.</p>")


@router.put("/automation")
def update_automation(payload:AutomationUpdate,conn=Depends(get_db)):
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if payload.enabled:
            cur.execute("SELECT encrypted_refresh_token FROM gmail_fiscal_connections WHERE account_email=%s",(ACCOUNT,))
            current=cur.fetchone()
            if not current or not current.get("encrypted_refresh_token"):
                raise HTTPException(409,"Autorice la cuenta Gmail antes de activar la revisión automática")
        cur.execute("""UPDATE gmail_fiscal_connections SET auto_enabled=%s,interval_minutes=%s,
          search_query=COALESCE(%s,search_query),next_sync_at=CASE WHEN %s THEN NOW() ELSE NULL END,updated_at=NOW()
          WHERE account_email=%s RETURNING account_email,status,auto_enabled,interval_minutes,search_query,next_sync_at""",
                    (payload.enabled,payload.interval_minutes,payload.search_query,payload.enabled,ACCOUNT)); row=cur.fetchone()
        cur.execute("INSERT INTO gmail_fiscal_audit(account_email,action,detail,performed_by) VALUES(%s,'AUTOMATION_UPDATED',jsonb_build_object('enabled',%s,'interval',%s),%s)",
                    (ACCOUNT,payload.enabled,payload.interval_minutes,payload.user))
    conn.commit(); return row


@router.post("/sync")
def run_sync(max_messages:int=Query(50,ge=1,le=100),user:str="ERP_USER",conn=Depends(get_db)):
    try: return sync_mailbox(conn,triggered_by=user,max_messages=max_messages)
    except Exception as exc: raise HTTPException(409,str(exc))


@router.get("/messages")
def list_messages(status:str|None=None,limit:int=Query(100,ge=1,le=500),conn=Depends(get_db)):
    ensure_schema(conn); where=["account_email=%s"]; params=[ACCOUNT]
    if status: where.append("status=%s"); params.append(status.upper())
    params.append(limit)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""SELECT * FROM gmail_fiscal_messages WHERE {' AND '.join(where)}
          ORDER BY received_at DESC NULLS LAST,id DESC LIMIT %s""",params); rows=cur.fetchall()
    return {"data":rows,"count":len(rows)}


@router.get("/messages/{message_id}/attachments")
def message_attachments(message_id:int,conn=Depends(get_db)):
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT id,message_id,gmail_attachment_id,filename,mime_type,content_hash,size_bytes,status,
          tax_document_id,error_detail,stored_path,created_at FROM gmail_fiscal_attachments WHERE message_id=%s ORDER BY id""",(message_id,)); rows=cur.fetchall()
    return {"data":rows}


@router.delete("/connection")
def disconnect(user:str="ERP_USER",conn=Depends(get_db)):
    ensure_schema(conn)
    with conn.cursor() as cur:
        cur.execute("""UPDATE gmail_fiscal_connections SET encrypted_refresh_token=NULL,status='PENDING_AUTH',auto_enabled=FALSE,
          next_sync_at=NULL,last_error=NULL,updated_at=NOW() WHERE account_email=%s""",(ACCOUNT,))
        cur.execute("INSERT INTO gmail_fiscal_audit(account_email,action,performed_by) VALUES(%s,'DISCONNECTED',%s)",(ACCOUNT,user))
    conn.commit(); return {"message":"Conexión local eliminada; revoque también el acceso en Google si corresponde"}


def start_gmail_fiscal_scheduler():
    start_scheduler()
