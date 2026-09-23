from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import secrets
import sys
import threading
import time
import zipfile
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode

import requests
from cryptography.fernet import Fernet, InvalidToken
from psycopg2.extras import Json, RealDictCursor

from database import get_conn, release_conn
from routers.accounting_tax import _ensure_purchase_obligation, _ensure_schema as ensure_tax_schema, _local, _parse_xml, _save_document
from routers.corporate_cards import (
    BacNotificationRequest,
    HistoryPostRequest,
    import_bac_notification,
    import_statement_pdf_bytes,
    post_history as post_corporate_card_history,
)


GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
SCOPES = "https://www.googleapis.com/auth/gmail.modify"
ACCOUNT = os.getenv("GMAIL_ACCOUNT", "gastos@mslogisticsgroup.com")
DEFAULT_SEARCH_QUERY = (
    '(has:attachment (filename:xml OR filename:zip OR filename:pdf) '
    'OR from:baccredomatic.com OR subject:BAC OR subject:"Notificación BAC") newer_than:730d'
)
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024
MAX_ZIP_MEMBERS = 50
_SCHEMA_READY = False
_SCHEDULER_STARTED = False
_CARD_HISTORY_POSTED_MONTH: str | None = None


def _configured_account_profiles() -> list[dict[str, object]]:
    raw = os.getenv("GMAIL_ACCOUNT_PROFILES", "").strip()
    profiles: list[dict[str, object]] = []
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            for item in data or []:
                if not isinstance(item, dict):
                    continue
                email = str(item.get("account_email") or item.get("email") or "").strip().lower()
                if not email:
                    continue
                profiles.append({
                    "account_email": email,
                    "company_code": str(item.get("company_code") or "MSL-CR").strip().upper(),
                    "process_bac": bool(item.get("process_bac", True)),
                    "process_tax": bool(item.get("process_tax", True)),
                })
        except Exception:
            profiles = []
    if not profiles:
        raw_accounts = os.getenv("GMAIL_ACCOUNTS", "").strip()
        for chunk in [part.strip() for part in raw_accounts.split(",") if part.strip()]:
            email, _, company = chunk.partition(":")
            profiles.append({
                "account_email": email.strip().lower(),
                "company_code": (company or "MSL-CR").strip().upper(),
                "process_bac": True,
                "process_tax": True,
            })
    if not profiles:
        profiles.extend([
            {
                "account_email": ACCOUNT.strip().lower(),
                "company_code": os.getenv("GMAIL_COMPANY_CODE", "MSL-CR").strip().upper(),
                "process_bac": True,
                "process_tax": True,
            },
            {
                "account_email": "contabilidad@mslogisticsgroup.com",
                "company_code": "MSL-CR",
                "process_bac": True,
                "process_tax": True,
            },
            {
                "account_email": "operations@xtravon.com",
                "company_code": "MCI-CR",
                "process_bac": True,
                "process_tax": True,
            },
        ])
    seen = set()
    unique: list[dict[str, object]] = []
    for profile in profiles:
        email = str(profile.get("account_email") or "").strip().lower()
        if not email or email in seen:
            continue
        seen.add(email)
        unique.append({**profile, "account_email": email})
    return unique


def _account_profile(account_email: str | None = None) -> dict[str, object]:
    profiles = _configured_account_profiles()
    wanted = str(account_email or "").strip().lower()
    if wanted:
        for profile in profiles:
            if profile["account_email"] == wanted:
                return profile
        return {
            "account_email": wanted,
            "company_code": "MSL-CR",
            "process_bac": True,
            "process_tax": True,
        }
    return profiles[0]


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
                search_query TEXT NOT NULL DEFAULT '(has:attachment (filename:xml OR filename:zip OR filename:pdf) OR from:baccredomatic.com OR subject:BAC OR subject:"Notificación BAC") newer_than:730d',
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
        for profile in _configured_account_profiles():
            cur.execute("""INSERT INTO gmail_fiscal_connections(account_email) VALUES(%s)
              ON CONFLICT(account_email) DO NOTHING""", (profile["account_email"],))
            cur.execute(
                """
                UPDATE gmail_fiscal_connections
                   SET search_query=%s,
                       updated_at=NOW()
                 WHERE account_email=%s
                   AND search_query='has:attachment (filename:xml OR filename:zip) newer_than:365d'
                """,
                (DEFAULT_SEARCH_QUERY, profile["account_email"]),
            )
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


