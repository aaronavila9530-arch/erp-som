from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import secrets
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from psycopg2.extras import Json, RealDictCursor

from database import get_conn, release_conn
from routers.accounting_tax import _ensure_schema as ensure_tax_schema, _local, _parse_xml, _save_document


GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/gmail.modify"
ACCOUNT = os.getenv("GMAIL_ACCOUNT", "gastos@mslogisticsgroup.com")
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_ZIP_MEMBERS = 50
_SCHEMA_READY = False
_SCHEDULER_STARTED = False


def ensure_schema(conn):
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    ensure_tax_schema(conn)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gmail_fiscal_connections (
                account_email TEXT PRIMARY KEY,
                encrypted_refresh_token TEXT,
                status VARCHAR(25) NOT NULL DEFAULT 'PENDING_AUTH',
                scopes TEXT,
                auto_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                interval_minutes INTEGER NOT NULL DEFAULT 10,
                search_query TEXT NOT NULL DEFAULT 'has:attachment (filename:xml OR filename:zip) newer_than:365d',
                last_sync_at TIMESTAMPTZ,
                next_sync_at TIMESTAMPTZ,
                last_error TEXT,
                connected_by TEXT,
                connected_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CHECK(interval_minutes BETWEEN 5 AND 1440)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gmail_fiscal_oauth_states (
                state VARCHAR(100) PRIMARY KEY,
                account_email TEXT NOT NULL,
                requested_by TEXT,
                expires_at TIMESTAMPTZ NOT NULL,
                consumed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gmail_fiscal_messages (
                id BIGSERIAL PRIMARY KEY,
                account_email TEXT NOT NULL,
                gmail_message_id TEXT NOT NULL,
                gmail_thread_id TEXT,
                sender TEXT,
                subject TEXT,
                received_at TIMESTAMPTZ,
                status VARCHAR(25) NOT NULL DEFAULT 'NEW',
                attachment_count INTEGER NOT NULL DEFAULT 0,
                xml_count INTEGER NOT NULL DEFAULT 0,
                imported_count INTEGER NOT NULL DEFAULT 0,
                duplicate_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                error_detail TEXT,
                processed_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(account_email,gmail_message_id)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gmail_fiscal_attachments (
                id BIGSERIAL PRIMARY KEY,
                message_id BIGINT NOT NULL REFERENCES gmail_fiscal_messages(id) ON DELETE CASCADE,
                gmail_attachment_id TEXT,
                filename TEXT,
                mime_type TEXT,
                content_hash VARCHAR(64),
                size_bytes BIGINT,
                status VARCHAR(25) NOT NULL DEFAULT 'NEW',
                tax_document_id BIGINT REFERENCES tax_electronic_documents(id),
                error_detail TEXT,
                stored_path TEXT,
                content BYTEA,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(message_id,content_hash,filename)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gmail_fiscal_audit (
                id BIGSERIAL PRIMARY KEY,
                account_email TEXT NOT NULL,
                action VARCHAR(40) NOT NULL,
                detail JSONB NOT NULL DEFAULT '{}'::jsonb,
                performed_by TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("ALTER TABLE gmail_fiscal_attachments ADD COLUMN IF NOT EXISTS content BYTEA")
        cur.execute("""INSERT INTO gmail_fiscal_connections(account_email) VALUES(%s)
          ON CONFLICT(account_email) DO NOTHING""", (ACCOUNT,))
    conn.commit()
    _SCHEMA_READY = True


def _fernet():
    key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "").strip().encode()
    if not key:
        raise RuntimeError("Falta CREDENTIAL_ENCRYPTION_KEY en el backend")
    try:
        return Fernet(key)
    except Exception as exc:
        raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY no es una llave Fernet válida") from exc


def encrypt_token(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_token(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise RuntimeError("No se pudo descifrar el token de Gmail") from exc


def oauth_configured():
    return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET") and os.getenv("GOOGLE_REDIRECT_URI") and os.getenv("CREDENTIAL_ENCRYPTION_KEY"))


def create_oauth_url(conn, requested_by: str):
    ensure_schema(conn)
    if not oauth_configured():
        raise RuntimeError("Faltan GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI o CREDENTIAL_ENCRYPTION_KEY")
    state = secrets.token_urlsafe(40)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gmail_fiscal_oauth_states WHERE expires_at<NOW() OR consumed_at IS NOT NULL")
        cur.execute("INSERT INTO gmail_fiscal_oauth_states(state,account_email,requested_by,expires_at) VALUES(%s,%s,%s,NOW()+INTERVAL '15 minutes')",
                    (state, ACCOUNT, requested_by))
    conn.commit()
    params = {"client_id":os.getenv("GOOGLE_CLIENT_ID"),"redirect_uri":os.getenv("GOOGLE_REDIRECT_URI"),
              "response_type":"code","scope":SCOPES,"access_type":"offline","prompt":"consent",
              "include_granted_scopes":"true","login_hint":ACCOUNT,"state":state}
    return GOOGLE_AUTH + "?" + urlencode(params)


def complete_oauth(conn, state: str, code: str):
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM gmail_fiscal_oauth_states WHERE state=%s AND consumed_at IS NULL AND expires_at>NOW() FOR UPDATE", (state,))
        record = cur.fetchone()
        if not record:
            raise RuntimeError("La autorización expiró o ya fue utilizada")
        response = requests.post(GOOGLE_TOKEN, data={"code":code,"client_id":os.getenv("GOOGLE_CLIENT_ID"),
          "client_secret":os.getenv("GOOGLE_CLIENT_SECRET"),"redirect_uri":os.getenv("GOOGLE_REDIRECT_URI"),"grant_type":"authorization_code"}, timeout=20)
        response.raise_for_status(); token=response.json(); refresh=token.get("refresh_token")
        if not refresh:
            raise RuntimeError("Google no devolvió refresh_token; revoque el acceso anterior y vuelva a autorizar")
        profile=_api(token["access_token"],"GET","/profile")
        if str(profile.get("emailAddress") or "").lower()!=str(record["account_email"]).lower():
            raise RuntimeError(f"Se autorizó {profile.get('emailAddress')} pero se esperaba {record['account_email']}")
        cur.execute("""UPDATE gmail_fiscal_connections SET encrypted_refresh_token=%s,status='CONNECTED',scopes=%s,
          connected_by=%s,connected_at=NOW(),last_error=NULL,updated_at=NOW() WHERE account_email=%s""",
                    (encrypt_token(refresh),token.get("scope",SCOPES),record.get("requested_by"),record["account_email"]))
        cur.execute("UPDATE gmail_fiscal_oauth_states SET consumed_at=NOW() WHERE state=%s",(state,))
        cur.execute("INSERT INTO gmail_fiscal_audit(account_email,action,performed_by) VALUES(%s,'OAUTH_CONNECTED',%s)",
                    (record["account_email"],record.get("requested_by")))
    conn.commit()
    return record["account_email"]


def _access_token(refresh_token):
    response=requests.post(GOOGLE_TOKEN,data={"client_id":os.getenv("GOOGLE_CLIENT_ID"),"client_secret":os.getenv("GOOGLE_CLIENT_SECRET"),
      "refresh_token":refresh_token,"grant_type":"refresh_token"},timeout=20)
    response.raise_for_status(); return response.json()["access_token"]


def _api(token, method, path, **kwargs):
    headers=kwargs.pop("headers",{}); headers["Authorization"]=f"Bearer {token}"
    response=requests.request(method,GMAIL_API+path,headers=headers,timeout=30,**kwargs)
    response.raise_for_status(); return response.json() if response.content else {}


def _headers(payload):
    return {item.get("name","").lower():item.get("value","") for item in payload.get("headers",[])}


def _walk_parts(payload):
    for part in payload.get("parts",[]) or []:
        yield part
        yield from _walk_parts(part)


def _decode_b64(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _attachment_bytes(token, message_id, part):
    body=part.get("body") or {}
    if body.get("data"):
        return _decode_b64(body["data"])
    attachment_id=body.get("attachmentId")
    if not attachment_id:
        return b""
    data=_api(token,"GET",f"/messages/{message_id}/attachments/{attachment_id}")
    return _decode_b64(data.get("data", ""))


def _xml_members(filename, content):
    if len(content)>MAX_ATTACHMENT_BYTES:
        raise ValueError("Adjunto mayor a 20 MB")
    if filename.lower().endswith(".xml"):
        return [(filename,content)]
    if not filename.lower().endswith(".zip"):
        return []
    result=[]
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members=[x for x in archive.infolist() if not x.is_dir()]
        if len(members)>MAX_ZIP_MEMBERS:
            raise ValueError("ZIP con más de 50 archivos")
        for member in members:
            normalized=Path(member.filename)
            if normalized.is_absolute() or ".." in normalized.parts:
                raise ValueError("Ruta insegura dentro del ZIP")
            if member.file_size>MAX_ATTACHMENT_BYTES:
                raise ValueError("XML comprimido mayor a 20 MB")
            if member.filename.lower().endswith(".xml"):
                result.append((Path(member.filename).name,archive.read(member)))
    return result


def _response_data(content):
    import xml.etree.ElementTree as ET
    try: root=ET.fromstring(content)
    except ET.ParseError: return None
    if _local(root.tag) not in {"MensajeHacienda","RespuestaHacienda"}: return None
    def text(name):
        return next((x.text.strip() for x in root.iter() if _local(x.tag)==name and x.text),None)
    return {"key":text("Clave"),"message":text("Mensaje") or text("IndEstado"),"detail":text("DetalleMensaje") or text("RespuestaXml")}


def _store_path(kind, digest, filename, content):
    folder=Path("storage/gmail_fiscal")/kind/datetime.now().strftime("%Y/%m")
    folder.mkdir(parents=True,exist_ok=True)
    safe=re.sub(r"[^A-Za-z0-9_.-]","_",filename)[:150]
    path=folder/f"{digest[:12]}_{safe}"; path.write_bytes(content); return str(path)


def _ensure_payment_obligation(cur, data, xml_path):
    reference=data.get("electronic_key") or data.get("document_number")
    if not reference:
        return None
    cur.execute("SELECT id FROM payment_obligations WHERE reference=%s AND active=TRUE ORDER BY id LIMIT 1",(reference,))
    existing=cur.fetchone()
    if existing:
        return existing["id"]
    issue=(data.get("issue_datetime") or datetime.now()).date()
    due=issue+timedelta(days=30)
    is_credit=data.get("document_type") in {"NC","NCE"}
    total=-(abs(data.get("total") or 0)) if is_credit else data.get("total") or 0
    cur.execute("""INSERT INTO payment_obligations(record_type,payee_type,payee_name,obligation_type,reference,
      issue_date,due_date,country,currency,total,balance,status,origin,file_xml,active,notes,created_at,updated_at)
      VALUES('OBLIGATION','SUPPLIER',%s,%s,%s,%s,%s,'Costa Rica',%s,%s,%s,'PENDING','GMAIL',%s,TRUE,%s,NOW(),NOW()) RETURNING id""",
                (data.get("issuer_name") or "PROVEEDOR POR VALIDAR","SUPPLIER_CREDIT_NOTE" if is_credit else "SUPPLIER_INVOICE",
                 reference,issue,due,data.get("currency_code") or "CRC",total,total,xml_path,
                 f"Importado automáticamente desde {ACCOUNT}"))
    return cur.fetchone()["id"]


def _process_xml(cur, message_db_id, filename, content, gmail_attachment_id):
    digest=hashlib.sha256(content).hexdigest()
    cur.execute("SELECT id,status,tax_document_id FROM gmail_fiscal_attachments WHERE message_id=%s AND content_hash=%s AND filename=%s",
                (message_db_id,digest,filename)); existing=cur.fetchone()
    if existing:
        return existing["status"],existing.get("tax_document_id")
    response=_response_data(content)
    if response:
        path=_store_path("responses",digest,filename,content)
        cur.execute("SELECT id FROM tax_electronic_documents WHERE electronic_key=%s ORDER BY id DESC LIMIT 1",(response.get("key"),)); doc=cur.fetchone()
        if not doc:
            status="REVIEW"; tax_id=None; error="Respuesta de Hacienda sin comprobante asociado"
        else:
            status_map={"1":"ACCEPTED","2":"PARTIAL","3":"REJECTED"}; hacienda=status_map.get(str(response.get("message")),str(response.get("message") or "PENDING").upper())
            cur.execute("UPDATE tax_electronic_documents SET hacienda_status=%s,hacienda_message=%s,response_xml_path=%s,response_xml_content=%s,status=%s,updated_at=NOW() WHERE id=%s",
                        (hacienda,response.get("detail"),path,content,hacienda,doc["id"])); status="IMPORTED"; tax_id=doc["id"]; error=None
    else:
        data=_parse_xml(content); key=data.get("electronic_key")
        cur.execute("SELECT id FROM tax_electronic_documents WHERE direction='PURCHASE' AND (xml_hash=%s OR (electronic_key=%s AND %s IS NOT NULL)) ORDER BY id LIMIT 1",
                    (digest,key,key)); doc=cur.fetchone()
        if doc:
            status="DUPLICATE"; tax_id=doc["id"]; error="XML ya registrado"
        else:
            path=_store_path("xml",digest,filename,content)
            tax_id=_save_document(cur,"PURCHASE",data,xml_hash=digest,xml_path=path,xml_content=content,source_table="gmail_attachment",source_id=digest,user="GMAIL_AUTOMATION")
            _ensure_payment_obligation(cur,data,path)
            status="IMPORTED"; error=None
    cur.execute("""INSERT INTO gmail_fiscal_attachments(message_id,gmail_attachment_id,filename,mime_type,content_hash,size_bytes,status,tax_document_id,error_detail,stored_path,content)
      VALUES(%s,%s,%s,'application/xml',%s,%s,%s,%s,%s,%s,%s)""",
                (message_db_id,gmail_attachment_id,filename,digest,len(content),status,tax_id,error,path if 'path' in locals() else None,content))
    return status,tax_id


def _labels(token):
    current=_api(token,"GET","/labels").get("labels",[]); by_name={x["name"]:x["id"] for x in current}
    result={}
    for name in ("ERP-SOM/Procesado","ERP-SOM/Revisar","ERP-SOM/Duplicado"):
        if name not in by_name:
            created=_api(token,"POST","/labels",json={"name":name,"labelListVisibility":"labelShow","messageListVisibility":"show"})
            by_name[name]=created["id"]
        result[name]=by_name[name]
    return result


def sync_mailbox(conn, triggered_by="SCHEDULER", max_messages=50):
    ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT pg_try_advisory_lock(hashtext(%s)) locked",(f"gmail-fiscal:{ACCOUNT}",)); locked=cur.fetchone()["locked"]
        if not locked: return {"status":"busy","message":"Ya existe una sincronización en curso"}
        try:
            cur.execute("SELECT * FROM gmail_fiscal_connections WHERE account_email=%s",(ACCOUNT,)); config=cur.fetchone()
            if not config or not config.get("encrypted_refresh_token"): raise RuntimeError("La cuenta Gmail todavía no ha sido autorizada")
            token=_access_token(decrypt_token(config["encrypted_refresh_token"])); labels=_labels(token)
            query=config["search_query"]+" -label:ERP-SOM/Procesado -label:ERP-SOM/Revisar -label:ERP-SOM/Duplicado"
            listed=_api(token,"GET","/messages",params={"q":query,"maxResults":min(max_messages,100)}).get("messages",[])
            summary={"messages":0,"xml":0,"imported":0,"duplicates":0,"review":0}
            for item in listed:
                msg=_api(token,"GET",f"/messages/{item['id']}",params={"format":"full"}); payload=msg.get("payload") or {}; hdr=_headers(payload)
                received=parsedate_to_datetime(hdr["date"]) if hdr.get("date") else None
                cur.execute("""INSERT INTO gmail_fiscal_messages(account_email,gmail_message_id,gmail_thread_id,sender,subject,received_at)
                  VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(account_email,gmail_message_id) DO UPDATE SET updated_at=NOW() RETURNING id""",
                            (ACCOUNT,item["id"],msg.get("threadId"),hdr.get("from"),hdr.get("subject"),received)); message_db_id=cur.fetchone()["id"]
                attachments=xml_count=imported=duplicates=errors=0; error_details=[]
                for part in _walk_parts(payload):
                    filename=part.get("filename") or ""
                    if not filename.lower().endswith((".xml",".zip")): continue
                    attachments+=1
                    try:
                        raw=_attachment_bytes(token,item["id"],part)
                        members=_xml_members(filename,raw)
                        if not members:
                            errors+=1; error_details.append(f"{filename}: no contiene archivos XML")
                        for inner_name,xml in members:
                            xml_count+=1
                            try:
                                status,_=_process_xml(cur,message_db_id,inner_name,xml,(part.get("body") or {}).get("attachmentId"))
                                if status=="IMPORTED": imported+=1
                                elif status=="DUPLICATE": duplicates+=1
                                else: errors+=1
                            except Exception as exc:
                                errors+=1; error_details.append(f"{inner_name}: {exc}")
                    except Exception as exc:
                        errors+=1; error_details.append(f"{filename}: {exc}")
                status="REVIEW" if errors else ("DUPLICATE" if duplicates and not imported else "PROCESSED")
                label=labels["ERP-SOM/Revisar" if status=="REVIEW" else ("ERP-SOM/Duplicado" if status=="DUPLICATE" else "ERP-SOM/Procesado")]
                _api(token,"POST",f"/messages/{item['id']}/modify",json={"addLabelIds":[label]})
                cur.execute("""UPDATE gmail_fiscal_messages SET status=%s,attachment_count=%s,xml_count=%s,imported_count=%s,
                  duplicate_count=%s,error_count=%s,error_detail=%s,processed_at=NOW(),updated_at=NOW() WHERE id=%s""",
                            (status,attachments,xml_count,imported,duplicates,errors,"\n".join(error_details) or None,message_db_id))
                summary["messages"]+=1; summary["xml"]+=xml_count; summary["imported"]+=imported; summary["duplicates"]+=duplicates; summary["review"]+=errors
                conn.commit()
            cur.execute("""UPDATE gmail_fiscal_connections SET status='CONNECTED',last_sync_at=NOW(),next_sync_at=NOW()+(interval_minutes||' minutes')::interval,
              last_error=NULL,updated_at=NOW() WHERE account_email=%s""",(ACCOUNT,))
            cur.execute("INSERT INTO gmail_fiscal_audit(account_email,action,detail,performed_by) VALUES(%s,'SYNC',%s,%s)",(ACCOUNT,Json(summary),triggered_by)); conn.commit()
            return {"status":"ok",**summary}
        except Exception as exc:
            conn.rollback()
            cur.execute("UPDATE gmail_fiscal_connections SET last_error=%s,updated_at=NOW() WHERE account_email=%s",(str(exc),ACCOUNT)); conn.commit()
            raise
        finally:
            cur.execute("SELECT pg_advisory_unlock(hashtext(%s))",(f"gmail-fiscal:{ACCOUNT}",)); conn.commit()


def _scheduler_loop():
    while True:
        time.sleep(60)
        conn=None
        try:
            conn=get_conn(); ensure_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT auto_enabled,status,next_sync_at FROM gmail_fiscal_connections WHERE account_email=%s",(ACCOUNT,)); cfg=cur.fetchone()
            if cfg and cfg["auto_enabled"] and cfg["status"]=="CONNECTED" and (not cfg["next_sync_at"] or cfg["next_sync_at"]<=datetime.now(timezone.utc)):
                sync_mailbox(conn)
        except Exception as exc:
            print(f"Gmail fiscal scheduler: {exc}")
        finally:
            if conn: release_conn(conn)


def start_scheduler():
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED: return
    _SCHEDULER_STARTED=True
    threading.Thread(target=_scheduler_loop,name="gmail-fiscal-scheduler",daemon=True).start()
