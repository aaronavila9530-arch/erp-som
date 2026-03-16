# ============================================================
# ERP-SOM
# Dashboard Servicios Router (Advanced Analytics)
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


# ============================================================
# DASHBOARD SERVICIOS (ADVANCED)
# ============================================================

@router.get("/servicios")
def get_dashboard_servicios(db: Session = Depends(get_db)):

    try:

        # ====================================================
        # DATASET BASE
        # ====================================================

        query = text("""

        WITH base AS (
            SELECT
                pais,
                puerto,
                operacion,
                tipo,
                cliente,
                surveyor,
                COALESCE(valor_factura,0) AS valor_factura,
                COALESCE(costo_operativo,0) AS costo_operativo,
                COALESCE(valor_factura,0) - COALESCE(costo_operativo,0) AS profit,
                fecha_factura
            FROM servicios
        )

        SELECT json_build_object(

        -- ===================================================
        -- SERVICIOS POR PAIS
        -- ===================================================
        'servicios_por_pais', (
            SELECT json_agg(t)
            FROM (
                SELECT pais, COUNT(*) AS total
                FROM base
                WHERE pais IS NOT NULL
                GROUP BY pais
                ORDER BY total DESC
            ) t
        ),

        -- ===================================================
        -- SERVICIOS POR OPERACION
        -- ===================================================
        'servicios_por_operacion', (
            SELECT json_agg(t)
            FROM (
                SELECT operacion, COUNT(*) AS total
                FROM base
                WHERE operacion IS NOT NULL
                GROUP BY operacion
                ORDER BY total DESC
            ) t
        ),

        -- ===================================================
        -- FACTURACION POR PAIS
        -- ===================================================
        'facturacion_por_pais', (
            SELECT json_agg(t)
            FROM (
                SELECT pais, SUM(valor_factura) AS total_facturado
                FROM base
                WHERE pais IS NOT NULL
                GROUP BY pais
                ORDER BY total_facturado DESC
            ) t
        ),

        -- ===================================================
        -- FACTURACION POR TIPO
        -- ===================================================
        'facturacion_por_tipo', (
            SELECT json_agg(t)
            FROM (
                SELECT tipo, SUM(valor_factura) AS total_facturado
                FROM base
                WHERE tipo IS NOT NULL
                GROUP BY tipo
                ORDER BY total_facturado DESC
            ) t
        ),

        -- ===================================================
        -- TOP PUERTOS
        -- ===================================================
        'top_puertos', (
            SELECT json_agg(t)
            FROM (
                SELECT puerto, COUNT(*) AS total
                FROM base
                WHERE puerto IS NOT NULL
                GROUP BY puerto
                ORDER BY total DESC
                LIMIT 10
            ) t
        ),

        -- ===================================================
        -- REVENUE MENSUAL
        -- ===================================================
        'revenue_mensual', (
            SELECT json_agg(t)
            FROM (
                SELECT
                    DATE_TRUNC('month', fecha_factura) AS mes,
                    SUM(valor_factura) AS revenue
                FROM base
                WHERE fecha_factura IS NOT NULL
                GROUP BY mes
                ORDER BY mes
            ) t
        ),

        -- ===================================================
        -- PROFIT POR SURVEYOR
        -- ===================================================
        'profit_por_surveyor', (
            SELECT json_agg(t)
            FROM (
                SELECT
                    surveyor,
                    SUM(profit) AS profit_total
                FROM base
                WHERE surveyor IS NOT NULL
                GROUP BY surveyor
                ORDER BY profit_total DESC
            ) t
        ),

        -- ===================================================
        -- CLIENTES MAS RENTABLES
        -- ===================================================
        'clientes_top', (
            SELECT json_agg(t)
            FROM (
                SELECT
                    cliente,
                    SUM(valor_factura) AS revenue
                FROM base
                WHERE cliente IS NOT NULL
                GROUP BY cliente
                ORDER BY revenue DESC
                LIMIT 10
            ) t
        )

        ) AS dashboard

        """)

        result = db.execute(query).fetchone()

        if not result:
            return {}

        return result.dashboard

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error generando dashboard servicios: {str(e)}"
        )