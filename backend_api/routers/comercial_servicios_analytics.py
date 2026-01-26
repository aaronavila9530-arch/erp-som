# ============================================================
# COMERCIAL — SERVICIOS ANALYTICS
# Archivo: backend_api/routers/comercial_servicios_analytics.py
# ============================================================

from fastapi import APIRouter, Depends, Query
from psycopg2.extras import RealDictCursor
from typing import Optional
from database import get_db
from fastapi import Header, HTTPException
from rbac_service import has_permission

def require_permission(module: str, action: str):
    def checker(
        x_user_role: str = Header(..., alias="X-User-Role")
    ):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(status_code=403, detail="No autorizado")
    return checker




router = APIRouter(
    prefix="/comercial/analytics/servicios",
    tags=["Comercial"]
)


# ============================================================
# ANALYTICS — RENTABILIDAD POR SERVICIO
# ============================================================
@router.get(
    "/by-servicio",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def servicios_analytics_by_servicio(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    puerto: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    """
    Analiza rentabilidad y desempeño por SERVICIO (operacion)
    Facturación neta de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # FILTROS BASE + DINÁMICOS
    # =====================================================
    filtros = ["s.fecha_inicio IS NOT NULL"]
    params = {}

    if year_from:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) >= %(year_from)s")
        params["year_from"] = year_from

    if year_to:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) <= %(year_to)s")
        params["year_to"] = year_to

    if continente:
        filtros.append("s.continente = %(continente)s")
        params["continente"] = continente

    if pais:
        filtros.append("s.pais = %(pais)s")
        params["pais"] = pais

    if puerto:
        filtros.append("s.puerto = %(puerto)s")
        params["puerto"] = puerto

    where_clause = " AND " + " AND ".join(filtros)

    # =====================================================
    # SQL PRINCIPAL (IVA APLICADO)
    # =====================================================
    sql = f"""
        SELECT
            s.operacion                                        AS servicio,
            COUNT(s.consec)                                   AS cantidad_servicios,

            -- FACTURACIÓN
            SUM(COALESCE(s.valor_factura, 0))                 AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )                                                  AS revenue_neto_total,

            AVG(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )                                                  AS revenue_neto_promedio,

            -- IVA
            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0)
                       - (COALESCE(s.valor_factura, 0) / 1.13)
                    ELSE 0
                END
            )                                                  AS iva_total,

            -- COSTOS
            SUM(COALESCE(s.honorarios, 0))                    AS costo_surveyor_total,
            SUM(COALESCE(s.costo_operativo, 0))               AS costo_operativo_total,
            SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            )                                                  AS costo_total,

            -- MÁRGENES
            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(COALESCE(s.costo_operativo, 0))              AS margen_bruto,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            )                                                  AS margen_neto,

            -- % MÁRGENES
            CASE
                WHEN SUM(
                    CASE
                        WHEN s.pais = 'Costa Rica'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                ) = 0 THEN 0
                ELSE ROUND(
                    (
                        (
                            SUM(
                                CASE
                                    WHEN s.pais = 'Costa Rica'
                                    THEN COALESCE(s.valor_factura, 0) / 1.13
                                    ELSE COALESCE(s.valor_factura, 0)
                                END
                            )
                            - SUM(COALESCE(s.costo_operativo, 0))
                        )
                        /
                        SUM(
                            CASE
                                WHEN s.pais = 'Costa Rica'
                                THEN COALESCE(s.valor_factura, 0) / 1.13
                                ELSE COALESCE(s.valor_factura, 0)
                            END
                        )
                    ) * 100,
                    2
                )
            END                                                AS margen_bruto_pct,

            CASE
                WHEN SUM(
                    CASE
                        WHEN s.pais = 'Costa Rica'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                ) = 0 THEN 0
                ELSE ROUND(
                    (
                        (
                            SUM(
                                CASE
                                    WHEN s.pais = 'Costa Rica'
                                    THEN COALESCE(s.valor_factura, 0) / 1.13
                                    ELSE COALESCE(s.valor_factura, 0)
                                END
                            )
                            - SUM(
                                COALESCE(s.honorarios, 0) +
                                COALESCE(s.costo_operativo, 0)
                            )
                        )
                        /
                        SUM(
                            CASE
                                WHEN s.pais = 'Costa Rica'
                                THEN COALESCE(s.valor_factura, 0) / 1.13
                                ELSE COALESCE(s.valor_factura, 0)
                            END
                        )
                    ) * 100,
                    2
                )
            END                                                AS margen_neto_pct,

            -- CATÁLOGO
            md.codigo                                         AS codigo_servicio,
            md.codigoprod                                     AS codigo_producto,
            md.costo                                          AS costo_base_catalogo

        FROM servicios s
        LEFT JOIN serviciosmd md
            ON UPPER(TRIM(s.operacion)) = UPPER(TRIM(md.nombre))

        WHERE s.estado = 'Finalizado'
        {where_clause}

        GROUP BY
            s.operacion,
            md.codigo,
            md.codigoprod,
            md.costo

        ORDER BY revenue_neto_total DESC;
    """

    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)

    rows = cur.fetchall()
    cur.close()

    return {
        "total_servicios": len(rows),
        "data": rows
    }


# ============================================================
# SERVICIOS NO OFRECIDOS (CATÁLOGO VS OPERACIÓN)
# ============================================================
@router.get(
    "/not-offered",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def servicios_no_ofrecidos(
    conn=Depends(get_db)
):
    """
    Devuelve servicios del catálogo (serviciosmd)
    que NO han sido ejecutados en la tabla servicios.
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    sql = """
        SELECT
            md.id,
            md.codigo,
            md.codigoprod,
            md.nombre AS servicio_catalogo,
            md.costo  AS costo_base
        FROM serviciosmd md
        LEFT JOIN servicios s
            ON UPPER(TRIM(md.nombre)) = UPPER(TRIM(s.operacion))
            AND s.estado = 'Finalizado'
            AND s.fecha_inicio IS NOT NULL
        WHERE s.consec IS NULL
        ORDER BY md.nombre;
    """

    cur.execute(sql)
    rows = cur.fetchall()
    cur.close()

    return {
        "total_no_ofrecidos": len(rows),
        "data": rows
    }


