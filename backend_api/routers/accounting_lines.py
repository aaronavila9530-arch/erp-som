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
        sql = """
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
                al.created_at
            FROM accounting_lines al
            JOIN accounting_entries ae ON ae.id = al.entry_id
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

        # ----------------------------------------------------
        # FILTRO CUENTA (jerárquico)
        # ejemplo: 1.1.02 → trae 1.1.02.01, 1.1.02.02 etc
        # ----------------------------------------------------
        if account_code:
            account_code = account_code.strip()

            if account_code:
                filtros.append("al.account_code LIKE %s")
                params.append(f"{account_code}%")

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
