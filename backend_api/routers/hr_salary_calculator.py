from __future__ import annotations

from datetime import datetime
import unicodedata
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from psycopg2.extras import Json, RealDictCursor

from database import get_db
from security.rbac import require_permission
from services.tenanting import company_code


router = APIRouter(prefix="/hr/salary-calculator", tags=["HHRR - Salary Calculator"])


EMPLOYEE_WORKER_RATES = {
    "SEM - Enfermedad y Maternidad": 0.055,
    "IVM - Invalidez, Vejez y Muerte": 0.0433,
    "Banco Popular": 0.01,
}

EMPLOYEE_EMPLOYER_RATES = {
    "SEM - Enfermedad y Maternidad": 0.0925,
    "IVM - Invalidez, Vejez y Muerte": 0.0558,
    "FODESAF": 0.05,
    "INA": 0.015,
    "FCL": 0.015,
    "ROP patronal": 0.02,
    "Banco Popular patronal": 0.005,
    "IMAS": 0.005,
    "INS Riesgos del Trabajo referencial": 0.01,
}

SALARY_TAX_BRACKETS_MONTHLY = [
    (918000, 0.0),
    (1347000, 0.10),
    (2364000, 0.15),
    (4727000, 0.20),
    (None, 0.25),
]

INDEPENDENT_CCSS_SCALE_MONTHLY = [
    (346789, 0.0705),
    (746185, 0.0998),
    (1492369, 0.1377),
    (2238554, 0.16),
    (None, 0.1911),
]

INDIVIDUAL_BUSINESS_TAX_BRACKETS_ANNUAL = [
    (6244000, 0.0),
    (8329000, 0.10),
    (10414000, 0.15),
    (20872000, 0.20),
    (None, 0.25),
]

CORPORATE_GROSS_THRESHOLD_ANNUAL = 119174000
PYME_REFERENCE_THRESHOLD_ANNUAL = 122145000
CORPORATE_TAX_BRACKETS_ANNUAL = [
    (5621000, 0.05),
    (8433000, 0.10),
    (11243000, 0.15),
    (None, 0.20),
]

DEFAULT_EXPENSE_CATEGORIES = [
    "Luz",
    "Agua",
    "Internet",
    "Telefonía celular",
    "Telefonía fija",
    "Alimentación",
    "Gasolina",
    "Activos / mobiliario",
    "Computadora y periféricos",
    "Escritorio / mesa / mueble",
    "Terreno (no depreciable)",
    "Depreciación vehicular",
    "Cuota vehicular",
    "Seguro médico",
    "Otro gasto deducible",
]

DEPRECIABLE_KEYWORDS = (
    "activo",
    "mobiliario",
    "computadora",
    "periferico",
    "escritorio",
    "mueble",
    "vehicular",
    "vehiculo",
    "automovil",
)
NON_DEPRECIABLE_KEYWORDS = ("terreno",)


class ExpenseItem(BaseModel):
    category: str
    amount: float = 0
    note: str | None = None
    purchase_year: int | None = None
    useful_life_years: int | None = None


class SalaryCalculatorRequest(BaseModel):
    scenario: Literal["EMPLOYEE", "INDEPENDENT", "OWNER"]
    amount: float = Field(0, description="Salario mensual, monto mensual a facturar o ingreso bruto mensual.")
    expenses: list[ExpenseItem] = []
    vehicle_debt_amount: float = 0
    vehicle_monthly_payment: float = 0
    vehicle_purchase_year: int | None = None
    vehicle_useful_life_years: int = 10
    distribution_type: Literal["NONE", "DIETAS", "DIVIDENDS"] = "NONE"
    distribution_amount: float = 0
    is_pyme: bool = False
    pyme_year: int = 0
    save: bool = False
    label: str | None = None


