from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
from io import BytesIO
import calendar
import re
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
SUPPLIER_AP_CODE = "2.1.01.01"
SUPPLIER_AP_NAME = "Cuentas por pagar-comerciales"


class ClassifyRequest(BaseModel):
    fiscal_category: str | None = None
    deductible_status: str | None = None
    requires_invoice: bool | None = None
    expense_account_code: str | None = None
    expense_account_name: str | None = None
    notes: str | None = None


class MatchRequest(BaseModel):
    obligation_id: int


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
          (%s, %s, 'GASTO', 'DEBIT', 3, '5.4', TRUE, TRUE)
        ON CONFLICT (account_code) DO UPDATE SET account_name=EXCLUDED.account_name, accepts_posting=TRUE, active=TRUE
    """, (CARD_PAYABLE_CODE, CARD_PAYABLE_NAME, DEFAULT_NON_DEDUCTIBLE_CODE, DEFAULT_NON_DEDUCTIBLE_NAME))
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


def _post_entry(cur, company: str, entry_date: date, description: str, origin: str, origin_id: int, lines: list[dict[str, Any]]) -> int:
    period = entry_date.strftime("%Y-%m")
    cur.execute("""
        SELECT status FROM accounting_period_controls
        WHERE company_code=%s AND period=%s
    """, (company, period))
    status = cur.fetchone()
    if status and status.get("status") == "CLOSED":
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
        cur.execute("""
            INSERT INTO accounting_entries(entry_date, period, description, origin, origin_id, created_by, workflow_status, company_code, posting_rule_code, posting_metadata, posted_by, posted_at)
            VALUES(%s,%s,%s,%s,%s,'SYSTEM','POSTED',%s,%s,%s,'SYSTEM',NOW())
            RETURNING id
        """, (entry_date, period, description, origin, origin_id, company, origin, Json({"source": "corporate_cards"})))
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
            cur.execute("""
                INSERT INTO corporate_card_transactions(
                    statement_id, company_code, card_last4, user_name, transaction_type,
                    reference, transaction_date, description, merchant, currency,
                    amount_original, amount_crc, fiscal_category, deductible_status,
                    requires_invoice, expense_account_code, expense_account_name
                ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(statement_id, reference, transaction_date, amount_original, currency) DO NOTHING
            """, (
                statement["id"], company, tx.get("card_last4"), tx.get("user_name"), tx.get("transaction_type"),
                tx.get("reference"), tx.get("transaction_date"), tx.get("description"), tx.get("merchant"),
                tx.get("currency"), tx.get("amount_original"), tx.get("amount_crc"),
                "SIN_CLASIFICAR", "PENDING_REVIEW", tx.get("transaction_type") == "PURCHASE",
                None, None,
            ))
            inserted += cur.rowcount
        conn.commit()
        return {"status": "ok", "statement": _statement_row(statement), "transactions_inserted": inserted}


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
    desc = (tx.get("description") or "").upper()
    cur.execute("""
        SELECT id, payee_name, reference, issue_date, due_date, currency, total, balance, status,
               CASE
                 WHEN UPPER(COALESCE(payee_name,'')) <> '' AND %s LIKE '%%' || UPPER(payee_name) || '%%' THEN 30
                 ELSE 0
               END
               + CASE WHEN currency=%s THEN 20 ELSE 0 END
               + CASE WHEN ABS(COALESCE(total,0)-%s) <= 2 THEN 40 ELSE 0 END AS score
        FROM payment_obligations
        WHERE active=TRUE
          AND status IN ('PENDING','PARTIAL')
          AND currency=%s
          AND ABS(COALESCE(total,0)-%s) <= 2
          AND issue_date BETWEEN (%s::date - INTERVAL '15 days') AND (%s::date + INTERVAL '15 days')
        ORDER BY score DESC, issue_date DESC
        LIMIT 10
    """, (desc, tx["currency"], amount, tx["currency"], amount, tx["transaction_date"], tx["transaction_date"]))
    return [dict(row) for row in cur.fetchall()]


@router.get("/transactions/{transaction_id}/match-candidates")
def match_candidates(transaction_id: int, conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        return {"items": _match_candidates(cur, transaction_id)}


@router.post("/statements/{statement_id}/auto-match")
def auto_match(statement_id: int, conn=Depends(get_db)):
    matched = 0
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
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
            cur.execute("""
                UPDATE corporate_card_transactions
                SET matched_obligation_id=%s, match_status='MATCHED_ITP', deductible_status='DEDUCTIBLE', requires_invoice=FALSE
                WHERE id=%s
            """, (best["id"], tx_id))
            matched += 1
        conn.commit()
    return {"status": "ok", "matched": matched}


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
        conn.commit()
        return {"status": "ok", "transaction": dict(row)}


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
        conn.commit()
        return {"status": "ok", "transaction": dict(row)}


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
            tx_date = tx.get("transaction_date")
            if not tx_date:
                continue
            amount_crc = _money(tx.get("amount_crc"))
            if amount_crc <= 0 and (tx.get("currency") or "CRC").upper() == "USD":
                amount_crc = (_money(tx.get("amount_original")) * _exchange_rate_for(cur, tx_date)).quantize(MONEY, rounding=ROUND_HALF_UP)
            elif amount_crc <= 0:
                amount_crc = _money(tx.get("amount_original"))
            if amount_crc <= 0:
                continue
            description = f"Tarjeta corporativa BAC {tx.get('user_name') or ''}: {tx.get('description') or ''}".strip()
            if tx.get("matched_obligation_id"):
                entry_id = _post_entry(cur, tx["company_code"], tx_date, description, "CORP_CARD_ITP_PAYMENT", tx["id"], [
                    {"account_code": SUPPLIER_AP_CODE, "account_name": SUPPLIER_AP_NAME, "debit": amount_crc, "credit": 0, "description": description},
                    {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": 0, "credit": amount_crc, "description": description},
                ])
                cur.execute("""
                    UPDATE payment_obligations
                    SET paid_with_card=TRUE, card_transaction_id=%s, card_paid_at=%s, card_holder_name=%s,
                        status='PAID', balance=0, last_payment_date=%s, updated_at=NOW()
                    WHERE id=%s
                """, (tx["id"], tx_date, tx.get("user_name"), tx_date, tx.get("matched_obligation_id")))
            else:
                deductible = (tx.get("deductible_status") or "").upper() != "NON_DEDUCTIBLE"
                account_code = tx.get("expense_account_code") or (DEFAULT_EXPENSE_CODE if deductible else DEFAULT_NON_DEDUCTIBLE_CODE)
                account_name = tx.get("expense_account_name") or (DEFAULT_EXPENSE_NAME if deductible else DEFAULT_NON_DEDUCTIBLE_NAME)
                entry_id = _post_entry(cur, tx["company_code"], tx_date, description, "CORP_CARD_EXPENSE", tx["id"], [
                    {"account_code": account_code, "account_name": account_name, "debit": amount_crc, "credit": 0, "description": description},
                    {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": 0, "credit": amount_crc, "description": description},
                ])
            cur.execute("UPDATE corporate_card_transactions SET accounting_entry_id=%s WHERE id=%s", (entry_id, tx["id"]))
            posted += 1
        conn.commit()
    return {"status": "ok", "posted": posted}


def _post_daily_for_statement(cur, statement_id: int) -> int:
    cur.execute("""
        SELECT * FROM corporate_card_transactions
        WHERE statement_id=%s AND transaction_type='PURCHASE'
        ORDER BY transaction_date, id
    """, (statement_id,))
    transactions = cur.fetchall() or []
    posted = 0
    for tx in transactions:
        tx_date = tx.get("transaction_date")
        if not tx_date:
            continue
        amount_crc = _money(tx.get("amount_crc"))
        if amount_crc <= 0 and (tx.get("currency") or "CRC").upper() == "USD":
            amount_crc = (_money(tx.get("amount_original")) * _exchange_rate_for(cur, tx_date)).quantize(MONEY, rounding=ROUND_HALF_UP)
        elif amount_crc <= 0:
            amount_crc = _money(tx.get("amount_original"))
        if amount_crc <= 0:
            continue
        description = f"Tarjeta corporativa BAC {tx.get('user_name') or ''}: {tx.get('description') or ''}".strip()
        if tx.get("matched_obligation_id"):
            entry_id = _post_entry(cur, tx["company_code"], tx_date, description, "CORP_CARD_ITP_PAYMENT", tx["id"], [
                {"account_code": SUPPLIER_AP_CODE, "account_name": SUPPLIER_AP_NAME, "debit": amount_crc, "credit": 0, "description": description},
                {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": 0, "credit": amount_crc, "description": description},
            ])
            cur.execute("""
                UPDATE payment_obligations
                SET paid_with_card=TRUE, card_transaction_id=%s, card_paid_at=%s, card_holder_name=%s,
                    status='PAID', balance=0, last_payment_date=%s, updated_at=NOW()
                WHERE id=%s
            """, (tx["id"], tx_date, tx.get("user_name"), tx_date, tx.get("matched_obligation_id")))
        else:
            deductible = (tx.get("deductible_status") or "").upper() != "NON_DEDUCTIBLE"
            account_code = tx.get("expense_account_code") or (DEFAULT_EXPENSE_CODE if deductible else DEFAULT_NON_DEDUCTIBLE_CODE)
            account_name = tx.get("expense_account_name") or (DEFAULT_EXPENSE_NAME if deductible else DEFAULT_NON_DEDUCTIBLE_NAME)
            entry_id = _post_entry(cur, tx["company_code"], tx_date, description, "CORP_CARD_EXPENSE", tx["id"], [
                {"account_code": account_code, "account_name": account_name, "debit": amount_crc, "credit": 0, "description": description},
                {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": 0, "credit": amount_crc, "description": description},
            ])
        cur.execute("UPDATE corporate_card_transactions SET accounting_entry_id=%s WHERE id=%s", (entry_id, tx["id"]))
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
        amount_crc = _money(payload.amount_crc if payload.amount_crc is not None else statement.get("cash_payment_crc"))
        amount_usd = _money(payload.amount_usd if payload.amount_usd is not None else statement.get("cash_payment_usd"))
        exchange_rate = Decimal(str(payload.exchange_rate)) if payload.exchange_rate else _exchange_rate_for(cur, pay_date)
        total_crc = amount_crc + (amount_usd * exchange_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
        if total_crc <= 0:
            raise HTTPException(400, "No hay monto contado para liquidar")
        bank_name = payload.bank_account_name or payload.bank_account_code
        description = f"Pago tarjeta corporativa BAC {statement.get('statement_period') or ''}"
        entry_id = _post_entry(cur, statement["company_code"], pay_date, description, "CORP_CARD_SETTLEMENT", statement_id, [
            {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": total_crc, "credit": 0, "description": description},
            {"account_code": payload.bank_account_code, "account_name": bank_name, "debit": 0, "credit": total_crc, "description": description},
        ])
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
) -> int:
    code, name = (bank_account_code, bank_account_name)
    if not code:
        code, name = _default_card_payment_bank(cur)
    name = name or code
    pay_date = statement.get("payment_due_date") or _due_on_15th(statement.get("cutoff_date"), statement.get("statement_period"))
    if not pay_date:
        raise HTTPException(400, f"Estado {statement.get('id')} no tiene fecha para pago de tarjeta")
    amount_crc = _money(statement.get("cash_payment_crc"))
    amount_usd = _money(statement.get("cash_payment_usd"))
    exchange_rate = _exchange_rate_for(cur, pay_date)
    total_crc = amount_crc + (amount_usd * exchange_rate).quantize(MONEY, rounding=ROUND_HALF_UP)
    if total_crc <= 0:
        return 0
    description = f"Pago tarjeta corporativa BAC {statement.get('statement_period') or ''}"
    entry_id = _post_entry(cur, statement["company_code"], pay_date, description, "CORP_CARD_SETTLEMENT", statement["id"], [
        {"account_code": CARD_PAYABLE_CODE, "account_name": CARD_PAYABLE_NAME, "debit": total_crc, "credit": 0, "description": description},
        {"account_code": code, "account_name": name, "debit": 0, "credit": total_crc, "description": description},
    ])
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
            if closed_purchase_periods:
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
                posted += _post_daily_for_statement(cur, statement_id)
            if payload.settle_previous and statement["id"] not in latest_ids:
                pay_date = statement.get("payment_due_date") or _due_on_15th(statement.get("cutoff_date"), statement.get("statement_period"))
                settlement_period = _period_from_date(pay_date)
                if _period_is_closed(cur, company, settlement_period):
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
                    ):
                        settled += 1
            elif statement["id"] in latest_ids:
                latest_pending.append(statement)
                if not closed_purchase_periods:
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
