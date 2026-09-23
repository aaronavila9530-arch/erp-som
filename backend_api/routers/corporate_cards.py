from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
from io import BytesIO
import calendar
import re
import unicodedata
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File
from psycopg2.extras import Json, RealDictCursor
from pydantic import BaseModel

from database import get_db
from services.tenanting import company_code


router = APIRouter(prefix="/accounting/corporate-cards", tags=["Accounting - Corporate Cards"])

MONEY = Decimal("0.01")
CARD_PAYABLE_CODE = "2.1.02.10"
CARD_PAYABLE_NAME = "Tarjeta corporativa BAC por pagar"
DEFAULT_EXPENSE_CODE = "5.4"
DEFAULT_EXPENSE_NAME = "Otros gastos"
DEFAULT_NON_DEDUCTIBLE_CODE = "5.4.99"
DEFAULT_NON_DEDUCTIBLE_NAME = "Gastos no deducibles"
PENDING_CARD_CODE = "1.1.99.10"
PENDING_CARD_NAME = "Cargos tarjeta pendientes de clasificar"
SUPPLIER_AP_CODE = "2.1.01.01"
SUPPLIER_AP_NAME = "Cuentas por pagar-comerciales"
SUPERMARKET_EXPENSE_CODE = "500-001-001-062"
SUPERMARKET_EXPENSE_NAME = "Gastos por supermercado"
BASIC_SERVICES_EXPENSE_CODE = "500-001-001-063"
BASIC_SERVICES_EXPENSE_NAME = "Servicios básicos"
RENT_EXPENSE_CODE = "5.1.05"
RENT_EXPENSE_NAME = "Gastos por alquiler"
CARD_EXPENSE_ACCOUNTS = [
    ("550-001-000-050", "Alimentación"),
    (SUPERMARKET_EXPENSE_CODE, SUPERMARKET_EXPENSE_NAME),
    ("500-001-001-050", "Transporte"),
    ("500-001-001-042", "Combustible"),
    ("500-001-001-023", "Teléfonos"),
    ("500-001-001-043", "Hospedaje"),
    ("500-001-001-044", "Viáticos"),
    (RENT_EXPENSE_CODE, RENT_EXPENSE_NAME),
    (BASIC_SERVICES_EXPENSE_CODE, BASIC_SERVICES_EXPENSE_NAME),
    ("500-001-001-054", "Pasajes de avión"),
    ("500-001-001-036", "Papeleria y Utiles de Oficina"),
    ("500-001-001-038", "Mant. y Reparación Vehículos"),
    ("550-001-000-059", "Gastos Médicos"),
    ("500-001-001-006", "Servicios Profesionales"),
]

CARD_MERCHANT_EXPENSE_RULES = [
    {
        "category": "Supermercado",
        "account_code": SUPERMARKET_EXPENSE_CODE,
        "account_name": SUPERMARKET_EXPENSE_NAME,
        "needles": [
            "AMPM", "AM PM", "PRISMAR", "AUTOMERCADO", "AUTO MERCADO",
            "CORPORACION DE SUPERMERCADOS UNIDOS", "SUPERMERCADOS UNIDOS",
            "MAS X MENOS", "MASXMENOS", "PALI", "VINDI", "WALMART",
        ],
    },
    {
        "category": "Alimentacion",
        "account_code": "550-001-000-050",
        "account_name": "Alimentación",
        "needles": [
            "NINA CAFE", "ROSTIPOLLOS", "LA CASONA DEL MAIZ", "CAFE KIVU",
            "SODA SAZON COLOMBIANO", "GRUPO NIMAX", "SERVICIOS DE PASTELERIA",
            "INVERSIONES GRANDES AMIGOS", "FENT COSTA RICA",
            "RESTAURANTE TIPICO DE FRAIJANES", "RESTAURANTE", "SODA ", "CAFE ",
            "CAFETERIA", "PASTELERIA", "PIZZA", "POLLO", "COMIDA",
        ],
    },
    {
        "category": "Combustible",
        "account_code": "500-001-001-042",
        "account_name": "Combustible",
        "needles": [
            "GRUPO POJI", "ESTACION DE SERVICIO SAN GERARDO",
            "ESTACION DE SERVICIO EUSSE", "BARRANCA", "ESTACION DE SERVICIO ZURQUI",
            "MI GAS RADIAL COYOL", "PETROLEOS DELTA", "PETRÓLEOS DELTA",
            "GASOLINERA", "ESTACION DE SERVICIO", "SERVICENTRO", "COMBUSTIBLE",
        ],
    },
    {
        "category": "Alquiler",
        "account_code": RENT_EXPENSE_CODE,
        "account_name": RENT_EXPENSE_NAME,
        "needles": ["PRIME PROPERTIES", "PRIME PROPERTY"],
    },
    {
        "category": "Servicios basicos",
        "account_code": BASIC_SERVICES_EXPENSE_CODE,
        "account_name": BASIC_SERVICES_EXPENSE_NAME,
        "needles": ["AMERICAN DATA", "AMERICAN DATA NETWORK", "DATA NETWORK"],
    },
]


class ClassifyRequest(BaseModel):
    fiscal_category: str | None = None
    deductible_status: str | None = None
    requires_invoice: bool | None = None
    expense_account_code: str | None = None
    expense_account_name: str | None = None
    notes: str | None = None
    force_closed_period: bool = False


class BulkClassifyItem(BaseModel):
    transaction_id: int
    fiscal_category: str | None = None
    deductible_status: str | None = None
    requires_invoice: bool | None = None
    expense_account_code: str | None = None
    expense_account_name: str | None = None
    notes: str | None = None


class BulkClassifyRequest(BaseModel):
    items: list[BulkClassifyItem] = []
    force_closed_periods: bool = False


class MatchRequest(BaseModel):
    obligation_id: int


class BacNotificationRequest(BaseModel):
    company_code: str | None = None
    mailbox: str | None = None
    folder: str | None = None
    message_id: str | None = None
    subject: str | None = None
    merchant: str | None = None
    transaction_date: date
    currency: str
    amount: float
    card_last4: str | None = None
    authorization: str | None = None
    reference: str | None = None
    holder_name: str | None = None
    allow_closed_period: bool = False


class SettlementRequest(BaseModel):
    payment_date: date | None = None
    bank_account_code: str
    bank_account_name: str | None = None
    amount_crc: float | None = None
    amount_usd: float | None = None
    exchange_rate: float | None = None


class HistoryPostRequest(BaseModel):
    years: list[int] = [2025, 2026]
    settle_previous: bool = True
    leave_latest_pending: bool = True
    latest_pending_per_card: bool = True
    bank_account_code: str | None = None
    bank_account_name: str | None = None
    force_closed_periods: bool = False


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(400, "Monto invalido")


def _to_float(value: Any) -> float:
    return float(_money(value))


def _parse_money(text: str | None) -> Decimal:
    raw = str(text or "").strip().replace(",", "")
    if raw.endswith("-"):
        raw = "-" + raw[:-1]
    return _money(raw)


def _merchant_norm(value: Any) -> str:
    text = str(value or "")
    text = text.replace("\ufffc", " ").replace("\u0000", " ")
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def classify_card_merchant(*values: Any) -> dict[str, str] | None:
    haystack = _merchant_norm(" ".join(str(value or "") for value in values))
    if not haystack:
        return None
    padded = f" {haystack} "
    for rule in CARD_MERCHANT_EXPENSE_RULES:
        for needle in rule["needles"]:
            normalized_needle = _merchant_norm(needle)
            if normalized_needle and normalized_needle in padded:
                return {
                    "fiscal_category": rule["category"],
                    "deductible_status": "DEDUCTIBLE",
                    "requires_invoice": False,
                    "expense_account_code": rule["account_code"],
                    "expense_account_name": rule["account_name"],
                }
    return None


def apply_card_merchant_classification(tx: dict[str, Any]) -> dict[str, Any]:
    classified = classify_card_merchant(tx.get("merchant"), tx.get("description"), tx.get("notes"))
    if not classified:
        return tx
    tx = dict(tx)
    tx["fiscal_category"] = tx.get("fiscal_category") or classified["fiscal_category"]
    tx["deductible_status"] = classified["deductible_status"]
    tx["requires_invoice"] = False
    tx["expense_account_code"] = classified["expense_account_code"]
    tx["expense_account_name"] = classified["expense_account_name"]
    return tx