def create_oauth_url(conn, requested_by: str, account_email: str | None = None):
    ensure_schema(conn)
    if not oauth_configured():
        raise RuntimeError("Faltan GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI o CREDENTIAL_ENCRYPTION_KEY")
    profile = _account_profile(account_email)
    target_account = str(profile["account_email"])
    state = secrets.token_urlsafe(40)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gmail_fiscal_oauth_states WHERE expires_at<NOW() OR consumed_at IS NOT NULL")
        cur.execute("INSERT INTO gmail_fiscal_oauth_states(state,account_email,requested_by,expires_at) VALUES(%s,%s,%s,NOW()+INTERVAL '15 minutes')",
                    (state, target_account, requested_by))
    conn.commit()
    params = {"client_id":os.getenv("GOOGLE_CLIENT_ID"),"redirect_uri":os.getenv("GOOGLE_REDIRECT_URI"),
              "response_type":"code","scope":SCOPES,"access_type":"offline","prompt":"consent",
              "include_granted_scopes":"true","login_hint":target_account,"state":state}
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


def _norm_text(value):
    import unicodedata
    text = str(value or "").replace("\ufffc", " ").replace("\u0000", " ")
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


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


def _message_body_text(payload):
    chunks = []
    candidates = [payload, *_walk_parts(payload)]
    for part in candidates:
        mime = str(part.get("mimeType") or "").lower()
        if mime not in {"text/plain", "text/html"}:
            continue
        data = ((part.get("body") or {}).get("data") or "").strip()
        if not data:
            continue
        try:
            text = _decode_b64(data).decode("utf-8", errors="replace")
        except Exception:
            continue
        if mime == "text/html":
            text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
            text = re.sub(r"(?s)<[^>]+>", " ", text)
        chunks.append(text)
    text = "\n".join(chunks)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"[ \t\r\f\v]+", " ", text)


def _parse_bac_money(text):
    pattern = re.compile(
        r"(?:monto\s+de|por\s+un\s+monto\s+de)\s*"
        r"(?P<amount>[0-9][0-9.,]*)\s*"
        r"(?P<currency>USD|CRC|COLONES|COLON|₡|\$)?",
        re.IGNORECASE,
    )
    match = pattern.search(text or "")
    if not match:
        return None
    raw = match.group("amount").strip()
    currency = (match.group("currency") or "CRC").upper()
    if currency in {"COLONES", "COLON", "₡"}:
        currency = "CRC"
    elif currency == "$":
        currency = "USD"
    if "," in raw and "." in raw:
        raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        raw = "".join(parts[:-1]) + "." + parts[-1] if len(parts[-1]) == 2 else raw.replace(",", "")
    try:
        return Decimal(raw), currency
    except (InvalidOperation, ValueError):
        return None


def _parse_bac_date(text, fallback_date):
    months = {
        "jan": 1, "ene": 1, "feb": 2, "mar": 3, "apr": 4, "abr": 4,
        "may": 5, "jun": 6, "jul": 7, "aug": 8, "ago": 8, "sep": 9,
        "set": 9, "oct": 10, "nov": 11, "dec": 12, "dic": 12,
    }
    match = re.search(r"\b([A-Za-z]{3})\s+(\d{1,2}),\s*(\d{4})\b", text or "", re.IGNORECASE)
    if match:
        month = months.get(match.group(1).lower())
        if month:
            try:
                return datetime(int(match.group(3)), month, int(match.group(2))).date()
            except ValueError:
                pass
    match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text or "")
    if match:
        day, month, year = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        try:
            return datetime(year, month, day).date()
        except ValueError:
            pass
    return fallback_date


def _field_after_label(text, label):
    pattern = re.compile(
        rf"{label}\s*:\s*(.+?)(?=\s+(?:Ciudad y pa[ií]s|Fecha|MASTER|VISA|Autorizaci[oó]n|Referencia|Tipo de Transacci[oó]n|Monto)\s*:|$)",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text or "")
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


