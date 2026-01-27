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
# ANALYTICS — RENTABILIDAD POR SERVICIO (PATRÓN OFICIAL + QUARTER)
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
    from datetime import datetime
    cur = conn.cursor(cursor_factory=RealDictCursor)

    current_year = datetime.now().year

    # =====================================================
    # NORMALIZACIÓN DE AÑOS (REGLA GLOBAL ERP-SOM)
    # =====================================================
    if year_from and not year_to:
        year_to = year_from

    if year_to and not year_from:
        year_from = year_to

    if not year_from and not year_to:
        year_from = year_to = current_year

    # =====================================================
    # FILTROS DINÁMICOS (BLINDADOS)
    # =====================================================
    filtros = [
        "UPPER(TRIM(s.estado)) = 'FINALIZADO'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio::date) BETWEEN %s AND %s"
    ]

    params = [year_from, year_to]

    if continente:
        filtros.append("UPPER(TRIM(s.continente)) = UPPER(%s)")
        params.append(continente.strip())

    if pais:
        filtros.append("UPPER(TRIM(s.pais)) = UPPER(%s)")
        params.append(pais.strip())

    if puerto:
        filtros.append("UPPER(TRIM(s.puerto)) = UPPER(%s)")
        params.append(puerto.strip())

    where_clause = " AND ".join(filtros)

    # =====================================================
    # SQL PRINCIPAL (CON QUARTER)
    # =====================================================
    sql = f"""
        SELECT
            TRIM(s.operacion) AS servicio,

            -- 🔹 QUARTER CALCULADO DESDE fecha_inicio
            'Q' || EXTRACT(QUARTER FROM s.fecha_inicio::date) AS quarter,

            COUNT(s.consec) AS cantidad_servicios,

            SUM(COALESCE(s.valor_factura, 0)) AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            ) AS revenue_neto_total,

            SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            ) AS costo_total,

            SUM(
                CASE
                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(
                COALESCE(s.honorarios, 0) +
                COALESCE(s.costo_operativo, 0)
            ) AS margen_neto,

            CASE
                WHEN SUM(
                    CASE
                        WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                ) = 0 THEN 0
                ELSE ROUND(
                    (
                        (
                            SUM(
                                CASE
                                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
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
                                WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                                THEN COALESCE(s.valor_factura, 0) / 1.13
                                ELSE COALESCE(s.valor_factura, 0)
                            END
                        )
                    ) * 100,
                    2
                )
            END AS margen_neto_pct

        FROM servicios s
        WHERE {where_clause}
        GROUP BY
            TRIM(s.operacion),
            EXTRACT(QUARTER FROM s.fecha_inicio::date)

        ORDER BY revenue_neto_total DESC;
    """

    cur.execute(sql, tuple(params))
    data = cur.fetchall()

    # =====================================================
    # METADATA TEMPORAL (QUARTERS DISPONIBLES)
    # =====================================================
    available_quarters = sorted({
        r["quarter"] for r in data if r.get("quarter")
    })

    cur.close()

    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "continente": continente,
            "pais": pais,
            "puerto": puerto,
            "available_quarters": available_quarters
        },
        "data": data
    }


