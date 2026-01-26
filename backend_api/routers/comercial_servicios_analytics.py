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
# ANALYTICS — RENTABILIDAD POR SERVICIO (CORREGIDO)
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
    • Año por defecto: año en curso (backend)
    • Filtros reales desde DB
    • Facturación neta de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # AÑO ACTUAL (BACKEND AUTHORITY)
    # =====================================================
    from datetime import datetime
    current_year = datetime.now().year

    year_from = year_from or current_year
    year_to = year_to or current_year

    # =====================================================
    # FILTROS BASE + DINÁMICOS
    # =====================================================
    filtros = [
        "s.estado = 'Finalizado'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio) BETWEEN %(year_from)s AND %(year_to)s"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

    if continente:
        filtros.append("TRIM(s.continente) = %(continente)s")
        params["continente"] = continente.strip()

    if pais:
        filtros.append("TRIM(s.pais) = %(pais)s")
        params["pais"] = pais.strip()

    if puerto:
        filtros.append("TRIM(s.puerto) = %(puerto)s")
        params["puerto"] = puerto.strip()

    where_clause = " AND ".join(filtros)

    # =====================================================
    # SQL PRINCIPAL — RENTABILIDAD POR SERVICIO
    # =====================================================
    sql = f"""
        SELECT
            TRIM(s.operacion)                               AS servicio,
            COUNT(s.consec)                                AS cantidad_servicios,

            -- FACTURACIÓN
            SUM(COALESCE(s.valor_factura, 0))              AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )                                               AS revenue_neto_total,

            -- COSTOS
            SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            )                                               AS costo_total,

            -- MÁRGENES
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
            )                                               AS margen_neto,

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
            END                                             AS margen_neto_pct

        FROM servicios s
        WHERE {where_clause}

        GROUP BY TRIM(s.operacion)
        ORDER BY revenue_neto_total DESC;
    """

    cur.execute(sql, params)
    data = cur.fetchall()

    # =====================================================
    # METADATA — FILTROS DISPONIBLES (REAL DB)
    # =====================================================
    meta_sql = """
        SELECT
            ARRAY_AGG(DISTINCT EXTRACT(YEAR FROM fecha_inicio)::INT ORDER BY EXTRACT(YEAR FROM fecha_inicio)::INT DESC)
                AS years,
            ARRAY_AGG(DISTINCT TRIM(continente) ORDER BY TRIM(continente))
                FILTER (WHERE continente IS NOT NULL AND TRIM(continente) <> '')
                AS continentes,
            ARRAY_AGG(DISTINCT TRIM(pais) ORDER BY TRIM(pais))
                FILTER (WHERE pais IS NOT NULL AND TRIM(pais) <> '')
                AS paises,
            ARRAY_AGG(DISTINCT TRIM(puerto) ORDER BY TRIM(puerto))
                FILTER (WHERE puerto IS NOT NULL AND TRIM(puerto) <> '')
                AS puertos,
            ARRAY_AGG(DISTINCT TRIM(operacion) ORDER BY TRIM(operacion))
                FILTER (WHERE operacion IS NOT NULL AND TRIM(operacion) <> '')
                AS servicios
        FROM servicios
        WHERE fecha_inicio IS NOT NULL;
    """

    cur.execute(meta_sql)
    meta = cur.fetchone() or {}
    cur.close()

    # =====================================================
    # RESPONSE
    # =====================================================
    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "available_years": meta.get("years", []),
            "continentes": meta.get("continentes", []),
            "paises": meta.get("paises", []),
            "puertos": meta.get("puertos", []),
            "servicios": meta.get("servicios", [])
        },
        "total_servicios_unicos": len(data),
        "data": data
    }


