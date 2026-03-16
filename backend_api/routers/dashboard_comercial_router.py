# ============================================================
# ERP-SOM
# DASHBOARD COMERCIAL ROUTER
# Basado en tabla: servicios
# Filtros cascada dinámicos
# Default: año en curso
# ============================================================

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from database import get_db


router = APIRouter(
    prefix="/dashboard-comercial",
    tags=["Dashboard Comercial"]
)


# ============================================================
# HELPERS
# ============================================================

def _empty_filtros(anio_seleccionado=None, pais=None, puerto=None, cliente=None, operacion=None):
    return {
        "anio_actual": datetime.now().year,
        "anio_seleccionado": anio_seleccionado if anio_seleccionado is not None else datetime.now().year,
        "pais_seleccionado": pais,
        "puerto_seleccionado": puerto,
        "cliente_seleccionado": cliente,
        "operacion_seleccionada": operacion,
        "anios": [],
        "paises": [],
        "puertos": [],
        "clientes": [],
        "operaciones": []
    }


def _empty_dashboard(anio_seleccionado=None, pais=None, puerto=None, cliente=None, operacion=None):
    return {
        "filtros": _empty_filtros(
            anio_seleccionado=anio_seleccionado,
            pais=pais,
            puerto=puerto,
            cliente=cliente,
            operacion=operacion
        ),
        "kpis": {
            "ticket_promedio": 0,
            "total_puertos": 0,
            "total_servicios": 0,
            "revenue_total": 0,
            "gastos_total": 0,
            "margen_bruto_usd": 0,
            "margen_bruto_pct": 0,
            "margen_neto_usd": 0,
            "margen_neto_pct": 0,
            "utilidad_usd": 0,
            "utilidad_pct": 0,
            "clientes_activos": 0,
            "paises_activos": 0
        },
        "revenue_mensual": [],
        "revenue_por_puerto": [],
        "servicios_por_puerto": [],
        "gastos_por_puerto": [],
        "margen_neto_por_puerto": [],
        "servicios_por_operacion": [],
        "clientes_por_puerto": [],
        "clientes_por_pais": [],
        "revenue_por_pais": [],
        "margen_pct_por_pais": []
    }


# ============================================================
# FILTROS COMERCIALES
# ============================================================

