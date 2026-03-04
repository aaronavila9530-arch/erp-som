from fastapi import (
    APIRouter,
    Query,
    Header,
    HTTPException,
    Depends
)
from typing import Optional
from psycopg2.extras import RealDictCursor
from datetime import date

from database import get_db
from rbac_service import has_permission


router = APIRouter(
    prefix="/comercial",
    tags=["Comercial"]
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
# GET /comercial/client-view
# ANALÍTICA COMERCIAL POR CLIENTE / SERVICIO
# ============================================================
@router.get(
    "/client-view",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_client_view(
    year: Optional[int] = Query(None),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    cliente: Optional[str] = Query(None),
    servicio: Optional[str] = Query(None),
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # AÑO / RANGO EFECTIVO (PRECEDENCIA)
    # --------------------------------------------------------
    if year_from or year_to:
        y_start = date(year_from or year_to, 1, 1)
        y_end = date((year_to or year_from) + 1, 1, 1)

    elif year:
        y_start = date(year, 1, 1)
        y_end = date(year + 1, 1, 1)

    else:
        current_year = date.today().year
        y_start = date(current_year, 1, 1)
        y_end = date(current_year + 1, 1, 1)

    # --------------------------------------------------------
    # FILTROS OPCIONALES
    # --------------------------------------------------------
    filtros = []

    params = {
        "y_start": y_start,
        "y_end": y_end
    }

    if cliente:
        filtros.append("s.cliente = %(cliente)s")
        params["cliente"] = cliente

    if servicio:
        filtros.append("s.operacion = %(servicio)s")
        params["servicio"] = servicio

    filtros_sql = ""
    if filtros:
        filtros_sql = " AND " + " AND ".join(filtros)

    # --------------------------------------------------------
    # SQL PRINCIPAL (BLINDADO)
    # --------------------------------------------------------
    sql = f"""
        WITH base AS (

            SELECT
                s.cliente,
                s.operacion                       AS servicios,
                s.operacion                       AS tipo_mas_frecuente,
                s.buque_contenedor,
                s.fecha_inicio,
                s.fecha_fin,
                s.factura,

                COALESCE(s.valor_factura, 0)      AS valor_factura,
                COALESCE(s.costo_operativo, 0)    AS costo_operativo,
                COALESCE(s.honorarios, 0)         AS honorarios,
                COALESCE(s.costo_tarjetas, 0)     AS costo_tarjetas,

                cli.pais,

                COALESCE(ca.comision, 0)          AS comision_bancaria,

                CASE
                    WHEN cli.pais = 'Costa Rica'
                    THEN s.valor_factura - (s.valor_factura / 1.13)
                    ELSE 0
                END                                AS iva

            FROM servicios s

            LEFT JOIN cliente cli
                ON cli.nombrejuridico = s.cliente

            LEFT JOIN cash_app ca
                ON ca.numero_documento = s.factura

            WHERE
                s.fecha_inicio >= %(y_start)s
                AND s.fecha_inicio < %(y_end)s
                {filtros_sql}
        )

        SELECT
            cliente,
            servicios,
            buque_contenedor,

            COUNT(*)                           AS frecuencia,
            tipo_mas_frecuente,

            MIN(fecha_inicio)                  AS fecha_inicio,
            MAX(fecha_fin)                     AS fecha_fin,

            factura,

            SUM(valor_factura)                 AS valor_facturado,
            SUM(costo_operativo)               AS costo_operativo,
            SUM(honorarios)                    AS honorarios,
            SUM(costo_tarjetas)                AS costo_tarjetas,
            SUM(iva)                           AS iva,
            SUM(comision_bancaria)             AS comision_bancaria,

            (
                SUM(valor_factura)
                - SUM(costo_operativo)
                - SUM(honorarios)
                - SUM(costo_tarjetas)
            )                                  AS margen_bruto,

            (
                SUM(valor_factura)
                - SUM(costo_operativo)
                - SUM(honorarios)
                - SUM(costo_tarjetas)
                - SUM(comision_bancaria)
                - SUM(iva)
            )                                  AS margen_neto

        FROM base

        GROUP BY
            cliente,
            servicios,
            buque_contenedor,
            tipo_mas_frecuente,
            factura

        ORDER BY valor_facturado DESC;
    """

    cur.execute(sql, params)
    rows = cur.fetchall()

    # --------------------------------------------------------
    # KPI — SERVICIOS REALES
    # DEFINICIÓN: cliente + operacion
    # --------------------------------------------------------
    cur.execute(f"""
        SELECT COUNT(*) AS total
        FROM (
            SELECT DISTINCT
                s.cliente,
                s.operacion
            FROM servicios s
            WHERE
                s.fecha_inicio >= %(y_start)s
                AND s.fecha_inicio < %(y_end)s
                {filtros_sql}
        ) t;
    """, params)

    total_services = cur.fetchone()["total"]

    # --------------------------------------------------------
    # KPIs (YA FILTRADOS)
    # --------------------------------------------------------
    total_clients = len({
        r["cliente"]
        for r in rows
        if r["cliente"]
    })

    total_fact = sum(r["valor_facturado"] or 0 for r in rows)

    total_costs = sum(
        (r["costo_operativo"] or 0)
        + (r["honorarios"] or 0)
        + (r["costo_tarjetas"] or 0)
        + (r["iva"] or 0)
        + (r["comision_bancaria"] or 0)
        for r in rows
    )

    gross_margin = sum(r["margen_bruto"] or 0 for r in rows)
    net_margin = sum(r["margen_neto"] or 0 for r in rows)

    kpis = {
        "clientes": total_clients,
        "servicios": total_services,
        "facturado": round(total_fact, 2),
        "costos": round(total_costs, 2),

        "ticket_promedio": round(
            (total_fact / total_services), 2
        ) if total_services else 0,

        "margen_bruto": round(gross_margin, 2),
        "margen_neto": round(net_margin, 2),

        "rentabilidad_monto": round(net_margin, 2),

        "rentabilidad_pct": round(
            (net_margin / total_fact) * 100, 2
        ) if total_fact else 0
    }

    # --------------------------------------------------------
    # AÑOS DISPONIBLES
    # --------------------------------------------------------
    cur.execute("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha_inicio)::int AS year
        FROM servicios
        ORDER BY year DESC
    """)

    years = [r["year"] for r in cur.fetchall()]

    cur.close()

    return {
        "year_applied": f"{y_start.year}-{y_end.year - 1}",
        "available_years": years,
        "kpis": kpis,
        "data": rows
    }


# ============================================================
# GET /comercial/clientes
# DETALLE DE CLIENTES (READ ONLY)
# ============================================================
@router.get(
    "/clientes",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def get_comercial_clientes(
    id: Optional[int] = Query(None),
    codigo: Optional[str] = Query(None),
    nombre: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    """
    Retorna clientes para Analytics Comercial.

    Filtros opcionales:
    - id
    - codigo
    - nombre (LIKE nombre comercial)

    Uso:
    - Lista completa
    - Popup detalle cliente
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # BASE QUERY
    # --------------------------------------------------------
    sql = """
        SELECT
            id,
            codigo,
            nombrejuridico,
            nombrecomercial,
            telefono,
            cedulajuridicavat,
            actividad_economica,
            creado_en,
            pais,
            provincia,
            canton,
            distrito,
            direccionexacta,
            prefijo,
            correo,
            contacto_principal,
            contacto_secundario,
            fecha_pago,
            comentarios
        FROM cliente
        WHERE 1 = 1
    """

    params = {}

    # --------------------------------------------------------
    # FILTROS DINÁMICOS
    # --------------------------------------------------------
    if id is not None:
        sql += " AND id = %(id)s"
        params["id"] = id

    if codigo:
        sql += " AND codigo = %(codigo)s"
        params["codigo"] = codigo

    if nombre:
        sql += """
            AND (
                nombrejuridico = %(nombre)s
                OR nombrecomercial ILIKE %(nombre_like)s
            )
        """
        params["nombre"] = nombre
        params["nombre_like"] = f"%{nombre}%"

    sql += " ORDER BY nombrecomercial ASC;"

    # --------------------------------------------------------
    # EXEC
    # --------------------------------------------------------
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()

    return {
        "total": len(rows),
        "data": rows
    }
