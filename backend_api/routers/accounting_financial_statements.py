from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from database import get_db
from routers.accounting import _ensure_accounting_professional_schema
from routers.accounting_tax import _ensure_schema as _ensure_tax_schema


router = APIRouter(
    prefix="/accounting/financial-statements",
    tags=["Accounting Financial Statements"],
)

MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(MONEY)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _to_float(value):
    return float(_money(value))


def _valid_period(value: str | None, field: str):
    if not value:
        return None
    if len(value) != 7 or value[4] != "-":
        raise HTTPException(400, f"{field} must use YYYY-MM")
    year = int(value[:4])
    month = int(value[5:7])
    if month < 1 or month > 12:
        raise HTTPException(400, f"{field} has invalid month")
    return year, month


def _period_start(value: str) -> date:
    year, month = _valid_period(value, "period")
    return date(year, month, 1)


def _next_month(value: str) -> date:
    year, month = _valid_period(value, "period")
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def _scope(period: str | None, period_from: str | None, period_to: str | None):
    if period:
        _valid_period(period, "period")
        start = _period_start(period)
        end = _next_month(period)
        label = period
    else:
        if not period_from and not period_to:
            period_to = date.today().strftime("%Y-%m")
        period_from = period_from or period_to
        period_to = period_to or period_from
        _valid_period(period_from, "period_from")
        _valid_period(period_to, "period_to")
        if period_from > period_to:
            raise HTTPException(400, "period_from cannot be greater than period_to")
        start = _period_start(period_from)
        end = _next_month(period_to)
        label = period_from if period_from == period_to else f"{period_from} to {period_to}"
    as_of = min(end - timedelta(days=1), date.today())
    return {
        "label": label,
        "period": period,
        "period_from": period_from or period,
        "period_to": period_to or period,
        "start": start,
        "end": end,
        "as_of": as_of,
    }


def _account_family(code: str | None):
    code = str(code or "").strip()
    if code.startswith("1"):
        return "ASSET"
    if code.startswith("2"):
        return "LIABILITY"
    if code.startswith("3"):
        return "EQUITY"
    if code.startswith("4"):
        return "REVENUE"
    if code.startswith(("5", "6", "7", "8", "9")):
        return "EXPENSE"
    return "OTHER"


def _natural_balance(code, debit, credit):
    family = _account_family(code)
    debit = _money(debit)
    credit = _money(credit)
    if family in {"LIABILITY", "EQUITY", "REVENUE"}:
        return credit - debit
    return debit - credit


def _line_dict(row, balance=None):
    return {
        "account_code": row.get("account_code"),
        "account_name": row.get("account_name"),
        "debit": _to_float(row.get("debit")),
        "credit": _to_float(row.get("credit")),
        "balance": _to_float(balance if balance is not None else row.get("balance")),
    }


def _fetch_account_totals(cur, where_sql, params):
    cur.execute(f"""
        SELECT
            l.account_code,
            MAX(l.account_name) AS account_name,
            COALESCE(SUM(l.debit),0) AS debit,
            COALESCE(SUM(l.credit),0) AS credit
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id = e.id
        WHERE e.workflow_status = 'POSTED'
          AND e.entry_date <= CURRENT_DATE
          AND {where_sql}
        GROUP BY l.account_code
        ORDER BY l.account_code
    """, params)
    return cur.fetchall()


