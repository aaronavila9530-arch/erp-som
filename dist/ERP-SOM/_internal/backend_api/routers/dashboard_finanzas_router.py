# ============================================================
# ERP-SOM
# DASHBOARD FINANZAS ROUTER
# ============================================================

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db


router = APIRouter(
    prefix="/dashboard-finanzas",
    tags=["Dashboard Finanzas"]
)


# ============================================================
# DASHBOARD RESUMEN FINANCIERO
# ============================================================

@router.get("/resumen")
def dashboard_finanzas_resumen(
    anio: int | None = Query(default=None),
    cliente: str | None = Query(default=None),
    db=Depends(get_db)
):

    try:

        cursor = db.cursor()

        anio_final = anio if anio else datetime.now().year

        query = """
        WITH invoices AS (

            SELECT
                codigo_cliente,
                nombre_cliente,
                fecha_emision,
                moneda,
                total,
                EXTRACT(YEAR FROM fecha_emision) AS anio
            FROM invoicing

        ),

        collections_base AS (

            SELECT
                codigo_cliente,
                nombre_cliente,
                fecha_emision,
                saldo_pendiente,
                bucket_aging,
                EXTRACT(YEAR FROM fecha_emision) AS anio
            FROM collections

        ),

        payments AS (

            SELECT
                codigo_cliente,
                fecha_pago,
                monto,
                EXTRACT(YEAR FROM fecha_pago) AS anio
            FROM incoming_payments

        ),

        obligations AS (

            SELECT
                payee_name,
                due_date,
                balance,
                status,
                EXTRACT(YEAR FROM issue_date) AS anio
            FROM payment_obligations

        )

        SELECT json_build_object(

            'kpis', json_build_object(

                'revenue_total',
                (SELECT COALESCE(SUM(total),0)
                 FROM invoices
                 WHERE anio=%s
                 AND (%s IS NULL OR codigo_cliente=%s)),

                'ar_total',
                (SELECT COALESCE(SUM(saldo_pendiente),0)
                 FROM collections_base
                 WHERE anio=%s
                 AND (%s IS NULL OR codigo_cliente=%s)),

                'payments_total',
                (SELECT COALESCE(SUM(monto),0)
                 FROM payments
                 WHERE anio=%s
                 AND (%s IS NULL OR codigo_cliente=%s)),

                'ap_total',
                (SELECT COALESCE(SUM(balance),0)
                 FROM obligations
                 WHERE anio=%s
                 AND status='PENDING')

            ),

            'revenue_mensual', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        TO_CHAR(fecha_emision,'YYYY-MM') mes,
                        SUM(total) revenue
                    FROM invoicing
                    WHERE EXTRACT(YEAR FROM fecha_emision)=%s
                    GROUP BY mes
                    ORDER BY mes
                ) t
            ), '[]'::json),

            'aging_ar', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        bucket_aging,
                        SUM(saldo_pendiente) total
                    FROM collections
                    WHERE saldo_pendiente > 0
                    GROUP BY bucket_aging
                ) t
            ), '[]'::json),

            'top_clientes_deuda', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        nombre_cliente,
                        SUM(saldo_pendiente) deuda
                    FROM collections
                    GROUP BY nombre_cliente
                    ORDER BY deuda DESC
                    LIMIT 10
                ) t
            ), '[]'::json)

        ) AS dashboard
        """

        params = (
            anio_final, cliente, cliente,
            anio_final, cliente, cliente,
            anio_final, cliente, cliente,
            anio_final,
            anio_final
        )

        cursor.execute(query, params)

        result = cursor.fetchone()

        return result[0]

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error dashboard finanzas: {str(e)}"
        )