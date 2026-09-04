from __future__ import annotations

import hashlib
import io
from pathlib import Path
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
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
    iban: str | None = None
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
            iban TEXT,
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
    cur.execute("ALTER TABLE masterdata_bank_accounts ADD COLUMN IF NOT EXISTS iban TEXT")
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
    iban = _clean(payload.iban)
    beneficiary_name = _clean(payload.beneficiary_name)
    if not bank_name:
        raise HTTPException(status_code=400, detail="Nombre del banco es obligatorio")
    if currency not in {"CRC", "USD", "EUR"}:
        raise HTTPException(status_code=400, detail="Moneda debe ser CRC, USD o EUR")
    if not iban:
        raise HTTPException(status_code=400, detail="Cuenta IBAN es obligatoria")
    if not beneficiary_name:
        raise HTTPException(status_code=400, detail="Nombre del beneficiario es obligatorio")
    return {
        "bank_name": bank_name,
        "currency": currency,
        "iban": iban,
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


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
ASSET_DIRS = (BACKEND_DIR / "assets", REPO_DIR / "assets")


def _asset(name: str) -> str | None:
    for directory in ASSET_DIRS:
        path = directory / name
        if path.is_file():
            return str(path)
    return None


def _is_mci(company: str, company_name: str | None) -> bool:
    return company.upper() == "MCI-CR" or "MARINE CLAIMS" in str(company_name or "").upper()


def _spanish_date(value: datetime) -> str:
    months = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    return f"{value.day:02d} de {months[value.month - 1]} de {value.year}"


def _safe_filename(value: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in {" ", "-", "_"} else "_" for ch in str(value or ""))
    return "_".join(clean.split()) or "datos_bancarios"


def _build_bank_letter_pdf(row: dict, company: str, company_name: str | None) -> bytes:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.units import inch
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    left = 0.75 * inch
    right = 0.75 * inch
    body_width = width - left - right
    header_y = height - 1.9 * inch
    top_y = header_y - 0.55 * inch
    footer_y = 0.7 * inch

    header = _asset("header.png")
    watermark = _asset("watermark.png")
    signature = _asset("FIRMA DIANA.png")

    display_company = (company_name or "").strip() or (
        "MSL MARINE CLAIMS & RISK INTELLIGENCE" if _is_mci(company, company_name)
        else "MSL MARINE SURVEYORS & LOGISTICS GROUP SRL"
    )

    def wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
        wrapped = []
        for raw_line in str(text or "").splitlines() or [""]:
            line = raw_line.strip()
            if not line:
                wrapped.append("")
                continue
            words = line.split(" ")
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if stringWidth(candidate, font_name, font_size) <= max_width:
                    current = candidate
                    continue
                if current:
                    wrapped.append(current)
                    current = word
                else:
                    wrapped.append(word)
                    current = ""
            if current:
                wrapped.append(current)
        return wrapped

    def draw_footer():
        c.setFont("Helvetica", 8)
        c.drawCentredString(
            width / 2,
            footer_y,
            "Head Office - Costa Rica, Alajuela, Plaza Aeropuerto G-14 - "
            "Phone (506) 8814-07-84 - (506) 4052-8382",
        )

    def draw_static():
        if watermark:
            c.saveState()
            c.setFillAlpha(0.08)
            c.drawImage(watermark, 1.2 * inch, 2.45 * inch, width=4.5 * inch, preserveAspectRatio=True, mask="auto")
            c.restoreState()
        if header:
            c.drawImage(header, left, header_y, width=3.6 * inch, preserveAspectRatio=True, mask="auto")
        draw_footer()

    def draw_wrapped(text: str, font_name: str, font_size: int, y: float, leading: int = 15) -> float:
        c.setFont(font_name, font_size)
        for line in wrap_text(text, font_name, font_size, body_width):
            c.drawString(left, y, line)
            y -= leading
        return y

    draw_static()
    y = top_y
    today = datetime.now(ZoneInfo("America/Costa_Rica"))

    y = draw_wrapped("Alajuela, Costa Rica", "Helvetica", 10, y)
    y = draw_wrapped(_spanish_date(today), "Helvetica", 10, y)
    y -= 24

    y = draw_wrapped("CERTIFICACION DE DATOS BANCARIOS", "Helvetica-Bold", 13, y, 18)
    y -= 12

    c.setFont("Helvetica", 10)
    body = (
        f"Por este medio, {display_company} brinda informacion fidedigna y confiable, "
        "certificando que los datos bancarios registrados para el beneficiario indicado "
        "son los siguientes:"
    )
    y = draw_wrapped(body, "Helvetica", 10, y)
    y -= 18

    details = [
        ("Beneficiario", row.get("beneficiary_name")),
        ("Banco", row.get("bank_name")),
        ("Moneda", row.get("currency")),
        ("Cuenta IBAN", row.get("iban")),
        ("Swift Code", row.get("swift_code")),
        ("UID", row.get("uid")),
        ("Direccion del banco", row.get("bank_address")),
    ]
    label_w = 1.75 * inch
    value_x = left + label_w + 0.15 * inch
    for label, value in details:
        if y < footer_y + 1.9 * inch:
            c.showPage()
            draw_static()
            y = top_y
        c.setFillColorRGB(0.96, 0.97, 0.98)
        c.rect(left, y - 4, body_width, 20, fill=1, stroke=0)
        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left + 8, y + 1, label)
        c.setFont("Helvetica", 9)
        for i, line in enumerate(wrap_text(value or "-", "Helvetica", 9, body_width - label_w - 0.3 * inch)):
            c.drawString(value_x, y + 1 - (i * 11), line)
        y -= 24

    y -= 12
    y = draw_wrapped(
        "Se extiende la presente para los fines que el interesado estime convenientes.",
        "Helvetica",
        10,
        y,
    )

    if y < footer_y + 1.65 * inch:
        c.showPage()
        draw_static()
        y = top_y

    signature_y = footer_y + 1.1 * inch
    if signature:
        c.drawImage(signature, left, signature_y + 0.35 * inch, width=1.8 * inch, height=0.6 * inch, preserveAspectRatio=True, mask="auto")
    if _is_mci(company, company_name):
        c.setFont("Helvetica", 10)
        c.drawString(left, signature_y + 10, "Msc. Diana Quiros Benambourg")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, signature_y - 4, "Business Manager")
        c.drawString(left, signature_y - 18, "MSL 2.0")
        c.drawString(left, signature_y - 32, "MARINE CLAIMS & RISK INTELLIGENCE")
    else:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, signature_y + 10, "Diana Quiros Benambourg")
        c.setFont("Helvetica", 10)
        c.drawString(left, signature_y - 4, "Business Manager")
        c.drawString(left, signature_y - 18, "MSL MARINE SURVEYORS & LOGISTICS GROUP SRL")

    c.save()
    buffer.seek(0)
    return buffer.read()


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
                   iban, uid, beneficiary_name, created_at, updated_at, created_by, updated_by
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
                company_code, bank_name, currency, iban, swift_code, bank_address, uid,
                beneficiary_name, created_by, updated_by
            )
            VALUES (%(company_code)s, %(bank_name)s, %(currency)s, %(iban)s, %(swift_code)s,
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
                iban=%(iban)s,
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


@router.get("/{bank_account_id}/letter.pdf", dependencies=[Depends(require_permission("master_data", "bank_accounts"))])
def export_bank_account_letter_pdf(
    bank_account_id: int,
    x_bank_access_token: str | None = Header(None, alias="X-Bank-Access-Token"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    x_company_name: str | None = Header(None, alias="X-Company-Name"),
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
            SELECT id, company_code, bank_name, currency, iban, swift_code,
                   bank_address, uid, beneficiary_name
            FROM masterdata_bank_accounts
            WHERE id=%s AND company_code=%s AND active=TRUE
            LIMIT 1
            """,
            (bank_account_id, company),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Dato bancario no encontrado")

    pdf_bytes = _build_bank_letter_pdf(dict(row), company, x_company_name)
    filename = f"Carta_Bancaria_{_safe_filename(row.get('beneficiary_name'))}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