def _build_trial_balance(cur, start, end):
    movement = _fetch_account_totals(cur, "e.entry_date >= %s AND e.entry_date < %s", [start, end])
    cumulative = _fetch_account_totals(cur, "e.entry_date < %s", [end])
    movement_map = {row["account_code"]: row for row in movement}
    rows = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    period_debit = Decimal("0")
    period_credit = Decimal("0")
    for row in cumulative:
        signed = _money(row["debit"]) - _money(row["credit"])
        debit_balance = signed if signed > 0 else Decimal("0")
        credit_balance = abs(signed) if signed < 0 else Decimal("0")
        movement_row = movement_map.get(row["account_code"], {})
        period_debit += _money(movement_row.get("debit"))
        period_credit += _money(movement_row.get("credit"))
        total_debit += debit_balance
        total_credit += credit_balance
        rows.append({
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "period_debit": _to_float(movement_row.get("debit")),
            "period_credit": _to_float(movement_row.get("credit")),
            "debit_balance": _to_float(debit_balance),
            "credit_balance": _to_float(credit_balance),
        })
    return {
        "rows": rows,
        "totals": {
            "period_debit": _to_float(period_debit),
            "period_credit": _to_float(period_credit),
            "debit_balance": _to_float(total_debit),
            "credit_balance": _to_float(total_credit),
            "difference": _to_float(total_debit - total_credit),
        },
    }


def _build_balance_sheet(cur, end):
    rows = _fetch_account_totals(cur, "e.entry_date < %s", [end])
    sections = {"assets": [], "liabilities": [], "equity": []}
    totals = {"assets": Decimal("0"), "liabilities": Decimal("0"), "equity": Decimal("0"), "current_result": Decimal("0")}
    for row in rows:
        family = _account_family(row["account_code"])
        balance = _natural_balance(row["account_code"], row["debit"], row["credit"])
        if family == "ASSET":
            sections["assets"].append(_line_dict(row, balance))
            totals["assets"] += balance
        elif family == "LIABILITY":
            sections["liabilities"].append(_line_dict(row, balance))
            totals["liabilities"] += balance
        elif family == "EQUITY":
            sections["equity"].append(_line_dict(row, balance))
            totals["equity"] += balance
        elif family == "REVENUE":
            totals["current_result"] += balance
        elif family == "EXPENSE":
            totals["current_result"] -= balance
    equity_plus_result = totals["equity"] + totals["current_result"]
    return {
        "sections": sections,
        "totals": {k: _to_float(v) for k, v in totals.items()} | {
            "equity_plus_result": _to_float(equity_plus_result),
            "liabilities_and_equity": _to_float(totals["liabilities"] + equity_plus_result),
            "difference": _to_float(totals["assets"] - totals["liabilities"] - equity_plus_result),
        },
    }


def _build_income_statement(cur, start, end):
    rows = _fetch_account_totals(cur, "e.entry_date >= %s AND e.entry_date < %s", [start, end])
    revenue, expenses = [], []
    total_revenue = Decimal("0")
    total_expenses = Decimal("0")
    for row in rows:
        family = _account_family(row["account_code"])
        balance = _natural_balance(row["account_code"], row["debit"], row["credit"])
        if family == "REVENUE":
            revenue.append(_line_dict(row, balance))
            total_revenue += balance
        elif family == "EXPENSE":
            expenses.append(_line_dict(row, balance))
            total_expenses += balance
    return {
        "revenue": revenue,
        "expenses": expenses,
        "totals": {
            "revenue": _to_float(total_revenue),
            "expenses": _to_float(total_expenses),
            "net_income": _to_float(total_revenue - total_expenses),
            "net_margin_pct": float(((total_revenue - total_expenses) / total_revenue * 100).quantize(MONEY)) if total_revenue else 0.0,
        },
    }


def _build_cash_flow(cur, start, end):
    cur.execute("""
        SELECT
            CASE
                WHEN e.origin IN ('CASH_APP','COLLECTIONS') THEN 'Operating inflows'
                WHEN e.origin IN ('ITP','PAYROLL') THEN 'Operating outflows'
                ELSE 'Other cash movements'
            END AS section,
            l.account_code,
            MAX(l.account_name) AS account_name,
            COALESCE(SUM(l.debit),0) AS debit,
            COALESCE(SUM(l.credit),0) AS credit
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id = e.id
        WHERE e.workflow_status = 'POSTED'
          AND e.entry_date >= %s
          AND e.entry_date < %s
          AND e.entry_date <= CURRENT_DATE
          AND (l.account_code LIKE '1.1.02%%' OR LOWER(l.account_name) LIKE '%%banco%%' OR LOWER(l.account_name) LIKE '%%bank%%')
        GROUP BY section, l.account_code
        ORDER BY section, l.account_code
    """, (start, end))
    rows = []
    totals = {}
    for row in cur.fetchall():
        movement = _money(row["debit"]) - _money(row["credit"])
        section = row["section"]
        totals[section] = totals.get(section, Decimal("0")) + movement
        rows.append(_line_dict(row, movement) | {"section": section, "cash_movement": _to_float(movement)})
    return {
        "rows": rows,
        "totals": {key: _to_float(value) for key, value in totals.items()} | {
            "net_cash_flow": _to_float(sum(totals.values(), Decimal("0")))
        },
    }


