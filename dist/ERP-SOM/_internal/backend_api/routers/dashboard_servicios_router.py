# ============================================================
# ERP-SOM
# Dashboard Servicios Router (psycopg2 compatible)
# Filtros cascada: año / país / puerto / cliente
# Default: año en curso usando fecha_inicio
# ============================================================

from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from database import get_db
from services.tenanting import company_code, ensure_company_column


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


# ============================================================
# HELPERS
# ============================================================

def _safe_list(result):
    return result if result is not None else []


# ============================================================
# DASHBOARD SERVICIOS
# ============================================================

@router.get("/servicios")
def get_dashboard_servicios(
    anio: int | None = Query(default=None),
    pais: str | None = Query(default=None),
    puerto: str | None = Query(default=None),
    cliente: str | None = Query(default=None),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    db=Depends(get_db)
):

    try:

        cursor = db.cursor()
        ensure_company_column("servicios")
        ensure_company_column("collections")
        company = company_code(header_value=x_company_code)

        # ----------------------------------------------------
        # DEFAULT YEAR = AÑO ACTUAL
        # Tomado contra fecha_inicio (yyyy-mm-dd)
        # ----------------------------------------------------

        anio_final = anio if anio is not None else datetime.now().year

        # ----------------------------------------------------
        # QUERY
        # ----------------------------------------------------

        query = """
        WITH base AS (
            SELECT
                consec,
                tipo,
                estado,
                num_informe,
                buque_contenedor,
                cliente,
                contacto,
                detalle,
                continente,
                pais,
                puerto,
                operacion,
                surveyor,
                COALESCE(honorarios, 0) AS honorarios,
                COALESCE(costo_operativo, 0) AS costo_operativo,
                fecha_inicio,
                hora_inicio,
                fecha_fin,
                hora_fin,
                demoras,
                duracion,
                factura,
                COALESCE(valor_factura, 0) AS valor_factura,
                fecha_factura,
                terminos_pago,
                fecha_vencimiento,
                dias_vencido,
                razon_cancelacion,
                comentario_cancelacion,
                status_informe,
                COALESCE(costo_tarjetas, 0) AS costo_tarjetas,
                (
                    COALESCE(valor_factura, 0)
                    - COALESCE(costo_operativo, 0)
                    - COALESCE(costo_tarjetas, 0)
                ) AS profit,
                CAST(SUBSTRING(CAST(fecha_inicio AS TEXT), 1, 4) AS INTEGER) AS anio_servicio
            FROM servicios
            WHERE fecha_inicio IS NOT NULL
              AND company_code = %s
        ),

        filtrada AS (
            SELECT *
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND (%s IS NULL OR puerto = %s)
              AND (%s IS NULL OR cliente = %s)
        ),

        scope_pais AS (
            SELECT DISTINCT pais
            FROM base
            WHERE anio_servicio = %s
              AND pais IS NOT NULL
            ORDER BY pais
        ),

        scope_puerto AS (
            SELECT DISTINCT puerto
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND puerto IS NOT NULL
            ORDER BY puerto
        ),

        scope_cliente AS (
            SELECT DISTINCT cliente
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND (%s IS NULL OR puerto = %s)
              AND cliente IS NOT NULL
            ORDER BY cliente
        )

        SELECT json_build_object(

            -- ================================================
            -- FILTROS DISPONIBLES
            -- ================================================
            'filtros', json_build_object(
                'anio_actual', %s,
                'anio_seleccionado', %s,
                'pais_seleccionado', %s,
                'puerto_seleccionado', %s,
                'cliente_seleccionado', %s,

                'anios', COALESCE((
                    SELECT json_agg(t)
                    FROM (
                        SELECT DISTINCT anio_servicio AS anio
                        FROM base
                        WHERE anio_servicio IS NOT NULL
                        ORDER BY anio_servicio DESC
                    ) t
                ), '[]'::json),

                'paises', COALESCE((
                    SELECT json_agg(t)
                    FROM (
                        SELECT pais
                        FROM scope_pais
                    ) t
                ), '[]'::json),

                'puertos', COALESCE((
                    SELECT json_agg(t)
                    FROM (
                        SELECT puerto
                        FROM scope_puerto
                    ) t
                ), '[]'::json),

                'clientes', COALESCE((
                    SELECT json_agg(t)
                    FROM (
                        SELECT cliente
                        FROM scope_cliente
                    ) t
                ), '[]'::json)
            ),

            -- ================================================
            -- KPIS
            -- ================================================
            'kpis', json_build_object(
                'total_operaciones', COALESCE((SELECT COUNT(*) FROM filtrada), 0),
                'total_servicios', COALESCE((SELECT COUNT(*) FROM filtrada), 0),
                'total_facturado', COALESCE((SELECT SUM(valor_factura) FROM filtrada), 0),
                'total_ar', COALESCE((
                    SELECT SUM(c.saldo_pendiente)
                    FROM collections c
                    WHERE c.tipo_documento = 'FACTURA'
                      AND c.saldo_pendiente > 0
                      AND c.company_code = %s
                      AND EXTRACT(YEAR FROM c.fecha_emision) = %s
                      AND (%s IS NULL OR c.nombre_cliente = %s OR c.codigo_cliente = %s)
                ), 0),
                'total_profit', COALESCE((SELECT SUM(profit) FROM filtrada), 0),
                'total_paises', COALESCE((SELECT COUNT(DISTINCT pais) FROM filtrada WHERE pais IS NOT NULL), 0),
                'total_puertos', COALESCE((SELECT COUNT(DISTINCT puerto) FROM filtrada WHERE puerto IS NOT NULL), 0),
                'total_clientes', COALESCE((SELECT COUNT(DISTINCT cliente) FROM filtrada WHERE cliente IS NOT NULL), 0)
            ),

            -- ================================================
            -- GRAFICOS
            -- ================================================
            'servicios_por_pais', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        pais,
                        COUNT(*) AS total
                    FROM filtrada
                    WHERE pais IS NOT NULL
                    GROUP BY pais
                    ORDER BY total DESC, pais
                    LIMIT 10
                ) t
            ), '[]'::json),

            'servicios_por_operacion', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        operacion,
                        COUNT(*) AS total
                    FROM filtrada
                    WHERE operacion IS NOT NULL
                    GROUP BY operacion
                    ORDER BY total DESC, operacion
                    LIMIT 10
                ) t
            ), '[]'::json),

            'facturacion_por_pais', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        pais,
                        SUM(valor_factura) AS total_facturado
                    FROM filtrada
                    WHERE pais IS NOT NULL
                    GROUP BY pais
                    ORDER BY total_facturado DESC, pais
                    LIMIT 10
                ) t
            ), '[]'::json),

            'facturacion_por_tipo', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        tipo,
                        SUM(valor_factura) AS total_facturado
                    FROM filtrada
                    WHERE tipo IS NOT NULL
                    GROUP BY tipo
                    ORDER BY total_facturado DESC, tipo
                ) t
            ), '[]'::json),

            'top_puertos', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        puerto,
                        COUNT(*) AS total
                    FROM filtrada
                    WHERE puerto IS NOT NULL
                    GROUP BY puerto
                    ORDER BY total DESC, puerto
                    LIMIT 10
                ) t
            ), '[]'::json),

            'revenue_mensual', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        SUBSTRING(CAST(fecha_inicio AS TEXT), 1, 7) AS mes,
                        SUM(valor_factura) AS revenue
                    FROM filtrada
                    WHERE fecha_inicio IS NOT NULL
                    GROUP BY SUBSTRING(CAST(fecha_inicio AS TEXT), 1, 7)
                    ORDER BY mes
                ) t
            ), '[]'::json),

            'profit_por_surveyor', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        surveyor,
                        SUM(profit) AS profit_total
                    FROM filtrada
                    WHERE surveyor IS NOT NULL
                    GROUP BY surveyor
                    ORDER BY profit_total DESC, surveyor
                    LIMIT 10
                ) t
            ), '[]'::json),

            'clientes_top', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        cliente,
                        SUM(valor_factura) AS revenue
                    FROM filtrada
                    WHERE cliente IS NOT NULL
                    GROUP BY cliente
                    ORDER BY revenue DESC, cliente
                    LIMIT 10
                ) t
            ), '[]'::json)

        ) AS dashboard;
        """

        params = (
            company,
            anio_final,
            pais, pais,
            puerto, puerto,
            cliente, cliente,

            anio_final,

            anio_final,
            pais, pais,

            anio_final,
            pais, pais,
            puerto, puerto,

            datetime.now().year,
            anio_final,
            pais,
            puerto,
            cliente,

            company,
            anio_final,
            cliente, cliente, cliente,
        )

        cursor.execute(query, params)
        result = cursor.fetchone()

        if not result or not result[0]:
            return {
                "filtros": {
                    "anio_actual": datetime.now().year,
                    "anio_seleccionado": anio_final,
                    "pais_seleccionado": pais,
                    "puerto_seleccionado": puerto,
                    "cliente_seleccionado": cliente,
                    "anios": [],
                    "paises": [],
                    "puertos": [],
                    "clientes": []
                },
                "kpis": {
                    "total_operaciones": 0,
                    "total_servicios": 0,
                    "total_facturado": 0,
                    "total_ar": 0,
                    "total_profit": 0,
                    "total_paises": 0,
                    "total_puertos": 0,
                    "total_clientes": 0
                },
                "servicios_por_pais": [],
                "servicios_por_operacion": [],
                "facturacion_por_pais": [],
                "facturacion_por_tipo": [],
                "top_puertos": [],
                "revenue_mensual": [],
                "profit_por_surveyor": [],
                "clientes_top": []
            }

        return result[0]

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error generando dashboard servicios: {str(e)}"
        )