def _ensure_schema(conn) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hr_salary_calculations (
            id SERIAL PRIMARY KEY,
            company_code VARCHAR(30) NOT NULL,
            scenario VARCHAR(30) NOT NULL,
            label TEXT,
            input_payload JSONB NOT NULL,
            result_payload JSONB NOT NULL,
            created_by TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_hr_salary_calc_company ON hr_salary_calculations(company_code, created_at DESC)")
    conn.commit()


def _money(value: float) -> float:
    return round(float(value or 0), 2)


def _plain(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _components(base: float, rates: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {"name": name, "rate": rate, "amount": _money(base * rate)}
        for name, rate in rates.items()
    ]


def _progressive_tax(amount: float, brackets: list[tuple[int | None, float]]) -> tuple[float, list[dict[str, Any]]]:
    amount = max(float(amount or 0), 0)
    lower = 0.0
    total = 0.0
    detail = []
    for upper, rate in brackets:
        cap = amount if upper is None else min(amount, float(upper))
        taxable = max(cap - lower, 0)
        tax = taxable * rate
        detail.append({
            "from": _money(lower),
            "to": upper,
            "rate": rate,
            "taxable": _money(taxable),
            "tax": _money(tax),
        })
        total += tax
        if upper is None or amount <= upper:
            break
        lower = float(upper)
    return _money(total), detail


def _scale_rate(amount: float, scale: list[tuple[int | None, float]]) -> float:
    amount = max(float(amount or 0), 0)
    for upper, rate in scale:
        if upper is None or amount <= upper:
            return rate
    return scale[-1][1]


def _asset_depreciation(cost: float, purchase_year: int | None, useful_life_years: int | None) -> dict[str, Any]:
    useful_life = max(int(useful_life_years or 0), 1)
    current_year = datetime.now().year
    age_years = max(current_year - int(purchase_year or current_year), 0)
    elapsed_years = min(age_years, useful_life)
    annual_depreciation = cost / useful_life
    accumulated = min(annual_depreciation * elapsed_years, cost)
    remaining = max(cost - accumulated, 0)
    monthly_depreciation = annual_depreciation / 12 if remaining > 0 else 0
    return {
        "purchase_year": purchase_year,
        "useful_life_years": useful_life,
        "age_years": age_years,
        "accumulated_depreciation": _money(accumulated),
        "remaining_book_value": _money(remaining),
        "monthly_depreciation": _money(monthly_depreciation),
    }


def _is_asset_category(category: str) -> bool:
    text = _plain(category)
    if any(word in text for word in NON_DEPRECIABLE_KEYWORDS):
        return False
    return any(word in text for word in DEPRECIABLE_KEYWORDS)


def _expense_total(req: SalaryCalculatorRequest) -> tuple[float, list[dict[str, Any]]]:
    items = []
    for item in req.expenses:
        if not item.amount:
            continue
        row = {"category": item.category, "amount": _money(item.amount), "note": item.note}
        if _is_asset_category(item.category):
            dep = _asset_depreciation(item.amount, item.purchase_year, item.useful_life_years or 10)
            row.update(dep)
            row["original_cost"] = _money(item.amount)
            row["amount"] = dep["monthly_depreciation"]
            row["note"] = item.note or "Gasto por depreciacion mensual referencial"
        items.append(row)
    if req.vehicle_debt_amount:
        dep = _asset_depreciation(req.vehicle_debt_amount, req.vehicle_purchase_year, req.vehicle_useful_life_years or 10)
        items.append({
            "category": "Depreciacion vehicular referencial",
            "amount": dep["monthly_depreciation"],
            "original_cost": _money(req.vehicle_debt_amount),
            "note": "Estimación mensual por antigüedad y vida útil",
            **dep,
        })
    if req.vehicle_monthly_payment:
        items.append({"category": "Cuota vehicular", "amount": _money(req.vehicle_monthly_payment), "note": "Gasto deducible indicado"})
    return _money(sum(item["amount"] for item in items)), items


def _pyme_exemption(req: SalaryCalculatorRequest, gross_annual: float) -> tuple[float, bool, bool]:
    if not req.is_pyme or gross_annual > CORPORATE_GROSS_THRESHOLD_ANNUAL:
        return 0.0, False, bool(req.is_pyme and gross_annual > CORPORATE_GROSS_THRESHOLD_ANNUAL)
    if 1 <= req.pyme_year <= 3:
        return 1.0, True, False
    if 4 <= req.pyme_year <= 5:
        return 0.75, True, False
    if req.pyme_year == 6:
        return 0.50, True, False
    return 0.0, True, False


def _employee(req: SalaryCalculatorRequest) -> dict[str, Any]:
    gross = _money(req.amount)
    worker = _components(gross, EMPLOYEE_WORKER_RATES)
    employer = _components(gross, EMPLOYEE_EMPLOYER_RATES)
    salary_tax, tax_detail = _progressive_tax(gross, SALARY_TAX_BRACKETS_MONTHLY)
    worker_total = _money(sum(item["amount"] for item in worker))
    employer_total = _money(sum(item["amount"] for item in employer))
    return {
        "scenario": "EMPLOYEE",
        "gross_salary": gross,
        "worker_contributions": worker,
        "worker_contributions_total": worker_total,
        "salary_income_tax": salary_tax,
        "salary_income_tax_detail": tax_detail,
        "net_salary": _money(gross - worker_total - salary_tax),
        "employer_contributions": employer,
        "employer_contributions_total": employer_total,
        "total_company_cost": _money(gross + employer_total),
    }


def _independent(req: SalaryCalculatorRequest) -> dict[str, Any]:
    gross = _money(req.amount)
    vat = _money(gross * 0.13)
    gross_annual = _money(gross * 12)
    expenses_total, expenses = _expense_total(req)
    net_before_ccss = _money(max(gross - expenses_total, 0))
    ccss_rate = _scale_rate(net_before_ccss, INDEPENDENT_CCSS_SCALE_MONTHLY)
    ccss = _money(net_before_ccss * ccss_rate)
    taxable_monthly = _money(max(net_before_ccss - ccss, 0))
    taxable_annual = _money(taxable_monthly * 12)
    base_annual_tax, tax_detail = _progressive_tax(taxable_annual, INDIVIDUAL_BUSINESS_TAX_BRACKETS_ANNUAL)
    pyme_exemption_rate, pyme_applied, pyme_limit_exceeded = _pyme_exemption(req, gross_annual)
    annual_tax = _money(base_annual_tax * (1 - pyme_exemption_rate))
    return {
        "scenario": "INDEPENDENT",
        "monthly_invoice_subtotal": gross,
        "vat_13": vat,
        "monthly_invoice_total": _money(gross + vat),
        "annual_gross_income": gross_annual,
        "deductible_expenses": expenses,
        "deductible_expenses_total": expenses_total,
        "net_before_ccss": net_before_ccss,
        "ccss_rate": ccss_rate,
        "ccss_independent": ccss,
        "taxable_income_monthly_reference": taxable_monthly,
        "taxable_income_annual_reference": taxable_annual,
        "base_annual_income_tax": base_annual_tax,
        "pyme_applied": pyme_applied,
        "pyme_gross_limit_exceeded": pyme_limit_exceeded,
        "pyme_exemption_rate": pyme_exemption_rate,
        "annual_income_tax": annual_tax,
        "monthly_income_tax_reference": _money(annual_tax / 12),
        "net_after_ccss_and_tax_monthly_reference": _money(taxable_monthly - annual_tax / 12),
        "cash_remaining_monthly_reference": _money(gross - expenses_total - ccss - annual_tax / 12),
        "income_tax_detail": tax_detail,
    }


def _owner(req: SalaryCalculatorRequest) -> dict[str, Any]:
    gross_monthly = _money(req.amount)
    vat = _money(gross_monthly * 0.13)
    gross_annual = _money(gross_monthly * 12)
    expenses_total_monthly, expenses = _expense_total(req)
    distribution = _money(req.distribution_amount if req.distribution_amount else (gross_monthly if req.distribution_type != "NONE" else 0))
    distribution_tax = _money(distribution * 0.15)
    distribution_net = _money(distribution - distribution_tax)
    deductible_distribution = distribution if req.distribution_type == "DIETAS" else 0
    net_annual = _money(max(gross_annual - expenses_total_monthly * 12 - deductible_distribution * 12, 0))

    if gross_annual > CORPORATE_GROSS_THRESHOLD_ANNUAL:
        base_tax = _money(net_annual * 0.30)
        corporate_tax_detail = [{"from": 0, "to": None, "rate": 0.30, "taxable": net_annual, "tax": base_tax}]
        regime = "GENERAL_30"
    else:
        base_tax, corporate_tax_detail = _progressive_tax(net_annual, CORPORATE_TAX_BRACKETS_ANNUAL)
        regime = "MICRO_SMALL_PROGRESSIVE"

    pyme_exemption_rate, pyme_applied, pyme_limit_exceeded = _pyme_exemption(req, gross_annual)

    final_tax = _money(base_tax * (1 - pyme_exemption_rate))
    return {
        "scenario": "OWNER",
        "monthly_gross_income": gross_monthly,
        "vat_13": vat,
        "monthly_income_total_with_vat": _money(gross_monthly + vat),
        "annual_gross_income": gross_annual,
        "deductible_expenses": expenses,
        "deductible_expenses_total_monthly": expenses_total_monthly,
        "distribution_type": req.distribution_type,
        "distribution_gross_monthly": distribution,
        "distribution_withholding_15": distribution_tax,
        "distribution_net_monthly": distribution_net,
        "distribution_is_deductible": req.distribution_type == "DIETAS",
        "annual_net_taxable_income": net_annual,
        "corporate_regime": regime,
        "base_corporate_income_tax": base_tax,
        "pyme_applied": pyme_applied,
        "pyme_gross_limit_exceeded": pyme_limit_exceeded,
        "pyme_exemption_rate": pyme_exemption_rate,
        "annual_corporate_income_tax": final_tax,
        "monthly_corporate_income_tax_reference": _money(final_tax / 12),
        "cash_remaining_monthly_reference": _money(gross_monthly - expenses_total_monthly - final_tax / 12 - distribution_tax),
        "corporate_tax_detail": corporate_tax_detail,
    }


def calculate_payload(req: SalaryCalculatorRequest) -> dict[str, Any]:
    if req.scenario == "EMPLOYEE":
        result = _employee(req)
    elif req.scenario == "INDEPENDENT":
        result = _independent(req)
    else:
        result = _owner(req)
    result["currency"] = "CRC"
    result["rule_version"] = "CR-2026"
    result["disclaimer"] = "Calculo referencial para planeacion. Validar declaracion final con contador y normativa vigente."
    return result


@router.get("/rules", dependencies=[Depends(require_permission("hhrr", "view"))])
def get_rules():
    return {
        "version": "CR-2026",
        "expense_categories": DEFAULT_EXPENSE_CATEGORIES,
        "employee_worker_rates": EMPLOYEE_WORKER_RATES,
        "employee_employer_rates": EMPLOYEE_EMPLOYER_RATES,
        "salary_tax_brackets_monthly": SALARY_TAX_BRACKETS_MONTHLY,
        "independent_ccss_scale_monthly": INDEPENDENT_CCSS_SCALE_MONTHLY,
        "individual_business_tax_brackets_annual": INDIVIDUAL_BUSINESS_TAX_BRACKETS_ANNUAL,
        "corporate_gross_threshold_annual": CORPORATE_GROSS_THRESHOLD_ANNUAL,
        "pyme_reference_threshold_annual": PYME_REFERENCE_THRESHOLD_ANNUAL,
        "corporate_tax_brackets_annual": CORPORATE_TAX_BRACKETS_ANNUAL,
    }


@router.post("/calculate", dependencies=[Depends(require_permission("hhrr", "view"))])
def calculate_salary(
    req: SalaryCalculatorRequest,
    x_user: str | None = Header(None, alias="X-User"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    _ensure_schema(conn)
    result = calculate_payload(req)
    if req.save:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO hr_salary_calculations (
                company_code, scenario, label, input_payload, result_payload, created_by, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                company_code(header_value=x_company_code),
                req.scenario,
                req.label,
                Json(req.dict()),
                Json(result),
                x_user,
                datetime.now(),
            ),
        )
        result["saved_id"] = cur.fetchone()[0]
        conn.commit()
    return result


@router.get("/history", dependencies=[Depends(require_permission("hhrr", "view"))])
def history(
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    limit: int = 50,
    conn=Depends(get_db),
):
    _ensure_schema(conn)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT id, company_code, scenario, label, input_payload, result_payload, created_by, created_at
        FROM hr_salary_calculations
        WHERE company_code = %s
        ORDER BY created_at DESC
        LIMIT %s
        """,
        (company_code(header_value=x_company_code), min(max(limit, 1), 200)),
    )
    return {"data": [dict(row) for row in cur.fetchall()]}
