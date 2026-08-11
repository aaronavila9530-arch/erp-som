from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
import calendar

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from psycopg2.extras import Json, RealDictCursor

from database import get_db
from services.tenanting import company_code


router = APIRouter(prefix="/accounting/tax-scenarios", tags=["Accounting - Tax Scenarios"])

CORPORATE_GROSS_THRESHOLD_ANNUAL = 119_174_000
CORPORATE_TAX_BRACKETS_ANNUAL = [
    (5_687_000, 0.05),
    (8_532_000, 0.10),
    (11_376_000, 0.15),
    (None, 0.20),
]


class ClientMove(BaseModel):
    client_name: str
    from_company: str = "MSL-CR"
    to_company: str = "MMS-CR"
    projected_amount_crc: float | None = None


class ExpenseMove(BaseModel):
    account_code: str
    account_name: str | None = None
    source_type: str | None = None
    from_company: str = "MSL-CR"
    to_company: str = "MMS-CR"
    projected_amount_crc: float | None = None


class ClientProjectionLock(BaseModel):
    client_name: str
    company_code: str = "MSL-CR"


class ExpenseProjectionLock(BaseModel):
    account_code: str
    account_name: str | None = None
    source_type: str | None = None
    company_code: str = "MSL-CR"


class CompanyOption(BaseModel):
    company_code: str
    is_pyme: bool = True
    pyme_year: int = 1
    manual_expenses_crc: float = 0


class TaxScenarioRequest(BaseModel):
    year: int = Field(default_factory=lambda: date.today().year)
    through_month: int = Field(default_factory=lambda: date.today().month, ge=1, le=12)
    source_company: str = "MSL-CR"
    target_company: str = "MMS-CR"
    company_options: list[CompanyOption] = Field(default_factory=list)
    client_moves: list[ClientMove] = Field(default_factory=list)
    expense_moves: list[ExpenseMove] = Field(default_factory=list)
    fixed_clients: list[ClientProjectionLock] = Field(default_factory=list)
    fixed_expenses: list[ExpenseProjectionLock] = Field(default_factory=list)
    save: bool = False
    label: str | None = None


def _money(value: Any) -> float:
    if isinstance(value, Decimal):
        value = float(value)
    return round(float(value or 0), 2)


def _progressive_tax(amount: float) -> tuple[float, list[dict[str, Any]]]:
    amount = max(float(amount or 0), 0)
    lower = 0.0
    total = 0.0
    detail = []
    for upper, rate in CORPORATE_TAX_BRACKETS_ANNUAL:
        cap = amount if upper is None else min(amount, float(upper))
        taxable = max(cap - lower, 0)
        tax = taxable * rate
        detail.append({"from": _money(lower), "to": upper, "rate": rate, "taxable": _money(taxable), "tax": _money(tax)})
        total += tax
        if upper is None or amount <= upper:
            break
        lower = float(upper)
    return _money(total), detail


def _pyme_exemption(is_pyme: bool, pyme_year: int, gross_annual: float) -> tuple[float, bool, bool]:
    if not is_pyme or gross_annual > CORPORATE_GROSS_THRESHOLD_ANNUAL:
        return 0.0, False, bool(is_pyme and gross_annual > CORPORATE_GROSS_THRESHOLD_ANNUAL)
    if 1 <= pyme_year <= 3:
        return 1.0, True, False
    if 4 <= pyme_year <= 5:
        return 0.75, True, False
    if pyme_year == 6:
        return 0.50, True, False
    return 0.0, True, False