def _parse_bac_card_notification(text, subject, account, message_id, folder, received_date, company_code="MSL-CR"):
    normalized = _norm_text(f"{subject}\n{text}")
    if "MONTO" not in normalized:
        return None
    if "TRANSFERENCIA LOCAL" in normalized or "REALIZO UNA TRANSFERENCIA" in normalized:
        return None
    if "TIPO DE TRANSACCION" not in normalized and "NOTIFICACION DE TRANSACCION" not in normalized:
        return None
    money = _parse_bac_money(text)
    if not money:
        amount_match = re.search(r"\b(CRC|USD|COLONES|COLON|₡|\$)\s*([0-9][0-9.,]*)", text or "", re.IGNORECASE)
        if not amount_match:
            return None
        money = _parse_bac_money(f"monto de {amount_match.group(2)} {amount_match.group(1)}")
    if not money:
        return None
    amount, currency = money
    merchant = _field_after_label(text, r"Comercio") or subject
    card_match = re.search(r"\b(?:MASTER|VISA)\s*:\s*\*+(\d{4})", text or "", re.IGNORECASE)
    auth_match = re.search(r"Autorizaci[oó]n\s*:\s*([0-9A-Za-z-]+)", text or "", re.IGNORECASE)
    ref_match = re.search(r"Referencia\s*:\s*([0-9A-Za-z-]+)", text or "", re.IGNORECASE)
    holder_match = re.search(r"Hola\s+(.+?)(?:\n|A continuaci[oó]n)", text or "", re.IGNORECASE | re.DOTALL)
    if not merchant and not ref_match and not auth_match:
        return None
    return {
        "company_code": company_code,
        "mailbox": account,
        "folder": folder,
        "message_id": message_id,
        "subject": subject,
        "merchant": merchant,
        "transaction_date": _parse_bac_date(text, received_date),
        "currency": currency,
        "amount": amount,
        "card_last4": card_match.group(1) if card_match else None,
        "authorization": auth_match.group(1).strip() if auth_match else None,
        "reference": ref_match.group(1).strip() if ref_match else None,
        "holder_name": re.sub(r"\s+", " ", holder_match.group(1)).strip() if holder_match else "",
        "allow_closed_period": True,
    }


def _parse_bac_partner_transfer(text, subject, account, message_id, folder, received_date, company_code="MSL-CR"):
    normalized = _norm_text(f"{subject}\n{text}")
    if "BAC" not in normalized or "TRANSFERENCIA" not in normalized:
        return None
    partner_map = (
        ("DIANA VERONICA QUIROS BENAMBOURG", "DIANA VERONICA QUIROS BENAMBOURG"),
        ("PABEL GONZALO PENA BARRETO", "PABEL GONZALO PEÑA BARRETO"),
    )
    partner_name = None
    for needle, label in partner_map:
        if needle in normalized:
            partner_name = label
            break
    if not partner_name:
        estimated = re.search(r"Estimad[oa]\(a\)\s+(.+?)\s*:", text or "", re.IGNORECASE | re.DOTALL)
        if estimated:
            partner_name = re.sub(r"\s+", " ", estimated.group(1)).strip()
    if not partner_name:
        return None
    money = _parse_bac_money(text)
    if not money:
        return None
    amount, currency = money
    ref_match = re.search(r"(?:numero|n[uú]mero)\s+de\s+referencia\s+(?:es\s+)?([0-9A-Za-z-]+)", text, re.IGNORECASE)
    if not ref_match:
        ref_match = re.search(r"\breferencia\s+(?:es\s+)?([0-9A-Za-z-]+)", text, re.IGNORECASE)
    if not ref_match:
        return None
    concept_match = re.search(r'"([^"]+)"', text or "")
    return {
        "company_code": company_code,
        "mailbox": account,
        "folder": folder,
        "message_id": message_id,
        "subject": subject,
        "partner_name": partner_name,
        "transfer_date": _parse_bac_date(text, received_date).isoformat(),
        "amount": str(amount),
        "currency": currency,
        "reference": ref_match.group(1).strip(),
        "concept": concept_match.group(1).strip() if concept_match else "",
        "allow_closed_period": True,
    }


def _process_bac_card_notification(conn, payload):
    request = BacNotificationRequest(**payload)
    return import_bac_notification(request, conn=conn)


def _process_bac_partner_transfer(payload):
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from api_client import post_bac_partner_transfer_api
    return post_bac_partner_transfer_api(payload)


def _looks_like_card_statement(filename, subject):
    text = _norm_text(f"{filename} {subject}")
    return str(filename or "").lower().endswith(".pdf") and (
        "ESTADOCTA" in text
        or "ESTADO DE CUENTA" in text
        or "TARJETA DE CREDITO" in text
        or "BACCREDOMATIC" in text
        or " BAC " in f" {text} "
    )


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


