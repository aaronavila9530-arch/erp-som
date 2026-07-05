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


router = APIRouter(
    prefix="/closing/period",
    tags=["Closing - Period"]
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
# GET /closing/period/status
# BLINDADO + AUTO-CREACIÓN SI NO EXISTE
# ============================================================
@router.get("/status")
def get_period_status(
    company_code: str = Query(...),
    fiscal_year: int = Query(...),
    period: int = Query(...),
    ledger: str = Query("0L"),
    conn=Depends(get_db)
):
    """
    Retorna el estado del período contable.
    Si no existe registro en closing_status,
    lo crea automáticamente con valores por defecto.
    """

    cur = None

    try:
        # ----------------------------------------------------
        # 1️⃣ Validaciones defensivas
        # ----------------------------------------------------
        company_code = (company_code or "").strip()
        ledger = (ledger or "0L").strip()

        if not company_code:
            raise HTTPException(400, "company_code es requerido")

        if fiscal_year <= 0:
            raise HTTPException(400, "fiscal_year inválido")

        if period <= 0 or period > 16:
            raise HTTPException(400, "period inválido")

        # ----------------------------------------------------
        # 2️⃣ Cursor
        # ----------------------------------------------------
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # ----------------------------------------------------
        # 3️⃣ Buscar registro existente
        # ----------------------------------------------------
        cur.execute(
            """
            SELECT
                company_code,
                fiscal_year,
                period,
                ledger,
                period_closed,
                gl_closed,
                tb_closed,
                pnl_closed,
                fs_closed,
                fy_opened,
                last_batch_id,
                updated_at
            FROM closing_status
            WHERE company_code = %s
              AND fiscal_year = %s
              AND period = %s
              AND ledger = %s
            """,
            (company_code, fiscal_year, period, ledger)
        )

        row = cur.fetchone()

        # ----------------------------------------------------
        # 4️⃣ Si no existe → crear registro inicial
        # ----------------------------------------------------
        if not row:

            cur.execute(
                """
                INSERT INTO closing_status (
                    company_code,
                    fiscal_year,
                    period,
                    ledger,
                    period_closed,
                    gl_closed,
                    tb_closed,
                    pnl_closed,
                    fs_closed,
                    fy_opened,
                    last_batch_id,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s,
                    FALSE, FALSE, FALSE, FALSE, FALSE, FALSE,
                    NULL,
                    NOW()
                )
                RETURNING
                    company_code,
                    fiscal_year,
                    period,
                    ledger,
                    period_closed,
                    gl_closed,
                    tb_closed,
                    pnl_closed,
                    fs_closed,
                    fy_opened,
                    last_batch_id,
                    updated_at
                """,
                (company_code, fiscal_year, period, ledger)
            )

            row = cur.fetchone()
            conn.commit()

        return row

    except HTTPException:
        if conn:
            conn.rollback()
        raise

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando estado del período: {repr(e)}"
        )

    finally:
        if cur:
            cur.close()