def _ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS accounting_tax_scenarios (
                id BIGSERIAL PRIMARY KEY,
                company_code VARCHAR(30) NOT NULL,
                label TEXT,
                input_payload JSONB NOT NULL,
                result_payload JSONB NOT NULL,
                created_by TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tax_scenarios_company ON accounting_tax_scenarios(company_code, created_at DESC)")
    conn.commit()


def _company_options(req: TaxScenarioRequest) -> dict[str, CompanyOption]:
    options = {
        company_code(req.source_company): CompanyOption(company_code=company_code(req.source_company), is_pyme=True, pyme_year=4),
        company_code(req.target_company): CompanyOption(company_code=company_code(req.target_company), is_pyme=True, pyme_year=1),
    }
    for item in req.company_options or []:
        options[company_code(item.company_code)] = item
    return options


def _fixed_client_keys(req: TaxScenarioRequest) -> set[tuple[str, str]]:
    return {
        (company_code(item.company_code), (item.client_name or "").strip().upper())
        for item in req.fixed_clients or []
        if (item.client_name or "").strip()
    }


def _fixed_expense_matches(row: dict[str, Any], req: TaxScenarioRequest) -> bool:
    row_company = company_code(row.get("company_code"))
    row_account = (row.get("account_code") or "").strip().upper()
    row_name = (row.get("account_name") or "").strip().upper()
    row_source = (row.get("source_type") or "").strip().upper()
    for item in req.fixed_expenses or []:
        if company_code(item.company_code) != row_company:
            continue
        if (item.account_code or "").strip().upper() != row_account:
            continue
        if item.source_type and item.source_type.strip().upper() != row_source:
            continue
        if item.account_name and item.account_name.strip().upper() != row_name:
            continue
        return True
    return False


def _apply_projection_lock(row: dict[str, Any], locked: bool, factor: float) -> dict[str, Any]:
    ytd = _money(row.get("ytd_amount_crc"))
    row["ytd_amount_crc"] = ytd
    row["projected_annual_crc"] = ytd if locked else _money(ytd * factor)
    row["future_projected_crc"] = _money(max(row["projected_annual_crc"] - ytd, 0))
    row["projection_mode"] = "FIXED" if locked else "PROJECTED"
    return row


def _fetch_company_names(cur) -> dict[str, str]:
    cur.execute(
        """
        SELECT company_code, COALESCE(NULLIF(trade_name, ''), company_name, company_code) AS name
        FROM company_profiles
        """
    )
    return {row["company_code"]: row["name"] for row in cur.fetchall()}


def _fetch_clients(cur, req: TaxScenarioRequest) -> list[dict[str, Any]]:
    start_date = date(req.year, 1, 1)
    end_date = date(req.year, req.through_month, calendar.monthrange(req.year, req.through_month)[1])
    cur.execute(
        """
        SELECT
            c.company_code,
            COALESCE(NULLIF(c.nombre_cliente, ''), NULLIF(c.codigo_cliente, ''), 'Cliente sin nombre') AS client_name,
            COALESCE(c.codigo_cliente, '') AS client_code,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(
                COALESCE(NULLIF(rev.revenue_crc, 0), c.total *
                    CASE
                        WHEN UPPER(COALESCE(c.moneda, 'CRC')) = 'USD' THEN COALESCE(fx.rate, 1)
                        ELSE 1
                    END)
            ), 0) AS ytd_amount_crc,
            SUM(CASE WHEN UPPER(COALESCE(c.moneda, 'CRC')) = 'USD' AND fx.rate IS NULL THEN 1 ELSE 0 END) AS missing_fx_count
        FROM collections c
        LEFT JOIN LATERAL (
            SELECT COALESCE(SUM(CASE WHEN l.account_code LIKE '4%%' THEN GREATEST(l.credit - l.debit, 0) ELSE 0 END), 0) AS revenue_crc
            FROM accounting_entries e
            JOIN accounting_lines l ON l.entry_id = e.id
            WHERE e.origin = 'COLLECTIONS'
              AND e.origin_id = c.id
              AND e.workflow_status = 'POSTED'
        ) rev ON TRUE
        LEFT JOIN LATERAL (
            SELECT er.rate
            FROM exchange_rate er
            WHERE er.rate_date <= c.fecha_emision
            ORDER BY er.rate_date DESC
            LIMIT 1
        ) fx ON TRUE
        WHERE c.company_code IN (%s, %s)
          AND c.fecha_emision >= %s
          AND c.fecha_emision <= %s
        GROUP BY c.company_code, COALESCE(NULLIF(c.nombre_cliente, ''), NULLIF(c.codigo_cliente, ''), 'Cliente sin nombre'), COALESCE(c.codigo_cliente, '')
        ORDER BY ytd_amount_crc DESC
        """,
        (company_code(req.source_company), company_code(req.target_company), start_date, end_date),
    )
    factor = 12 / max(int(req.through_month or 1), 1)
    fixed_keys = _fixed_client_keys(req)
    rows = []
    for row in cur.fetchall():
        item = dict(row)
        locked = (company_code(item.get("company_code")), (item.get("client_name") or "").strip().upper()) in fixed_keys
        _apply_projection_lock(item, locked, factor)
        item["missing_fx_count"] = int(item.get("missing_fx_count") or 0)
        rows.append(item)
    return rows


def _fetch_expenses(cur, req: TaxScenarioRequest) -> dict[str, dict[str, Any]]:
    period_from = f"{req.year}-01"
    period_to = f"{req.year}-{int(req.through_month):02d}"
    cur.execute(
        """
        SELECT
            e.company_code,
            COALESCE(SUM(GREATEST(COALESCE(l.debit, 0) - COALESCE(l.credit, 0), 0)), 0) AS ytd_expense_crc
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id = e.id
        WHERE e.company_code IN (%s, %s)
          AND e.period >= %s
          AND e.period <= %s
          AND (l.account_code LIKE '5%%' OR l.account_code LIKE '6%%')
        GROUP BY e.company_code
        """,
        (company_code(req.source_company), company_code(req.target_company), period_from, period_to),
    )
    factor = 12 / max(int(req.through_month or 1), 1)
    data = {}
    for row in cur.fetchall():
        ytd = _money(row["ytd_expense_crc"])
        data[row["company_code"]] = {"ytd_expense_crc": ytd, "projected_annual_expense_crc": _money(ytd * factor)}
    return data


def _fetch_expense_rows(cur, req: TaxScenarioRequest) -> list[dict[str, Any]]:
    period_from = f"{req.year}-01"
    period_to = f"{req.year}-{int(req.through_month):02d}"
    cur.execute(
        """
        SELECT
            e.company_code,
            'POSTED_GL' AS source_type,
            COALESCE(NULLIF(l.account_code, ''), 'SIN-CUENTA') AS account_code,
            COALESCE(NULLIF(l.account_name, ''), 'Gasto sin nombre') AS account_name,
            'POSTED' AS status,
            COUNT(DISTINCT e.id) AS entry_count,
            COALESCE(SUM(GREATEST(COALESCE(l.debit, 0) - COALESCE(l.credit, 0), 0)), 0) AS ytd_amount_crc
        FROM accounting_entries e
        JOIN accounting_lines l ON l.entry_id = e.id
        WHERE e.company_code IN (%s, %s)
          AND e.period >= %s
          AND e.period <= %s
          AND (l.account_code LIKE '5%%' OR l.account_code LIKE '6%%')
        GROUP BY e.company_code, COALESCE(NULLIF(l.account_code, ''), 'SIN-CUENTA'), COALESCE(NULLIF(l.account_name, ''), 'Gasto sin nombre')
        HAVING COALESCE(SUM(GREATEST(COALESCE(l.debit, 0) - COALESCE(l.credit, 0), 0)), 0) <> 0
        ORDER BY ytd_amount_crc DESC
        """,
        (company_code(req.source_company), company_code(req.target_company), period_from, period_to),
    )
    factor = 12 / max(int(req.through_month or 1), 1)
    rows = []
    for row in cur.fetchall():
        item = {**dict(row), "entry_count": int(row.get("entry_count") or 0)}
        rows.append(_apply_projection_lock(item, _fixed_expense_matches(item, req), factor))
    cur.execute(
        """
        SELECT
            %s AS company_code,
            'ITP_PENDING' AS source_type,
            'ITP-' || COALESCE(NULLIF(p.obligation_type, ''), NULLIF(p.payee_type, ''), 'GASTO') AS account_code,
            COALESCE(NULLIF(p.payee_name, ''), NULLIF(p.obligation_type, ''), 'Factura/obligacion pendiente') AS account_name,
            COALESCE(NULLIF(p.status, ''), 'PENDING') AS status,
            COUNT(*) AS entry_count,
            COALESCE(SUM(COALESCE(NULLIF(p.balance, 0), p.total, 0) *
                CASE
                    WHEN UPPER(COALESCE(p.currency, 'CRC')) = 'USD' THEN COALESCE(fx.rate, 1)
                    ELSE 1
                END
            ), 0) AS ytd_amount_crc
        FROM payment_obligations p
        LEFT JOIN accounting_entries e
          ON e.origin = 'ITP'
         AND e.origin_id = p.id
         AND e.workflow_status = 'POSTED'
        LEFT JOIN LATERAL (
            SELECT er.rate
            FROM exchange_rate er
            WHERE er.rate_date <= COALESCE(p.issue_date, p.created_at::date, CURRENT_DATE)
            ORDER BY er.rate_date DESC
            LIMIT 1
        ) fx ON TRUE
        WHERE p.active = TRUE
          AND p.record_type = 'OBLIGATION'
          AND COALESCE(p.issue_date, p.created_at::date, CURRENT_DATE) >= %s
          AND COALESCE(p.issue_date, p.created_at::date, CURRENT_DATE) <= %s
          AND e.id IS NULL
        GROUP BY COALESCE(NULLIF(p.obligation_type, ''), NULLIF(p.payee_type, ''), 'GASTO'),
                 COALESCE(NULLIF(p.payee_name, ''), NULLIF(p.obligation_type, ''), 'Factura/obligacion pendiente'),
                 COALESCE(NULLIF(p.status, ''), 'PENDING')
        HAVING COALESCE(SUM(COALESCE(NULLIF(p.balance, 0), p.total, 0)), 0) <> 0
        ORDER BY ytd_amount_crc DESC
        """,
        (company_code(req.source_company), date(req.year, 1, 1), date(req.year, req.through_month, calendar.monthrange(req.year, req.through_month)[1])),
    )
    for row in cur.fetchall():
        ytd = _money(row["ytd_amount_crc"])
        item = {**dict(row), "entry_count": int(row.get("entry_count") or 0), "ytd_amount_crc": ytd}
        rows.append(_apply_projection_lock(item, _fixed_expense_matches(item, req), factor))
    cur.execute(
        """
        SELECT
            %s AS company_code,
            'PAYROLL_PENDING' AS source_type,
            'PAYROLL' AS account_code,
            'Planilla y salarios sin asiento POSTED' AS account_name,
            'PAYROLL' AS status,
            COUNT(*) AS entry_count,
            COALESCE(SUM(COALESCE(pr.salario_bruto, 0)), 0) AS ytd_amount_crc
        FROM payroll_runs pr
        LEFT JOIN accounting_entries e
          ON e.origin = 'PAYROLL'
         AND e.origin_id = pr.id
         AND e.workflow_status = 'POSTED'
        WHERE pr.year = %s
          AND pr.month <= %s
          AND e.id IS NULL
        HAVING COALESCE(SUM(COALESCE(pr.salario_bruto, 0)), 0) <> 0
        """,
        (company_code(req.source_company), req.year, req.through_month),
    )
    for row in cur.fetchall():
        ytd = _money(row["ytd_amount_crc"])
        item = {**dict(row), "entry_count": int(row.get("entry_count") or 0), "ytd_amount_crc": ytd}
        rows.append(_apply_projection_lock(item, _fixed_expense_matches(item, req), factor))
    return rows


def _company_tax(company: str, gross: float, expenses: float, option: CompanyOption) -> dict[str, Any]:
    net = _money(max(gross - expenses, 0))
    if gross > CORPORATE_GROSS_THRESHOLD_ANNUAL:
        base_tax = _money(net * 0.30)
        detail = [{"from": 0, "to": None, "rate": 0.30, "taxable": net, "tax": base_tax}]
        regime = "GENERAL_30"
    else:
        base_tax, detail = _progressive_tax(net)
        regime = "PYME_ESCALONADA"
    exemption, pyme_applied, limit_exceeded = _pyme_exemption(option.is_pyme, int(option.pyme_year or 0), gross)
    final_tax = _money(base_tax * (1 - exemption))
    return {
        "company_code": company,
        "gross_projected_crc": _money(gross),
        "deductible_expenses_projected_crc": _money(expenses),
        "net_taxable_projected_crc": net,
        "regime": regime,
        "base_income_tax_crc": base_tax,
        "pyme_applied": pyme_applied,
        "pyme_year": option.pyme_year,
        "pyme_exemption_rate": exemption,
        "pyme_gross_limit_exceeded": limit_exceeded,
        "income_tax_projected_crc": final_tax,
        "effective_tax_rate": _money(final_tax / gross * 100) if gross else 0,
        "pyme_threshold_crc": CORPORATE_GROSS_THRESHOLD_ANNUAL,
        "pyme_threshold_remaining_crc": _money(CORPORATE_GROSS_THRESHOLD_ANNUAL - gross),
        "pyme_threshold_usage_pct": _money(gross / CORPORATE_GROSS_THRESHOLD_ANNUAL * 100) if CORPORATE_GROSS_THRESHOLD_ANNUAL else 0,
        "tax_detail": detail,
    }


def _build_auto_moves(req: TaxScenarioRequest, clients: list[dict[str, Any]]) -> list[ClientMove]:
    source = company_code(req.source_company)
    source_total = sum(row["projected_annual_crc"] for row in clients if row["company_code"] == source)
    excess = source_total - CORPORATE_GROSS_THRESHOLD_ANNUAL
    if excess <= 0:
        return []
    selected = []
    moved = 0.0
    for row in sorted([r for r in clients if r["company_code"] == source], key=lambda r: r["projected_annual_crc"], reverse=True):
        future_amount = _money(max(_money(row.get("projected_annual_crc")) - _money(row.get("ytd_amount_crc")), 0))
        if future_amount <= 0:
            continue
        selected.append(ClientMove(client_name=row["client_name"], from_company=source, to_company=company_code(req.target_company), projected_amount_crc=future_amount))
        moved += future_amount
        if moved >= excess:
            break
    return selected


def _expense_summary(expense_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for row in expense_rows:
        code = company_code(row.get("company_code"))
        item = summary.setdefault(code, {"ytd_expense_crc": 0.0, "projected_annual_expense_crc": 0.0})
        item["ytd_expense_crc"] = _money(item["ytd_expense_crc"] + _money(row.get("ytd_amount_crc")))
        item["projected_annual_expense_crc"] = _money(item["projected_annual_expense_crc"] + _money(row.get("projected_annual_crc")))
    return summary


def _scenario(
    req: TaxScenarioRequest,
    clients: list[dict[str, Any]],
    expense_rows: list[dict[str, Any]],
    client_moves: list[ClientMove],
    expense_moves: list[ExpenseMove],
    label: str,
) -> dict[str, Any]:
    options = _company_options(req)
    companies = list(options.keys())
    gross_ytd = {code: sum(row["ytd_amount_crc"] for row in clients if row["company_code"] == code) for code in companies}
    gross = {code: sum(row["projected_annual_crc"] for row in clients if row["company_code"] == code) for code in companies}
    moved_clients = []
    for move in client_moves:
        src = company_code(move.from_company)
        dst = company_code(move.to_company)
        client_row = next((row for row in clients if row["company_code"] == src and row["client_name"] == move.client_name), None)
        future_available = _money(
            max(_money((client_row or {}).get("projected_annual_crc")) - _money((client_row or {}).get("ytd_amount_crc")), 0)
        )
        amount = move.projected_amount_crc
        if amount is None:
            amount = future_available
        amount = _money(min(_money(amount), future_available))
        if amount <= 0:
            continue
        gross[src] = _money(gross.get(src, 0) - amount)
        gross[dst] = _money(gross.get(dst, 0) + amount)
        moved_clients.append({
            "client_name": move.client_name,
            "from_company": src,
            "to_company": dst,
            "projected_amount_crc": amount,
            "movement_basis": "FUTURE_ONLY",
            "ytd_kept_crc": _money((client_row or {}).get("ytd_amount_crc")),
        })

    expense_totals = {code: sum(row["projected_annual_crc"] for row in expense_rows if row["company_code"] == code) for code in companies}
    expense_totals = {code: _money(expense_totals.get(code, 0) + options[code].manual_expenses_crc) for code in companies}
    moved_expenses = []
    for move in expense_moves:
        src = company_code(move.from_company)
        dst = company_code(move.to_company)
        amount = move.projected_amount_crc
        if amount is None:
            amount = next(
                (
                    row["projected_annual_crc"]
                    for row in expense_rows
                    if row["company_code"] == src and row["account_code"] == move.account_code
                    and (not move.source_type or row.get("source_type") == move.source_type)
                    and (not move.account_name or row.get("account_name") == move.account_name)
                ),
                0,
            )
        amount = _money(amount)
        expense_totals[src] = _money(expense_totals.get(src, 0) - amount)
        expense_totals[dst] = _money(expense_totals.get(dst, 0) + amount)
        moved_expenses.append(
            {
                "account_code": move.account_code,
                "account_name": move.account_name,
                "source_type": move.source_type,
                "from_company": src,
                "to_company": dst,
                "projected_amount_crc": amount,
            }
        )

    for code in companies:
        expense_totals[code] = _money(max(expense_totals.get(code, 0), 0))

    company_results = [_company_tax(code, gross.get(code, 0), expense_totals.get(code, 0), options[code]) for code in companies]
    for row in company_results:
        ytd = _money(gross_ytd.get(row["company_code"], 0))
        row["gross_ytd_crc"] = ytd
        row["gross_future_projected_crc"] = _money(max(row["gross_projected_crc"] - ytd, 0))
        row["pyme_threshold_ytd_remaining_crc"] = _money(CORPORATE_GROSS_THRESHOLD_ANNUAL - ytd)
        row["pyme_threshold_ytd_usage_pct"] = _money(ytd / CORPORATE_GROSS_THRESHOLD_ANNUAL * 100) if CORPORATE_GROSS_THRESHOLD_ANNUAL else 0
    total_tax = _money(sum(row["income_tax_projected_crc"] for row in company_results))
    warnings = []
    for row in company_results:
        if row["pyme_gross_limit_exceeded"]:
            warnings.append(f"{row['company_code']} supera el umbral PYME por ventas brutas proyectadas.")
    return {
        "label": label,
        "moved_clients": moved_clients,
        "moved_expenses": moved_expenses,
        "companies": company_results,
        "total_projected_tax_crc": total_tax,
        "warnings": warnings,
    }


def _analysis(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    tax_delta = _money(baseline["total_projected_tax_crc"] - optimized["total_projected_tax_crc"])
    moved = optimized.get("moved_clients") or []
    moved_expenses = optimized.get("moved_expenses") or []
    pros = ["Visualiza el impacto fiscal antes de facturar.", "Mantiene la regla de ventas brutas PYME separada por sociedad.", "Usa datos reales del ERP y proyecta a diciembre."]
    cons = ["La reasignacion debe tener sustancia comercial real, contratos y operacion en la sociedad correcta.", "Los gastos se distribuyen proporcionalmente si no se asignan de forma manual.", "Es una simulacion gerencial; la declaracion final debe validarse con contador."]
    if (moved or moved_expenses) and tax_delta > 0:
        recommendation = f"El escenario con {len(moved)} cliente(s) y {len(moved_expenses)} gasto(s) reasignados reduce impuesto proyectado en CRC {tax_delta:,.2f} y ayuda a controlar el umbral PYME."
    elif (moved or moved_expenses) and tax_delta < 0:
        recommendation = f"El escenario con {len(moved)} cliente(s) y {len(moved_expenses)} gasto(s) reasignados aumenta el impuesto proyectado en CRC {abs(tax_delta):,.2f}. Revise si el gasto movido debe quedarse donde se genera la venta."
    elif moved or moved_expenses:
        recommendation = f"El escenario con {len(moved)} cliente(s) y {len(moved_expenses)} gasto(s) reasignados no cambia el impuesto proyectado con los gastos actuales, pero ayuda a controlar ventas brutas y sustancia por sociedad."
    else:
        recommendation = "Con los datos actuales no hace falta mover clientes para el umbral PYME, salvo estrategia comercial o riesgo operativo."
    return {"recommendation": recommendation, "tax_saving_crc": tax_delta, "pros": pros, "cons": cons}


@router.post("/analyze")
def analyze_tax_scenarios(
    req: TaxScenarioRequest,
    x_user: str | None = Header(None, alias="X-User"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _ensure_schema(conn)
    req.source_company = company_code(req.source_company, x_company_code)
    req.target_company = company_code(req.target_company)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        names = _fetch_company_names(cur)
        clients = _fetch_clients(cur, req)
        expense_rows = _fetch_expense_rows(cur, req)
        expenses = _expense_summary(expense_rows)
    manual_moves = req.client_moves or []
    manual_expense_moves = req.expense_moves or []
    auto_moves = _build_auto_moves(req, clients)
    baseline = _scenario(req, clients, expense_rows, [], [], "Actual sin mover clientes")
    optimized = _scenario(req, clients, expense_rows, manual_moves or auto_moves, manual_expense_moves, "Escenario recomendado")
    result = {
        "currency": "CRC",
        "rule_version": "CR-2026",
        "year": req.year,
        "through_month": req.through_month,
        "projection_factor": _money(12 / max(int(req.through_month or 1), 1)),
        "company_names": names,
        "clients": clients,
        "expenses": expenses,
        "expense_rows": expense_rows,
        "baseline": baseline,
        "optimized": optimized,
        "auto_moves": [item.dict() for item in auto_moves],
        "fixed_clients": [item.dict() for item in req.fixed_clients],
        "fixed_expenses": [item.dict() for item in req.fixed_expenses],
        "analysis": _analysis(baseline, optimized),
        "disclaimer": "Simulacion referencial de planeacion fiscal. No sustituye criterio legal, tributario ni contable.",
    }
    if req.save:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounting_tax_scenarios (company_code, label, input_payload, result_payload, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (req.source_company, req.label, Json(req.dict()), Json(result), x_user, datetime.now()),
            )
            result["saved_id"] = cur.fetchone()[0]
        conn.commit()
    return result


@router.get("/history")
def tax_scenario_history(
    limit: int = 25,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, label, created_by, created_at, result_payload
            FROM accounting_tax_scenarios
            WHERE company_code = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (company_code(header_value=x_company_code), max(1, min(int(limit or 25), 100))),
        )
        return [dict(row) for row in cur.fetchall()]