def _process_xml(cur, message_db_id, filename, content, gmail_attachment_id, company_code="MSL-CR"):
    digest=hashlib.sha256(content).hexdigest()
    cur.execute("SELECT id,status,tax_document_id FROM gmail_fiscal_attachments WHERE message_id=%s AND content_hash=%s AND filename=%s",
                (message_db_id,digest,filename)); existing=cur.fetchone()
    if existing:
        return existing["status"],existing.get("tax_document_id")
    response=_response_data(content)
    if response:
        path=_store_path("responses",digest,filename,content)
        cur.execute("SELECT id FROM tax_electronic_documents WHERE company_code=%s AND electronic_key=%s ORDER BY id DESC LIMIT 1",(company_code,response.get("key"),)); doc=cur.fetchone()
        if not doc:
            status="REVIEW"; tax_id=None; error="Respuesta de Hacienda sin comprobante asociado"
        else:
            status_map={"1":"ACCEPTED","2":"PARTIAL","3":"REJECTED"}; hacienda=status_map.get(str(response.get("message")),str(response.get("message") or "PENDING").upper())
            cur.execute("UPDATE tax_electronic_documents SET hacienda_status=%s,hacienda_message=%s,response_xml_path=%s,response_xml_content=%s,status=%s,updated_at=NOW() WHERE id=%s",
                        (hacienda,response.get("detail"),path,content,hacienda,doc["id"])); status="IMPORTED"; tax_id=doc["id"]; error=None
    else:
        data=_parse_xml(content); key=data.get("electronic_key")
        cur.execute("SELECT id FROM tax_electronic_documents WHERE company_code=%s AND direction='PURCHASE' AND (xml_hash=%s OR (electronic_key=%s AND %s IS NOT NULL)) ORDER BY id LIMIT 1",
                    (company_code,digest,key,key)); doc=cur.fetchone()
        if doc:
            status="DUPLICATE"; tax_id=doc["id"]; error="XML ya registrado"
        else:
            path=_store_path("xml",digest,filename,content)
            tax_id=_save_document(cur,"PURCHASE",data,xml_hash=digest,xml_path=path,xml_content=content,source_table="gmail_attachment",source_id=digest,user="GMAIL_AUTOMATION",company_code=company_code)
            _ensure_purchase_obligation(cur,data,path,company_code=company_code)
            status="IMPORTED"; error=None
    cur.execute("""INSERT INTO gmail_fiscal_attachments(message_id,gmail_attachment_id,filename,mime_type,content_hash,size_bytes,status,tax_document_id,error_detail,stored_path,content)
      VALUES(%s,%s,%s,'application/xml',%s,%s,%s,%s,%s,%s,%s)""",
                (message_db_id,gmail_attachment_id,filename,digest,len(content),status,tax_id,error,path if 'path' in locals() else None,content))
    return status,tax_id


def _process_card_statement_pdf(conn, cur, message_db_id, filename, content, gmail_attachment_id, company_code="MSL-CR"):
    digest = hashlib.sha256(content).hexdigest()
    cur.execute(
        "SELECT id,status FROM gmail_fiscal_attachments WHERE message_id=%s AND content_hash=%s AND filename=%s",
        (message_db_id, digest, filename),
    )
    existing = cur.fetchone()
    if existing:
        return existing["status"], None
    try:
        response = import_statement_pdf_bytes(
            conn=conn,
            raw=content,
            filename=filename,
            company=company_code,
            imported_by="GMAIL_AUTOMATION",
        )
        if response.get("status") == "exists":
            status = "DUPLICATE"
            error = "Estado BAC ya importado"
        else:
            status = "IMPORTED"
            statement = response.get("statement") or {}
            error = f"Estado BAC {statement.get('statement_period') or ''} importado"
    except Exception as exc:
        status = "REVIEW"
        error = str(exc)
    cur.execute(
        """INSERT INTO gmail_fiscal_attachments(message_id,gmail_attachment_id,filename,mime_type,content_hash,size_bytes,status,error_detail,content)
           VALUES(%s,%s,%s,'application/pdf',%s,%s,%s,%s,%s)""",
        (message_db_id, gmail_attachment_id, filename, digest, len(content), status, error, content),
    )
    return status, error