# ============================================================
# SERVICIOS NO OFRECIDOS (CATÁLOGO VS OPERACIÓN) — CORREGIDO
# ============================================================
@router.get(
    "/not-offered",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def servicios_no_ofrecidos(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    puerto: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    """
    Devuelve servicios del catálogo (serviciosmd)
    que NO han sido ejecutados en el período filtrado.
    • Año por defecto: año en curso (backend)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # AÑO ACTUAL (BACKEND AUTHORITY)
    # =====================================================
    from datetime import datetime
    current_year = datetime.now().year

    year_from = year_from or current_year
    year_to = year_to or current_year

    # =====================================================
    # FILTROS DE EJECUCIÓN (SERVICIOS)
    # =====================================================
    filtros = [
        "s.estado = 'Finalizado'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio) BETWEEN %(year_from)s AND %(year_to)s"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

    if continente:
        filtros.append("TRIM(s.continente) = %(continente)s")
        params["continente"] = continente.strip()

    if pais:
        filtros.append("TRIM(s.pais) = %(pais)s")
        params["pais"] = pais.strip()

    if puerto:
        filtros.append("TRIM(s.puerto) = %(puerto)s")
        params["puerto"] = puerto.strip()

    where_exec = " AND ".join(filtros)

    # =====================================================
    # SQL — SERVICIOS NO OFRECIDOS
    # =====================================================
    sql = f"""
        SELECT
            md.id,
            md.codigo,
            md.codigoprod,
            TRIM(md.nombre)        AS servicio,
            COALESCE(md.costo, 0) AS costo_base
        FROM serviciosmd md
        WHERE NOT EXISTS (
            SELECT 1
            FROM servicios s
            WHERE
                UPPER(TRIM(s.operacion)) = UPPER(TRIM(md.nombre))
                AND {where_exec}
        )
        ORDER BY TRIM(md.nombre);
    """

    cur.execute(sql, params)
    data = cur.fetchall()

    cur.close()

    # =====================================================
    # RESPONSE
    # =====================================================
    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to
        },
        "total_no_ofrecidos": len(data),
        "data": data
    }

# ============================================================
# COSTOS POR SURVEYOR — CORREGIDO
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
    Analiza costos y rentabilidad generados por surveyor.
    • Año por defecto: año en curso (backend)
    • Facturación neta de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # AÑO ACTUAL (BACKEND AUTHORITY)
    # =====================================================
    from datetime import datetime
    current_year = datetime.now().year

    year_from = year_from or current_year
    year_to = year_to or current_year

    # =====================================================
    # FILTROS BASE
    # =====================================================
    filtros = [
        "s.estado = 'Finalizado'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio) BETWEEN %(year_from)s AND %(year_to)s",
        "s.surveyor IS NOT NULL",
        "TRIM(s.surveyor) <> ''"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

    where_clause = " AND ".join(filtros)

    # =====================================================
    # SQL — COSTOS POR SURVEYOR
    # =====================================================
    sql = f"""
        SELECT
            TRIM(s.surveyor) AS surveyor,

            COUNT(s.consec) AS total_servicios,

            -- COSTOS
            SUM(COALESCE(s.honorarios, 0))               AS honorarios_total,
            AVG(COALESCE(s.honorarios, 0))               AS honorarios_promedio,
            SUM(COALESCE(s.costo_operativo, 0))          AS costo_operativo_total,
            SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            )                                            AS costo_total,

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
        WHERE {where_clause}

        GROUP BY TRIM(s.surveyor)
        ORDER BY honorarios_total DESC;
    """

    cur.execute(sql, params)
    data = cur.fetchall()
    cur.close()

    # =====================================================
    # RESPONSE
    # =====================================================
    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to
        },
        "total_surveyors": len(data),
        "data": data
    }


# ============================================================
# SERVICIOS POR PAÍS / PUERTO — CORREGIDO
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
    por continente / país / puerto.

    • Año por defecto: año en curso (backend)
    • Solo servicios Finalizados
    • Facturación neta de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # AÑO ACTUAL (BACKEND AUTHORITY)
    # =====================================================
    from datetime import datetime
    current_year = datetime.now().year

    year_from = year_from or current_year
    year_to = year_to or current_year

    # =====================================================
    # FILTROS BASE
    # =====================================================
    filtros = [
        "s.estado = 'Finalizado'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio) BETWEEN %(year_from)s AND %(year_to)s",
        "s.continente IS NOT NULL",
        "s.pais IS NOT NULL",
        "s.puerto IS NOT NULL",
        "TRIM(s.continente) <> ''",
        "TRIM(s.pais) <> ''",
        "TRIM(s.puerto) <> ''"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

    where_clause = " AND ".join(filtros)

    # =====================================================
    # SQL — SERVICIOS POR UBICACIÓN
    # =====================================================
    sql = f"""
        SELECT
            TRIM(s.continente) AS continente,
            TRIM(s.pais)       AS pais,
            TRIM(s.puerto)     AS puerto,

            -- VOLUMEN
            COUNT(s.consec) AS total_servicios,

            -- FACTURACIÓN
            SUM(COALESCE(s.valor_factura, 0)) AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            ) AS revenue_neto_total,

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
            SUM(COALESCE(s.honorarios, 0))      AS honorarios_total,
            SUM(COALESCE(s.costo_operativo, 0)) AS costo_operativo_total,
            SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            ) AS costo_total,

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
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            ) AS margen_neto

        FROM servicios s
        WHERE {where_clause}

        GROUP BY
            TRIM(s.continente),
            TRIM(s.pais),
            TRIM(s.puerto)

        ORDER BY revenue_neto_total DESC;
    """

    cur.execute(sql, params)
    data = cur.fetchall()
    cur.close()

    # =====================================================
    # RESPONSE
    # =====================================================
    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to
        },
        "total_ubicaciones": len(data),
        "data": data
    }

# ============================================================
# KPIs EJECUTIVOS — SERVICIOS (CORREGIDO)
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
    KPIs ejecutivos para análisis de servicios.

    • Año por defecto: año en curso (backend)
    • Servicios únicos (NO ejecuciones)
    • Revenue neto de IVA (Costa Rica 13%)
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # AÑO ACTUAL (BACKEND AUTHORITY)
    # =====================================================
    from datetime import datetime
    current_year = datetime.now().year

    year_from = year_from or current_year
    year_to = year_to or current_year

    # =====================================================
    # FILTROS BASE
    # =====================================================
    filtros = [
        "s.estado = 'Finalizado'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio) BETWEEN %(year_from)s AND %(year_to)s",
        "s.operacion IS NOT NULL",
        "TRIM(s.operacion) <> ''"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

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

    where_clause = " AND ".join(filtros)

    # =====================================================
    # SQL — KPIs EJECUTIVOS
    # =====================================================
    sql = f"""
        WITH base AS (
            SELECT
                TRIM(s.operacion) AS operacion,

                -- SERVICIOS ÚNICOS
                COUNT(DISTINCT TRIM(s.operacion)) AS servicio_unico,

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
            WHERE {where_clause}
            GROUP BY TRIM(s.operacion)
        ),
        resumen AS (
            SELECT
                COUNT(*)                    AS total_servicios,
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

            (SELECT operacion FROM base ORDER BY revenue_neto DESC LIMIT 1)
                AS servicio_mayor_ingreso,

            (SELECT operacion FROM base ORDER BY revenue_neto ASC LIMIT 1)
                AS servicio_menor_ingreso

        FROM resumen r;
    """

    cur.execute(sql, params)
    kpis = cur.fetchone() or {}
    cur.close()

    # =====================================================
    # RESPONSE
    # =====================================================
    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to
        },
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
            "servicio_mayor_ingreso": kpis.get("servicio_mayor_ingreso"),
            "servicio_menor_ingreso": kpis.get("servicio_menor_ingreso"),
        }
    }
