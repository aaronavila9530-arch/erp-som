from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal


def _norm(value) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def _tokens(value) -> set[str]:
    return {token for token in _norm(value).split() if len(token) >= 3}


SURVEYOR_ALIASES = {
    "MAGALLY BARQUERO": (
        "MAGALLY BARQUERO",
        "SHARON OROCU",
        "OROCU BARQUERO SHARON STACEY",
        "SHARON STACEY BARQUERO SANCHEZ",
        "SHARON STACEY BARQUERO",
    ),
}


def _identity_keys(value) -> set[str]:
    text = _norm(value)
    tokens = _tokens(value)
    keys = {text} if text else set()
    for canonical, aliases in SURVEYOR_ALIASES.items():
        for alias in aliases:
            alias_text = _norm(alias)
            alias_tokens = _tokens(alias)
            if not alias_text:
                continue
            if alias_text in text or text in alias_text or (alias_tokens and alias_tokens <= tokens):
                keys.add(_norm(canonical))
    return keys


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except Exception:
        return None


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def reconcile_surveyor_invoice_obligations(
    cur,
    company_code: str,
    issuer_name: str | None,
    issue_date,
    reference: str | None = None,
    invoice_obligation_id: int | None = None,
    window_days_before: int = 90,
    window_days_after: int = 45,
) -> list[int]:
    """Close preliminary service surveyor obligations superseded by an e-invoice.

    Services can create preliminary payables from the surveyor assignment, while
    the real Hacienda XML later creates the payable with the final legal amount.
    This function prevents both from staying open.
    """
    issuer_tokens = _tokens(issuer_name)
    issuer_keys = _identity_keys(issuer_name)
    if not issuer_tokens and not issuer_keys:
        return []

    invoice_date = _as_date(issue_date)
    if not invoice_date:
        return []

    cur.execute(
        """
        SELECT id, payee_name, issue_date, due_date, total, balance, service_id, reference, status
        FROM payment_obligations
        WHERE company_code=%s
          AND COALESCE(active, TRUE)=TRUE
          AND origin='SERVICIOS'
          AND payee_type='SURVEYOR'
          AND obligation_type='SURVEYOR_FEE'
          AND status IN ('PENDING','PARTIAL','PAID')
          AND COALESCE(issue_date, due_date, %s::date)
                BETWEEN (%s::date - (%s || ' days')::interval)
                    AND (%s::date + (%s || ' days')::interval)
        FOR UPDATE
        """,
        (company_code, invoice_date, invoice_date, int(window_days_before), invoice_date, int(window_days_after)),
    )
    matched_ids: list[int] = []
    for row in cur.fetchall() or []:
        payee_tokens = _tokens(row.get("payee_name"))
        payee_keys = _identity_keys(row.get("payee_name"))
        if not payee_tokens and not payee_keys:
            continue
        alias_match = bool(issuer_keys & payee_keys)
        if row.get("status") == "PAID" and not alias_match:
            continue
        if alias_match:
            matched_ids.append(int(row["id"]))
            continue
        overlap = issuer_tokens & payee_tokens
        short_name_match = len(overlap) >= 1 and min(len(issuer_tokens), len(payee_tokens)) == 1
        full_name_match = len(overlap) >= 2
        if full_name_match or short_name_match:
            matched_ids.append(int(row["id"]))

    if not matched_ids:
        return []

    note = (
        "Reemplazada por factura electronica del surveyor"
        + (f" Ref {reference}" if reference else "")
        + (f" ITP {invoice_obligation_id}" if invoice_obligation_id else "")
        + "."
    )
    cur.execute(
        """
        UPDATE payment_obligations
           SET balance=0,
               status='REPLACED',
               active=FALSE,
               notes=TRIM(BOTH E'\n' FROM CONCAT_WS(E'\n', NULLIF(notes,''), %s)),
               updated_at=NOW()
         WHERE id=ANY(%s)
        """,
        (note, matched_ids),
    )
    return matched_ids