def _build_equity_changes(cur, start, end):
    cur.execute("""
        SELECT l.account_code, MAX(l.account_name) AS account_name,
               COALESCE(SUM(CASE WHEN e.entry_date < %s THEN l.credit-l.debit ELSE 0 END),0) AS opening,
               COALESCE(SUM(CASE WHEN e.entry_date >= %s AND e.entry_date < %s THEN l.credit-l.debit ELSE 0 END),0) AS movement
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id = e.id
        WHERE e.workflow_status='POSTED'
          AND e.entry_date < %s
          AND e.entry_date <= CURRENT_DATE
          AND l.account_code LIKE '3%%'
        GROUP BY l.account_code
        ORDER BY l.account_code
    """, (start, start, end, end))
    rows = []
    opening_total = Decimal("0")
    movement_total = Decimal("0")
    for row in cur.fetchall():
        opening = _money(row["opening"])
        movement = _money(row["movement"])
        opening_total += opening
        movement_total += movement
        rows.append({
            "account_code": row["account_code"],
            "account_name": row["account_name"],
            "opening": _to_float(opening),
            "movement": _to_float(movement),
            "ending": _to_float(opening + movement),
        })
    income = _build_income_statement(cur, start, end)["totals"]["net_income"]
    return {
        "rows": rows,
        "totals": {
            "opening": _to_float(opening_total),
            "equity_movement": _to_float(movement_total),
            "period_result": income,
            "ending_with_result": _to_float(opening_total + movement_total + _money(income)),
        },
    }


def _build_journal(cur, start, end, limit):
    cur.execute("""
        SELECT e.entry_date, e.id AS entry_id, e.period, e.origin, e.description,
               l.account_code, l.account_name, l.line_description, l.debit, l.credit
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id=e.id
        WHERE e.workflow_status='POSTED'
          AND e.entry_date >= %s
          AND e.entry_date < %s
          AND e.entry_date <= CURRENT_DATE
        ORDER BY e.entry_date DESC, e.id DESC, l.id ASC
        LIMIT %s
    """, (start, end, limit))
    return {"rows": [_serialize_row(row) for row in cur.fetchall()]}


def _build_general_ledger(cur, start, end, limit):
    cur.execute("""
        SELECT l.account_code, l.account_name, e.entry_date, e.id AS entry_id, e.origin,
               COALESCE(e.description,l.line_description) AS description, l.debit, l.credit
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id=e.id
        WHERE e.workflow_status='POSTED'
          AND e.entry_date >= %s
          AND e.entry_date < %s
          AND e.entry_date <= CURRENT_DATE
        ORDER BY l.account_code, e.entry_date, e.id, l.id
        LIMIT %s
    """, (start, end, limit))
    rows = []
    running = {}
    for row in cur.fetchall():
        signed = _money(row["debit"]) - _money(row["credit"])
        running[row["account_code"]] = running.get(row["account_code"], Decimal("0")) + signed
        rows.append(_serialize_row(row) | {"running_balance": _to_float(running[row["account_code"]])})
    return {"rows": rows}