# ============================================================
# SERVICIOS NO OFRECIDOS (CATÁLOGO VS OPERACIÓN) — ERP-SOM
# ============================================================
@router.get(
    "/not-offered",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def servicios_no_ofrecidos(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    quarter: Optional[str] = Query(None),   # 👈 NUEVO
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    puerto: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    from datetime import datetime
    cur = conn.cursor(cursor_factory=RealDictCursor)

    current_year = datetime.now().year

    # =====================================================
    # NORMALIZACIÓN DE AÑOS
    # =====================================================
    if year_from and not year_to:
        year_to = year_from
    if year_to and not year_from:
        year_from = year_to
    if not year_from and not year_to:
        year_from = year_to = current_year

    # =====================================================
    # FILTROS BASE — SERVICIOS EJECUTADOS
    # =====================================================
    filtros = [
        "UPPER(TRIM(s.estado)) = 'FINALIZADO'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio::date) BETWEEN %s AND %s",
        "s.operacion IS NOT NULL",
        "TRIM(s.operacion) <> ''"
    ]

    params = [year_from, year_to]

    # =====================================================
    # QUARTER (CRÍTICO)
    # =====================================================
    if quarter:
        filtros.append(
            "EXTRACT(QUARTER FROM s.fecha_inicio::date) = %s"
        )
        params.append(int(quarter.replace("Q", "")))

    # =====================================================
    # FILTROS GEO
    # =====================================================
    if continente:
        filtros.append("UPPER(TRIM(s.continente)) = UPPER(%s)")
        params.append(continente.strip())

    if pais:
        filtros.append("UPPER(TRIM(s.pais)) = UPPER(%s)")
        params.append(pais.strip())

    if puerto:
        filtros.append("UPPER(TRIM(s.puerto)) = UPPER(%s)")
        params.append(puerto.strip())

    where_exec = " AND ".join(filtros)

    # =====================================================
    # QUARTERS DISPONIBLES (DINÁMICOS)
    # =====================================================
    sql_quarters = f"""
        SELECT DISTINCT
            'Q' || EXTRACT(QUARTER FROM s.fecha_inicio::date) AS quarter
        FROM servicios s
        WHERE {where_exec}
        ORDER BY quarter;
    """

    cur.execute(sql_quarters, tuple(params))
    available_quarters = [r["quarter"] for r in cur.fetchall()]

    # =====================================================
    # SERVICIOS NO OFRECIDOS (LÓGICA CORRECTA)
    # =====================================================
    sql = f"""
        SELECT
            md.id,
            md.codigo,
            md.codigoprod,
            TRIM(md.nombre) AS servicio,
            COALESCE(NULLIF(md.costo, '')::NUMERIC, 0) AS costo_base
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

    cur.execute(sql, tuple(params))
    data = cur.fetchall()
    cur.close()

    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "quarter": quarter,
            "continente": continente,
            "pais": pais,
            "puerto": puerto,
            "available_quarters": available_quarters
        },
        "total_no_ofrecidos": len(data),
        "data": data
    }

# ============================================================
# COSTOS POR SURVEYOR — FECHA HÍBRIDA ERP-SOM
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
    from datetime import datetime
    cur = conn.cursor(cursor_factory=RealDictCursor)

    current_year = datetime.now().year

    # ---------------- NORMALIZACIÓN AÑOS ----------------
    if year_from and not year_to:
        year_to = year_from
    if year_to and not year_from:
        year_from = year_to
    if not year_from and not year_to:
        year_from = year_to = current_year

    # ---------------- FECHA ANALÍTICA ----------------
    fecha_analitica = """
        CASE
            WHEN EXTRACT(YEAR FROM s.fecha_inicio::date) >= 2026
                 AND s.fecha_inicio IS NOT NULL
            THEN s.fecha_inicio::date

            WHEN s.num_informe ~ '^[0-9]+-[0-9]{4}-[0-9]{4}$'
            THEN TO_DATE(
                RIGHT(s.num_informe, 4) || '-' ||
                SUBSTRING(s.num_informe FROM '[0-9]{4}-(\\d{2})(\\d{2})-' FOR '#"\\1"') || '-' ||
                SUBSTRING(s.num_informe FROM '[0-9]{4}-(\\d{2})(\\d{2})-' FOR '#"\\2"'),
                'YYYY-MM-DD'
            )

            ELSE NULL
        END
    """

    filtros = [
        "UPPER(TRIM(s.estado)) = 'FINALIZADO'",
        f"{fecha_analitica} IS NOT NULL",
        f"EXTRACT(YEAR FROM {fecha_analitica}) BETWEEN %s AND %s",
        "s.surveyor IS NOT NULL",
        "TRIM(s.surveyor) <> ''"
    ]

    params = [year_from, year_to]
    where_clause = " AND ".join(filtros)

    # ---------------- QUARTERS DISPONIBLES ----------------
    sql_quarters = f"""
        SELECT DISTINCT
            'Q' || EXTRACT(QUARTER FROM {fecha_analitica}) AS quarter
        FROM servicios s
        WHERE {where_clause}
        ORDER BY quarter;
    """
    cur.execute(sql_quarters, tuple(params))
    available_quarters = [r["quarter"] for r in cur.fetchall()]

    # ---------------- COSTOS POR SURVEYOR ----------------
    sql = f"""
        SELECT
            UPPER(TRIM(s.surveyor)) AS surveyor,
            COUNT(*) AS total_servicios,

            SUM(COALESCE(s.honorarios, 0)) AS honorarios_total,
            SUM(COALESCE(s.costo_operativo, 0)) AS costo_operativo_total,
            SUM(COALESCE(s.honorarios, 0) + COALESCE(s.costo_operativo, 0)) AS costo_total,

            SUM(COALESCE(s.valor_factura, 0)) AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            ) AS revenue_neto_total

        FROM servicios s
        WHERE {where_clause}
        GROUP BY UPPER(TRIM(s.surveyor))
        ORDER BY honorarios_total DESC;
    """

    cur.execute(sql, tuple(params))
    data = cur.fetchall()
    cur.close()

    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "available_quarters": available_quarters,
            "fecha_regla": ">=2026 fecha_inicio | <=2025 num_informe"
        },
        "total_surveyors": len(data),
        "data": data
    }

# ============================================================
# SERVICIOS POR PAÍS / PUERTO — FECHA HÍBRIDA ERP-SOM
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

    Regla de fecha analítica:
    • >= 2026 → fecha_inicio
    • <= 2025 → num_informe (XXXX-DDMM-YYYY)
    """

    from datetime import datetime
    cur = conn.cursor(cursor_factory=RealDictCursor)

    current_year = datetime.now().year

    # =====================================================
    # NORMALIZACIÓN DE AÑOS (ERP-SOM)
    # =====================================================
    if year_from and not year_to:
        year_to = year_from
    if year_to and not year_from:
        year_from = year_to
    if not year_from and not year_to:
        year_from = year_to = current_year

    # =====================================================
    # FECHA ANALÍTICA (HÍBRIDA)
    # =====================================================
    fecha_analitica = """
        CASE
            WHEN s.fecha_inicio IS NOT NULL
                 AND EXTRACT(YEAR FROM s.fecha_inicio::date) >= 2026
            THEN s.fecha_inicio::date

            WHEN s.num_informe ~ '^[0-9]+-[0-9]{4}-[0-9]{4}$'
            THEN TO_DATE(
                RIGHT(s.num_informe, 4) || '-' ||
                SUBSTRING(s.num_informe FROM '[0-9]+-(\\d{2})(\\d{2})-' FOR '#"\\1"') || '-' ||
                SUBSTRING(s.num_informe FROM '[0-9]+-(\\d{2})(\\d{2})-' FOR '#"\\2"'),
                'YYYY-MM-DD'
            )

            ELSE NULL
        END
    """

    # =====================================================
    # FILTROS BASE (BLINDADOS)
    # =====================================================
    filtros = [
        "UPPER(TRIM(s.estado)) = 'FINALIZADO'",
        f"{fecha_analitica} IS NOT NULL",
        f"EXTRACT(YEAR FROM {fecha_analitica}) BETWEEN %s AND %s",
        "s.continente IS NOT NULL",
        "s.pais IS NOT NULL",
        "s.puerto IS NOT NULL",
        "TRIM(s.continente) <> ''",
        "TRIM(s.pais) <> ''",
        "TRIM(s.puerto) <> ''"
    ]

    params = [year_from, year_to]
    where_clause = " AND ".join(filtros)

    # =====================================================
    # QUARTERS DISPONIBLES (DINÁMICOS)
    # =====================================================
    sql_quarters = f"""
        SELECT DISTINCT
            'Q' || EXTRACT(QUARTER FROM {fecha_analitica}) AS quarter
        FROM servicios s
        WHERE {where_clause}
        ORDER BY quarter;
    """

    cur.execute(sql_quarters, tuple(params))
    available_quarters = [r["quarter"] for r in cur.fetchall()]

    # =====================================================
    # SQL — SERVICIOS POR UBICACIÓN
    # =====================================================
    sql = f"""
        SELECT
            UPPER(TRIM(s.continente)) AS continente,
            UPPER(TRIM(s.pais))       AS pais,
            UPPER(TRIM(s.puerto))     AS puerto,

            -- VOLUMEN
            COUNT(s.consec) AS total_servicios,

            -- FACTURACIÓN
            SUM(COALESCE(s.valor_factura, 0)) AS revenue_bruto_total,

            SUM(
                CASE
                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            ) AS revenue_neto_total,

            -- IVA
            SUM(
                CASE
                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
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
                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                    THEN COALESCE(s.valor_factura, 0) / 1.13
                    ELSE COALESCE(s.valor_factura, 0)
                END
            )
            - SUM(COALESCE(s.costo_operativo, 0)) AS margen_bruto,

            SUM(
                CASE
                    WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
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
            UPPER(TRIM(s.continente)),
            UPPER(TRIM(s.pais)),
            UPPER(TRIM(s.puerto))

        ORDER BY revenue_neto_total DESC;
    """

    cur.execute(sql, tuple(params))
    data = cur.fetchall()
    cur.close()

    # =====================================================
    # RESPONSE
    # =====================================================
    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "available_quarters": available_quarters,
            "fecha_regla": ">=2026 fecha_inicio | <=2025 num_informe"
        },
        "total_ubicaciones": len(data),
        "data": data
    }