def _parse_date(text: str | None) -> date | None:
    if not text:
        return None
    months = {
        "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
        "JAN": 1, "APR": 4, "AUG": 8, "DEC": 12,
    }
    match = re.match(r"^\s*(\d{1,2})-([A-Z]{3})-(\d{2,4})\s*$", text.strip().upper())
    if not match:
        return None
    day = int(match.group(1))
    month = months.get(match.group(2))
    year = int(match.group(3))
    if year < 100:
        year += 2000
    if not month:
        return None
    return date(year, month, day)


def _due_on_15th(cutoff: date | None, period: str | None) -> date | None:
    if cutoff:
        year, month = cutoff.year, cutoff.month
    elif period and re.match(r"^\d{4}-\d{2}$", period):
        year, month = (int(part) for part in period.split("-"))
    else:
        return None
    month += 1
    if month == 13:
        year += 1
        month = 1
    return date(year, month, 15)


def _period_from_date(value: date | None) -> str | None:
    return value.strftime("%Y-%m") if value else None


def _period_is_closed(cur, company: str, period: str | None) -> bool:
    if not period:
        return False
    cur.execute("""
        SELECT status FROM accounting_period_controls
        WHERE company_code=%s AND period=%s
    """, (company, period))
    row = cur.fetchone()
    return bool(row and row.get("status") == "CLOSED")


def _closed_purchase_periods_for_statement(cur, statement_id: int, company: str) -> list[str]:
    cur.execute("""
        SELECT DISTINCT TO_CHAR(transaction_date, 'YYYY-MM') AS period
        FROM corporate_card_transactions
        WHERE statement_id=%s
          AND company_code=%s
          AND transaction_type='PURCHASE'
          AND transaction_date IS NOT NULL
        ORDER BY period
    """, (statement_id, company))
    return [
        row["period"]
        for row in (cur.fetchall() or [])
        if _period_is_closed(cur, company, row.get("period"))
    ]


def _read_pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise HTTPException(500, f"No se pudo cargar pypdf para leer el PDF: {exc}") from exc
    reader = PdfReader(BytesIO(raw))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_bac_statement(raw: bytes) -> dict[str, Any]:
    text = _read_pdf_text(raw)
    if "BAC" not in text.upper():
        raise HTTPException(400, "El PDF no parece ser un estado BAC")
    cutoff = None
    cutoff_match = re.search(r"Fecha\s+(?:de\s+)?corte:?\s+(\d{2}-[A-Z]{3}-\d{2})", text, re.I)
    if cutoff_match:
        cutoff = _parse_date(cutoff_match.group(1))
    if not cutoff:
        month_match = re.search(r"(?:Estado|estado)\s+de\s+cuenta:?\s+([A-Z]{3})-(\d{4})", text, re.I)
        if month_match:
            months = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7, "AGO": 8, "SET": 9, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12}
            month = months.get(month_match.group(1).upper())
            if month:
                year = int(month_match.group(2))
                cutoff = date(year, month, calendar.monthrange(year, month)[1])
    statement_period = _period_from_date(cutoff)

    main_card = None
    main_card_match = re.search(r"\*{8,}(\d{4})", text)
    if main_card_match:
        main_card = main_card_match.group(1)

    cash_crc = Decimal("0.00")
    cash_usd = Decimal("0.00")
    cash_match = re.search(r"Pago\s+de\s+Contado\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})", text, re.I)
    if cash_match:
        cash_crc = _parse_money(cash_match.group(1))
        cash_usd = _parse_money(cash_match.group(2))

    current_holder = None
    current_last4 = main_card
    transactions: list[dict[str, Any]] = []
    movement_re = re.compile(r"^(\d{10,14})\s+(\d{2}-[A-Z]{3}-\d{2})\s+(.+?)\s+(CRC|USD)\s+([\d,]+\.\d{2}-?)$", re.I)
    holder_re = re.compile(r"\*{8,}(\d{4})\s+([A-Z][A-Z\s/]+)$")
    for raw_line in text.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        holder_match = holder_re.search(line)
        if holder_match and not re.search(r"\d{2}-[A-Z]{3}-\d{2}", line, re.I):
            current_last4 = holder_match.group(1)
            current_holder = holder_match.group(2).strip(" /")
            continue
        movement_match = movement_re.match(line)
        if not movement_match:
            continue
        ref, tx_date_raw, description, currency, amount_raw = movement_match.groups()
        amount = _parse_money(amount_raw)
        tx_type = "PAYMENT" if amount < 0 or "PAGO RECIBIDO" in description.upper() else "PURCHASE"
        transactions.append({
            "reference": ref,
            "transaction_date": _parse_date(tx_date_raw),
            "description": description.strip(),
            "merchant": description.strip(),
            "currency": currency.upper(),
            "amount_original": abs(amount),
            "amount_crc": abs(amount) if currency.upper() == "CRC" else Decimal("0.00"),
            "transaction_type": tx_type,
            "card_last4": current_last4,
            "user_name": current_holder,
        })

    financing_match = re.search(
        r"Origen del credito \(establecimiento\)\s+(.+?)\s+.*?Monto de credito\s+([\d,]+\.\d{2})\s+Moneda\s+(CRC|USD)",
        text,
        re.I | re.S,
    )
    if financing_match:
        transactions.append({
            "reference": "FINANCING",
            "transaction_date": cutoff,
            "description": financing_match.group(1).strip(),
            "merchant": financing_match.group(1).strip(),
            "currency": financing_match.group(3).upper(),
            "amount_original": _parse_money(financing_match.group(2)),
            "amount_crc": _parse_money(financing_match.group(2)) if financing_match.group(3).upper() == "CRC" else Decimal("0.00"),
            "transaction_type": "FINANCING",
            "card_last4": current_last4,
            "user_name": current_holder,
        })

    return {
        "raw_text": text,
        "statement_period": statement_period,
        "cutoff_date": cutoff,
        "payment_due_date": _due_on_15th(cutoff, statement_period),
        "card_last4": main_card or current_last4,
        "cash_payment_crc": cash_crc,
        "cash_payment_usd": cash_usd,
        "transactions": transactions,
    }


