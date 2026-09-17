from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, Header, HTTPException, Query
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
        """, (company, start, month_end))
        profitability = _serialize(cur.fetchone() or {})
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

    total_pending = {}
    for row in obligation_buckets:
        cur_code = row.get("currency") or "CRC"
        total_pending[cur_code] = _float(_money(total_pending.get(cur_code)) + _money(row.get("amount")))

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
        "alerts": alerts,
        "decision_notes": [
            "Priorice OVERDUE y vencimientos dentro del mes antes de comprometer nuevos pagos.",
            "Use SAVINGS y GOAL para reservar caja antes de los primeros meses del siguiente FY.",
            "Compare proyectos con utilidad positiva contra obligaciones ITP para calendarizar compromisos.",
        ],
    }