def _build_aging(cur, entity_type, as_of):
    try:
        from routers.accounting_auxiliaries import _ensure_schema as _ensure_aux_schema, sync_auxiliaries
        _ensure_aux_schema(cur.connection)
        sync_auxiliaries(cur.connection)
    except Exception:
        cur.connection.rollback()
    cur.execute("""
        SELECT e.entity_code, e.entity_name, d.document_number, d.issue_date, d.due_date,
               d.currency_code, d.original_amount, d.open_amount,
               GREATEST((%s::date - COALESCE(d.due_date,d.issue_date,%s::date))::int, 0) AS days_due
        FROM accounting_auxiliary_documents d
        JOIN accounting_auxiliary_entities e ON e.id=d.entity_id
        WHERE e.entity_type=%s
          AND d.status='OPEN'
          AND COALESCE(d.open_amount,0) <> 0
        ORDER BY days_due DESC, e.entity_name, d.document_number
    """, (as_of, as_of, entity_type))
    buckets = {"current": Decimal("0"), "1_30": Decimal("0"), "31_60": Decimal("0"), "61_90": Decimal("0"), "over_90": Decimal("0")}
    rows = []
    for row in cur.fetchall():
        days = int(row["days_due"] or 0)
        amount = _money(row["open_amount"])
        bucket = "current" if days == 0 else "1_30" if days <= 30 else "31_60" if days <= 60 else "61_90" if days <= 90 else "over_90"
        buckets[bucket] += amount
        rows.append(_serialize_row(row) | {"bucket": bucket})
    return {"rows": rows, "buckets": {k: _to_float(v) for k, v in buckets.items()}, "total": _to_float(sum(buckets.values(), Decimal("0")))}


def _build_tax_summary(cur, start, end):
    _ensure_tax_schema(cur.connection)
    cur.execute("""
        SELECT direction,
               COALESCE(SUM(subtotal),0) AS subtotal,
               COALESCE(SUM(tax_amount),0) AS tax,
               COALESCE(SUM(total),0) AS total,
               COUNT(*) AS documents
        FROM tax_electronic_documents
        WHERE issue_datetime >= %s
          AND issue_datetime < %s
        GROUP BY direction
    """, (start, end))
    docs = {row["direction"]: row for row in cur.fetchall()}
    sales_tax = _money((docs.get("SALE") or {}).get("tax"))
    purchase_tax = _money((docs.get("PURCHASE") or {}).get("tax"))
    cur.execute("""
        SELECT l.account_code, MAX(l.account_name) AS account_name,
               COALESCE(SUM(l.debit),0) AS debit,
               COALESCE(SUM(l.credit),0) AS credit
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id=e.id
        WHERE e.workflow_status='POSTED'
          AND e.entry_date >= %s
          AND e.entry_date < %s
          AND e.entry_date <= CURRENT_DATE
          AND (LOWER(l.account_name) LIKE '%%iva%%' OR LOWER(l.account_name) LIKE '%%retenc%%' OR l.account_code LIKE '2.1.02%%' OR l.account_code LIKE '2.1.03%%' OR l.account_code='1.1.13.99')
        GROUP BY l.account_code
        ORDER BY l.account_code
    """, (start, end))
    tax_lines = []
    iva_gl = Decimal("0")
    retentions = Decimal("0")
    for row in cur.fetchall():
        balance = _natural_balance(row["account_code"], row["debit"], row["credit"])
        name = (row["account_name"] or "").lower()
        if "retenc" in name or str(row["account_code"]).startswith("2.1.03"):
            retentions += balance
        else:
            iva_gl += balance
        tax_lines.append(_line_dict(row, balance))
    return {
        "documents": {
            "sales": _serialize_row(docs.get("SALE") or {}),
            "purchases": _serialize_row(docs.get("PURCHASE") or {}),
        },
        "iva": {
            "debit_fiscal": _to_float(sales_tax),
            "credit_fiscal": _to_float(purchase_tax),
            "net_documental": _to_float(sales_tax - purchase_tax),
            "net_accounting": _to_float(iva_gl),
            "difference": _to_float((sales_tax - purchase_tax) - iva_gl),
        },
        "retentions": {"balance": _to_float(retentions)},
        "accounts": tax_lines,
    }


