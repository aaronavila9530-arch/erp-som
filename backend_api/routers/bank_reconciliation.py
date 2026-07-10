from fastapi import APIRouter, Depends, Query, HTTPException, Header
from psycopg2.extras import RealDictCursor
from typing import Optional

from database import get_db
from rbac_service import has_permission


router = APIRouter(
    prefix="/bank-reconciliation",
    tags=["Bank Reconciliation"]
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
# GET /bank-reconciliation
# LISTADO PAGINADO cash_app + incoming_payments
# ============================================================
@router.get("")
def get_bank_reconciliation(
    codigo_cliente: Optional[str] = Query(None),
    referencia: Optional[str] = Query(None),
    ver_todos: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    conn=Depends(get_db)
):

    # -----------------------------
    # PROTECCIÓN ANTI-LAG
    # -----------------------------
    if not ver_todos and not codigo_cliente and not referencia:
        return {
            "page": page,
            "page_size": page_size,
            "total": 0,
            "data": []
        }

    offset = (page - 1) * page_size
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ============================================================
    # ===================== CASH_APP (NO TOCAR) ==================
    # ============================================================
    where_clauses = []
    params = {}

    if codigo_cliente:
        where_clauses.append("ca.codigo_cliente = %(codigo_cliente)s")
        params["codigo_cliente"] = codigo_cliente

    if referencia:
        where_clauses.append("ca.referencia ILIKE %(referencia)s")
        params["referencia"] = f"%{referencia}%"

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    cash_sql = f"""
        SELECT
            ca.id,
            ca.numero_documento,
            ca.codigo_cliente,
            ca.nombre_cliente,
            ca.banco,
            ca.fecha_pago,
            ca.comision,
            ca.referencia,
            ca.monto_pagado,
            ca.tipo_aplicacion,
            ca.created_at,

            -- Calculados solo para UI
            0::numeric AS monto_aplicado,
            ca.monto_pagado AS saldo,

            CASE
                WHEN ca.monto_pagado > 0 THEN 'APLICADO'
                ELSE 'DESAPLICADO'
            END AS estado
        FROM cash_app ca
        {where_sql}
        ORDER BY ca.fecha_pago DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """

    params_cash = params.copy()
    params_cash["limit"] = page_size
    params_cash["offset"] = offset

    cur.execute(cash_sql, params_cash)
    cash_rows = cur.fetchall()

    count_cash_sql = f"""
        SELECT COUNT(*) AS total
        FROM cash_app ca
        {where_sql}
    """
    cur.execute(count_cash_sql, params)
    total_cash = cur.fetchone()["total"]

    # ============================================================
    # ================= INCOMING_PAYMENTS (AGREGADO) =============
    # ============================================================
    where_ip = []
    params_ip = {}

    if codigo_cliente:
        where_ip.append("ip.codigo_cliente = %(codigo_cliente)s")
        params_ip["codigo_cliente"] = codigo_cliente

    if referencia:
        where_ip.append("ip.numero_referencia ILIKE %(referencia)s")
        params_ip["referencia"] = f"%{referencia}%"

    where_ip_sql = ""
    if where_ip:
        where_ip_sql = "WHERE " + " AND ".join(where_ip)

    incoming_sql = f"""
        SELECT
            'incoming_' || ip.id AS id,
            ip.documento AS numero_documento,
            ip.codigo_cliente,
            ip.nombre_cliente,
            ip.banco,
            ip.fecha_pago,
            NULL::numeric AS comision,
            ip.numero_referencia AS referencia,
            ip.monto AS monto_pagado,
            'PAGO' AS tipo_aplicacion,
            ip.created_at,

            -- Calculados solo para UI
            0::numeric AS monto_aplicado,
            ip.monto AS saldo,
            ip.estado
        FROM incoming_payments ip
        {where_ip_sql}
        ORDER BY ip.fecha_pago DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """

    params_ip["limit"] = page_size
    params_ip["offset"] = offset

    cur.execute(incoming_sql, params_ip)
    incoming_rows = cur.fetchall()

    count_ip_sql = f"""
        SELECT COUNT(*) AS total
        FROM incoming_payments ip
        {where_ip_sql}
    """
    cur.execute(count_ip_sql, params_ip)
    total_ip = cur.fetchone()["total"]

    cur.close()

    # ============================================================
    # ======================= RESULTADO ==========================
    # ============================================================
    data = cash_rows + incoming_rows

    return {
        "page": page,
        "page_size": page_size,
        "total": total_cash + total_ip,
        "data": data
    }


# ============================================================
# GET /bank-reconciliation/paid-invoices-report
# REPORTE DE FACTURAS PAGADAS
# ============================================================
@router.get("/paid-invoices-report")
def get_paid_invoices_report(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    month: Optional[int] = Query(None, ge=1, le=12),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    cliente: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(500, ge=1, le=1000),
    conn=Depends(get_db)
):
    """
    Devuelve pagos aplicados a facturas desde cash_app e incoming_payments.
    Permite filtrar por mes, anio, rango de fechas y cliente.
    """
    offset = (page - 1) * page_size
    cur = conn.cursor(cursor_factory=RealDictCursor)

    where = []
    params = {
        "limit": page_size,
        "offset": offset,
    }

    if date_from:
        where.append("pagos.fecha_pago >= %(date_from)s::date")
        params["date_from"] = date_from

    if date_to:
        where.append("pagos.fecha_pago <= %(date_to)s::date")
        params["date_to"] = date_to

    if year and not date_from and not date_to:
        where.append("EXTRACT(YEAR FROM pagos.fecha_pago) = %(year)s")
        params["year"] = year

    if month and not date_from and not date_to:
        where.append("EXTRACT(MONTH FROM pagos.fecha_pago) = %(month)s")
        params["month"] = month

    if cliente:
        where.append("""
            (
                pagos.codigo_cliente ILIKE %(cliente_like)s
                OR pagos.nombre_cliente ILIKE %(cliente_like)s
            )
        """)
        params["cliente_like"] = f"%{cliente}%"

    where_sql = ""
    if where:
        where_sql = "WHERE " + " AND ".join(where)

    base_sql = f"""
        WITH pagos AS (
            SELECT
                'cash_app'::text AS source,
                ca.id::text AS payment_id,
                ca.numero_documento,
                ca.codigo_cliente,
                ca.nombre_cliente,
                ca.banco,
                ca.fecha_pago,
                ca.comision,
                ca.referencia,
                ca.monto_pagado,
                ca.tipo_aplicacion,
                CASE
                    WHEN c.estado_factura IS NOT NULL THEN c.estado_factura
                    WHEN ca.monto_pagado > 0 THEN 'APLICADO'
                    ELSE 'DESAPLICADO'
                END AS estado_factura,
                c.total AS total_factura,
                c.saldo_pendiente
            FROM cash_app ca
            LEFT JOIN collections c
                ON ltrim(c.numero_documento, '0') = ltrim(ca.numero_documento, '0')
               AND c.codigo_cliente = ca.codigo_cliente
               AND c.tipo_documento = 'FACTURA'
            WHERE ca.monto_pagado > 0

            UNION ALL

            SELECT
                'incoming_payments'::text AS source,
                ip.id::text AS payment_id,
                ip.documento AS numero_documento,
                ip.codigo_cliente,
                ip.nombre_cliente,
                ip.banco,
                ip.fecha_pago,
                NULL::numeric AS comision,
                ip.numero_referencia AS referencia,
                ip.monto AS monto_pagado,
                'PAGO'::text AS tipo_aplicacion,
                COALESCE(c.estado_factura, ip.estado) AS estado_factura,
                c.total AS total_factura,
                c.saldo_pendiente
            FROM incoming_payments ip
            LEFT JOIN collections c
                ON ltrim(c.numero_documento, '0') = ltrim(ip.documento, '0')
               AND c.codigo_cliente = ip.codigo_cliente
               AND c.tipo_documento = 'FACTURA'
            WHERE ip.monto > 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM cash_app ca2
                  WHERE ltrim(ca2.numero_documento, '0') = ltrim(ip.documento, '0')
                    AND ca2.codigo_cliente = ip.codigo_cliente
                    AND COALESCE(ca2.referencia, '') = COALESCE(ip.numero_referencia, '')
                    AND ca2.fecha_pago = ip.fecha_pago
                    AND ca2.monto_pagado = ip.monto
              )
        )
        SELECT *
        FROM pagos
        {where_sql}
    """

    try:
        cur.execute(
            f"""
            SELECT COUNT(*) AS total,
                   COUNT(DISTINCT numero_documento || '|' || COALESCE(codigo_cliente, '')) AS total_facturas,
                   COUNT(DISTINCT codigo_cliente) AS total_clientes,
                   COALESCE(SUM(monto_pagado), 0) AS total_pagado,
                   COALESCE(SUM(comision), 0) AS total_comision
            FROM ({base_sql}) q
            """,
            params
        )
        summary = cur.fetchone() or {}

        cur.execute(
            base_sql + """
            ORDER BY fecha_pago DESC, numero_documento ASC, source ASC
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params
        )
        rows = cur.fetchall()

        return {
            "page": page,
            "page_size": page_size,
            "total": summary.get("total", 0),
            "summary": {
                "total_facturas": summary.get("total_facturas", 0),
                "total_clientes": summary.get("total_clientes", 0),
                "total_pagado": summary.get("total_pagado", 0),
                "total_comision": summary.get("total_comision", 0),
            },
            "data": rows
        }
    finally:
        cur.close()


# ============================================================
# POST /bank-reconciliation/{cash_app_id}/reverse
# REVERSA TOTAL (DELETE REAL)
# ============================================================
@router.post("/{cash_app_id}/reverse")
def reverse_cash_app(
    cash_app_id: int,
    payload: dict,
    conn=Depends(get_db)
):
    """
    payload esperado:
    {
        "reason": "WRONG_PAYMENT",
        "comment": "Payment registered incorrectly"
    }
    """

    reason = payload.get("reason")
    comment = payload.get("comment")

    if not reason or not comment:
        raise HTTPException(
            status_code=400,
            detail="Reason and comment are required."
        )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # 1️⃣ INTENTAR CASH_APP (NO TOCADO)
    # =====================================================
    cur.execute("""
        SELECT id
        FROM cash_app
        WHERE id = %(id)s
    """, {"id": cash_app_id})

    row = cur.fetchone()

    if row:
        # -----------------------------
        # REVERSA REAL cash_app
        # -----------------------------
        cur.execute("""
            DELETE FROM cash_app
            WHERE id = %(id)s
        """, {"id": cash_app_id})

        conn.commit()
        cur.close()

        return {
            "status": "success",
            "message": "Payment reversed and removed from cash_app.",
            "source": "cash_app",
            "id": cash_app_id
        }

    # =====================================================
    # 2️⃣ SI NO EXISTE EN cash_app → incoming_payments
    # =====================================================
    cur.execute("""
        SELECT id
        FROM incoming_payments
        WHERE id = %(id)s
    """, {"id": cash_app_id})

    row = cur.fetchone()

    if row:
        # -----------------------------
        # REVERSA REAL incoming_payments
        # -----------------------------
        cur.execute("""
            DELETE FROM incoming_payments
            WHERE id = %(id)s
        """, {"id": cash_app_id})

        conn.commit()
        cur.close()

        return {
            "status": "success",
            "message": "Payment reversed and removed from incoming_payments.",
            "source": "incoming_payments",
            "id": cash_app_id
        }

    # =====================================================
    # 3️⃣ NO EXISTE EN NINGUNA
    # =====================================================
    cur.close()
    raise HTTPException(
        status_code=404,
        detail="Payment not found in cash_app or incoming_payments."
    )