def _labels(token):
    current=_api(token,"GET","/labels").get("labels",[]); by_name={x["name"]:x["id"] for x in current}
    result={}
    for name in ("ERP-SOM/Procesado","ERP-SOM/Revisar","ERP-SOM/Duplicado"):
        if name not in by_name:
            created=_api(token,"POST","/labels",json={"name":name,"labelListVisibility":"labelShow","messageListVisibility":"show"})
            by_name[name]=created["id"]
        result[name]=by_name[name]
    return result


def sync_mailbox(conn, triggered_by="SCHEDULER", max_messages=50, account_email: str | None = None):
    ensure_schema(conn)
    profile = _account_profile(account_email)
    target_account = str(profile["account_email"])
    target_company = str(profile.get("company_code") or "MSL-CR").upper()
    process_bac = bool(profile.get("process_bac", True))
    process_tax = bool(profile.get("process_tax", True))
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT pg_try_advisory_lock(hashtext(%s)) locked",(f"gmail-fiscal:{target_account}",)); locked=cur.fetchone()["locked"]
        if not locked: return {"status":"busy","message":"Ya existe una sincronización en curso"}
        try:
            cur.execute("SELECT * FROM gmail_fiscal_connections WHERE account_email=%s",(target_account,)); config=cur.fetchone()
            if not config or not config.get("encrypted_refresh_token"): raise RuntimeError("La cuenta Gmail todavía no ha sido autorizada")
            token=_access_token(decrypt_token(config["encrypted_refresh_token"])); labels=_labels(token)
            query=config["search_query"]+" -label:ERP-SOM/Procesado -label:ERP-SOM/Revisar -label:ERP-SOM/Duplicado"
            listed=_api(token,"GET","/messages",params={"q":query,"maxResults":min(max_messages,100)}).get("messages",[])
            summary={
                "messages":0,
                "xml":0,
                "imported":0,
                "duplicates":0,
                "review":0,
                "card_pdfs":0,
                "card_imported":0,
                "card_duplicates":0,
                "bac_card_messages":0,
                "bac_card_posted":0,
                "bac_card_matched":0,
                "bac_partner_messages":0,
                "bac_partner_imported":0,
            }
            for item in listed:
                msg=_api(token,"GET",f"/messages/{item['id']}",params={"format":"full"}); payload=msg.get("payload") or {}; hdr=_headers(payload)
                received=parsedate_to_datetime(hdr["date"]) if hdr.get("date") else None
                received_date=(received.date() if received else datetime.now(timezone.utc).date())
                subject=hdr.get("subject")
                cur.execute("""INSERT INTO gmail_fiscal_messages(account_email,gmail_message_id,gmail_thread_id,sender,subject,received_at)
                  VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT(account_email,gmail_message_id) DO UPDATE SET updated_at=NOW() RETURNING id""",
                            (target_account,item["id"],msg.get("threadId"),hdr.get("from"),subject,received)); message_db_id=cur.fetchone()["id"]
                attachments=xml_count=imported=duplicates=errors=card_pdfs=bac_card_notifications=bac_partner_notifications=0; error_details=[]
                body_text=_message_body_text(payload)
                bac_payload=_parse_bac_card_notification(
                    body_text,
                    subject or "",
                    target_account,
                    item["id"],
                    "Gmail/BAC",
                    received_date,
                    target_company,
                ) if process_bac else None
                if bac_payload:
                    try:
                        result=_process_bac_card_notification(conn,bac_payload)
                        bac_card_notifications+=1
                        status_value=str(result.get("status") or "").upper()
                        if result.get("posted") or status_value=="POSTED":
                            summary["bac_card_posted"]+=1
                        elif status_value in {"MATCHED","SEMI_REQUIRED"}:
                            summary["bac_card_matched"]+=1
                        imported+=1
                    except Exception as exc:
                        errors+=1
                        error_details.append(f"Notificacion BAC: {exc}")
                else:
                    partner_payload=_parse_bac_partner_transfer(
                        body_text,
                        subject or "",
                        target_account,
                        item["id"],
                        "Gmail/BAC",
                        received_date,
                        target_company,
                    ) if process_bac else None
                    if partner_payload:
                        try:
                            _process_bac_partner_transfer(partner_payload)
                            bac_partner_notifications+=1
                            summary["bac_partner_messages"]+=1
                            summary["bac_partner_imported"]+=1
                            imported+=1
                        except Exception as exc:
                            errors+=1
                            error_details.append(f"Transferencia BAC socios: {exc}")
                for part in _walk_parts(payload):
                    filename=part.get("filename") or ""
                    if not filename.lower().endswith((".xml",".zip",".pdf")): continue
                    attachments+=1
                    try:
                        raw=_attachment_bytes(token,item["id"],part)
                        if process_bac and _looks_like_card_statement(filename, subject or ""):
                            card_pdfs+=1
                            status, detail = _process_card_statement_pdf(
                                conn,
                                cur,
                                message_db_id,
                                filename,
                                raw,
                                (part.get("body") or {}).get("attachmentId"),
                                target_company,
                            )
                            if status == "IMPORTED":
                                imported+=1
                                summary["card_imported"]+=1
                            elif status == "DUPLICATE":
                                duplicates+=1
                                summary["card_duplicates"]+=1
                            else:
                                errors+=1
                                if detail:
                                    error_details.append(f"{filename}: {detail}")
                            continue
                        if filename.lower().endswith(".pdf") or not process_tax:
                            continue
                        members=_xml_members(filename,raw)
                        if not members:
                            errors+=1; error_details.append(f"{filename}: no contiene archivos XML")
                        for inner_name,xml in members:
                            xml_count+=1
                            try:
                                status,_=_process_xml(cur,message_db_id,inner_name,xml,(part.get("body") or {}).get("attachmentId"),target_company)
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
                summary["messages"]+=1
                summary["xml"]+=xml_count
                summary["imported"]+=imported
                summary["duplicates"]+=duplicates
                summary["review"]+=errors
                summary["card_pdfs"]+=card_pdfs
                summary["bac_card_messages"]+=bac_card_notifications
                conn.commit()
            cur.execute("""UPDATE gmail_fiscal_connections SET status='CONNECTED',last_sync_at=NOW(),next_sync_at=NOW()+(interval_minutes||' minutes')::interval,
              last_error=NULL,updated_at=NOW() WHERE account_email=%s""",(target_account,))
            cur.execute("INSERT INTO gmail_fiscal_audit(account_email,action,detail,performed_by) VALUES(%s,'SYNC',%s,%s)",(target_account,Json(summary),triggered_by)); conn.commit()
            return {"status":"ok","account_email":target_account,"company_code":target_company,**summary}
        except Exception as exc:
            conn.rollback()
            cur.execute("UPDATE gmail_fiscal_connections SET last_error=%s,updated_at=NOW() WHERE account_email=%s",(str(exc),target_account)); conn.commit()
            raise
        finally:
            cur.execute("SELECT pg_advisory_unlock(hashtext(%s))",(f"gmail-fiscal:{target_account}",)); conn.commit()


