from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

from database import get_db
from routers.totp_service import validate_totp
from security.auth import get_current_user
from security.rbac import require_permission
from services.tenanting import company_code


router = APIRouter(prefix="/master-data/bank-accounts", tags=["Master Data - Bank Accounts"])


class TotpUnlockRequest(BaseModel):
    totp_code: str


class BankAccountPayload(BaseModel):
    bank_name: str
    currency: str
    swift_code: str | None = None
    bank_address: str | None = None
    uid: str | None = None
    beneficiary_name: str


def _ensure_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS masterdata_bank_access_tokens (
            token_hash TEXT PRIMARY KEY,
            usuario TEXT NOT NULL,
            company_code VARCHAR(30) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS masterdata_bank_accounts (
            id SERIAL PRIMARY KEY,
            company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
            bank_name TEXT NOT NULL,
            currency VARCHAR(10) NOT NULL,
            swift_code TEXT,
            bank_address TEXT,
            uid TEXT,
            beneficiary_name TEXT NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by TEXT,
            updated_by TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_masterdata_bank_accounts_company
        ON masterdata_bank_accounts(company_code, active, bank_name)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_masterdata_bank_tokens_expiry
        ON masterdata_bank_access_tokens(expires_at)
        """
    )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _clean(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _validate_payload(payload: BankAccountPayload) -> dict:
    bank_name = _clean(payload.bank_name)
    currency = (_clean(payload.currency) or "").upper()
    beneficiary_name = _clean(payload.beneficiary_name)
    if not bank_name:
        raise HTTPException(status_code=400, detail="Nombre del banco es obligatorio")
    if currency not in {"CRC", "USD", "EUR"}:
        raise HTTPException(status_code=400, detail="Moneda debe ser CRC, USD o EUR")
    if not beneficiary_name:
        raise HTTPException(status_code=400, detail="Nombre del beneficiario es obligatorio")
    return {
        "bank_name": bank_name,
        "currency": currency,
        "swift_code": _clean(payload.swift_code),
        "bank_address": _clean(payload.bank_address),
        "uid": _clean(payload.uid),
        "beneficiary_name": beneficiary_name,
    }


def _require_bank_token(cur, token: str | None, user: dict, company: str):
    token = str(token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Requiere revalidar Microsoft Authenticator")
    cur.execute(
        "DELETE FROM masterdata_bank_access_tokens WHERE expires_at <= NOW()"
    )
    cur.execute(
        """
        SELECT usuario
        FROM masterdata_bank_access_tokens
        WHERE token_hash=%s
          AND lower(usuario)=lower(%s)
          AND company_code=%s
          AND expires_at > NOW()
        LIMIT 1
        """,
        (_token_hash(token), user["usuario"], company),
    )
    if not cur.fetchone():
        raise HTTPException(status_code=401, detail="Revalidación vencida o inválida")


def _require_sensitive_permission(cur, user: dict):
    role = str(user.get("rol") or "").strip().lower()
    if role in {"admin", "master"}:
        return
    cur.execute(
        """
        SELECT 1
        FROM user_module_permissions
        WHERE lower(usuario)=lower(%s)
          AND lower(module_code)='master_data'
          AND lower(action_code) IN ('bank_accounts', 'admin')
          AND allowed=TRUE
        LIMIT 1
        """,
        (user["usuario"],),
    )
    if not cur.fetchone():
        raise HTTPException(status_code=403, detail="No autorizado para datos bancarios sensibles")


@router.post("/unlock", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
def unlock_bank_accounts(
    payload: TotpUnlockRequest,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    code = str(payload.totp_code or "").strip().replace(" ", "")
    if not code:
        raise HTTPException(status_code=400, detail="Código Authenticator requerido")
    if not validate_totp(user["usuario"], code):
        raise HTTPException(status_code=401, detail="Código Authenticator inválido")

    company = company_code(header_value=x_company_code)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_schema(cur)
        _require_sensitive_permission(cur, user)
        cur.execute("DELETE FROM masterdata_bank_access_tokens WHERE expires_at <= NOW()")
        cur.execute(
            """
            INSERT INTO masterdata_bank_access_tokens (token_hash, usuario, company_code, expires_at)
            VALUES (%s, %s, %s, %s)
            """,
            (_token_hash(token), user["usuario"], company, expires_at),
        )
        conn.commit()
    return {"access_token": token, "expires_at": expires_at.isoformat(timespec="seconds") + "Z"}


@router.get("", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
@router.get("/", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
def list_bank_accounts(
    x_bank_access_token: str | None = Header(None, alias="X-Bank-Access-Token"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    company = company_code(header_value=x_company_code)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_schema(cur)
        _require_sensitive_permission(cur, user)
        _require_bank_token(cur, x_bank_access_token, user, company)
        cur.execute(
            """
            SELECT id, company_code, bank_name, currency, swift_code, bank_address,
                   uid, beneficiary_name, created_at, updated_at, created_by, updated_by
            FROM masterdata_bank_accounts
            WHERE company_code=%s AND active=TRUE
            ORDER BY bank_name, currency, beneficiary_name
            """,
            (company,),
        )
        return {"data": [dict(row) for row in cur.fetchall()]}


@router.post("", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
@router.post("/", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
def create_bank_account(
    payload: BankAccountPayload,
    x_bank_access_token: str | None = Header(None, alias="X-Bank-Access-Token"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    company = company_code(header_value=x_company_code)
    data = _validate_payload(payload)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_schema(cur)
        _require_sensitive_permission(cur, user)
        _require_bank_token(cur, x_bank_access_token, user, company)
        cur.execute(
            """
            INSERT INTO masterdata_bank_accounts (
                company_code, bank_name, currency, swift_code, bank_address, uid,
                beneficiary_name, created_by, updated_by
            )
            VALUES (%(company_code)s, %(bank_name)s, %(currency)s, %(swift_code)s,
                    %(bank_address)s, %(uid)s, %(beneficiary_name)s, %(usuario)s, %(usuario)s)
            RETURNING *
            """,
            {**data, "company_code": company, "usuario": user["usuario"]},
        )
        row = dict(cur.fetchone())
        conn.commit()
    return row


@router.put("/{bank_account_id}", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
def update_bank_account(
    bank_account_id: int,
    payload: BankAccountPayload,
    x_bank_access_token: str | None = Header(None, alias="X-Bank-Access-Token"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    company = company_code(header_value=x_company_code)
    data = _validate_payload(payload)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_schema(cur)
        _require_sensitive_permission(cur, user)
        _require_bank_token(cur, x_bank_access_token, user, company)
        cur.execute(
            """
            UPDATE masterdata_bank_accounts
            SET bank_name=%(bank_name)s,
                currency=%(currency)s,
                swift_code=%(swift_code)s,
                bank_address=%(bank_address)s,
                uid=%(uid)s,
                beneficiary_name=%(beneficiary_name)s,
                updated_by=%(usuario)s,
                updated_at=NOW()
            WHERE id=%(id)s AND company_code=%(company_code)s AND active=TRUE
            RETURNING *
            """,
            {**data, "id": bank_account_id, "company_code": company, "usuario": user["usuario"]},
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dato bancario no encontrado")
        conn.commit()
    return dict(row)


@router.delete("/{bank_account_id}", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
def delete_bank_account(
    bank_account_id: int,
    x_bank_access_token: str | None = Header(None, alias="X-Bank-Access-Token"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    company = company_code(header_value=x_company_code)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_schema(cur)
        _require_sensitive_permission(cur, user)
        _require_bank_token(cur, x_bank_access_token, user, company)
        cur.execute(
            """
            UPDATE masterdata_bank_accounts
            SET active=FALSE, updated_by=%s, updated_at=NOW()
            WHERE id=%s AND company_code=%s AND active=TRUE
            RETURNING id
            """,
            (user["usuario"], bank_account_id, company),
        )
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Dato bancario no encontrado")
        conn.commit()
    return {"status": "deleted", "id": bank_account_id}
