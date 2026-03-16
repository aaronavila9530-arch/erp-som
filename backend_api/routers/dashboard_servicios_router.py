# ============================================================
# ERP-SOM
# Dashboard Servicios Router (psycopg2 compatible)
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from database import get_db


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


# ============================================================
# DASHBOARD SERVICIOS
# ============================================================

@router.get("/servicios")
def get_dashboard_servicios(db = Depends(get_db)):

    try:

        cursor = db.cursor()

        query = """

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

        )

        """

        cursor.execute(query)

        result = cursor.fetchone()

        if not result:
            return {}

        return result[0]

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error generando dashboard servicios: {str(e)}"
        )