def _run_monthly_card_history_if_due(conn):
    global _CARD_HISTORY_POSTED_MONTH
    today = datetime.now().date()
    if today.day != 3:
        return
    marker = today.strftime("%Y-%m")
    if _CARD_HISTORY_POSTED_MONTH == marker:
        return
    payload = HistoryPostRequest(
        years=[today.year - 1, today.year],
        settle_previous=True,
        leave_latest_pending=True,
        latest_pending_per_card=True,
        force_closed_periods=True,
    )
    try:
        post_corporate_card_history(payload=payload, x_company_code=None, conn=conn)
        _CARD_HISTORY_POSTED_MONTH = marker
    except Exception as exc:
        print(f"Corporate card monthly scheduler: {exc}")


def _scheduler_loop():
    while True:
        time.sleep(60)
        conn=None
        try:
            conn=get_conn(); ensure_schema(conn)
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT account_email, auto_enabled, status, next_sync_at
                    FROM gmail_fiscal_connections
                    WHERE auto_enabled=TRUE
                      AND status='CONNECTED'
                      AND (next_sync_at IS NULL OR next_sync_at <= NOW())
                    ORDER BY account_email
                """)
                due = cur.fetchall() or []
            for cfg in due:
                sync_mailbox(conn, account_email=cfg["account_email"])
            _run_monthly_card_history_if_due(conn)
        except Exception as exc:
            print(f"Gmail fiscal scheduler: {exc}")
        finally:
            if conn: release_conn(conn)


def start_scheduler():
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED: return
    _SCHEDULER_STARTED=True
    threading.Thread(target=_scheduler_loop,name="gmail-fiscal-scheduler",daemon=True).start()