# ============================================================
# KPIs EJECUTIVOS — SERVICIOS (BLINDADO FINAL + QUARTER)
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

    Reglas:
    • Sin años → año actual
    • Un año → año exacto
    • Ambos → rango real
    • KPIs sobre servicios FINALIZADOS
    • Revenue neto de IVA (Costa Rica 13%)
    • Quarter calculado desde fecha_inicio (Q1–Q4)
    """

    from datetime import datetime
    cur = conn.cursor(cursor_factory=RealDictCursor)

    current_year = datetime.now().year

    # =====================================================
    # NORMALIZACIÓN DE AÑOS (CRÍTICO)
    # =====================================================
    if year_from and not year_to:
        year_to = year_from

    if year_to and not year_from:
        year_from = year_to

    if not year_from and not year_to:
        year_from = year_to = current_year

    # =====================================================
    # FILTROS BASE (REALMENTE BLINDADOS)
    # =====================================================
    filtros = [
        "UPPER(TRIM(s.estado)) = 'FINALIZADO'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio::date) BETWEEN %(year_from)s AND %(year_to)s",
        "s.operacion IS NOT NULL",
        "TRIM(s.operacion) <> ''"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

    if continente:
        filtros.append("UPPER(TRIM(s.continente)) = UPPER(TRIM(%(continente)s))")
        params["continente"] = continente.strip()

    if pais:
        filtros.append("UPPER(TRIM(s.pais)) = UPPER(TRIM(%(pais)s))")
        params["pais"] = pais.strip()

    if puerto:
        filtros.append("UPPER(TRIM(s.puerto)) = UPPER(TRIM(%(puerto)s))")
        params["puerto"] = puerto.strip()

    if operacion:
        filtros.append("UPPER(TRIM(s.operacion)) = UPPER(TRIM(%(operacion)s))")
        params["operacion"] = operacion.strip()

    where_clause = " AND ".join(filtros)

    # =====================================================
    # QUARTERS DISPONIBLES (DESDE SERVICIOS)
    # =====================================================
    sql_quarters = f"""
        SELECT DISTINCT
            'Q' || EXTRACT(QUARTER FROM s.fecha_inicio::date) AS quarter
        FROM servicios s
        WHERE {where_clause}
        ORDER BY quarter;
    """

    cur.execute(sql_quarters, params)
    available_quarters = [r["quarter"] for r in cur.fetchall()]

    # =====================================================
    # SQL — KPIs EJECUTIVOS
    # =====================================================
    sql = f"""
        WITH base AS (
            SELECT
                UPPER(TRIM(s.operacion)) AS operacion,

                -- FACTURACIÓN
                SUM(COALESCE(s.valor_factura, 0)) AS revenue_bruto,

                SUM(
                    CASE
                        WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                ) AS revenue_neto,

                -- IVA
                SUM(
                    CASE
                        WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
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
                        WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
                        THEN COALESCE(s.valor_factura, 0) / 1.13
                        ELSE COALESCE(s.valor_factura, 0)
                    END
                )
                - SUM(COALESCE(s.costo_operativo, 0)) AS margen_bruto,

                SUM(
                    CASE
                        WHEN UPPER(TRIM(s.pais)) = 'COSTA RICA'
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
            GROUP BY UPPER(TRIM(s.operacion))
        ),
        resumen AS (
            SELECT
                COUNT(*) AS total_servicios,

                COALESCE(SUM(revenue_bruto), 0) AS revenue_bruto_total,
                COALESCE(SUM(revenue_neto), 0) AS revenue_neto_total,
                COALESCE(SUM(iva_total), 0) AS iva_total,

                COALESCE(SUM(honorarios + costos_operativos), 0) AS costos_totales,
                COALESCE(SUM(margen_bruto), 0) AS margen_bruto_total,
                COALESCE(SUM(margen_neto), 0) AS margen_neto_total
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
    # RESPONSE (BLINDADO A None)
    # =====================================================
    def _n(v):
        return round(v or 0, 2)

    return {
        "filters": {
            "year_from": year_from,
            "year_to": year_to,
            "available_quarters": available_quarters
        },
        "kpis": {
            "total_servicios": kpis.get("total_servicios", 0),

            "revenue_bruto_total": _n(kpis.get("revenue_bruto_total")),
            "revenue_neto_total": _n(kpis.get("revenue_neto_total")),
            "iva_total": _n(kpis.get("iva_total")),

            "costos_totales": _n(kpis.get("costos_totales")),

            "margen_bruto_total": _n(kpis.get("margen_bruto_total")),
            "margen_neto_total": _n(kpis.get("margen_neto_total")),
            "margen_neto_pct": _n(kpis.get("margen_neto_pct")),

            "servicio_mas_rentable": kpis.get("servicio_mas_rentable"),
            "servicio_menos_rentable": kpis.get("servicio_menos_rentable"),
            "servicio_mayor_ingreso": kpis.get("servicio_mayor_ingreso"),
            "servicio_menor_ingreso": kpis.get("servicio_menor_ingreso"),
        }
    }


# ============================================================
# COSTOS POR SURVEYOR — PARETO 80/20 (ERP-SOM + QUARTER)
# ============================================================
from typing import Optional
from fastapi import Query, Depends
from psycopg2.extras import RealDictCursor
from datetime import datetime

@router.get(
    "/costos-surveyor-pareto",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def costos_surveyor_pareto(
    year: Optional[int] = Query(None),
    operacion: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    """
    Analiza honorarios por surveyor con desglose por ubicación
    y cálculo Pareto 80/20.

    • Año exacto (por fecha_inicio)
    • Filtro opcional por operación
    • Quarter calculado desde fecha_inicio (Q1–Q4)
    • Expone available_years y available_quarters para UI
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =========================================================
    # 1️⃣ AÑOS DISPONIBLES (METADATA PARA UI)
    # =========================================================
    cur.execute("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha_inicio)::int AS year
        FROM servicios
        WHERE fecha_inicio IS NOT NULL
        ORDER BY year;
    """)

    available_years = [r["year"] for r in cur.fetchall() if r["year"]]

    # Año por defecto = año actual
    current_year = datetime.now().year
    year = year or current_year

    # =========================================================
    # 2️⃣ QUARTERS DISPONIBLES (METADATA PARA UI)
    # =========================================================
    cur.execute("""
        SELECT DISTINCT
            'Q' || EXTRACT(QUARTER FROM fecha_inicio::date) AS quarter
        FROM servicios
        WHERE
            fecha_inicio IS NOT NULL
            AND EXTRACT(YEAR FROM fecha_inicio::date) = %s
        ORDER BY quarter;
    """, (year,))

    available_quarters = [r["quarter"] for r in cur.fetchall()]

    # =========================================================
    # 3️⃣ FILTROS BASE (BLINDADOS)
    # =========================================================
    filtros = [
        "UPPER(TRIM(s.estado)) = 'FINALIZADO'",
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio::date) = %s",
        "s.surveyor IS NOT NULL",
        "TRIM(s.surveyor) <> ''"
    ]

    params = [year]

    if operacion:
        filtros.append("UPPER(TRIM(s.operacion)) = UPPER(%s)")
        params.append(operacion.strip())

    where_clause = " AND ".join(filtros)

    # =========================================================
    # 4️⃣ QUERY PRINCIPAL · PARETO 80/20
    # =========================================================
    sql = f"""
        WITH base AS (
            SELECT
                UPPER(TRIM(s.surveyor))   AS surveyor,
                UPPER(TRIM(s.continente)) AS continente,
                UPPER(TRIM(s.pais))       AS pais,
                UPPER(TRIM(s.puerto))     AS puerto,
                COUNT(*)                  AS total_servicios,
                SUM(COALESCE(s.honorarios, 0)) AS honorarios_total
            FROM servicios s
            WHERE {where_clause}
            GROUP BY
                UPPER(TRIM(s.surveyor)),
                UPPER(TRIM(s.continente)),
                UPPER(TRIM(s.pais)),
                UPPER(TRIM(s.puerto))
        ),
        ranked AS (
            SELECT
                *,
                SUM(honorarios_total) OVER () AS total_global,
                SUM(honorarios_total)
                    OVER (
                        ORDER BY honorarios_total DESC
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                    ) AS acumulado
            FROM base
        )
        SELECT
            surveyor,
            continente,
            pais,
            puerto,
            total_servicios,
            honorarios_total,
            ROUND(
                (acumulado / NULLIF(total_global, 0)) * 100,
                2
            ) AS acumulado_pct,
            CASE
                WHEN (acumulado / NULLIF(total_global, 0)) <= 0.8
                THEN TRUE
                ELSE FALSE
            END AS es_pareto_80
        FROM ranked
        ORDER BY honorarios_total DESC;
    """

    cur.execute(sql, tuple(params))
    data = cur.fetchall()
    cur.close()

    # =========================================================
    # 5️⃣ RESPONSE FINAL (UI-FRIENDLY)
    # =========================================================
    return {
        "filters": {
            "year": year,
            "operacion": operacion,
            "available_years": available_years,
            "available_quarters": available_quarters
        },
        "total_surveyors": len({r["surveyor"] for r in data}),
        "data": data
    }