def ensure_schema(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corporate_cards (
            id BIGSERIAL PRIMARY KEY,
            company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
            bank_name TEXT NOT NULL DEFAULT 'BAC',
            card_last4 VARCHAR(8) NOT NULL,
            holder_name TEXT NOT NULL,
            user_key TEXT,
            payable_account_code VARCHAR(50) NOT NULL DEFAULT '2.1.02.10',
            payable_account_name TEXT NOT NULL DEFAULT 'Tarjeta corporativa BAC por pagar',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(company_code, bank_name, card_last4, holder_name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corporate_card_statements (
            id BIGSERIAL PRIMARY KEY,
            company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
            bank_name TEXT NOT NULL DEFAULT 'BAC',
            card_last4 VARCHAR(8),
            statement_period VARCHAR(7),
            cutoff_date DATE,
            payment_due_date DATE,
            cash_payment_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            cash_payment_usd NUMERIC(18,2) NOT NULL DEFAULT 0,
            source_filename TEXT,
            file_hash TEXT NOT NULL UNIQUE,
            raw_text TEXT,
            parsed_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status VARCHAR(30) NOT NULL DEFAULT 'IMPORTED',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            imported_by TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corporate_card_transactions (
            id BIGSERIAL PRIMARY KEY,
            statement_id BIGINT REFERENCES corporate_card_statements(id) ON DELETE CASCADE,
            company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
            card_last4 VARCHAR(8),
            user_name TEXT,
            transaction_type VARCHAR(30) NOT NULL DEFAULT 'PURCHASE',
            reference TEXT,
            transaction_date DATE,
            description TEXT,
            merchant TEXT,
            currency VARCHAR(3) NOT NULL DEFAULT 'CRC',
            amount_original NUMERIC(18,2) NOT NULL DEFAULT 0,
            amount_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            fiscal_category TEXT,
            deductible_status VARCHAR(30) NOT NULL DEFAULT 'PENDING_REVIEW',
            requires_invoice BOOLEAN NOT NULL DEFAULT TRUE,
            expense_account_code VARCHAR(50),
            expense_account_name TEXT,
            matched_obligation_id BIGINT,
            match_status VARCHAR(30) NOT NULL DEFAULT 'UNMATCHED',
            accounting_entry_id BIGINT,
            notes TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(statement_id, reference, transaction_date, amount_original, currency)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corporate_card_settlements (
            id BIGSERIAL PRIMARY KEY,
            statement_id BIGINT REFERENCES corporate_card_statements(id) ON DELETE CASCADE,
            company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
            payment_date DATE NOT NULL,
            bank_account_code TEXT NOT NULL,
            bank_account_name TEXT,
            amount_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            amount_usd NUMERIC(18,2) NOT NULL DEFAULT 0,
            exchange_rate NUMERIC(18,6),
            accounting_entry_id BIGINT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_by TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS corporate_card_bac_notifications (
            id BIGSERIAL PRIMARY KEY,
            company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
            mailbox TEXT,
            folder TEXT,
            message_id TEXT,
            subject TEXT,
            merchant TEXT,
            transaction_date DATE NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'CRC',
            amount NUMERIC(18,2) NOT NULL DEFAULT 0,
            card_last4 VARCHAR(8),
            authorization_code TEXT,
            reference TEXT,
            holder_name TEXT,
            matched_transaction_id BIGINT,
            matched_obligation_id BIGINT,
            status VARCHAR(30) NOT NULL DEFAULT 'IMPORTED',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_corp_card_bac_notification_identity
        ON corporate_card_bac_notifications(
            company_code,
            COALESCE(reference,''),
            COALESCE(authorization_code,''),
            COALESCE(card_last4,''),
            transaction_date,
            currency,
            amount
        )
    """)
    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_corp_card_settlement_statement
        ON corporate_card_settlements(statement_id)
    """)
    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS paid_with_card BOOLEAN NOT NULL DEFAULT FALSE")
    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS card_transaction_id BIGINT")
    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS card_paid_at DATE")
    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS card_holder_name TEXT")
    cur.execute("""
        INSERT INTO accounting_accounts(account_code, account_name, account_type, normal_balance, account_level, parent_account, accepts_posting, active)
        VALUES
          (%s, %s, 'PASIVO', 'CREDIT', 3, '2.1.02', TRUE, TRUE),
          (%s, %s, 'GASTO', 'DEBIT', 3, '5.4', TRUE, TRUE),
          (%s, %s, 'ACTIVO', 'DEBIT', 3, '1.1.99', TRUE, TRUE)
        ON CONFLICT (account_code) DO UPDATE SET account_name=EXCLUDED.account_name, accepts_posting=TRUE, active=TRUE
    """, (
        CARD_PAYABLE_CODE,
        CARD_PAYABLE_NAME,
        DEFAULT_NON_DEDUCTIBLE_CODE,
        DEFAULT_NON_DEDUCTIBLE_NAME,
        PENDING_CARD_CODE,
        PENDING_CARD_NAME,
    ))
    for code, name in CARD_EXPENSE_ACCOUNTS:
        cur.execute("""
            INSERT INTO accounting_accounts(account_code, account_name, account_type, normal_balance, account_level, parent_account, accepts_posting, active)
            VALUES(%s, %s, 'GASTO', 'DEBIT', 3, '5', TRUE, TRUE)
            ON CONFLICT (account_code) DO UPDATE
            SET account_name=EXCLUDED.account_name, accepts_posting=TRUE, active=TRUE
        """, (code, name))
    for holder, last4, user_key in (
        ("AARON", "3155", "aaron01"),
        ("DIANA", "3156", "diana"),
        ("PABEL", "3157", "pabel"),
        ("ITP", "3148", "itp"),
    ):
        cur.execute("""
            INSERT INTO corporate_cards(company_code, bank_name, card_last4, holder_name, user_key)
            VALUES('MSL-CR','BAC',%s,%s,%s)
            ON CONFLICT(company_code, bank_name, card_last4, holder_name) DO NOTHING
        """, (last4, holder, user_key))
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corp_card_tx_statement ON corporate_card_transactions(statement_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corp_card_tx_company_date ON corporate_card_transactions(company_code, transaction_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_corp_card_bac_company_date ON corporate_card_bac_notifications(company_code, transaction_date)")
    # Schema bootstrap mixes DDL plus seed rows and is called from read and write
    # paths. Commit it immediately so long-running card posting does not deadlock
    # against idle setup transactions holding relation locks.
    cur.connection.commit()


def _statement_row(row):
    if not row:
        return None
    return {key: row[key] for key in row.keys()}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def _norm_text(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()


def _overlap_score(left: str, right: str) -> int:
    left_tokens = {token for token in _norm_text(left).split() if len(token) >= 3}
    right_tokens = {token for token in _norm_text(right).split() if len(token) >= 3}
    if not left_tokens or not right_tokens:
        return 0
    overlap = left_tokens & right_tokens
    if not overlap:
        return 0
    return min(25, len(overlap) * 8)


def _date_delta_days(left: Any, right: Any) -> int | None:
    if not left or not right:
        return None
    try:
        return abs((left - right).days)
    except Exception:
        return None


def _score_candidate(
    *,
    tx: dict[str, Any],
    name: str | None,
    currency: str | None,
    total: Any,
    issue_date: Any,
    status: str | None,
    paid_with_card: bool = False,
    reference: str | None = None,
) -> tuple[int, Decimal]:
    amount = _money(tx.get("amount_original"))
    candidate_total = _money(total)
    amount_delta = abs(candidate_total - amount)
    desc = f"{tx.get('description') or ''} {tx.get('merchant') or ''}"
    score = 0
    if (currency or "").upper() == (tx.get("currency") or "").upper():
        score += 20
    if amount_delta <= Decimal("2.00"):
        score += 45
    elif amount_delta <= Decimal("500.00"):
        score += 15
    days = _date_delta_days(issue_date, tx.get("transaction_date"))
    if days is not None:
        if days <= 3:
            score += 20
        elif days <= 20:
            score += 12
        elif days <= 45:
            score += 5
    score += _overlap_score(desc, name or "")
    if reference and str(reference).strip() and str(tx.get("reference") or "").strip() == str(reference).strip():
        score += 25
    if (status or "").upper() in {"PENDING", "PARTIAL", "PENDIENTE"}:
        score += 10
    if paid_with_card:
        score -= 100
    return score, amount_delta


def _tax_documents_available(cur) -> bool:
    cur.execute("SELECT to_regclass('public.tax_electronic_documents') AS table_name")
    row = cur.fetchone()
    return bool(row and row.get("table_name"))


def _ensure_obligation_from_tax_doc(cur, company: str, tax_doc_id: int) -> int:
    cur.execute("""
        SELECT * FROM tax_electronic_documents
        WHERE id=%s AND company_code=%s AND direction='PURCHASE'
    """, (tax_doc_id, company))
    doc = cur.fetchone()
    if not doc:
        raise HTTPException(404, "Factura electronica no existe")
    reference = doc.get("electronic_key") or doc.get("document_number") or f"TAXDOC-{tax_doc_id}"
    cur.execute("""
        SELECT id FROM payment_obligations
        WHERE company_code=%s AND active=TRUE AND reference=%s
        ORDER BY id DESC
        LIMIT 1
    """, (company, reference))
    existing = cur.fetchone()
    if existing:
        return int(existing["id"])
    issue_date = doc.get("issue_datetime")
    if isinstance(issue_date, datetime):
        issue_date = issue_date.date()
    obligation_type = "SUPPLIER_CREDIT_NOTE" if "CREDIT" in str(doc.get("document_type") or "").upper() else "SUPPLIER_INVOICE"
    cur.execute("""
        INSERT INTO payment_obligations(
            company_code, record_type, payee_type, payee_name, obligation_type,
            reference, issue_date, due_date, currency, total, balance, status,
            origin, notes, active, created_at, updated_at
        ) VALUES(
            %s, 'PAYABLE', 'SUPPLIER', %s, %s,
            %s, %s, COALESCE(%s, CURRENT_DATE), %s, %s, %s, 'PENDING',
            'HACIENDA_XML', %s, TRUE, NOW(), NOW()
        )
        RETURNING id
    """, (
        company,
        doc.get("issuer_name") or "Proveedor factura electronica",
        obligation_type,
        reference,
        issue_date,
        issue_date,
        doc.get("currency_code") or "CRC",
        _money(doc.get("total")),
        _money(doc.get("total")),
        f"Creada automaticamente desde factura electronica para pago con tarjeta BAC. Documento {doc.get('document_number') or reference}",
    ))
    row = cur.fetchone()
    return int(row["id"])


def _post_entry(
    cur,
    company: str,
    entry_date: date,
    description: str,
    origin: str,
    origin_id: int,
    lines: list[dict[str, Any]],
    force_closed_period: bool = False,
) -> int:
    period = entry_date.strftime("%Y-%m")
    if _period_is_closed(cur, company, period) and not force_closed_period:
        raise HTTPException(409, f"El periodo {period} esta cerrado")
    total_debit = sum(_money(line.get("debit")) for line in lines)
    total_credit = sum(_money(line.get("credit")) for line in lines)
    if total_debit != total_credit or total_debit <= 0:
        raise HTTPException(400, "El asiento de tarjeta no balancea")
    cur.execute("""
        SELECT id FROM accounting_entries
        WHERE origin=%s AND origin_id=%s AND company_code=%s
        LIMIT 1
    """, (origin, origin_id, company))
    existing = cur.fetchone()
    if existing:
        entry_id = existing["id"]
        cur.execute("""
            UPDATE accounting_entries
            SET entry_date=%s, period=%s, description=%s, workflow_status='POSTED', updated_at=NOW()
            WHERE id=%s
        """, (entry_date, period, description, entry_id))
        cur.execute("DELETE FROM accounting_lines WHERE entry_id=%s", (entry_id,))
    else:
        metadata = {"source": "corporate_cards"}
        if force_closed_period:
            metadata["force_closed_period"] = True
            metadata["force_reason"] = "Carga historica de tarjetas corporativas solicitada para cuadrar contabilidad"
        cur.execute("""
            INSERT INTO accounting_entries(entry_date, period, description, origin, origin_id, created_by, workflow_status, company_code, posting_rule_code, posting_metadata, posted_by, posted_at)
            VALUES(%s,%s,%s,%s,%s,'SYSTEM','POSTED',%s,%s,%s,'SYSTEM',NOW())
            RETURNING id
        """, (entry_date, period, description, origin, origin_id, company, origin, Json(metadata)))
        entry_id = cur.fetchone()["id"]
    for line in lines:
        cur.execute("""
            INSERT INTO accounting_lines(entry_id, account_code, account_name, debit, credit, line_description)
            VALUES(%s,%s,%s,%s,%s,%s)
        """, (
            entry_id,
            line["account_code"],
            line["account_name"],
            _money(line.get("debit")),
            _money(line.get("credit")),
            line.get("description") or description,
        ))
    return entry_id


def _exchange_rate_for(cur, tx_date: date | None) -> Decimal:
    cur.execute("""
        SELECT rate
        FROM exchange_rate
        WHERE rate_date <= COALESCE(%s::date, CURRENT_DATE)
        ORDER BY rate_date DESC
        LIMIT 1
    """, (tx_date,))
    row = cur.fetchone()
    if not row:
        return Decimal("1.00")
    return Decimal(str(row.get("rate") or 1))


def _amount_crc_for_transaction(cur, tx: dict[str, Any]) -> Decimal:
    tx_date = tx.get("transaction_date")
    amount_crc = _money(tx.get("amount_crc"))
    if amount_crc <= 0 and (tx.get("currency") or "CRC").upper() == "USD":
        amount_crc = (_money(tx.get("amount_original")) * _exchange_rate_for(cur, tx_date)).quantize(MONEY, rounding=ROUND_HALF_UP)
    elif amount_crc <= 0:
        amount_crc = _money(tx.get("amount_original"))
    return amount_crc


def _settlement_amounts(cur, statement: dict[str, Any], pay_date: date, override_crc=None, override_usd=None, override_rate=None):
    amount_crc = _money(override_crc if override_crc is not None else statement.get("cash_payment_crc"))
    amount_usd = _money(override_usd if override_usd is not None else statement.get("cash_payment_usd"))
    exchange_rate = Decimal(str(override_rate)) if override_rate else _exchange_rate_for(cur, pay_date)
    usd_crc = (amount_usd * exchange_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
    total_crc = amount_crc + usd_crc
    return amount_crc, amount_usd, exchange_rate, usd_crc, total_crc


def _settlement_description(statement: dict[str, Any], amount_crc: Decimal, amount_usd: Decimal, exchange_rate: Decimal, usd_crc: Decimal, total_crc: Decimal) -> str:
    period = statement.get("statement_period") or ""
    card = statement.get("card_last4") or ""
    return (
        f"Pago tarjeta corporativa BAC {period}"
        f"{' tarjeta ' + str(card) if card else ''}: "
        f"contado CRC {amount_crc:,.2f}; "
        f"contado USD {amount_usd:,.2f} x TC BCCR {exchange_rate:,.6f} = CRC {usd_crc:,.2f}; "
        f"total CRC {total_crc:,.2f}"
    )


def _settlement_lines(bank_code: str, bank_name: str, description: str, amount_crc: Decimal, amount_usd: Decimal, usd_crc: Decimal, total_crc: Decimal) -> list[dict[str, Any]]:
    lines = [
        {
            "account_code": CARD_PAYABLE_CODE,
            "account_name": CARD_PAYABLE_NAME,
            "debit": total_crc,
            "credit": 0,
            "description": description,
        }
    ]
    if amount_crc > 0:
        lines.append({
            "account_code": bank_code,
            "account_name": bank_name,
            "debit": 0,
            "credit": amount_crc,
            "description": f"{description} | Rebajo banco por contado CRC",
        })
    if amount_usd > 0:
        lines.append({
            "account_code": bank_code,
            "account_name": bank_name,
            "debit": 0,
            "credit": usd_crc,
            "description": f"{description} | Rebajo banco por contado USD {amount_usd:,.2f} convertido a CRC",
        })
    return lines


def _post_card_transaction(cur, tx: dict[str, Any], force_closed_period: bool = False) -> int | None:
    tx = apply_card_merchant_classification(tx)
    tx_date = tx.get("transaction_date")
    if not tx_date:
        return None
    amount_crc = _amount_crc_for_transaction(cur, tx)
    if amount_crc <= 0:
        return None
    description = f"Tarjeta corporativa BAC {tx.get('user_name') or ''}: {tx.get('description') or ''}".strip()
    origins_to_remove = ["CORP_CARD_PENDING"]
    if tx.get("matched_obligation_id"):
        origins_to_remove.append("CORP_CARD_EXPENSE")
        cur.execute("""
            SELECT id FROM accounting_entries
            WHERE origin = ANY(%s) AND origin_id=%s AND company_code=%s
        """, (origins_to_remove, tx["id"], tx["company_code"]))
        stale = [row["id"] for row in (cur.fetchall() or [])]
        if stale:
            cur.execute("DELETE FROM accounting_lines WHERE entry_id = ANY(%s)", (stale,))
            cur.execute("DELETE FROM accounting_entries WHERE id = ANY(%s)", (stale,))
        entry_id = _post_entry(cur, tx["company_code"], tx_date, description, "CORP_CARD_ITP_PAYMENT", tx["id"], [
            {"account_code": SUPPLIER_AP_CODE, "account_name": SUPPLIER_AP_NAME, "debit": amount_crc, "credit": 0, "description": description},
            {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": 0, "credit": amount_crc, "description": description},
        ], force_closed_period=force_closed_period)
        cur.execute("""
            UPDATE payment_obligations
            SET paid_with_card=TRUE, card_transaction_id=%s, card_paid_at=%s, card_holder_name=%s,
                status='PAID', balance=0, last_payment_date=%s, updated_at=NOW()
            WHERE id=%s
        """, (tx["id"], tx_date, tx.get("user_name"), tx_date, tx.get("matched_obligation_id")))
    else:
        fiscal_status = (tx.get("deductible_status") or "PENDING_REVIEW").upper()
        requires_invoice = bool(tx.get("requires_invoice"))
        if fiscal_status == "PENDING_REVIEW" or requires_invoice:
            cur.execute("""
                SELECT id FROM accounting_entries
                WHERE origin IN ('CORP_CARD_EXPENSE', 'CORP_CARD_ITP_PAYMENT')
                  AND origin_id=%s AND company_code=%s
            """, (tx["id"], tx["company_code"]))
            stale = [row["id"] for row in (cur.fetchall() or [])]
            if stale:
                cur.execute("DELETE FROM accounting_lines WHERE entry_id = ANY(%s)", (stale,))
                cur.execute("DELETE FROM accounting_entries WHERE id = ANY(%s)", (stale,))
            entry_id = _post_entry(cur, tx["company_code"], tx_date, description, "CORP_CARD_PENDING", tx["id"], [
                {"account_code": PENDING_CARD_CODE, "account_name": PENDING_CARD_NAME, "debit": amount_crc, "credit": 0, "description": description},
                {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": 0, "credit": amount_crc, "description": description},
            ], force_closed_period=force_closed_period)
            cur.execute("UPDATE corporate_card_transactions SET accounting_entry_id=%s WHERE id=%s", (entry_id, tx["id"]))
            return entry_id
        origins_to_remove.append("CORP_CARD_ITP_PAYMENT")
        cur.execute("""
            SELECT id FROM accounting_entries
            WHERE origin = ANY(%s) AND origin_id=%s AND company_code=%s
        """, (origins_to_remove, tx["id"], tx["company_code"]))
        stale = [row["id"] for row in (cur.fetchall() or [])]
        if stale:
            cur.execute("DELETE FROM accounting_lines WHERE entry_id = ANY(%s)", (stale,))
            cur.execute("DELETE FROM accounting_entries WHERE id = ANY(%s)", (stale,))
        deductible = fiscal_status != "NON_DEDUCTIBLE"
        account_code = tx.get("expense_account_code") or (DEFAULT_EXPENSE_CODE if deductible else DEFAULT_NON_DEDUCTIBLE_CODE)
        account_name = tx.get("expense_account_name") or (DEFAULT_EXPENSE_NAME if deductible else DEFAULT_NON_DEDUCTIBLE_NAME)
        if tx.get("expense_account_code") or tx.get("fiscal_category"):
            cur.execute("""
                UPDATE corporate_card_transactions
                SET fiscal_category=COALESCE(%s, fiscal_category),
                    deductible_status=%s,
                    requires_invoice=%s,
                    expense_account_code=%s,
                    expense_account_name=%s
                WHERE id=%s
            """, (
                tx.get("fiscal_category"),
                tx.get("deductible_status") or fiscal_status,
                bool(tx.get("requires_invoice")),
                account_code,
                account_name,
                tx["id"],
            ))
        entry_id = _post_entry(cur, tx["company_code"], tx_date, description, "CORP_CARD_EXPENSE", tx["id"], [
            {"account_code": account_code, "account_name": account_name, "debit": amount_crc, "credit": 0, "description": description},
            {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": 0, "credit": amount_crc, "description": description},
        ], force_closed_period=force_closed_period)
    cur.execute("UPDATE corporate_card_transactions SET accounting_entry_id=%s WHERE id=%s", (entry_id, tx["id"]))
    return entry_id


def _default_card_payment_bank(cur) -> tuple[str, str]:
    cur.execute("""
        SELECT account_code, account_name
        FROM accounting_accounts
        WHERE active=TRUE
          AND accepts_posting=TRUE
          AND account_code LIKE '1.1.02%%'
          AND (
            UPPER(account_name) LIKE '%%BAC%%'
            OR UPPER(account_name) LIKE '%%SAN JOSE%%'
          )
        ORDER BY
          CASE WHEN UPPER(account_name) LIKE '%%CRC%%' OR UPPER(account_name) LIKE '%%COLON%%' THEN 0 ELSE 1 END,
          account_code
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        raise HTTPException(
            409,
            "No encontre una cuenta bancaria BAC para liquidar tarjetas. Indique bank_account_code.",
        )
    return row["account_code"], row["account_name"]


@router.post("/statements/import-pdf")
def import_statement_pdf(
    file: UploadFile = File(...),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    x_user: str | None = Header(None, alias="X-User"),
    conn=Depends(get_db),
):
    company = company_code(header_value=x_company_code)
    raw = file.file.read()
    digest = sha256(raw).hexdigest()
    parsed = parse_bac_statement(raw)
    if not parsed.get("card_last4") and not parsed.get("transactions") and _money(parsed.get("cash_payment_crc")) == 0 and _money(parsed.get("cash_payment_usd")) == 0:
        raw_text = str(parsed.get("raw_text") or "").upper()
        if "CUENTA IBAN" in raw_text or "CUENTA BANCARIA" in raw_text:
            raise HTTPException(
                400,
                "El PDF corresponde a un estado de cuenta bancaria BAC, no a una tarjeta de credito. "
                "Para obligaciones quincenales de tarjetas se necesita el estado de tarjeta BAC con pago de contado.",
            )
        raise HTTPException(
            400,
            "No se detectaron datos de tarjeta BAC en el PDF: falta tarjeta, periodo, pago de contado y movimientos.",
        )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("SELECT * FROM corporate_card_statements WHERE file_hash=%s", (digest,))
        existing = cur.fetchone()
        if existing:
            conn.commit()
            return {"status": "exists", "statement": _statement_row(existing)}
        cur.execute("""
            INSERT INTO corporate_card_statements(
                company_code, bank_name, card_last4, statement_period, cutoff_date,
                payment_due_date, cash_payment_crc, cash_payment_usd, source_filename,
                file_hash, raw_text, parsed_payload, imported_by
            ) VALUES(%s,'BAC',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
        """, (
            company, parsed.get("card_last4"), parsed.get("statement_period"), parsed.get("cutoff_date"),
            parsed.get("payment_due_date"), parsed.get("cash_payment_crc"), parsed.get("cash_payment_usd"),
            file.filename, digest, parsed.get("raw_text"), Json(_json_safe(parsed)), x_user or "SYSTEM",
        ))
        statement = cur.fetchone()
        inserted = 0
        for tx in parsed.get("transactions") or []:
            classified = apply_card_merchant_classification(tx)
            cur.execute("""
                INSERT INTO corporate_card_transactions(
                    statement_id, company_code, card_last4, user_name, transaction_type,
                    reference, transaction_date, description, merchant, currency,
                    amount_original, amount_crc, fiscal_category, deductible_status,
                    requires_invoice, expense_account_code, expense_account_name
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(statement_id, reference, transaction_date, amount_original, currency) DO NOTHING
            """, (
                statement["id"], company, classified.get("card_last4"), classified.get("user_name"), classified.get("transaction_type"),
                classified.get("reference"), classified.get("transaction_date"), classified.get("description"), classified.get("merchant"),
                classified.get("currency"), classified.get("amount_original"), classified.get("amount_crc"),
                classified.get("fiscal_category") or "SIN_CLASIFICAR",
                classified.get("deductible_status") or "PENDING_REVIEW",
                bool(classified.get("requires_invoice", classified.get("transaction_type") == "PURCHASE")),
                classified.get("expense_account_code"),
                classified.get("expense_account_name"),
            ))
            inserted += cur.rowcount
        auto_result = _auto_match_statement(cur, int(statement["id"]), post_matched=True)
        conn.commit()
        return {
            "status": "ok",
            "statement": _statement_row(statement),
            "transactions_inserted": inserted,
            "auto_match": auto_result,
        }


@router.get("/statements")
def list_statements(
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("""
            SELECT s.*,
                   COUNT(t.id) AS transaction_count,
                   COUNT(t.id) FILTER(WHERE t.match_status='MATCHED_ITP') AS matched_count,
                   COUNT(t.id) FILTER(WHERE t.accounting_entry_id IS NOT NULL) AS posted_count
            FROM corporate_card_statements s
            LEFT JOIN corporate_card_transactions t ON t.statement_id=s.id
            WHERE s.company_code=%s
            GROUP BY s.id
            ORDER BY s.cutoff_date DESC NULLS LAST, s.id DESC
        """, (company_code(header_value=x_company_code),))
        return {"items": [dict(row) for row in cur.fetchall()]}


@router.get("/statements/{statement_id}/transactions")
def list_transactions(statement_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("""
            SELECT * FROM corporate_card_transactions
            WHERE statement_id=%s
            ORDER BY transaction_date NULLS LAST, id
        """, (statement_id,))
        return {"items": [dict(row) for row in cur.fetchall()]}


def _match_candidates(cur, tx_id: int) -> list[dict[str, Any]]:
    cur.execute("SELECT * FROM corporate_card_transactions WHERE id=%s", (tx_id,))
    tx = cur.fetchone()
    if not tx:
        raise HTTPException(404, "Movimiento de tarjeta no existe")
    amount = _money(tx["amount_original"])
    tx_dict = dict(tx)
    cur.execute("""
        SELECT id, payee_name, reference, issue_date, due_date, currency, total, balance, status,
               obligation_type, payee_type, notes, COALESCE(paid_with_card, FALSE) AS paid_with_card
        FROM payment_obligations
        WHERE active=TRUE
          AND status IN ('PENDING','PARTIAL')
          AND COALESCE(paid_with_card, FALSE)=FALSE
          AND currency=%s
          AND (
              ABS(COALESCE(total,0)-%s) <= 500
              OR issue_date BETWEEN (%s::date - INTERVAL '45 days') AND (%s::date + INTERVAL '45 days')
              OR UPPER(COALESCE(payee_name,'')) <> '' AND %s LIKE '%%' || UPPER(payee_name) || '%%'
          )
        LIMIT 50
    """, (
        tx["currency"],
        amount,
        tx["transaction_date"],
        tx["transaction_date"],
        _norm_text(f"{tx.get('description') or ''} {tx.get('merchant') or ''}"),
    ))
    candidates: list[dict[str, Any]] = []
    for row in cur.fetchall() or []:
        candidate = dict(row)
        score, amount_delta = _score_candidate(
            tx=tx_dict,
            name=candidate.get("payee_name"),
            currency=candidate.get("currency"),
            total=candidate.get("total"),
            issue_date=candidate.get("issue_date"),
            status=candidate.get("status"),
            paid_with_card=bool(candidate.get("paid_with_card")),
            reference=candidate.get("reference"),
        )
        candidate.update({
            "source_type": "ITP",
            "obligation_id": candidate["id"],
            "tax_document_id": None,
            "company_code": tx["company_code"],
            "score": score,
            "amount_delta": amount_delta,
        })
        candidates.append(candidate)

    if _tax_documents_available(cur):
        cur.execute("""
            SELECT d.id, d.issuer_name AS payee_name,
                   COALESCE(d.electronic_key, d.document_number) AS reference,
                   d.issue_datetime::date AS issue_date,
                   d.issue_datetime::date AS due_date,
                   d.currency_code AS currency,
                   d.total, d.total AS balance,
                   d.status, d.document_type AS obligation_type,
                   'SUPPLIER' AS payee_type,
                   d.hacienda_status AS notes
            FROM tax_electronic_documents d
            WHERE d.company_code=%s
              AND d.direction='PURCHASE'
              AND COALESCE(d.total,0) > 0
              AND d.currency_code=%s
              AND NOT EXISTS (
                  SELECT 1
                  FROM payment_obligations po
                  WHERE po.company_code=d.company_code
                    AND po.active=TRUE
                    AND po.reference IN (d.electronic_key, d.document_number)
              )
              AND (
                  ABS(COALESCE(d.total,0)-%s) <= 500
                  OR d.issue_datetime::date BETWEEN (%s::date - INTERVAL '45 days') AND (%s::date + INTERVAL '45 days')
                  OR UPPER(COALESCE(d.issuer_name,'')) <> '' AND %s LIKE '%%' || UPPER(d.issuer_name) || '%%'
              )
            LIMIT 50
        """, (
            tx["company_code"],
            tx["currency"],
            amount,
            tx["transaction_date"],
            tx["transaction_date"],
            _norm_text(f"{tx.get('description') or ''} {tx.get('merchant') or ''}"),
        ))
        for row in cur.fetchall() or []:
            candidate = dict(row)
            score, amount_delta = _score_candidate(
                tx=tx_dict,
                name=candidate.get("payee_name"),
                currency=candidate.get("currency"),
                total=candidate.get("total"),
                issue_date=candidate.get("issue_date"),
                status="PENDING",
                reference=candidate.get("reference"),
            )
            candidate.update({
                "source_type": "TAX_DOC",
                "obligation_id": None,
                "tax_document_id": candidate["id"],
                "company_code": tx["company_code"],
                "score": score,
                "amount_delta": amount_delta,
            })
            candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            -int(item.get("score") or 0),
            _money(item.get("amount_delta")),
            item.get("issue_date") or date.min,
            int(item.get("id") or 0),
        )
    )
    return candidates[:50]


def _resolve_candidate_obligation(cur, company: str, candidate: dict[str, Any]) -> int:
    if candidate.get("source_type") == "TAX_DOC":
        return _ensure_obligation_from_tax_doc(cur, company, int(candidate["tax_document_id"]))
    return int(candidate.get("obligation_id") or candidate["id"])


def _auto_match_statement(cur, statement_id: int, post_matched: bool = True) -> dict[str, Any]:
    matched = 0
    posted = 0
    blocked: list[dict[str, Any]] = []
    cur.execute("""
        SELECT id FROM corporate_card_transactions
        WHERE statement_id=%s AND transaction_type='PURCHASE' AND match_status='UNMATCHED'
        ORDER BY transaction_date, id
    """, (statement_id,))
    ids = [row["id"] for row in cur.fetchall()]
    for tx_id in ids:
        candidates = _match_candidates(cur, tx_id)
        if not candidates:
            continue
        best = candidates[0]
        if int(best.get("score") or 0) < 60:
            continue
        if len(candidates) > 1 and int(best.get("score") or 0) == int(candidates[1].get("score") or 0):
            continue
        obligation_id = _resolve_candidate_obligation(cur, best.get("company_code") or "MSL-CR", best)
        cur.execute("""
            UPDATE corporate_card_transactions
            SET matched_obligation_id=%s, match_status='MATCHED_ITP', deductible_status='DEDUCTIBLE', requires_invoice=FALSE
            WHERE id=%s
            RETURNING *
        """, (obligation_id, tx_id))
        tx = cur.fetchone()
        matched += 1
        if post_matched and tx:
            try:
                if _post_card_transaction(cur, dict(tx)):
                    posted += 1
            except HTTPException as exc:
                blocked.append({"transaction_id": tx_id, "reason": str(exc.detail)})
    return {"matched": matched, "posted": posted, "blocked": blocked}


def _find_or_create_notification_transaction(cur, payload: BacNotificationRequest, company: str) -> dict[str, Any]:
    reference = (payload.reference or payload.authorization or "").strip() or None
    amount = _money(payload.amount)
    currency = (payload.currency or "CRC").upper()
    merchant = (payload.merchant or payload.subject or "Notificacion BAC").strip()
    cur.execute("""
        SELECT *
        FROM corporate_card_transactions
        WHERE company_code=%s
          AND transaction_type='PURCHASE'
          AND currency=%s
          AND ABS(COALESCE(amount_original,0)-%s) <= 2
          AND transaction_date BETWEEN (%s::date - INTERVAL '3 days') AND (%s::date + INTERVAL '3 days')
          AND (%s IS NULL OR card_last4=%s)
          AND (
              %s IS NULL
              OR reference=%s
              OR %s ILIKE '%%' || COALESCE(reference,'') || '%%'
              OR COALESCE(description,'') ILIKE '%%' || %s || '%%'
              OR COALESCE(merchant,'') ILIKE '%%' || %s || '%%'
          )
        ORDER BY
          CASE WHEN reference=%s THEN 0 ELSE 1 END,
          ABS(COALESCE(amount_original,0)-%s),
          id DESC
        LIMIT 1
    """, (
        company,
        currency,
        amount,
        payload.transaction_date,
        payload.transaction_date,
        payload.card_last4,
        payload.card_last4,
        reference,
        reference,
        reference,
        merchant,
        merchant,
        reference,
        amount,
    ))
    existing = cur.fetchone()
    if existing:
        return dict(existing)
    classified = apply_card_merchant_classification({
        "merchant": merchant,
        "description": merchant,
        "transaction_type": "PURCHASE",
    })
    cur.execute("""
        INSERT INTO corporate_card_transactions(
            statement_id, company_code, card_last4, user_name, transaction_type,
            reference, transaction_date, description, merchant, currency,
            amount_original, amount_crc, fiscal_category, deductible_status,
            requires_invoice, expense_account_code, expense_account_name, notes
        ) VALUES(
            NULL, %s, %s, %s, 'PURCHASE',
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        RETURNING *
    """, (
        company,
        payload.card_last4,
        payload.holder_name,
        reference,
        payload.transaction_date,
        merchant,
        merchant,
        currency,
        amount,
        amount if currency == "CRC" else Decimal("0.00"),
        classified.get("fiscal_category") or "SIN_CLASIFICAR",
        classified.get("deductible_status") or "PENDING_REVIEW",
        bool(classified.get("requires_invoice", True)),
        classified.get("expense_account_code"),
        classified.get("expense_account_name"),
        f"Creado desde notificacion BAC autorizacion {payload.authorization or ''} referencia {payload.reference or ''}".strip(),
    ))
    return dict(cur.fetchone())


@router.post("/bac-notifications/import")
def import_bac_notification(
    payload: BacNotificationRequest,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    company = company_code(payload.company_code, header_value=x_company_code)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        amount = _money(payload.amount)
        currency = (payload.currency or "CRC").upper()
        cur.execute("""
            INSERT INTO corporate_card_bac_notifications(
                company_code, mailbox, folder, message_id, subject, merchant,
                transaction_date, currency, amount, card_last4, authorization_code,
                reference, holder_name
            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(
                company_code,
                (COALESCE(reference,'')),
                (COALESCE(authorization_code,'')),
                (COALESCE(card_last4,'')),
                transaction_date,
                currency,
                amount
            ) DO UPDATE SET
                mailbox=EXCLUDED.mailbox,
                folder=EXCLUDED.folder,
                message_id=EXCLUDED.message_id,
                subject=EXCLUDED.subject,
                merchant=EXCLUDED.merchant,
                holder_name=EXCLUDED.holder_name,
                updated_at=NOW()
            RETURNING *
        """, (
            company,
            payload.mailbox,
            payload.folder,
            payload.message_id,
            payload.subject,
            payload.merchant,
            payload.transaction_date,
            currency,
            amount,
            payload.card_last4,
            payload.authorization,
            payload.reference,
            payload.holder_name,
        ))
        notification = cur.fetchone()
        tx = _find_or_create_notification_transaction(cur, payload, company)
        candidates = _match_candidates(cur, int(tx["id"]))
        posted = False
        status = "SEMI_REQUIRED"
        blocked_reason = None
        obligation_id = tx.get("matched_obligation_id")
        if not obligation_id and candidates:
            best = candidates[0]
            if int(best.get("score") or 0) >= 60 and not (
                len(candidates) > 1 and int(best.get("score") or 0) == int(candidates[1].get("score") or 0)
            ):
                obligation_id = _resolve_candidate_obligation(cur, company, best)
                cur.execute("""
                    UPDATE corporate_card_transactions
                    SET matched_obligation_id=%s, match_status='MATCHED_ITP',
                        deductible_status='DEDUCTIBLE', requires_invoice=FALSE
                    WHERE id=%s
                    RETURNING *
                """, (obligation_id, tx["id"]))
                tx = dict(cur.fetchone())
        if obligation_id:
            status = "MATCHED"
            try:
                posted = bool(_post_card_transaction(
                    cur,
                    dict(tx),
                    force_closed_period=bool(payload.allow_closed_period),
                ))
                if posted:
                    status = "POSTED"
            except HTTPException as exc:
                blocked_reason = str(exc.detail)
        cur.execute("""
            UPDATE corporate_card_bac_notifications
            SET matched_transaction_id=%s, matched_obligation_id=%s, status=%s, updated_at=NOW()
            WHERE id=%s
        """, (tx["id"], obligation_id, status, notification["id"]))
        conn.commit()
        return {
            "status": status,
            "notification_id": notification["id"],
            "transaction_id": tx["id"],
            "matched_obligation_id": obligation_id,
            "posted": posted,
            "blocked_reason": blocked_reason,
            "candidates": candidates[:10],
        }


@router.get("/transactions/{transaction_id}/match-candidates")
def match_candidates(transaction_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        return {"items": _match_candidates(cur, transaction_id)}


@router.post("/statements/{statement_id}/auto-match")
def auto_match(statement_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        result = _auto_match_statement(cur, statement_id, post_matched=True)
        conn.commit()
    return {"status": "ok", **result}


@router.post("/transactions/{transaction_id}/match-itp")
def match_itp(transaction_id: int, payload: MatchRequest, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("SELECT id FROM payment_obligations WHERE id=%s", (payload.obligation_id,))
        if not cur.fetchone():
            raise HTTPException(404, "Factura/obligacion ITP no existe")
        cur.execute("""
            UPDATE corporate_card_transactions
            SET matched_obligation_id=%s, match_status='MATCHED_ITP', deductible_status='DEDUCTIBLE', requires_invoice=FALSE
            WHERE id=%s
            RETURNING *
        """, (payload.obligation_id, transaction_id))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Movimiento de tarjeta no existe")
        posted = False
        blocked_reason = None
        period = _period_from_date(row.get("transaction_date"))
        if _period_is_closed(cur, row["company_code"], period):
            blocked_reason = f"El periodo {period} esta cerrado; cruce guardado sin asiento."
        else:
            posted = bool(_post_card_transaction(cur, dict(row)))
        conn.commit()
        return {"status": "ok", "transaction": dict(row), "posted": posted, "blocked_reason": blocked_reason}


@router.put("/transactions/{transaction_id}/classify")
def classify_transaction(transaction_id: int, payload: ClassifyRequest, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("""
            UPDATE corporate_card_transactions
            SET fiscal_category=COALESCE(%s, fiscal_category),
                deductible_status=COALESCE(%s, deductible_status),
                requires_invoice=COALESCE(%s, requires_invoice),
                expense_account_code=COALESCE(%s, expense_account_code),
                expense_account_name=COALESCE(%s, expense_account_name),
                notes=COALESCE(%s, notes)
            WHERE id=%s
            RETURNING *
        """, (
            payload.fiscal_category,
            payload.deductible_status,
            payload.requires_invoice,
            payload.expense_account_code,
            payload.expense_account_name,
            payload.notes,
            transaction_id,
        ))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Movimiento de tarjeta no existe")
        posted = False
        blocked_reason = None
        if (row.get("deductible_status") or "").upper() in {"DEDUCTIBLE", "NON_DEDUCTIBLE"} or row.get("matched_obligation_id"):
            period = _period_from_date(row.get("transaction_date"))
            if _period_is_closed(cur, row["company_code"], period) and not payload.force_closed_period:
                blocked_reason = f"El periodo {period} esta cerrado; clasificacion guardada sin asiento."
            else:
                posted = bool(_post_card_transaction(cur, dict(row), force_closed_period=payload.force_closed_period))
        conn.commit()
        return {
            "status": "ok",
            "transaction": dict(row),
            "posted": posted,
            "blocked_reason": blocked_reason,
        }


@router.put("/statements/{statement_id}/classify")
def classify_statement_transactions(statement_id: int, payload: BulkClassifyRequest, conn=Depends(get_db)):
    updated = 0
    posted = 0
    blocked: list[dict[str, Any]] = []
    items = payload.items or []
    if not items:
        return {"status": "ok", "updated": 0, "posted": 0, "blocked": []}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        for item in items:
            cur.execute("""
                UPDATE corporate_card_transactions
                SET fiscal_category=COALESCE(%s, fiscal_category),
                    deductible_status=COALESCE(%s, deductible_status),
                    requires_invoice=COALESCE(%s, requires_invoice),
                    expense_account_code=COALESCE(%s, expense_account_code),
                    expense_account_name=COALESCE(%s, expense_account_name),
                    notes=COALESCE(%s, notes)
                WHERE id=%s AND statement_id=%s
                RETURNING *
            """, (
                item.fiscal_category,
                item.deductible_status,
                item.requires_invoice,
                item.expense_account_code,
                item.expense_account_name,
                item.notes,
                item.transaction_id,
                statement_id,
            ))
            row = cur.fetchone()
            if not row:
                blocked.append({"transaction_id": item.transaction_id, "reason": "Movimiento no existe en este estado"})
                continue
            updated += 1
            should_post = (
                (row.get("deductible_status") or "").upper() in {"DEDUCTIBLE", "NON_DEDUCTIBLE"}
                or row.get("matched_obligation_id")
                or bool(row.get("requires_invoice"))
            )
            if not should_post:
                continue
            period = _period_from_date(row.get("transaction_date"))
            if _period_is_closed(cur, row["company_code"], period) and not payload.force_closed_periods:
                blocked.append({"transaction_id": row["id"], "reason": f"Periodo {period} cerrado"})
                continue
            if _post_card_transaction(cur, dict(row), force_closed_period=payload.force_closed_periods):
                posted += 1

        conn.commit()
        return {"status": "ok", "updated": updated, "posted": posted, "blocked": blocked}


@router.post("/statements/{statement_id}/post-daily")
def post_daily(statement_id: int, conn=Depends(get_db)):
    posted = 0
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("""
            SELECT * FROM corporate_card_transactions
            WHERE statement_id=%s AND transaction_type='PURCHASE'
            ORDER BY transaction_date, id
        """, (statement_id,))
        transactions = cur.fetchall() or []
        for tx in transactions:
            if _post_card_transaction(cur, dict(tx)):
                posted += 1
        conn.commit()
    return {"status": "ok", "posted": posted}


def _post_daily_for_statement(cur, statement_id: int, force_closed_period: bool = False) -> int:
    cur.execute("""
        SELECT * FROM corporate_card_transactions
        WHERE statement_id=%s AND transaction_type='PURCHASE'
        ORDER BY transaction_date, id
    """, (statement_id,))
    transactions = cur.fetchall() or []
    posted = 0
    for tx in transactions:
        if _post_card_transaction(cur, dict(tx), force_closed_period=force_closed_period):
            posted += 1
    cur.execute("""
        UPDATE corporate_card_statements
        SET status=CASE WHEN status='SETTLED' THEN status ELSE 'POSTED_PENDING_PAYMENT' END
        WHERE id=%s
    """, (statement_id,))
    return posted


@router.post("/statements/{statement_id}/post-settlement")
def post_settlement(statement_id: int, payload: SettlementRequest, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("SELECT * FROM corporate_card_statements WHERE id=%s", (statement_id,))
        statement = cur.fetchone()
        if not statement:
            raise HTTPException(404, "Estado de cuenta no existe")
        pay_date = payload.payment_date or statement.get("payment_due_date") or _due_on_15th(statement.get("cutoff_date"), statement.get("statement_period"))
        amount_crc, amount_usd, exchange_rate, usd_crc, total_crc = _settlement_amounts(
            cur,
            statement,
            pay_date,
            override_crc=payload.amount_crc,
            override_usd=payload.amount_usd,
            override_rate=payload.exchange_rate,
        )
        if total_crc <= 0:
            raise HTTPException(400, "No hay monto contado para liquidar")
        bank_name = payload.bank_account_name or payload.bank_account_code
        description = _settlement_description(statement, amount_crc, amount_usd, exchange_rate, usd_crc, total_crc)
        entry_id = _post_entry(
            cur,
            statement["company_code"],
            pay_date,
            description,
            "CORP_CARD_SETTLEMENT",
            statement_id,
            _settlement_lines(payload.bank_account_code, bank_name, description, amount_crc, amount_usd, usd_crc, total_crc),
        )
        cur.execute("""
            INSERT INTO corporate_card_settlements(
                statement_id, company_code, payment_date, bank_account_code, bank_account_name,
                amount_crc, amount_usd, exchange_rate, accounting_entry_id, created_by
            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'SYSTEM')
            ON CONFLICT(statement_id) DO UPDATE SET
                payment_date=EXCLUDED.payment_date,
                bank_account_code=EXCLUDED.bank_account_code,
                bank_account_name=EXCLUDED.bank_account_name,
                amount_crc=EXCLUDED.amount_crc,
                amount_usd=EXCLUDED.amount_usd,
                exchange_rate=EXCLUDED.exchange_rate,
                accounting_entry_id=EXCLUDED.accounting_entry_id
            RETURNING *
        """, (statement_id, statement["company_code"], pay_date, payload.bank_account_code, bank_name, amount_crc, amount_usd, exchange_rate, entry_id))
        settlement = cur.fetchone()
        cur.execute("UPDATE corporate_card_statements SET status='SETTLED' WHERE id=%s", (statement_id,))
        conn.commit()
        return {"status": "ok", "settlement": dict(settlement), "entry_id": entry_id}


def _post_settlement_for_statement(
    cur,
    statement: dict[str, Any],
    bank_account_code: str | None = None,
    bank_account_name: str | None = None,
    force_closed_period: bool = False,
) -> int:
    code, name = (bank_account_code, bank_account_name)
    if not code:
        code, name = _default_card_payment_bank(cur)
    name = name or code
    pay_date = statement.get("payment_due_date") or _due_on_15th(statement.get("cutoff_date"), statement.get("statement_period"))
    if not pay_date:
        raise HTTPException(400, f"Estado {statement.get('id')} no tiene fecha para pago de tarjeta")
    amount_crc, amount_usd, exchange_rate, usd_crc, total_crc = _settlement_amounts(cur, statement, pay_date)
    if total_crc <= 0:
        return 0
    description = _settlement_description(statement, amount_crc, amount_usd, exchange_rate, usd_crc, total_crc)
    entry_id = _post_entry(
        cur,
        statement["company_code"],
        pay_date,
        description,
        "CORP_CARD_SETTLEMENT",
        statement["id"],
        _settlement_lines(code, name, description, amount_crc, amount_usd, usd_crc, total_crc),
        force_closed_period=force_closed_period,
    )
    cur.execute("""
        INSERT INTO corporate_card_settlements(
            statement_id, company_code, payment_date, bank_account_code, bank_account_name,
            amount_crc, amount_usd, exchange_rate, accounting_entry_id, created_by
        ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,'SYSTEM')
        ON CONFLICT(statement_id) DO UPDATE SET
            payment_date=EXCLUDED.payment_date,
            bank_account_code=EXCLUDED.bank_account_code,
            bank_account_name=EXCLUDED.bank_account_name,
            amount_crc=EXCLUDED.amount_crc,
            amount_usd=EXCLUDED.amount_usd,
            exchange_rate=EXCLUDED.exchange_rate,
            accounting_entry_id=EXCLUDED.accounting_entry_id
        RETURNING id
    """, (statement["id"], statement["company_code"], pay_date, code, name, amount_crc, amount_usd, exchange_rate, entry_id))
    cur.execute("UPDATE corporate_card_statements SET status='SETTLED' WHERE id=%s", (statement["id"],))
    return entry_id


@router.post("/statements/post-history")
def post_history(
    payload: HistoryPostRequest,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    company = company_code(header_value=x_company_code)
    years = sorted({int(year) for year in (payload.years or [2025, 2026])})
    if not years:
        raise HTTPException(400, "Indique al menos un ano")
    start_period = f"{years[0]}-01"
    end_period = f"{years[-1]}-12"
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute("""
            SELECT *
            FROM corporate_card_statements
            WHERE company_code=%s
              AND statement_period BETWEEN %s AND %s
            ORDER BY cutoff_date NULLS LAST, statement_period, id
        """, (company, start_period, end_period))
        statements = [dict(row) for row in cur.fetchall()]
        if not statements:
            return {"status": "empty", "message": "No hay estados BAC importados para 2025-2026", "posted": 0, "settled": 0}
        latest_ids: set[int] = set()
        if payload.leave_latest_pending and payload.latest_pending_per_card:
            for statement in statements:
                key = statement.get("card_last4") or f"statement:{statement.get('id')}"
                previous = next((item for item in statements if item["id"] in latest_ids and (item.get("card_last4") or f"statement:{item.get('id')}") == key), None)
                if previous:
                    latest_ids.discard(previous["id"])
                latest_ids.add(statement["id"])
        elif payload.leave_latest_pending:
            latest_ids.add(statements[-1]["id"])
        posted = 0
        settled = 0
        latest_pending = []
        blocked = []
        for statement in statements:
            statement_id = int(statement["id"])
            statement_label = f"{statement.get('statement_period') or 'sin-periodo'} / {statement.get('card_last4') or 'sin-tarjeta'}"
            closed_purchase_periods = _closed_purchase_periods_for_statement(cur, statement_id, company)
            if closed_purchase_periods and not payload.force_closed_periods:
                blocked.append({
                    "statement_id": statement_id,
                    "statement": statement_label,
                    "action": "post_daily",
                    "periods": closed_purchase_periods,
                    "reason": "Periodo contable cerrado",
                })
                cur.execute("""
                    UPDATE corporate_card_statements
                    SET status='BLOCKED_CLOSED_PERIOD'
                    WHERE id=%s AND status<>'SETTLED'
                """, (statement_id,))
            else:
                posted += _post_daily_for_statement(cur, statement_id, force_closed_period=payload.force_closed_periods)
            if payload.settle_previous and statement["id"] not in latest_ids:
                pay_date = statement.get("payment_due_date") or _due_on_15th(statement.get("cutoff_date"), statement.get("statement_period"))
                settlement_period = _period_from_date(pay_date)
                if _period_is_closed(cur, company, settlement_period) and not payload.force_closed_periods:
                    blocked.append({
                        "statement_id": statement_id,
                        "statement": statement_label,
                        "action": "post_settlement",
                        "periods": [settlement_period],
                        "reason": "Periodo contable cerrado",
                    })
                    cur.execute("""
                        UPDATE corporate_card_statements
                        SET status='POSTED_PENDING_PAYMENT'
                        WHERE id=%s AND status<>'SETTLED'
                    """, (statement_id,))
                elif _post_settlement_for_statement(
                        cur,
                        statement,
                        bank_account_code=payload.bank_account_code,
                        bank_account_name=payload.bank_account_name,
                        force_closed_period=payload.force_closed_periods,
                    ):
                        settled += 1
            elif statement["id"] in latest_ids:
                latest_pending.append(statement)
                if payload.force_closed_periods or not closed_purchase_periods:
                    cur.execute("""
                        UPDATE corporate_card_statements
                        SET status='POSTED_PENDING_PAYMENT'
                        WHERE id=%s AND status<>'SETTLED'
                    """, (statement["id"],))
        conn.commit()
        return {
            "status": "ok",
            "statements": len(statements),
            "posted": posted,
            "settled": settled,
            "latest_pending": latest_pending,
            "blocked": blocked,
        }