def _build_profitability(cur, start, end):
    cur.execute("""
        SELECT
            COALESCE(NULLIF(TRIM(cliente),''),'SIN CLIENTE') AS client,
            COALESCE(NULLIF(TRIM(operacion),''),'SIN SERVICIO') AS service,
            COUNT(*) AS services_count,
            COALESCE(SUM(COALESCE(honorarios,0)),0) AS revenue,
            COALESCE(SUM(COALESCE(costo_operativo,0)+COALESCE(costo_tarjetas,0)),0) AS direct_cost,
            COALESCE(SUM(COALESCE(honorarios,0)-COALESCE(costo_operativo,0)-COALESCE(costo_tarjetas,0)),0) AS gross_profit
        FROM servicios
        WHERE COALESCE(fecha_inicio, fecha_fin, CURRENT_DATE) >= %s
          AND COALESCE(fecha_inicio, fecha_fin, CURRENT_DATE) < %s
        GROUP BY client, service
        ORDER BY gross_profit DESC, revenue DESC
    """, (start, end))
    rows = []
    totals = {"revenue": Decimal("0"), "direct_cost": Decimal("0"), "gross_profit": Decimal("0")}
    for row in cur.fetchall():
        revenue = _money(row["revenue"])
        direct_cost = _money(row["direct_cost"])
        profit = _money(row["gross_profit"])
        totals["revenue"] += revenue
        totals["direct_cost"] += direct_cost
        totals["gross_profit"] += profit
        rows.append(_serialize_row(row) | {
            "margin_pct": float((profit / revenue * 100).quantize(MONEY)) if revenue else 0.0
        })
    return {
        "rows": rows,
        "totals": {
            "revenue": _to_float(totals["revenue"]),
            "direct_cost": _to_float(totals["direct_cost"]),
            "gross_profit": _to_float(totals["gross_profit"]),
            "margin_pct": float((totals["gross_profit"] / totals["revenue"] * 100).quantize(MONEY)) if totals["revenue"] else 0.0,
        },
    }


def _serialize_row(row):
    result = {}
    for key, value in dict(row or {}).items():
        if isinstance(value, Decimal):
            result[key] = _to_float(value)
        elif hasattr(value, "isoformat"):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


@router.get("/complete")
def complete_financial_statements(
    period: str | None = None,
    period_from: str | None = None,
    period_to: str | None = None,
    limit: int = Query(1000, ge=50, le=5000),
    conn=Depends(get_db),
):
    _ensure_accounting_professional_schema(conn)
    scope = _scope(period, period_from, period_to)
    start = scope["start"]
    end = scope["end"]
    as_of = scope["as_of"]
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        trial_balance = _build_trial_balance(cur, start, end)
        balance_sheet = _build_balance_sheet(cur, end)
        income_statement = _build_income_statement(cur, start, end)
        cash_flow = _build_cash_flow(cur, start, end)
        equity_changes = _build_equity_changes(cur, start, end)
        journal = _build_journal(cur, start, end, limit)
        general_ledger = _build_general_ledger(cur, start, end, limit)
        aging_ar = _build_aging(cur, "CUSTOMER", as_of)
        aging_ap = _build_aging(cur, "SUPPLIER", as_of)
        tax_summary = _build_tax_summary(cur, start, end)
        profitability = _build_profitability(cur, start, end)
    return {
        "scope": {
            "label": scope["label"],
            "period_from": scope["period_from"],
            "period_to": scope["period_to"],
            "start": start.isoformat(),
            "end_exclusive": end.isoformat(),
            "as_of": as_of.isoformat(),
            "basis": "POSTED accounting entries only; future entry dates excluded.",
        },
        "balance_sheet": balance_sheet,
        "income_statement": income_statement,
        "cash_flow": cash_flow,
        "equity_changes": equity_changes,
        "trial_balance": trial_balance,
        "general_ledger": general_ledger,
        "journal": journal,
        "aging_ar": aging_ar,
        "aging_ap": aging_ap,
        "tax_summary": tax_summary,
        "profitability": profitability,
    }