# ============================================================
# COSTOS POR SURVEYOR
# ============================================================
@router.get(
    "/costos-por-surveyor",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def costos_por_surveyor(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    conn=Depends(get_db)
):
    """
    Analiza costos y rentabilidad generados por surveyor
    Facturación neta de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = []
    params = {}

    if year_from:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) >= %(year_from)s")
        params["year_from"] = year_from

    if year_to:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) <= %(year_to)s")
        params["year_to"] = year_to

    where_clause = ""
    if filtros:
        where_clause = "AND " + " AND ".join(filtros)

    sql = f"""
        SELECT
            s.surveyor                                   AS surveyor,

            COUNT(s.consec)                              AS total_servicios,

            -- COSTOS
            SUM(COALESCE(s.honorarios, 0))               AS honorarios_total,
            AVG(COALESCE(s.honorarios, 0))               AS honorarios_promedio,
            SUM(COALESCE(s.costo_operativo, 0))          AS costo_operativo_total,

            -- FACTURACIÓN
            SUM(COALESCE(s.valor_factura, 0))            AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )                                            AS revenue_neto_total,

            -- IVA
            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0)
                       - (COALESCE(s.valor_factura, 0) / 1.13)
                    ELSE 0
                END
            )                                            AS iva_total,

            -- MÁRGENES
            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(COALESCE(s.costo_operativo, 0))        AS margen_bruto,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            )                                            AS margen_neto

        FROM servicios s
        WHERE s.estado = 'Finalizado'
          AND s.surveyor IS NOT NULL
          AND TRIM(s.surveyor) <> ''
        {where_clause}

        GROUP BY s.surveyor
        ORDER BY honorarios_total DESC;
    """

    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)

    rows = cur.fetchall()
    cur.close()

    return {
        "total_surveyors": len(rows),
        "data": rows
    }


# ============================================================
# SERVICIOS POR PAÍS / PUERTO
# ============================================================
@router.get(
    "/por-ubicacion",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def servicios_por_ubicacion(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    conn=Depends(get_db)
):
    """
    Analiza volumen, revenue, costos y rentabilidad
    por continente / país / puerto
    Facturación neta de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = []
    params = {}

    if year_from:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) >= %(year_from)s")
        params["year_from"] = year_from

    if year_to:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) <= %(year_to)s")
        params["year_to"] = year_to

    where_clause = ""
    if filtros:
        where_clause = "AND " + " AND ".join(filtros)

    sql = f"""
        SELECT
            s.continente,
            s.pais,
            s.puerto,

            -- VOLUMEN
            COUNT(s.consec)                              AS total_servicios,

            -- FACTURACIÓN
            SUM(COALESCE(s.valor_factura, 0))            AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )                                            AS revenue_neto_total,

            -- IVA
            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0)
                       - (COALESCE(s.valor_factura, 0) / 1.13)
                    ELSE 0
                END
            )                                            AS iva_total,

            -- COSTOS
            SUM(COALESCE(s.honorarios, 0))               AS honorarios_total,
            SUM(COALESCE(s.costo_operativo, 0))          AS costo_operativo_total,

            -- MÁRGENES
            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(COALESCE(s.costo_operativo, 0))        AS margen_bruto,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            )                                            AS margen_neto

        FROM servicios s
        WHERE s.estado = 'Finalizado'
          AND s.continente IS NOT NULL
          AND s.pais IS NOT NULL
          AND s.puerto IS NOT NULL
          AND TRIM(s.continente) <> ''
          AND TRIM(s.pais) <> ''
          AND TRIM(s.puerto) <> ''
        {where_clause}

        GROUP BY s.continente, s.pais, s.puerto
        ORDER BY revenue_neto_total DESC;
    """

    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)

    rows = cur.fetchall()
    cur.close()

    return {
        "total_ubicaciones": len(rows),
        "data": rows
    }