@router.get("/filtros")
def get_dashboard_comercial_filtros(
    anio: int | None = Query(default=None),
    pais: str | None = Query(default=None),
    puerto: str | None = Query(default=None),
    cliente: str | None = Query(default=None),
    operacion: str | None = Query(default=None),
    db=Depends(get_db)
):
    """
    Endpoint solo para poblar filtros dinámicos en cascada.
    Se puede llamar al abrir pantalla o cuando cambian combos.
    """

    try:

        cursor = db.cursor()

        anio_final = anio if anio is not None else datetime.now().year

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
                EXTRACT(YEAR FROM fecha_inicio)::int AS anio_servicio
            FROM servicios
            WHERE fecha_inicio IS NOT NULL
        ),

        scope_pais AS (
            SELECT DISTINCT pais
            FROM base
            WHERE anio_servicio = %s
              AND pais IS NOT NULL
              AND TRIM(pais) <> ''
            ORDER BY pais
        ),

        scope_puerto AS (
            SELECT DISTINCT puerto
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND puerto IS NOT NULL
              AND TRIM(puerto) <> ''
            ORDER BY puerto
        ),

        scope_cliente AS (
            SELECT DISTINCT cliente
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND (%s IS NULL OR puerto = %s)
              AND cliente IS NOT NULL
              AND TRIM(cliente) <> ''
            ORDER BY cliente
        ),

        scope_operacion AS (
            SELECT DISTINCT operacion
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND (%s IS NULL OR puerto = %s)
              AND (%s IS NULL OR cliente = %s)
              AND operacion IS NOT NULL
              AND TRIM(operacion) <> ''
            ORDER BY operacion
        )

        SELECT json_build_object(
            'anio_actual', %s,
            'anio_seleccionado', %s,
            'pais_seleccionado', %s,
            'puerto_seleccionado', %s,
            'cliente_seleccionado', %s,
            'operacion_seleccionada', %s,

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
            ), '[]'::json),

            'operaciones', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT operacion
                    FROM scope_operacion
                ) t
            ), '[]'::json)
        ) AS filtros;
        """

        params = (
            anio_final,

            anio_final,
            pais, pais,

            anio_final,
            pais, pais,
            puerto, puerto,

            anio_final,
            pais, pais,
            puerto, puerto,
            cliente, cliente,

            datetime.now().year,
            anio_final,
            pais,
            puerto,
            cliente,
            operacion
        )

        cursor.execute(query, params)
        result = cursor.fetchone()

        if not result or not result[0]:
            return _empty_filtros(
                anio_seleccionado=anio_final,
                pais=pais,
                puerto=puerto,
                cliente=cliente,
                operacion=operacion
            )

        return result[0]

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo filtros dashboard comercial: {str(e)}"
        )


# ============================================================
# DASHBOARD COMERCIAL - RESUMEN
# ============================================================

@router.get("/resumen")
def get_dashboard_comercial_resumen(
    anio: int | None = Query(default=None),
    pais: str | None = Query(default=None),
    puerto: str | None = Query(default=None),
    cliente: str | None = Query(default=None),
    operacion: str | None = Query(default=None),
    db=Depends(get_db)
):
    """
    Dashboard comercial completo basado en servicios.
    Incluye filtros + KPIs + gráficos.
    """

    try:

        cursor = db.cursor()

        anio_final = anio if anio is not None else datetime.now().year

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
                EXTRACT(YEAR FROM fecha_inicio)::int AS anio_servicio,
                TO_CHAR(fecha_inicio, 'YYYY-MM') AS mes,
                (
                    COALESCE(honorarios, 0)
                    + COALESCE(costo_operativo, 0)
                ) AS costo_directo,
                (
                    COALESCE(honorarios, 0)
                    + COALESCE(costo_operativo, 0)
                    + COALESCE(costo_tarjetas, 0)
                ) AS gasto_total,
                (
                    COALESCE(valor_factura, 0)
                    - (
                        COALESCE(honorarios, 0)
                        + COALESCE(costo_operativo, 0)
                    )
                ) AS margen_bruto_usd,
                (
                    COALESCE(valor_factura, 0)
                    - (
                        COALESCE(honorarios, 0)
                        + COALESCE(costo_operativo, 0)
                        + COALESCE(costo_tarjetas, 0)
                    )
                ) AS margen_neto_usd
            FROM servicios
            WHERE fecha_inicio IS NOT NULL
        ),

        filtrada AS (
            SELECT *
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND (%s IS NULL OR puerto = %s)
              AND (%s IS NULL OR cliente = %s)
              AND (%s IS NULL OR operacion = %s)
        ),

        scope_pais AS (
            SELECT DISTINCT pais
            FROM base
            WHERE anio_servicio = %s
              AND pais IS NOT NULL
              AND TRIM(pais) <> ''
            ORDER BY pais
        ),

        scope_puerto AS (
            SELECT DISTINCT puerto
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND puerto IS NOT NULL
              AND TRIM(puerto) <> ''
            ORDER BY puerto
        ),

        scope_cliente AS (
            SELECT DISTINCT cliente
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND (%s IS NULL OR puerto = %s)
              AND cliente IS NOT NULL
              AND TRIM(cliente) <> ''
            ORDER BY cliente
        ),

        scope_operacion AS (
            SELECT DISTINCT operacion
            FROM base
            WHERE anio_servicio = %s
              AND (%s IS NULL OR pais = %s)
              AND (%s IS NULL OR puerto = %s)
              AND (%s IS NULL OR cliente = %s)
              AND operacion IS NOT NULL
              AND TRIM(operacion) <> ''
            ORDER BY operacion
        )

        SELECT json_build_object(

            -- =================================================
            -- FILTROS
            -- =================================================
            'filtros', json_build_object(
                'anio_actual', %s,
                'anio_seleccionado', %s,
                'pais_seleccionado', %s,
                'puerto_seleccionado', %s,
                'cliente_seleccionado', %s,
                'operacion_seleccionada', %s,

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
                ), '[]'::json),

                'operaciones', COALESCE((
                    SELECT json_agg(t)
                    FROM (
                        SELECT operacion
                        FROM scope_operacion
                    ) t
                ), '[]'::json)
            ),

            -- =================================================
            -- KPIS
            -- =================================================
            'kpis', json_build_object(
                'ticket_promedio', COALESCE((SELECT AVG(valor_factura) FROM filtrada), 0),
                'total_puertos', COALESCE((SELECT COUNT(DISTINCT puerto) FROM filtrada WHERE puerto IS NOT NULL AND TRIM(puerto) <> ''), 0),
                'total_servicios', COALESCE((SELECT COUNT(*) FROM filtrada), 0),
                'revenue_total', COALESCE((SELECT SUM(valor_factura) FROM filtrada), 0),
                'gastos_total', COALESCE((SELECT SUM(gasto_total) FROM filtrada), 0),
                'margen_bruto_usd', COALESCE((SELECT SUM(margen_bruto_usd) FROM filtrada), 0),
                'margen_bruto_pct', COALESCE((
                    SELECT
                        CASE
                            WHEN SUM(valor_factura) = 0 THEN 0
                            ELSE (SUM(margen_bruto_usd) / SUM(valor_factura)) * 100
                        END
                    FROM filtrada
                ), 0),
                'margen_neto_usd', COALESCE((SELECT SUM(margen_neto_usd) FROM filtrada), 0),
                'margen_neto_pct', COALESCE((
                    SELECT
                        CASE
                            WHEN SUM(valor_factura) = 0 THEN 0
                            ELSE (SUM(margen_neto_usd) / SUM(valor_factura)) * 100
                        END
                    FROM filtrada
                ), 0),
                'utilidad_usd', COALESCE((SELECT SUM(margen_neto_usd) FROM filtrada), 0),
                'utilidad_pct', COALESCE((
                    SELECT
                        CASE
                            WHEN SUM(valor_factura) = 0 THEN 0
                            ELSE (SUM(margen_neto_usd) / SUM(valor_factura)) * 100
                        END
                    FROM filtrada
                ), 0),
                'clientes_activos', COALESCE((SELECT COUNT(DISTINCT cliente) FROM filtrada WHERE cliente IS NOT NULL AND TRIM(cliente) <> ''), 0),
                'paises_activos', COALESCE((SELECT COUNT(DISTINCT pais) FROM filtrada WHERE pais IS NOT NULL AND TRIM(pais) <> ''), 0)
            ),

            -- =================================================
            -- GRAFICOS
            -- =================================================
            'revenue_mensual', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        mes,
                        SUM(valor_factura) AS revenue
                    FROM filtrada
                    GROUP BY mes
                    ORDER BY mes
                ) t
            ), '[]'::json),

            'revenue_por_puerto', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        puerto,
                        SUM(valor_factura) AS total_revenue
                    FROM filtrada
                    WHERE puerto IS NOT NULL
                      AND TRIM(puerto) <> ''
                    GROUP BY puerto
                    ORDER BY total_revenue DESC, puerto
                    LIMIT 15
                ) t
            ), '[]'::json),

            'servicios_por_puerto', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        puerto,
                        COUNT(*) AS total_servicios
                    FROM filtrada
                    WHERE puerto IS NOT NULL
                      AND TRIM(puerto) <> ''
                    GROUP BY puerto
                    ORDER BY total_servicios DESC, puerto
                    LIMIT 15
                ) t
            ), '[]'::json),

            'gastos_por_puerto', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        puerto,
                        SUM(gasto_total) AS total_gastos
                    FROM filtrada
                    WHERE puerto IS NOT NULL
                      AND TRIM(puerto) <> ''
                    GROUP BY puerto
                    ORDER BY total_gastos DESC, puerto
                    LIMIT 15
                ) t
            ), '[]'::json),

            'margen_neto_por_puerto', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        puerto,
                        SUM(margen_neto_usd) AS margen_neto
                    FROM filtrada
                    WHERE puerto IS NOT NULL
                      AND TRIM(puerto) <> ''
                    GROUP BY puerto
                    ORDER BY margen_neto DESC, puerto
                    LIMIT 15
                ) t
            ), '[]'::json),

            'servicios_por_operacion', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        operacion,
                        COUNT(*) AS total_servicios
                    FROM filtrada
                    WHERE operacion IS NOT NULL
                      AND TRIM(operacion) <> ''
                    GROUP BY operacion
                    ORDER BY total_servicios DESC, operacion
                    LIMIT 15
                ) t
            ), '[]'::json),

            'clientes_por_puerto', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        puerto,
                        COUNT(DISTINCT cliente) AS total_clientes
                    FROM filtrada
                    WHERE puerto IS NOT NULL
                      AND TRIM(puerto) <> ''
                      AND cliente IS NOT NULL
                      AND TRIM(cliente) <> ''
                    GROUP BY puerto
                    ORDER BY total_clientes DESC, puerto
                    LIMIT 15
                ) t
            ), '[]'::json),

            'clientes_por_pais', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        pais,
                        COUNT(DISTINCT cliente) AS total_clientes
                    FROM filtrada
                    WHERE pais IS NOT NULL
                      AND TRIM(pais) <> ''
                      AND cliente IS NOT NULL
                      AND TRIM(cliente) <> ''
                    GROUP BY pais
                    ORDER BY total_clientes DESC, pais
                    LIMIT 15
                ) t
            ), '[]'::json),

            'revenue_por_pais', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        pais,
                        SUM(valor_factura) AS total_revenue
                    FROM filtrada
                    WHERE pais IS NOT NULL
                      AND TRIM(pais) <> ''
                    GROUP BY pais
                    ORDER BY total_revenue DESC, pais
                    LIMIT 15
                ) t
            ), '[]'::json),

            'margen_pct_por_pais', COALESCE((
                SELECT json_agg(t)
                FROM (
                    SELECT
                        pais,
                        CASE
                            WHEN SUM(valor_factura) = 0 THEN 0
                            ELSE (SUM(margen_neto_usd) / SUM(valor_factura)) * 100
                        END AS margen_pct
                    FROM filtrada
                    WHERE pais IS NOT NULL
                      AND TRIM(pais) <> ''
                    GROUP BY pais
                    ORDER BY margen_pct DESC, pais
                    LIMIT 15
                ) t
            ), '[]'::json)

        ) AS dashboard;
        """

        params = (
            # filtrada
            anio_final,
            pais, pais,
            puerto, puerto,
            cliente, cliente,
            operacion, operacion,

            # scope_pais
            anio_final,

            # scope_puerto
            anio_final,
            pais, pais,

            # scope_cliente
            anio_final,
            pais, pais,
            puerto, puerto,

            # scope_operacion
            anio_final,
            pais, pais,
            puerto, puerto,
            cliente, cliente,

            # json filtros
            datetime.now().year,
            anio_final,
            pais,
            puerto,
            cliente,
            operacion
        )

        cursor.execute(query, params)
        result = cursor.fetchone()

        if not result or not result[0]:
            return _empty_dashboard(
                anio_seleccionado=anio_final,
                pais=pais,
                puerto=puerto,
                cliente=cliente,
                operacion=operacion
            )

        return result[0]

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error generando dashboard comercial: {str(e)}"
        )