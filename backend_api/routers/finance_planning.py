from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from psycopg2.extras import Json, RealDictCursor

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


def _fortnight_bucket(value: date | None) -> tuple[str, str]:
    day = value or date.today()
    period = day.strftime("%Y-%m")
    half = "Q1" if day.day <= 15 else "Q2"
    label = f"{period} · Quincena 1" if half == "Q1" else f"{period} · Quincena 2"
    return f"{period}-{half}", label


def _month_key(value: date | None) -> str:
    return (value or date.today()).strftime("%Y-%m")


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


def _parse_date(value, fallback: date | None = None) -> date:
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text)
    except Exception:
        return fallback or date.today()


def _account_currency(row: dict | None) -> str:
    account = row or {}
    currency = str(account.get("currency_code") or "").upper()
    if currency in {"CRC", "USD"}:
        return currency
    name = str(account.get("account_name") or "").upper()
    return "USD" if "USD" in name or "DOLAR" in name else "CRC"


def _exchange_rate(cur, value_date: date) -> Decimal:
    cur.execute("SELECT to_regclass('public.exchange_rate') AS table_name")
    row = cur.fetchone()
    table_name = (row or {}).get("table_name") if isinstance(row, dict) else (row[0] if row else None)
    if not table_name:
        return Decimal("1.00")
    cur.execute(
        """
        SELECT rate
        FROM exchange_rate
        WHERE rate_date <= %s
        ORDER BY rate_date DESC
        LIMIT 1
        """,
        (value_date,),
    )
    rate_row = cur.fetchone()
    raw = (rate_row or {}).get("rate") if isinstance(rate_row, dict) else (rate_row[0] if rate_row else None)
    rate = _money(raw or 1)
    return rate if rate > 0 else Decimal("1.00")


def _assert_period_open(cur, company: str, period: str):
    cur.execute("SELECT status FROM accounting_period_controls WHERE company_code=%s AND period=%s", (company, period))
    row = cur.fetchone()
    status = str(((row or {}).get("status") if isinstance(row, dict) else (row[0] if row else "OPEN")) or "OPEN").upper()
    if status == "CLOSED":
        raise HTTPException(409, f"Accounting period {period} is closed")


def _ensure_bank_adjustment_account(cur, user: str) -> tuple[str, str]:
    code = "1.1.02.98"
    name = "Diferencias bancarias por conciliar"
    cur.execute("SELECT account_code, account_name FROM accounting_accounts WHERE account_code=%s", (code,))
    row = cur.fetchone()
    if row:
        return row["account_code"], row["account_name"]
    cur.execute("""
        INSERT INTO accounting_accounts(
            account_code, account_name, account_type, normal_balance, account_level,
            parent_account, accepts_posting, requires_third_party, requires_cost_center,
            currency_code, financial_statement_line, tax_mapping, active, created_by, updated_by
        )
        VALUES(%s,%s,'ASSET','DEBIT',4,'1.1.02',TRUE,FALSE,FALSE,NULL,'Cash and banks','BANK_RECON',TRUE,%s,%s)
        ON CONFLICT (account_code) DO UPDATE
        SET account_name=EXCLUDED.account_name,
            accepts_posting=TRUE,
            active=TRUE,
            updated_by=EXCLUDED.updated_by,
            updated_at=NOW()
        RETURNING account_code, account_name
    """, (code, name, user, user))
    created = cur.fetchone()
    return created["account_code"], created["account_name"]


def _bank_balance_at(cur, company: str, account_code: str, value_date: date) -> tuple[dict, Decimal]:
    cur.execute("""
        SELECT *
        FROM accounting_accounts
        WHERE account_code=%s
          AND COALESCE(active, TRUE)=TRUE
          AND COALESCE(accepts_posting, TRUE)=TRUE
    """, (account_code,))
    account = cur.fetchone()
    if not account:
        raise HTTPException(404, "Cuenta bancaria no encontrada o no posteable")
    if not str(account["account_code"]).startswith("1.1.02."):
        raise HTTPException(400, "Solo se pueden ajustar cuentas bancarias bajo 1.1.02")
    currency = _account_currency(account)
    cur.execute("""
        SELECT COALESCE(SUM(
            CASE
                WHEN e.id IS NULL THEN 0
                WHEN %s='USD'
                THEN CASE
                    WHEN e.currency_code='USD' AND COALESCE(NULLIF(e.exchange_rate,0),0) > 0
                    THEN (COALESCE(l.debit,0)-COALESCE(l.credit,0)) / e.exchange_rate
                    ELSE COALESCE(l.debit,0)-COALESCE(l.credit,0)
                END
                ELSE COALESCE(l.debit,0)-COALESCE(l.credit,0)
            END
        ), 0) AS current_amount
        FROM accounting_lines l
        JOIN accounting_entries e ON e.id=l.entry_id
        WHERE l.account_code=%s
          AND e.company_code=%s
          AND e.workflow_status='POSTED'
          AND COALESCE(e.reversed, FALSE)=FALSE
          AND e.entry_date <= %s
    """, (currency, account_code, company, value_date))
    row = cur.fetchone() or {}
    raw = row.get("current_amount") if isinstance(row, dict) else row[0]
    return account, _money(raw)