# ============================================================
# KPIs EJECUTIVOS — SERVICIOS
# ============================================================
@router.get(
    "/kpis",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def servicios_kpis_ejecutivos(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    puerto: Optional[str] = Query(None),
    operacion: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    """
    KPIs ejecutivos para análisis de servicios
    Revenue neto de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # FILTROS DINÁMICOS
    # =====================================================
    filtros = []
    params = {}

    if year_from:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) >= %(year_from)s")
        params["year_from"] = year_from

    if year_to:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) <= %(year_to)s")
        params["year_to"] = year_to

    if continente:
        filtros.append("s.continente = %(continente)s")
        params["continente"] = continente

    if pais:
        filtros.append("s.pais = %(pais)s")
        params["pais"] = pais

    if puerto:
        filtros.append("s.puerto = %(puerto)s")
        params["puerto"] = puerto

    if operacion:
        filtros.append("s.operacion = %(operacion)s")
        params["operacion"] = operacion

    where_clause = ""
    if filtros:
        where_clause = "AND " + " AND ".join(filtros)

    # =====================================================
    # SQL KPIs
    # =====================================================
    sql = f"""
        WITH base AS (
            SELECT
                s.operacion,
                COUNT(s.consec) AS total_servicios,

                -- FACTURACIÓN
                SUM(COALESCE(s.valor_factura, 0)) AS revenue_bruto,

                SUM(
                    CASE
                        WHEN s.pais = 'Costa Rica'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                ) AS revenue_neto,

                -- IVA
                SUM(
                    CASE
                        WHEN s.pais = 'Costa Rica'
                        THEN COALESCE(s.valor_factura, 0)
                           - (COALESCE(s.valor_factura, 0) / 1.13)
                        ELSE 0
                    END
                ) AS iva_total,

                -- COSTOS
                SUM(COALESCE(s.honorarios, 0))      AS honorarios,
                SUM(COALESCE(s.costo_operativo, 0)) AS costos_operativos,

                -- MÁRGENES
                SUM(
                    CASE
                        WHEN s.pais = 'Costa Rica'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                )
                - SUM(COALESCE(s.costo_operativo, 0)) AS margen_bruto,

                SUM(
                    CASE
                        WHEN s.pais = 'Costa Rica'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                )
                - SUM(
                    COALESCE(s.honorarios, 0)
                    + COALESCE(s.costo_operativo, 0)
                ) AS margen_neto

            FROM servicios s
            WHERE s.estado = 'Finalizado'
              AND s.operacion IS NOT NULL
              AND TRIM(s.operacion) <> ''
            {where_clause}
            GROUP BY s.operacion
        ),
        resumen AS (
            SELECT
                SUM(total_servicios)        AS total_servicios,
                SUM(revenue_bruto)          AS revenue_bruto_total,
                SUM(revenue_neto)           AS revenue_neto_total,
                SUM(iva_total)              AS iva_total,
                SUM(honorarios + costos_operativos) AS costos_totales,
                SUM(margen_bruto)           AS margen_bruto_total,
                SUM(margen_neto)            AS margen_neto_total
            FROM base
        )
        SELECT
            r.*,

            ROUND(
                CASE
                    WHEN r.revenue_neto_total > 0
                    THEN (r.margen_neto_total / r.revenue_neto_total) * 100
                    ELSE 0
                END,
                2
            ) AS margen_neto_pct,

            (SELECT operacion FROM base ORDER BY margen_neto DESC LIMIT 1)
                AS servicio_mas_rentable,

            (SELECT operacion FROM base ORDER BY margen_neto ASC LIMIT 1)
                AS servicio_menos_rentable,

            (SELECT operacion FROM base ORDER BY total_servicios DESC LIMIT 1)
                AS servicio_mas_solicitado,

            (SELECT operacion FROM base ORDER BY total_servicios ASC LIMIT 1)
                AS servicio_menos_solicitado,

            (SELECT operacion FROM base ORDER BY costos_operativos DESC LIMIT 1)
                AS servicio_mayor_costo,

            (SELECT operacion FROM base ORDER BY costos_operativos ASC LIMIT 1)
                AS servicio_menor_costo

        FROM resumen r;
    """

    # =====================================================
    # EXECUTE (BLINDADO)
    # =====================================================
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)

    kpis = cur.fetchone() or {}
    cur.close()

    # =====================================================
    # RESPONSE
    # =====================================================
    return {
        "kpis": {
            "total_servicios": kpis.get("total_servicios", 0),

            "revenue_bruto_total": round(kpis.get("revenue_bruto_total", 0), 2),
            "revenue_neto_total": round(kpis.get("revenue_neto_total", 0), 2),
            "iva_total": round(kpis.get("iva_total", 0), 2),

            "costos_totales": round(kpis.get("costos_totales", 0), 2),

            "margen_bruto_total": round(kpis.get("margen_bruto_total", 0), 2),
            "margen_neto_total": round(kpis.get("margen_neto_total", 0), 2),
            "margen_neto_pct": kpis.get("margen_neto_pct", 0),

            "servicio_mas_rentable": kpis.get("servicio_mas_rentable"),
            "servicio_menos_rentable": kpis.get("servicio_menos_rentable"),
            "servicio_mas_solicitado": kpis.get("servicio_mas_solicitado"),
            "servicio_menos_solicitado": kpis.get("servicio_menos_solicitado"),
            "servicio_mayor_costo": kpis.get("servicio_mayor_costo"),
            "servicio_menor_costo": kpis.get("servicio_menor_costo"),
        }
    }
