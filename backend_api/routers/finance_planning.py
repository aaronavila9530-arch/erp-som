from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Header, Query
from psycopg2.extras import RealDictCursor

from database import get_db
from routers.accounting_advanced import _ensure_schema as ensure_accounting_advanced_schema
from services.tenanting import company_code as normalize_company_code


router = APIRouter(prefix="/finance/planning", tags=["Finance - Planning"])
MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(MONEY)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _float(value) -> float:
    return float(_money(value))


def _period_bounds(period: str) -> tuple[date, date]:
    text = str(period or "").strip()
    if len(text) != 7 or text[4] != "-":
        today = date.today()
        text = today.strftime("%Y-%m")
    year = int(text[:4])
    month = int(text[5:7])
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def _add_months(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 + int(months)
    return date(month_index // 12, month_index % 12 + 1, 1)


def _serialize(row):
    out = {}
    for key, value in dict(row or {}).items():
        if isinstance(value, Decimal):
            out[key] = _float(value)
        elif hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def _company(x_company_code: str | None) -> str:
    return normalize_company_code(header_value=x_company_code)


@router.get("/summary")
def finance_planning_summary(
    period: str | None = Query(None),
    months: int = Query(4, ge=1, le=18),
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    """
    RECONIS-style planning summary for SOM Finance.

    It intentionally reads only when the user presses Buscar in each UI.  The
    endpoint consolidates ITP, payment application, Accounting, projects and
    savings/goals so web, desktop and Android make decisions from one source.
    """
    company = _company(x_company_code)
    period = str(period or date.today().strftime("%Y-%m")).strip()
    start, month_end = _period_bounds(period)
    horizon_end = _add_months(start, months)
    today = date.today()

    ensure_accounting_advanced_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT to_regclass('public.payment_obligations') AS table_name")
        has_itp = bool((cur.fetchone() or {}).get("table_name"))
        obligation_buckets = []
        obligations = []
        if has_itp:
            cur.execute("""
                SELECT
                    COALESCE(currency, 'CRC') AS currency,
                    CASE
                        WHEN due_date IS NOT NULL AND due_date < %s THEN 'OVERDUE'
                        WHEN due_date IS NULL THEN 'SIN_FECHA'
                        WHEN due_date < %s THEN 'ESTE_MES'
                        WHEN due_date < %s THEN 'HORIZONTE'
                        ELSE 'FUTURO'
                    END AS bucket,
                    COUNT(*) AS count,
                    COALESCE(SUM(balance), 0) AS amount
                FROM payment_obligations
                WHERE company_code=%s
                  AND COALESCE(active, TRUE)=TRUE
                  AND COALESCE(record_type, 'OBLIGATION')='OBLIGATION'
                  AND status IN ('PENDING','PARTIAL')
                  AND (due_date IS NULL OR due_date < %s)
                GROUP BY COALESCE(currency, 'CRC'), bucket
                ORDER BY currency, bucket
            """, (today, month_end, horizon_end, company, horizon_end))
            obligation_buckets = [_serialize(row) for row in cur.fetchall()]

            cur.execute("""
                SELECT id, payee_name, obligation_type, reference, due_date, currency, total,
                       balance, status, origin, payment_method, payment_bank_account_code,
                       vessel, country, operation
                FROM payment_obligations
                WHERE company_code=%s
                  AND COALESCE(active, TRUE)=TRUE
                  AND COALESCE(record_type, 'OBLIGATION')='OBLIGATION'
                  AND status IN ('PENDING','PARTIAL')
                  AND (due_date IS NULL OR due_date < %s)
                ORDER BY due_date NULLS LAST, balance DESC
                LIMIT 120
            """, (company, horizon_end))
            obligations = [_serialize(row) for row in cur.fetchall()]

        cur.execute("SELECT to_regclass('public.itp_biweekly_payment_lines') AS table_name")
        has_biweekly = bool((cur.fetchone() or {}).get("table_name"))
        applied_payments = []
        if has_biweekly:
            cur.execute("""
                SELECT COALESCE(currency, 'CRC') AS currency,
                       COALESCE(SUM(amount), 0) AS amount,
                       COUNT(*) AS count
                FROM itp_biweekly_payment_lines
                WHERE company_code=%s
                  AND payment_date >= %s
                  AND payment_date < %s
                GROUP BY COALESCE(currency, 'CRC')
                ORDER BY currency
            """, (company, start, horizon_end))
            applied_payments = [_serialize(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT e.period, COALESCE(l.account_code, '') AS account_code,
                   COALESCE(MAX(l.account_name), l.account_code) AS account_name,
                   COALESCE(SUM(l.debit - l.credit), 0) AS actual_amount
            FROM accounting_entries e
            JOIN accounting_lines l ON l.entry_id=e.id
            WHERE e.company_code=%s
              AND e.workflow_status='POSTED'
              AND e.entry_date >= %s
              AND e.entry_date < %s
              AND l.account_code LIKE '5%%'
            GROUP BY e.period, l.account_code
            ORDER BY actual_amount DESC
            LIMIT 80
        """, (company, start, horizon_end))
        expenses = [_serialize(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT b.*,
                   COALESCE(a.account_name, b.account_code) AS account_name,
                   COALESCE(c.contrib_amount, 0) AS contributed_amount,
                   COALESCE(b.current_amount, 0) + COALESCE(c.contrib_amount, 0) AS progress_amount,
                   CASE
                     WHEN COALESCE(NULLIF(b.target_amount, 0), b.budget_amount, 0)=0 THEN 0
                     ELSE ROUND(((COALESCE(b.current_amount, 0) + COALESCE(c.contrib_amount, 0))
                          / COALESCE(NULLIF(b.target_amount, 0), b.budget_amount, 1))*100, 2)
                   END AS progress_pct
            FROM accounting_budgets b
            LEFT JOIN accounting_accounts a ON a.account_code=b.account_code
            LEFT JOIN (
                SELECT budget_id, SUM(amount) AS contrib_amount
                FROM accounting_budget_contributions
                WHERE company_code=%s
                GROUP BY budget_id
            ) c ON c.budget_id=b.id
            WHERE b.company_code=%s
              AND UPPER(COALESCE(b.status, 'ACTIVE')) IN ('ACTIVE','PAUSED')
              AND (
                b.period >= %s
                OR COALESCE(b.target_date, (b.period || '-01')::date) >= %s
              )
            ORDER BY COALESCE(b.target_date, (b.period || '-01')::date), b.purpose, b.name
            LIMIT 120
        """, (company, company, period, start))
        goals = [_serialize(row) for row in cur.fetchall()]

        cur.execute("SELECT to_regclass('public.proyectos_calculo') AS table_name")
        has_projects = bool((cur.fetchone() or {}).get("table_name"))
        projects = []
        if has_projects:
            cur.execute("""
                SELECT nombre_proyecto, moneda, tiempo,
                       COUNT(*) AS personas,
                       COALESCE(SUM(total_honorarios),0) AS total_honorarios,
                       COALESCE(MAX(total_gastos),0) AS total_gastos,
                       COALESCE(MAX(precio),0) AS precio,
                       COALESCE(MAX(utilidad),0) AS utilidad,
                       MAX(creado_el) AS creado_el
                FROM proyectos_calculo
                GROUP BY nombre_proyecto, moneda, tiempo
                ORDER BY creado_el DESC NULLS LAST
                LIMIT 80
            """)
            projects = [_serialize(row) for row in cur.fetchall()]

    total_pending = {}
    for row in obligation_buckets:
        cur_code = row.get("currency") or "CRC"
        total_pending[cur_code] = _float(_money(total_pending.get(cur_code)) + _money(row.get("amount")))

    return {
        "period": period,
        "company_code": company,
        "horizon_months": months,
        "as_of": today.isoformat(),
        "totals": {
            "pending_by_currency": total_pending,
            "obligation_lines": len(obligations),
            "goals_active": len(goals),
            "projects": len(projects),
        },
        "obligation_buckets": obligation_buckets,
        "obligations": obligations,
        "applied_payments": applied_payments,
        "expenses": expenses,
        "goals": goals,
        "projects": projects,
        "decision_notes": [
            "Priorice OVERDUE y vencimientos dentro del mes antes de comprometer nuevos pagos.",
            "Use SAVINGS y GOAL para reservar caja antes de los primeros meses del siguiente FY.",
            "Compare proyectos con utilidad positiva contra obligaciones ITP para calendarizar compromisos.",
        ],
    }
