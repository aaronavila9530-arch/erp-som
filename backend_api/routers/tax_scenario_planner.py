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
    (5_621_000, 0.05),
    (8_433_000, 0.10),
    (11_243_000, 0.15),
    (None, 0.20),
]


class ClientMove(BaseModel):
    client_name: str
    from_company: str = "MSL-CR"
    to_company: str = "MMS-CR"
    projected_amount_crc: float | None = None


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
    company_options: list[CompanyOption] = []
    client_moves: list[ClientMove] = []
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
                COALESCE(c.total, 0) *
                CASE
                    WHEN UPPER(COALESCE(c.moneda, 'CRC')) = 'USD' THEN COALESCE(fx.rate, 1)
                    ELSE 1
                END
            ), 0) AS ytd_amount_crc,
            SUM(CASE WHEN UPPER(COALESCE(c.moneda, 'CRC')) = 'USD' AND fx.rate IS NULL THEN 1 ELSE 0 END) AS missing_fx_count
        FROM collections c
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
    return [
        {
            **dict(row),
            "ytd_amount_crc": _money(row["ytd_amount_crc"]),
            "projected_annual_crc": _money(_money(row["ytd_amount_crc"]) * factor),
            "missing_fx_count": int(row.get("missing_fx_count") or 0),
        }
        for row in cur.fetchall()
    ]


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
        selected.append(ClientMove(client_name=row["client_name"], from_company=source, to_company=company_code(req.target_company), projected_amount_crc=row["projected_annual_crc"]))
        moved += row["projected_annual_crc"]
        if moved >= excess:
            break
    return selected


def _scenario(req: TaxScenarioRequest, clients: list[dict[str, Any]], expenses: dict[str, dict[str, Any]], moves: list[ClientMove], label: str) -> dict[str, Any]:
    options = _company_options(req)
    companies = list(options.keys())
    gross = {code: sum(row["projected_annual_crc"] for row in clients if row["company_code"] == code) for code in companies}
    moved_clients = []
    for move in moves:
        src = company_code(move.from_company)
        dst = company_code(move.to_company)
        amount = move.projected_amount_crc
        if amount is None:
            amount = next((row["projected_annual_crc"] for row in clients if row["company_code"] == src and row["client_name"] == move.client_name), 0)
        amount = _money(amount)
        gross[src] = _money(gross.get(src, 0) - amount)
        gross[dst] = _money(gross.get(dst, 0) + amount)
        moved_clients.append({"client_name": move.client_name, "from_company": src, "to_company": dst, "projected_amount_crc": amount})

    expense_totals = {}
    total_gross_before = sum(sum(row["projected_annual_crc"] for row in clients if row["company_code"] == code) for code in companies)
    for code in companies:
        base_expenses = _money((expenses.get(code) or {}).get("projected_annual_expense_crc", 0) + options[code].manual_expenses_crc)
        if total_gross_before and moved_clients:
            ratio = gross.get(code, 0) / max(sum(gross.values()), 1)
            total_expenses = sum(_money((expenses.get(c) or {}).get("projected_annual_expense_crc", 0) + options[c].manual_expenses_crc) for c in companies)
            base_expenses = _money(total_expenses * ratio)
        expense_totals[code] = base_expenses

    company_results = [_company_tax(code, gross.get(code, 0), expense_totals.get(code, 0), options[code]) for code in companies]
    total_tax = _money(sum(row["income_tax_projected_crc"] for row in company_results))
    warnings = []
    for row in company_results:
        if row["pyme_gross_limit_exceeded"]:
            warnings.append(f"{row['company_code']} supera el umbral PYME por ventas brutas proyectadas.")
    return {
        "label": label,
        "moved_clients": moved_clients,
        "companies": company_results,
        "total_projected_tax_crc": total_tax,
        "warnings": warnings,
    }


def _analysis(baseline: dict[str, Any], optimized: dict[str, Any]) -> dict[str, Any]:
    tax_delta = _money(baseline["total_projected_tax_crc"] - optimized["total_projected_tax_crc"])
    moved = optimized.get("moved_clients") or []
    pros = ["Visualiza el impacto fiscal antes de facturar.", "Mantiene la regla de ventas brutas PYME separada por sociedad.", "Usa datos reales del ERP y proyecta a diciembre."]
    cons = ["La reasignacion debe tener sustancia comercial real, contratos y operacion en la sociedad correcta.", "Los gastos se distribuyen proporcionalmente si no se asignan de forma manual.", "Es una simulacion gerencial; la declaracion final debe validarse con contador."]
    if moved and tax_delta > 0:
        recommendation = f"Mover {len(moved)} cliente(s) al escenario alterno reduce impuesto proyectado en CRC {tax_delta:,.2f} y ayuda a controlar el umbral PYME."
    elif moved:
        recommendation = f"Mover {len(moved)} cliente(s) al escenario alterno no cambia el impuesto proyectado con los gastos actuales, pero ayuda a controlar ventas brutas y riesgo de perder PYME."
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
        expenses = _fetch_expenses(cur, req)
    manual_moves = req.client_moves or []
    auto_moves = _build_auto_moves(req, clients)
    baseline = _scenario(req, clients, expenses, [], "Actual sin mover clientes")
    optimized = _scenario(req, clients, expenses, manual_moves or auto_moves, "Escenario recomendado")
    result = {
        "currency": "CRC",
        "rule_version": "CR-2026",
        "year": req.year,
        "through_month": req.through_month,
        "projection_factor": _money(12 / max(int(req.through_month or 1), 1)),
        "company_names": names,
        "clients": clients,
        "expenses": expenses,
        "baseline": baseline,
        "optimized": optimized,
        "auto_moves": [item.dict() for item in auto_moves],
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
