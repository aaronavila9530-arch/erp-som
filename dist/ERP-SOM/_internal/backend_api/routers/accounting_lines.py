from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header,
    Query
)
from psycopg2.extras import RealDictCursor

from database import get_db
from rbac_service import has_permission
from services.tenanting import company_code


router = APIRouter(
    prefix="/accounting-lines",
    tags=["Accounting"]
)

ACCOUNT_TYPE_ALIASES = {
    "ACTIVO": ("ACTIVO", "ASSET"),
    "ASSET": ("ACTIVO", "ASSET"),
    "PASIVO": ("PASIVO", "LIABILITY"),
    "LIABILITY": ("PASIVO", "LIABILITY"),
    "PATRIMONIO": ("PATRIMONIO", "EQUITY"),
    "EQUITY": ("PATRIMONIO", "EQUITY"),
    "INGRESO": ("INGRESO", "REVENUE", "INCOME"),
    "REVENUE": ("INGRESO", "REVENUE", "INCOME"),
    "INCOME": ("INGRESO", "REVENUE", "INCOME"),
    "COSTO": ("COSTO", "COST"),
    "COST": ("COSTO", "COST"),
    "GASTO": ("GASTO", "EXPENSE"),
    "EXPENSE": ("GASTO", "EXPENSE"),
}


def _account_type_values(value: str | None):
    text = str(value or "").strip().upper()
    if not text or text == "TODOS":
        return None
    return ACCOUNT_TYPE_ALIASES.get(text, (text,))


def _account_type_case() -> str:
    raw_case = "UPPER(COALESCE(a.account_type, ''))"
    return f"""
        CASE
            WHEN {raw_case} IN ('ACTIVO', 'ASSET') THEN 'ACTIVO'
            WHEN {raw_case} IN ('PASIVO', 'LIABILITY') THEN 'PASIVO'
            WHEN {raw_case} IN ('PATRIMONIO', 'EQUITY') THEN 'PATRIMONIO'
            WHEN {raw_case} IN ('INGRESO', 'REVENUE', 'INCOME') THEN 'INGRESO'
            WHEN {raw_case} IN ('COSTO', 'COST') THEN 'COSTO'
            WHEN {raw_case} IN ('GASTO', 'EXPENSE') THEN 'GASTO'
            WHEN al.account_code LIKE '1%%' THEN 'ACTIVO'
            WHEN al.account_code LIKE '2%%' THEN 'PASIVO'
            WHEN al.account_code LIKE '3%%' THEN 'PATRIMONIO'
            WHEN al.account_code LIKE '4%%' THEN 'INGRESO'
            WHEN al.account_code LIKE '5%%' THEN 'GASTO'
            WHEN al.account_code LIKE '6%%' THEN 'COSTO'
            WHEN {raw_case} = '' THEN 'SIN CLASIFICAR'
            ELSE {raw_case}
        END
    """

# ============================================================
# RBAC GUARD
# ============================================================
def require_permission(module: str, action: str):
    def checker(
        x_user_role: str = Header(..., alias="X-User-Role")
    ):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(
                status_code=403,
                detail="No autorizado"
            )
    return checker


# ============================================================
# GET /accounting-lines
# Libro Diario – líneas contables REALES (ERP-SOM BLINDADO)
# ============================================================
@router.get("")
def get_accounting_lines(
    account_code: str | None = Query(None),
    account_type: str | None = Query(None),
    origin: str | None = Query(None),
    period: str | None = Query(None),
    period_from: str | None = Query(None),
    period_to: str | None = Query(None),
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db)
):
    """
    Retorna líneas contables DIRECTAMENTE desde accounting_lines.

    Filosofía ERP-SOM:
    • NO agrupa
    • NO calcula
    • NO inventa

    Solo permite filtros opcionales seguros.
    """

    if not conn:
        raise HTTPException(status_code=500, detail="No DB connection")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # ----------------------------------------------------
        # BASE QUERY
        # ----------------------------------------------------
        sql = f"""
            SELECT
                al.id              AS line_id,
                al.entry_id,
                ae.period,
                ae.entry_date,
                ae.origin,
                ae.workflow_status,
                ae.company_code,
                al.account_code,
                al.account_name,
                al.debit,
                al.credit,
                al.line_description,
                al.created_at,
                {_account_type_case()} AS account_type
            FROM accounting_lines al
            JOIN accounting_entries ae ON ae.id = al.entry_id
            LEFT JOIN accounting_accounts a ON a.account_code = al.account_code
        """

        filtros = []
        params = []
        company = company_code(company_code_param, x_company_code)
        filtros.append("ae.company_code = %s")
        params.append(company)

        if period:
            filtros.append("ae.period = %s")
            params.append(period)
        if period_from:
            filtros.append("ae.period >= %s")
            params.append(period_from)
        if period_to:
            filtros.append("ae.period <= %s")
            params.append(period_to)
        if origin:
            origin_value = origin.strip().upper()
            if origin_value and origin_value != "TODOS":
                if origin_value == "ITP":
                    filtros.append("ae.origin = ANY(%s)")
                    params.append(["ITP", "ITP_PAYMENT", "ITP_BIWEEKLY_PAYMENT"])
                else:
                    filtros.append("ae.origin = %s")
                    params.append(origin_value)

        # ----------------------------------------------------
        # FILTRO CUENTA (jerárquico)
        # ejemplo: 1.1.02 → trae 1.1.02.01, 1.1.02.02 etc
        # ----------------------------------------------------
        if account_code:
            account_code = account_code.strip()

            if account_code:
                filtros.append("al.account_code LIKE %s")
                params.append(f"{account_code}%")

        account_types = _account_type_values(account_type)
        if account_types:
            filtros.append(f"""
                {_account_type_case()} = ANY(%s)
            """)
            params.append(list(account_types))

        # ----------------------------------------------------
        # WHERE DINÁMICO
        # ----------------------------------------------------
        if filtros:
            sql += " WHERE " + " AND ".join(filtros)

        # ----------------------------------------------------
        # ORDER ERP-SOM
        # ----------------------------------------------------
        sql += """
            ORDER BY
                ae.period,
                ae.entry_date,
                al.entry_id,
                al.id
        """

        cur.execute(sql, params)

        rows = cur.fetchall()

        return rows

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error leyendo accounting_lines: {repr(e)}"
        )

    finally:
        cur.close()