def _ensure_planning_schema(conn):
    ensure_accounting_advanced_schema(conn)
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS finance_planning_projects (
                id BIGSERIAL PRIMARY KEY,
                company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
                project_code TEXT,
                name TEXT NOT NULL,
                client_name TEXT,
                description TEXT,
                owner TEXT,
                start_date DATE,
                target_date DATE,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
                expected_revenue NUMERIC(18,2) NOT NULL DEFAULT 0,
                expected_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
                expected_savings NUMERIC(18,2) NOT NULL DEFAULT 0,
                monthly_savings NUMERIC(18,2) NOT NULL DEFAULT 0,
                probability_pct NUMERIC(8,2) NOT NULL DEFAULT 100,
                status TEXT NOT NULL DEFAULT 'PLANNED',
                priority TEXT NOT NULL DEFAULT 'MEDIUM',
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_finance_planning_projects_company ON finance_planning_projects(company_code, status, target_date)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS finance_planning_project_schedule (
                id BIGSERIAL PRIMARY KEY,
                project_id BIGINT REFERENCES finance_planning_projects(id) ON DELETE CASCADE,
                company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
                due_date DATE NOT NULL,
                concept TEXT NOT NULL,
                direction TEXT NOT NULL DEFAULT 'INFLOW',
                currency_code VARCHAR(3) NOT NULL DEFAULT 'USD',
                amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'PLANNED',
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_finance_planning_schedule_company ON finance_planning_project_schedule(company_code, due_date, status)")
    conn.commit()


def _project_payload(payload: dict, company: str, user: str | None = None) -> dict:
    name = str((payload or {}).get("name") or (payload or {}).get("nombre_proyecto") or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    status = str((payload or {}).get("status") or "PLANNED").strip().upper()
    if status not in {"PLANNED", "ACTIVE", "PAUSED", "DONE", "CANCELLED"}:
        raise HTTPException(400, "status must be PLANNED, ACTIVE, PAUSED, DONE or CANCELLED")
    priority = str((payload or {}).get("priority") or "MEDIUM").strip().upper()
    if priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise HTTPException(400, "priority must be LOW, MEDIUM, HIGH or CRITICAL")
    return {
        "company_code": company,
        "project_code": (payload or {}).get("project_code") or None,
        "name": name,
        "client_name": (payload or {}).get("client_name") or (payload or {}).get("cliente") or None,
        "description": (payload or {}).get("description") or None,
        "owner": (payload or {}).get("owner") or None,
        "start_date": (payload or {}).get("start_date") or None,
        "target_date": (payload or {}).get("target_date") or None,
        "currency_code": str((payload or {}).get("currency_code") or (payload or {}).get("moneda") or "USD").upper()[:3],
        "expected_revenue": _money((payload or {}).get("expected_revenue") or (payload or {}).get("precio")),
        "expected_cost": _money((payload or {}).get("expected_cost") or (payload or {}).get("total_gastos")),
        "expected_savings": _money((payload or {}).get("expected_savings")),
        "monthly_savings": _money((payload or {}).get("monthly_savings")),
        "probability_pct": _money((payload or {}).get("probability_pct") or 100),
        "status": status,
        "priority": priority,
        "notes": (payload or {}).get("notes") or (payload or {}).get("comentarios") or None,
        "created_by": user or (payload or {}).get("created_by") or "ERP_USER",
    }


@router.get("/projects")
def list_planning_projects(
    status: str = "ALL",
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_planning_schema(conn)
    company = _company(x_company_code)
    filters = ["company_code=%s"]
    params = [company]
    status = str(status or "ALL").upper()
    if status != "ALL":
        filters.append("status=%s")
        params.append(status)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            f"""
            SELECT *,
                   expected_revenue - expected_cost AS expected_profit,
                   CASE WHEN expected_revenue=0 THEN 0
                        ELSE ROUND(((expected_revenue - expected_cost) / expected_revenue) * 100, 2)
                   END AS expected_margin_pct,
                   ROUND((expected_revenue - expected_cost) * (probability_pct / 100.0), 2) AS weighted_profit
            FROM finance_planning_projects
            WHERE {" AND ".join(filters)}
            ORDER BY target_date NULLS LAST, priority DESC, id DESC
            """,
            params,
        )
        return {"data": [_serialize(row) for row in cur.fetchall()]}


@router.post("/projects")
def create_planning_project(
    payload: dict,
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    x_user: str | None = Header(None, alias="X-User"),
):
    _ensure_planning_schema(conn)
    company = _company(x_company_code)
    data = _project_payload(payload, company, x_user)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO finance_planning_projects(
                company_code, project_code, name, client_name, description, owner,
                start_date, target_date, currency_code, expected_revenue, expected_cost,
                expected_savings, monthly_savings, probability_pct, status, priority,
                notes, created_by
            )
            VALUES(
                %(company_code)s, %(project_code)s, %(name)s, %(client_name)s, %(description)s, %(owner)s,
                %(start_date)s, %(target_date)s, %(currency_code)s, %(expected_revenue)s, %(expected_cost)s,
                %(expected_savings)s, %(monthly_savings)s, %(probability_pct)s, %(status)s, %(priority)s,
                %(notes)s, %(created_by)s
            )
            RETURNING *
        """, data)
        row = cur.fetchone()
        _replace_project_schedule(cur, row["id"], company, data, payload.get("schedule") or [])
    conn.commit()
    return {"status": "ok", "project": _serialize(row)}


@router.put("/projects/{project_id}")
def update_planning_project(
    project_id: int,
    payload: dict,
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    x_user: str | None = Header(None, alias="X-User"),
):
    _ensure_planning_schema(conn)
    company = _company(x_company_code)
    data = _project_payload(payload, company, x_user)
    data["id"] = project_id
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id FROM finance_planning_projects WHERE id=%s AND company_code=%s", (project_id, company))
        if not cur.fetchone():
            raise HTTPException(404, "Project not found")
        cur.execute("""
            UPDATE finance_planning_projects
            SET project_code=%(project_code)s, name=%(name)s, client_name=%(client_name)s,
                description=%(description)s, owner=%(owner)s, start_date=%(start_date)s,
                target_date=%(target_date)s, currency_code=%(currency_code)s,
                expected_revenue=%(expected_revenue)s, expected_cost=%(expected_cost)s,
                expected_savings=%(expected_savings)s, monthly_savings=%(monthly_savings)s,
                probability_pct=%(probability_pct)s, status=%(status)s, priority=%(priority)s,
                notes=%(notes)s, updated_at=NOW()
            WHERE id=%(id)s AND company_code=%(company_code)s
            RETURNING *
        """, data)
        row = cur.fetchone()
        _replace_project_schedule(cur, row["id"], company, data, payload.get("schedule") or [])
    conn.commit()
    return {"status": "ok", "project": _serialize(row)}


@router.delete("/projects/{project_id}")
def delete_planning_project(
    project_id: int,
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_planning_schema(conn)
    company = _company(x_company_code)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("DELETE FROM finance_planning_projects WHERE id=%s AND company_code=%s RETURNING *", (project_id, company))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Project not found")
    conn.commit()
    return {"status": "ok", "deleted": project_id}


@router.post("/bank-adjustment")
def create_bank_balance_adjustment(
    payload: dict = Body(...),
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    x_user: str | None = Header(None, alias="X-User"),
):
    _ensure_planning_schema(conn)
    company = _company(x_company_code)
    user = str(x_user or payload.get("created_by") or "WEB").strip() or "WEB"
    account_code = str(payload.get("account_code") or "").strip()
    if not account_code:
        raise HTTPException(400, "account_code is required")
    real_amount = _money(payload.get("real_amount"))
    adjustment_date = _parse_date(payload.get("adjustment_date"), date.today())
    period = adjustment_date.strftime("%Y-%m")
    reason = str(payload.get("reason") or "").strip()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        _assert_period_open(cur, company, period)
        account, current_amount = _bank_balance_at(cur, company, account_code, adjustment_date)
        currency = _account_currency(account)
        difference = (real_amount - current_amount).quantize(MONEY)
        if abs(difference) < MONEY:
            return {
                "status": "no_change",
                "account_code": account_code,
                "current_amount": _float(current_amount),
                "real_amount": _float(real_amount),
                "difference": 0.0,
            }
        clearing_code, clearing_name = _ensure_bank_adjustment_account(cur, user)
        exchange_rate = _exchange_rate(cur, adjustment_date) if currency == "USD" else Decimal("1.00")
        amount_crc = (abs(difference) * exchange_rate).quantize(MONEY)
        description = f"Ajuste saldo real banco {account['account_name']}"
        metadata = {
            "source": "finance_planning",
            "event_type": "bank_balance_adjustment",
            "account_code": account_code,
            "account_name": account["account_name"],
            "account_currency": currency,
            "current_amount": str(current_amount),
            "real_amount": str(real_amount),
            "difference": str(difference),
            "reason": reason,
        }
        cur.execute("""
            INSERT INTO accounting_entries(
                entry_date, period, description, origin, origin_id, created_by,
                workflow_status, company_code, currency_code, exchange_rate,
                posting_rule_code, posting_metadata, posted_by, posted_at
            )
            VALUES(%s,%s,%s,'PLN_BANK_ADJUSTMENT',NULL,%s,'POSTED',%s,%s,%s,%s,%s,%s,NOW())
            RETURNING id
        """, (
            adjustment_date, period, description, user, company, currency, exchange_rate,
            "PLN_BANK_ADJUSTMENT", Json(metadata), user,
        ))
        entry = cur.fetchone()
        bank_name = account["account_name"]
        detail = (
            f"Saldo real {currency} {real_amount:,.2f}; contable {current_amount:,.2f}; "
            f"diferencia {difference:,.2f}. {reason}".strip()
        )
        if difference > 0:
            lines = [
                (account_code, bank_name, amount_crc, Decimal("0.00")),
                (clearing_code, clearing_name, Decimal("0.00"), amount_crc),
            ]
        else:
            lines = [
                (clearing_code, clearing_name, amount_crc, Decimal("0.00")),
                (account_code, bank_name, Decimal("0.00"), amount_crc),
            ]
        for line_code, line_name, debit, credit in lines:
            cur.execute("""
                INSERT INTO accounting_lines(
                    entry_id, account_code, account_name, debit, credit, line_description
                )
                VALUES(%s,%s,%s,%s,%s,%s)
            """, (entry["id"], line_code, line_name, debit, credit, detail))
    conn.commit()
    return {
        "status": "ok",
        "entry_id": entry["id"],
        "account_code": account_code,
        "currency_code": currency,
        "current_amount": _float(current_amount),
        "real_amount": _float(real_amount),
        "difference": _float(difference),
        "exchange_rate": _float(exchange_rate),
        "amount_posted_crc": _float(amount_crc),
    }


def _replace_project_schedule(cur, project_id: int, company: str, project: dict, schedule: list):
    cur.execute("DELETE FROM finance_planning_project_schedule WHERE project_id=%s AND company_code=%s", (project_id, company))
    rows = schedule if isinstance(schedule, list) and schedule else []
    if not rows:
        target = project.get("target_date")
        if project.get("expected_revenue"):
            rows.append({"due_date": target, "concept": "Ingreso esperado", "direction": "INFLOW", "amount": project.get("expected_revenue")})
        if project.get("expected_cost"):
            rows.append({"due_date": target, "concept": "Costo esperado", "direction": "OUTFLOW", "amount": project.get("expected_cost")})
        if project.get("monthly_savings"):
            rows.append({"due_date": target, "concept": "Ahorro mensual sugerido", "direction": "SAVING", "amount": project.get("monthly_savings")})
    for item in rows:
        due_date = item.get("due_date") or project.get("target_date") or date.today().isoformat()
        direction = str(item.get("direction") or "INFLOW").upper()
        if direction not in {"INFLOW", "OUTFLOW", "SAVING"}:
            direction = "INFLOW"
        cur.execute("""
            INSERT INTO finance_planning_project_schedule(
                project_id, company_code, due_date, concept, direction, currency_code,
                amount, status, notes
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            project_id, company, due_date, item.get("concept") or "Cronograma",
            direction, str(item.get("currency_code") or project.get("currency_code") or "USD").upper()[:3],
            _money(item.get("amount")), str(item.get("status") or "PLANNED").upper(),
            item.get("notes"),
        ))


@router.get("/summary")
def finance_planning_summary(
    period: str | None = Query(None),
    months: int = Query(4, ge=1, le=18),
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    """
    Enterprise planning summary for SOM Finance.

    It intentionally reads only when the user presses Buscar in each UI.  The
    endpoint consolidates ITP, payment application, Accounting, projects and
    savings/goals so web, desktop and Android make decisions from one source.
    """
    company = _company(x_company_code)
    period = str(period or date.today().strftime("%Y-%m")).strip()
    start, month_end = _period_bounds(period)
    horizon_end = _add_months(start, months)
    today = date.today()

    _ensure_planning_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT to_regclass('public.payment_obligations') AS table_name")
        has_itp = bool((cur.fetchone() or {}).get("table_name"))
        cur.execute("SELECT to_regclass('public.itp_biweekly_payment_lines') AS table_name")
        has_biweekly = bool((cur.fetchone() or {}).get("table_name"))
        obligation_buckets = []
        obligations = []
        if has_itp:
            paid_cte = """
                WITH paid AS (
                    SELECT
                        COALESCE(obligation_id, 0) AS obligation_id,
                        NULLIF(BTRIM(COALESCE(reference, '')), '') AS reference,
                        COALESCE(SUM(amount), 0) AS paid_amount
                    FROM itp_biweekly_payment_lines
                    WHERE COALESCE(accounting_entry_id, 0) > 0
                      AND COALESCE(amount, 0) > 0
                    GROUP BY COALESCE(obligation_id, 0), NULLIF(BTRIM(COALESCE(reference, '')), '')
                ),
                obligations_effective AS (
                    SELECT po.*,
                           LEAST(
                               COALESCE(po.balance, 0),
                               GREATEST(COALESCE(po.total, po.balance, 0) - COALESCE((
                                   SELECT SUM(paid_amount)
                                   FROM paid p
                                   WHERE p.obligation_id = po.id
                                      OR (
                                          p.reference IS NOT NULL
                                          AND p.reference = NULLIF(BTRIM(COALESCE(po.reference, '')), '')
                                      )
                               ), 0), 0)
                           ) AS effective_balance
                    FROM payment_obligations po
                )
            """ if has_biweekly else """
                WITH obligations_effective AS (
                    SELECT po.*, COALESCE(po.balance, 0) AS effective_balance
                    FROM payment_obligations po
                )
            """
            cur.execute("""
                {paid_cte}
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
                    COALESCE(SUM(effective_balance), 0) AS amount
                FROM obligations_effective
                WHERE company_code=%s
                  AND COALESCE(active, TRUE)=TRUE
                  AND COALESCE(record_type, 'OBLIGATION')='OBLIGATION'
                  AND status IN ('PENDING','PARTIAL')
                  AND COALESCE(effective_balance,0) > 0
                  AND (due_date IS NULL OR due_date < %s)
                GROUP BY COALESCE(currency, 'CRC'), bucket
                ORDER BY currency, bucket
            """.format(paid_cte=paid_cte), (today, month_end, horizon_end, company, horizon_end))
            obligation_buckets = [_serialize(row) for row in cur.fetchall()]

            cur.execute("""
                {paid_cte}
                SELECT id, payee_name, obligation_type, reference, due_date, currency, total,
                       effective_balance AS balance, status, origin, payment_method, payment_bank_account_code,
                       vessel, country, operation
                FROM obligations_effective
                WHERE company_code=%s
                  AND COALESCE(active, TRUE)=TRUE
                  AND COALESCE(record_type, 'OBLIGATION')='OBLIGATION'
                  AND status IN ('PENDING','PARTIAL')
                  AND COALESCE(effective_balance,0) > 0
                  AND (due_date IS NULL OR due_date < %s)
                ORDER BY due_date NULLS LAST, effective_balance DESC
                LIMIT 120
            """.format(paid_cte=paid_cte), (company, horizon_end))
            obligations = [_serialize(row) for row in cur.fetchall()]

        applied_payments = []
        if has_biweekly:
            cur.execute("""
                SELECT COALESCE(currency, 'CRC') AS currency,
                       COALESCE(SUM(amount), 0) AS amount,
                       COUNT(*) AS count
                FROM itp_biweekly_payment_lines
                WHERE company_code=%s
                  AND COALESCE(accounting_entry_id, 0) > 0
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

        profitability_sql = """
            SELECT
                COALESCE(SUM(CASE WHEN l.account_code LIKE '4%%' THEN l.credit - l.debit ELSE 0 END), 0) AS revenue,
                COALESCE(SUM(CASE WHEN l.account_code LIKE '5%%' THEN l.debit - l.credit ELSE 0 END), 0) AS expenses,
                COALESCE(SUM(CASE WHEN l.account_code LIKE '4%%' THEN l.credit - l.debit ELSE 0 END), 0)
                  - COALESCE(SUM(CASE WHEN l.account_code LIKE '5%%' THEN l.debit - l.credit ELSE 0 END), 0) AS profit
            FROM accounting_entries e
            JOIN accounting_lines l ON l.entry_id=e.id
            WHERE e.company_code=%s
              AND e.workflow_status='POSTED'
              AND e.entry_date >= %s
              AND e.entry_date < %s
              AND (l.account_code LIKE '4%%' OR l.account_code LIKE '5%%')
        """
        cur.execute(profitability_sql, (company, start, month_end))
        profitability = _serialize(cur.fetchone() or {})
        profitability["scope"] = f"Periodo {period}"
        if not _money(profitability.get("revenue")) and not _money(profitability.get("expenses")):
            ytd_start = date(start.year, 1, 1)
            ytd_end = min(horizon_end, today + timedelta(days=1))
            cur.execute(profitability_sql, (company, ytd_start, ytd_end))
            profitability = _serialize(cur.fetchone() or {})
            profitability["scope"] = f"YTD {start.year} al {min(today, ytd_end - timedelta(days=1)).isoformat()}"
        revenue = _money(profitability.get("revenue"))
        profit = _money(profitability.get("profit"))
        profitability["margin_pct"] = _float((profit / revenue * Decimal("100")).quantize(MONEY)) if revenue else 0.0

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

        cur.execute("""
            SELECT *,
                   expected_revenue - expected_cost AS expected_profit,
                   CASE WHEN expected_revenue=0 THEN 0
                        ELSE ROUND(((expected_revenue - expected_cost) / expected_revenue) * 100, 2)
                   END AS expected_margin_pct,
                   ROUND((expected_revenue - expected_cost) * (probability_pct / 100.0), 2) AS weighted_profit
            FROM finance_planning_projects
            WHERE company_code=%s
              AND status IN ('PLANNED','ACTIVE','PAUSED')
            ORDER BY target_date NULLS LAST, priority DESC, id DESC
            LIMIT 120
        """, (company,))
        projects = [_serialize(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT due_date, concept, direction, currency_code, amount, status, notes,
                   project_id
            FROM finance_planning_project_schedule
            WHERE company_code=%s
              AND due_date >= %s
              AND due_date < %s
              AND status IN ('PLANNED','ACTIVE')
            ORDER BY due_date, direction, amount DESC
            LIMIT 160
        """, (company, start, horizon_end))
        project_schedule = [_serialize(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT month, currency_code,
                   SUM(planned_inflow) AS planned_inflow,
                   SUM(planned_outflow) AS planned_outflow,
                   SUM(planned_saving) AS planned_saving
            FROM (
                SELECT date_trunc('month', due_date)::date AS month, currency_code,
                       CASE WHEN direction='INFLOW' THEN amount ELSE 0 END AS planned_inflow,
                       CASE WHEN direction='OUTFLOW' THEN amount ELSE 0 END AS planned_outflow,
                       CASE WHEN direction='SAVING' THEN amount ELSE 0 END AS planned_saving
                FROM finance_planning_project_schedule
                WHERE company_code=%s AND due_date >= %s AND due_date < %s
                UNION ALL
                SELECT date_trunc('month', COALESCE(target_date, (period || '-01')::date))::date AS month,
                       currency_code,
                       0 AS planned_inflow,
                       0 AS planned_outflow,
                       COALESCE(monthly_contribution, 0) AS planned_saving
                FROM accounting_budgets
                WHERE company_code=%s
                  AND UPPER(COALESCE(purpose, 'BUDGET')) IN ('SAVINGS','GOAL')
                  AND UPPER(COALESCE(status, 'ACTIVE')) IN ('ACTIVE','PAUSED')
                  AND COALESCE(target_date, (period || '-01')::date) >= %s
            ) s
            GROUP BY month, currency_code
            ORDER BY month, currency_code
        """, (company, start, horizon_end, company, start))
        monthly_plan = [_serialize(row) for row in cur.fetchall()]

        cur.execute("""
            SELECT
                a.account_code,
                a.account_name,
                CASE
                    WHEN UPPER(COALESCE(a.currency_code, '')) IN ('CRC','USD') THEN UPPER(a.currency_code)
                    WHEN UPPER(a.account_name) LIKE '%%USD%%' OR UPPER(a.account_name) LIKE '%%DOLAR%%' THEN 'USD'
                    ELSE 'CRC'
                END AS currency_code,
                CASE
                    WHEN UPPER(a.account_name) LIKE '%%BAC%%' THEN 'BAC'
                    WHEN UPPER(a.account_name) LIKE '%%BCR%%' OR UPPER(a.account_name) LIKE '%%COSTA RICA%%' THEN 'BCR'
                    ELSE 'OTRO'
                END AS bank_name,
                COALESCE(SUM(
                    CASE
                        WHEN e.id IS NULL THEN 0
                        WHEN (
                            UPPER(COALESCE(a.currency_code, ''))='USD'
                            OR UPPER(a.account_name) LIKE '%%USD%%'
                            OR UPPER(a.account_name) LIKE '%%DOLAR%%'
                        )
                        THEN CASE
                            WHEN e.currency_code='USD' AND COALESCE(NULLIF(e.exchange_rate,0),0) > 0
                            THEN (COALESCE(l.debit,0)-COALESCE(l.credit,0)) / e.exchange_rate
                            ELSE COALESCE(l.debit,0)-COALESCE(l.credit,0)
                        END
                        ELSE COALESCE(l.debit,0)-COALESCE(l.credit,0)
                    END
                ), 0) AS available_amount,
                MAX(e.entry_date) AS last_movement_date
            FROM accounting_accounts a
            LEFT JOIN accounting_lines l ON l.account_code=a.account_code
            LEFT JOIN accounting_entries e
              ON e.id=l.entry_id
             AND e.company_code=%s
             AND e.workflow_status='POSTED'
             AND COALESCE(e.reversed, FALSE)=FALSE
             AND e.entry_date <= %s
            WHERE COALESCE(a.active, TRUE)=TRUE
              AND COALESCE(a.accepts_posting, TRUE)=TRUE
              AND (
                   a.account_code IN ('1.1.02.02.01','1.1.02.02.02','1.1.02.04','1.1.02.04.01')
                   OR (
                        a.account_code LIKE '1.1.02.%%'
                        AND (
                            UPPER(a.account_name) LIKE '%%BAC%%'
                            OR UPPER(a.account_name) LIKE '%%BCR%%'
                            OR UPPER(a.account_name) LIKE '%%BANCO DE COSTA RICA%%'
                            OR UPPER(a.account_name) LIKE 'BANCO %%'
                        )
                   )
              )
              AND LOWER(a.account_name) NOT LIKE '%%tarjeta%%'
              AND a.account_code <> '1.1.02.02'
            GROUP BY a.account_code, a.account_name, a.currency_code
            ORDER BY bank_name, currency_code, a.account_code
        """, (company, today))
        bank_accounts = [_serialize(row) for row in cur.fetchall()]

        cur.execute("SELECT to_regclass('public.collections') AS table_name")
        has_collections = bool((cur.fetchone() or {}).get("table_name"))
        collections_open = []
        collections_aging = []
        if has_collections:
            cur.execute("""
                SELECT COALESCE(moneda, 'CRC') AS currency_code,
                       COUNT(*) AS count,
                       COALESCE(SUM(saldo_pendiente), 0) AS amount
                FROM collections
                WHERE company_code=%s
                  AND COALESCE(saldo_pendiente,0) > 0
                  AND UPPER(COALESCE(estado_factura,'PENDIENTE_PAGO')) NOT IN ('PAGADA','WRITE_OFF')
                GROUP BY COALESCE(moneda, 'CRC')
                ORDER BY currency_code
            """, (company,))
            collections_open = [_serialize(row) for row in cur.fetchall()]
            cur.execute("""
                SELECT COALESCE(moneda, 'CRC') AS currency_code,
                       COALESCE(bucket_aging, 'SIN_BUCKET') AS bucket,
                       COUNT(*) AS count,
                       COALESCE(SUM(saldo_pendiente), 0) AS amount
                FROM collections
                WHERE company_code=%s
                  AND COALESCE(saldo_pendiente,0) > 0
                  AND UPPER(COALESCE(estado_factura,'PENDIENTE_PAGO')) NOT IN ('PAGADA','WRITE_OFF')
                GROUP BY COALESCE(moneda, 'CRC'), COALESCE(bucket_aging, 'SIN_BUCKET')
                ORDER BY currency_code, bucket
            """, (company,))
            collections_aging = [_serialize(row) for row in cur.fetchall()]

        cash_requirement_rows = []
        if has_itp:
            cur.execute("""
                {paid_cte}
                SELECT
                    'ITP' AS source,
                    id,
                    payee_name AS concept,
                    obligation_type AS category,
                    COALESCE(planned_payment_date, due_date, issue_date, %s::date) AS due_date,
                    COALESCE(currency, 'CRC') AS currency_code,
                    COALESCE(effective_balance, 0) AS amount,
                    status,
                    origin
                FROM obligations_effective
                WHERE company_code=%s
                  AND COALESCE(active, TRUE)=TRUE
                  AND COALESCE(record_type, 'OBLIGATION')='OBLIGATION'
                  AND status IN ('PENDING','PARTIAL')
                  AND COALESCE(effective_balance,0) > 0
                  AND COALESCE(planned_payment_date, due_date, issue_date, %s::date) < %s
                ORDER BY due_date NULLS LAST, effective_balance DESC
            """.format(paid_cte=paid_cte), (today, company, today, horizon_end))
            cash_requirement_rows.extend(_serialize(row) for row in cur.fetchall())

        if has_biweekly:
            cur.execute("""
                SELECT
                    'QUINCENAL_DRAFT' AS source,
                    id,
                    beneficiary AS concept,
                    category,
                    COALESCE(payment_date, %s::date) AS due_date,
                    COALESCE(currency, 'CRC') AS currency_code,
                    COALESCE(amount, 0) AS amount,
                    CASE WHEN accounting_entry_id IS NULL THEN 'PENDING' ELSE 'POSTED' END AS status,
                    source AS origin
                FROM itp_biweekly_payment_lines
                WHERE company_code=%s
                  AND accounting_entry_id IS NULL
                  AND COALESCE(amount,0) > 0
                  AND COALESCE(payment_date, %s::date) >= %s
                  AND COALESCE(payment_date, %s::date) < %s
                  AND obligation_id IS NULL
                ORDER BY payment_date, amount DESC
            """, (today, company, today, start, today, horizon_end))
            cash_requirement_rows.extend(_serialize(row) for row in cur.fetchall())

    total_pending = {}
    for row in obligation_buckets:
        cur_code = row.get("currency") or "CRC"
        total_pending[cur_code] = _float(_money(total_pending.get(cur_code)) + _money(row.get("amount")))

    bank_totals = {}
    for row in bank_accounts:
        cur_code = row.get("currency_code") or "CRC"
        bank_totals[cur_code] = _money(bank_totals.get(cur_code)) + _money(row.get("available_amount"))

    collections_totals = {}
    for row in collections_open:
        cur_code = row.get("currency_code") or "CRC"
        collections_totals[cur_code] = _money(collections_totals.get(cur_code)) + _money(row.get("amount"))

    requirement_by_fortnight = {}
    requirement_by_month = {}
    for row in cash_requirement_rows:
        due_text = row.get("due_date")
        try:
            due = date.fromisoformat(str(due_text))
        except Exception:
            due = today
        cur_code = row.get("currency_code") or "CRC"
        amount = _money(row.get("amount"))
        bucket_key, bucket_label = _fortnight_bucket(due)
        item = requirement_by_fortnight.setdefault(
            (bucket_key, cur_code),
            {
                "bucket": bucket_key,
                "label": bucket_label,
                "period": due.strftime("%Y-%m"),
                "currency_code": cur_code,
                "required_amount": Decimal("0.00"),
                "count": 0,
            },
        )
        item["required_amount"] += amount
        item["count"] += 1
        month_key = _month_key(due)
        month_item = requirement_by_month.setdefault(
            (month_key, cur_code),
            {
                "month": month_key,
                "currency_code": cur_code,
                "required_amount": Decimal("0.00"),
                "count": 0,
            },
        )
        month_item["required_amount"] += amount
        month_item["count"] += 1

    running_by_currency = {cur: _money(amount) for cur, amount in bank_totals.items()}
    cash_coverage_fortnight = []
    for (_bucket, cur_code), row in sorted(requirement_by_fortnight.items(), key=lambda item: (item[1]["bucket"], item[1]["currency_code"])):
        available_before = _money(running_by_currency.get(cur_code))
        required = _money(row["required_amount"])
        remaining = available_before - required
        running_by_currency[cur_code] = remaining
        status = "CUBRE" if remaining >= 0 else "FALTANTE"
        coverage_pct = _float((available_before / required * Decimal("100")).quantize(MONEY)) if required else 100.0
        cash_coverage_fortnight.append({
            **row,
            "available_before": _float(available_before),
            "required_amount": _float(required),
            "remaining_after": _float(remaining),
            "shortfall": _float(abs(remaining) if remaining < 0 else 0),
            "coverage_pct": coverage_pct,
            "status": status,
        })

    cash_coverage_month = []
    for (_month, cur_code), row in sorted(requirement_by_month.items(), key=lambda item: (item[1]["month"], item[1]["currency_code"])):
        required = _money(row["required_amount"])
        available = _money(bank_totals.get(cur_code))
        remaining = available - required
        cash_coverage_month.append({
            **row,
            "bank_available": _float(available),
            "required_amount": _float(required),
            "remaining_if_paid": _float(remaining),
            "shortfall": _float(abs(remaining) if remaining < 0 else 0),
            "coverage_pct": _float((available / required * Decimal("100")).quantize(MONEY)) if required else 100.0,
            "status": "CUBRE" if remaining >= 0 else "FALTANTE",
        })

    cash_requirements = sorted(cash_requirement_rows, key=lambda row: (str(row.get("due_date") or ""), str(row.get("currency_code") or ""), -float(row.get("amount") or 0)))

    total_project_profit = sum(_money(row.get("expected_profit")) for row in projects)
    total_weighted_profit = sum(_money(row.get("weighted_profit")) for row in projects)
    total_monthly_savings = sum(_money(row.get("monthly_contribution")) for row in goals) + sum(_money(row.get("monthly_savings")) for row in projects)
    alerts = []
    for row in obligation_buckets:
        if row.get("bucket") == "OVERDUE" and _money(row.get("amount")) > 0:
            alerts.append({
                "severity": "HIGH",
                "code": "OVERDUE_ITP",
                "message": f"Obligaciones vencidas {row.get('currency')} {_float(row.get('amount')):,.2f}.",
            })
    for row in cash_coverage_fortnight:
        if row.get("status") == "FALTANTE":
            alerts.append({
                "severity": "HIGH",
                "code": "CASH_SHORTFALL",
                "message": f"{row.get('label')} {row.get('currency_code')}: faltan {_float(row.get('shortfall')):,.2f} para cubrir obligaciones.",
            })
    if _money(profitability.get("profit")) < 0:
        alerts.append({"severity": "HIGH", "code": "NEGATIVE_MARGIN", "message": "La rentabilidad del periodo está negativa."})
    if total_project_profit < 0:
        alerts.append({"severity": "MEDIUM", "code": "PROJECT_LOSS", "message": "La cartera de proyectos planificada tiene utilidad esperada negativa."})
    if total_monthly_savings <= 0:
        alerts.append({"severity": "MEDIUM", "code": "NO_MONTHLY_SAVINGS", "message": "No hay ahorro mensual configurado para metas/proyectos."})

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
            "project_expected_profit": _float(total_project_profit),
            "project_weighted_profit": _float(total_weighted_profit),
            "monthly_savings": _float(total_monthly_savings),
            "bank_available_by_currency": {key: _float(value) for key, value in bank_totals.items()},
            "collections_open_by_currency": {key: _float(value) for key, value in collections_totals.items()},
        },
        "profitability": profitability,
        "obligation_buckets": obligation_buckets,
        "obligations": obligations,
        "applied_payments": applied_payments,
        "expenses": expenses,
        "goals": goals,
        "projects": projects,
        "project_schedule": project_schedule,
        "monthly_plan": monthly_plan,
        "bank_accounts": bank_accounts,
        "collections_open": collections_open,
        "collections_aging": collections_aging,
        "cash_requirements": cash_requirements[:200],
        "cash_coverage_fortnight": cash_coverage_fortnight,
        "cash_coverage_month": cash_coverage_month,
        "alerts": alerts,
        "decision_notes": [
            "Priorice OVERDUE y vencimientos dentro del mes antes de comprometer nuevos pagos.",
            "Use SAVINGS y GOAL para reservar caja antes de los primeros meses del siguiente FY.",
            "Compare proyectos con utilidad positiva contra obligaciones ITP para calendarizar compromisos.",
        ],
    }
