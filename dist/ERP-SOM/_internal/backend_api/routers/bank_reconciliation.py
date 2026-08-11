from fastapi import APIRouter, Depends, Query, HTTPException, Header
from psycopg2.extras import RealDictCursor
from typing import Optional
from decimal import Decimal, InvalidOperation

from database import get_db
from rbac_service import has_permission
from services.finance_audit import actor_from_headers, audit_event, row_to_dict


router = APIRouter(
    prefix="/bank-reconciliation",
    tags=["Bank Reconciliation"]
)


def _money(value):
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(400, "Invalid amount")


def _ensure_professional_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_reconciliation_statements (
                id BIGSERIAL PRIMARY KEY,
                bank_name TEXT NOT NULL,
                bank_account_code TEXT,
                bank_account_name TEXT,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
                statement_period VARCHAR(7),
                statement_date DATE,
                source_filename TEXT,
                status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                imported_by TEXT,
                closed_by TEXT,
                closed_at TIMESTAMP,
                close_note TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                CHECK (status IN ('OPEN','MATCHED','CLOSED','REOPENED'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_reconciliation_statement_lines (
                id BIGSERIAL PRIMARY KEY,
                statement_id BIGINT NOT NULL REFERENCES bank_reconciliation_statements(id) ON DELETE CASCADE,
                line_date DATE NOT NULL,
                description TEXT,
                reference TEXT,
                debit NUMERIC(18,2) NOT NULL DEFAULT 0,
                credit NUMERIC(18,2) NOT NULL DEFAULT 0,
                amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
                matched_source TEXT,
                matched_id TEXT,
                matched_entry_id INTEGER,
                match_confidence NUMERIC(5,2),
                match_status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
                difference NUMERIC(18,2) NOT NULL DEFAULT 0,
                bank_fee_entry_id INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(statement_id, line_date, reference, amount),
                CHECK (match_status IN ('OPEN','AUTO_MATCHED','MANUAL_MATCHED','DIFFERENCE','BANK_FEE','REVERSED'))
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_reconciliation_closures (
                id BIGSERIAL PRIMARY KEY,
                bank_name TEXT NOT NULL,
                bank_account_code TEXT,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
                statement_period VARCHAR(7) NOT NULL,
                total_statement NUMERIC(18,2) NOT NULL DEFAULT 0,
                total_matched NUMERIC(18,2) NOT NULL DEFAULT 0,
                total_open NUMERIC(18,2) NOT NULL DEFAULT 0,
                open_items INTEGER NOT NULL DEFAULT 0,
                closed_by TEXT,
                closed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                status VARCHAR(20) NOT NULL DEFAULT 'CLOSED',
                note TEXT
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bank_recon_lines_status ON bank_reconciliation_statement_lines(match_status,line_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_bank_recon_statement_filter ON bank_reconciliation_statements(bank_account_code,currency_code,statement_period,status)")
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ux_bank_recon_closure_scope
            ON bank_reconciliation_closures(bank_name, COALESCE(bank_account_code,''), currency_code, statement_period)
        """)
    conn.commit()

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


@router.post("/statements/import")
def import_bank_statement(payload: dict, conn=Depends(get_db), x_user: str | None = Header(None, alias="X-User")):
    _ensure_professional_schema(conn)
    bank_name = str(payload.get("bank_name") or "").strip()
    currency = str(payload.get("currency_code") or "CRC").strip().upper()
    rows = payload.get("rows") or []
    if not bank_name or not rows:
        raise HTTPException(400, "bank_name and rows are required")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            INSERT INTO bank_reconciliation_statements (
                bank_name,bank_account_code,bank_account_name,currency_code,statement_period,
                statement_date,source_filename,imported_by
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
        """, (
            bank_name,
            payload.get("bank_account_code"),
            payload.get("bank_account_name"),
            currency,
            payload.get("statement_period"),
            payload.get("statement_date"),
            payload.get("source_filename"),
            x_user or payload.get("user") or "unknown",
        ))
        statement = cur.fetchone()
        inserted = 0
        skipped = 0
        for row in rows:
            debit = _money(row.get("debit"))
            credit = _money(row.get("credit"))
            amount = _money(row.get("amount"))
            if amount == 0:
                amount = credit - debit if credit else debit * Decimal("-1")
            try:
                cur.execute("""
                    INSERT INTO bank_reconciliation_statement_lines (
                        statement_id,line_date,description,reference,debit,credit,amount,currency_code
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(statement_id, line_date, reference, amount) DO NOTHING
                """, (
                    statement["id"],
                    row.get("line_date") or row.get("date"),
                    row.get("description"),
                    row.get("reference"),
                    debit,
                    credit,
                    amount,
                    str(row.get("currency_code") or currency).upper(),
                ))
                if cur.rowcount:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                raise
        audit_event(
            cur,
            module="bank_reconciliation",
            action="STATEMENT_IMPORTED",
            entity_type="bank_statement",
            entity_id=statement["id"],
            performed_by=x_user or payload.get("user") or "unknown",
            after={"statement": row_to_dict(statement)},
            metadata={"inserted": inserted, "skipped": skipped},
        )
    conn.commit()
    return {"status": "ok", "statement_id": statement["id"], "inserted": inserted, "skipped": skipped}


@router.get("/statements")
def list_bank_statements(
    bank_account_code: Optional[str] = Query(None),
    currency_code: Optional[str] = Query(None),
    period: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    conn=Depends(get_db),
):
    _ensure_professional_schema(conn)
    bank_account_code = bank_account_code if isinstance(bank_account_code, str) and bank_account_code else None
    currency_code = currency_code if isinstance(currency_code, str) and currency_code else None
    period = period if isinstance(period, str) and period else None
    status = status if isinstance(status, str) and status else None
    where, params = [], []
    if bank_account_code:
        where.append("s.bank_account_code=%s"); params.append(bank_account_code)
    if currency_code:
        where.append("s.currency_code=%s"); params.append(currency_code.upper())
    if period:
        where.append("s.statement_period=%s"); params.append(period)
    if status:
        where.append("s.status=%s"); params.append(status.upper())
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT s.*,
                   COUNT(l.id) AS line_count,
                   COUNT(l.id) FILTER (WHERE l.match_status='OPEN') AS open_count,
                   COALESCE(SUM(l.amount),0) AS statement_total,
                   COALESCE(SUM(l.amount) FILTER (WHERE l.match_status<>'OPEN'),0) AS matched_total,
                   COALESCE(SUM(l.amount) FILTER (WHERE l.match_status='OPEN'),0) AS open_total
            FROM bank_reconciliation_statements s
            LEFT JOIN bank_reconciliation_statement_lines l ON l.statement_id=s.id
            {where_sql}
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """, params)
        return {"data": cur.fetchall()}


@router.get("/statements/{statement_id}/lines")
def list_bank_statement_lines(statement_id: int, status: Optional[str] = Query(None), conn=Depends(get_db)):
    _ensure_professional_schema(conn)
    status = status if isinstance(status, str) and status else None
    params = [statement_id]
    where = "WHERE statement_id=%s"
    if status:
        where += " AND match_status=%s"
        params.append(status.upper())
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT *
            FROM bank_reconciliation_statement_lines
            {where}
            ORDER BY line_date DESC,id DESC
        """, params)
        return {"data": cur.fetchall()}


@router.post("/statements/{statement_id}/auto-match")
def auto_match_bank_statement(statement_id: int, payload: dict | None = None, conn=Depends(get_db)):
    _ensure_professional_schema(conn)
    payload = payload or {}
    tolerance = _money(payload.get("tolerance", "1.00"))
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM bank_reconciliation_statements WHERE id=%s FOR UPDATE", (statement_id,))
        statement = cur.fetchone()
        if not statement:
            raise HTTPException(404, "Statement not found")
        cur.execute("""
            SELECT * FROM bank_reconciliation_statement_lines
            WHERE statement_id=%s AND match_status='OPEN'
            ORDER BY line_date,id
        """, (statement_id,))
        matched = 0
        differences = 0
        for line in cur.fetchall():
            amount_abs = abs(Decimal(line["amount"] or 0))
            ref = str(line.get("reference") or "").strip()
            cur.execute("""
                SELECT 'cash_app' AS source, ca.id::text AS source_id, ca.monto_pagado AS amount,
                       ca.fecha_pago AS payment_date, ae.id AS entry_id
                FROM cash_app ca
                LEFT JOIN accounting_entries ae ON ae.origin='CASH_APP' AND ae.origin_id=ca.id
                WHERE ca.fecha_pago BETWEEN %s::date - INTERVAL '3 days' AND %s::date + INTERVAL '3 days'
                  AND ABS(COALESCE(ca.monto_pagado,0)-%s) <= %s
                  AND (%s='' OR COALESCE(ca.referencia,'') ILIKE %s)
                ORDER BY ABS(COALESCE(ca.monto_pagado,0)-%s), ca.fecha_pago DESC
                LIMIT 1
            """, (line["line_date"], line["line_date"], amount_abs, tolerance, ref, f"%{ref}%", amount_abs))
            candidate = cur.fetchone()
            if not candidate:
                cur.execute("""
                    SELECT 'accounting_line' AS source, l.id::text AS source_id,
                           ABS(COALESCE(l.debit,0)-COALESCE(l.credit,0)) AS amount,
                           e.entry_date AS payment_date, e.id AS entry_id
                    FROM accounting_lines l
                    JOIN accounting_entries e ON e.id=l.entry_id AND e.workflow_status='POSTED'
                    WHERE l.account_code=%s
                      AND e.entry_date BETWEEN %s::date - INTERVAL '3 days' AND %s::date + INTERVAL '3 days'
                      AND ABS(ABS(COALESCE(l.debit,0)-COALESCE(l.credit,0))-%s) <= %s
                    ORDER BY ABS(ABS(COALESCE(l.debit,0)-COALESCE(l.credit,0))-%s), e.entry_date DESC
                    LIMIT 1
                """, (statement.get("bank_account_code"), line["line_date"], line["line_date"], amount_abs, tolerance, amount_abs))
                candidate = cur.fetchone()
            if candidate:
                difference = Decimal(candidate["amount"] or 0) - amount_abs
                status = "AUTO_MATCHED" if abs(difference) <= tolerance else "DIFFERENCE"
                cur.execute("""
                    UPDATE bank_reconciliation_statement_lines
                    SET matched_source=%s,matched_id=%s,matched_entry_id=%s,
                        match_confidence=%s,match_status=%s,difference=%s,updated_at=NOW()
                    WHERE id=%s
                """, (candidate["source"], candidate["source_id"], candidate["entry_id"],
                      Decimal("100.00") if status == "AUTO_MATCHED" else Decimal("75.00"),
                      status, difference, line["id"]))
                matched += 1
                if status == "DIFFERENCE":
                    differences += 1
        cur.execute("""
            UPDATE bank_reconciliation_statements
            SET status=CASE WHEN NOT EXISTS (
                    SELECT 1 FROM bank_reconciliation_statement_lines
                    WHERE statement_id=%s AND match_status='OPEN'
                ) THEN 'MATCHED' ELSE status END,
                updated_at=NOW()
            WHERE id=%s
        """, (statement_id, statement_id))
    conn.commit()
    return {"status": "ok", "matched": matched, "differences": differences}


@router.post("/lines/{line_id}/bank-fee")
def mark_bank_fee(line_id: int, payload: dict | None = None, conn=Depends(get_db), x_user: str | None = Header(None, alias="X-User")):
    _ensure_professional_schema(conn)
    payload = payload or {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM bank_reconciliation_statement_lines WHERE id=%s FOR UPDATE", (line_id,))
        line = cur.fetchone()
        if not line:
            raise HTTPException(404, "Statement line not found")
        cur.execute("""
            UPDATE bank_reconciliation_statement_lines
            SET match_status='BANK_FEE', matched_source='bank_fee', difference=0, updated_at=NOW()
            WHERE id=%s RETURNING *
        """, (line_id,))
        updated = cur.fetchone()
        audit_event(
            cur,
            module="bank_reconciliation",
            action="BANK_FEE_MARKED",
            entity_type="bank_statement_line",
            entity_id=line_id,
            performed_by=x_user or payload.get("user") or "unknown",
            before=row_to_dict(line),
            after=row_to_dict(updated),
            metadata={"note": payload.get("note")},
        )
    conn.commit()
    return {"status": "ok", "line": updated}


@router.post("/statements/{statement_id}/close")
def close_bank_reconciliation(statement_id: int, payload: dict | None = None, conn=Depends(get_db), x_user: str | None = Header(None, alias="X-User")):
    _ensure_professional_schema(conn)
    payload = payload or {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM bank_reconciliation_statements WHERE id=%s FOR UPDATE", (statement_id,))
        statement = cur.fetchone()
        if not statement:
            raise HTTPException(404, "Statement not found")
        cur.execute("""
            SELECT COUNT(*) FILTER (WHERE match_status='OPEN') AS open_items,
                   COALESCE(SUM(amount),0) AS total_statement,
                   COALESCE(SUM(amount) FILTER (WHERE match_status<>'OPEN'),0) AS total_matched,
                   COALESCE(SUM(amount) FILTER (WHERE match_status='OPEN'),0) AS total_open
            FROM bank_reconciliation_statement_lines
            WHERE statement_id=%s
        """, (statement_id,))
        totals = cur.fetchone()
        if int(totals["open_items"] or 0) > 0 and not payload.get("force_close"):
            raise HTTPException(409, "Open bank items remain. Use force_close only with documented reason.")
        user = x_user or payload.get("user") or "unknown"
        cur.execute("""
            UPDATE bank_reconciliation_statements
            SET status='CLOSED', closed_by=%s, closed_at=NOW(), close_note=%s, updated_at=NOW()
            WHERE id=%s RETURNING *
        """, (user, payload.get("note"), statement_id))
        closed = cur.fetchone()
        cur.execute("""
            DELETE FROM bank_reconciliation_closures
            WHERE bank_name=%s
              AND COALESCE(bank_account_code,'')=COALESCE(%s,'')
              AND currency_code=%s
              AND statement_period=%s
        """, (
            statement["bank_name"], statement.get("bank_account_code"), statement["currency_code"],
            statement.get("statement_period") or str(statement.get("statement_date") or "")[:7],
        ))
        cur.execute("""
            INSERT INTO bank_reconciliation_closures (
                bank_name,bank_account_code,currency_code,statement_period,
                total_statement,total_matched,total_open,open_items,closed_by,note
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            statement["bank_name"], statement.get("bank_account_code"), statement["currency_code"],
            statement.get("statement_period") or str(statement.get("statement_date") or "")[:7],
            totals["total_statement"], totals["total_matched"], totals["total_open"], totals["open_items"],
            user, payload.get("note"),
        ))
        audit_event(
            cur,
            module="bank_reconciliation",
            action="RECONCILIATION_CLOSED",
            entity_type="bank_statement",
            entity_id=statement_id,
            performed_by=user,
            before=row_to_dict(statement),
            after=row_to_dict(closed),
            metadata=row_to_dict(totals),
        )
    conn.commit()
    return {"status": "ok", "statement": closed, "totals": totals}

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
    conn=Depends(get_db),
    x_user: str | None = Header(None, alias="X-User"),
    x_role: str | None = Header(None, alias="X-Role"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
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
    performed_by, performed_role = actor_from_headers(x_user, x_role, x_user_role)

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
        SELECT *
        FROM cash_app
        WHERE id = %(id)s
    """, {"id": cash_app_id})

    row = cur.fetchone()

    if row:
        before = row_to_dict(row)
        # -----------------------------
        # REVERSA REAL cash_app
        # -----------------------------
        cur.execute("""
            DELETE FROM cash_app
            WHERE id = %(id)s
        """, {"id": cash_app_id})

        audit_event(
            cur,
            module="bank_reconciliation",
            action="PAYMENT_REVERSED",
            entity_type="cash_app",
            entity_id=cash_app_id,
            performed_by=performed_by,
            performed_role=performed_role,
            reason=reason,
            before=before,
            metadata={"comment": comment},
        )

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
        SELECT *
        FROM incoming_payments
        WHERE id = %(id)s
    """, {"id": cash_app_id})

    row = cur.fetchone()

    if row:
        before = row_to_dict(row)
        # -----------------------------
        # REVERSA REAL incoming_payments
        # -----------------------------
        cur.execute("""
            DELETE FROM incoming_payments
            WHERE id = %(id)s
        """, {"id": cash_app_id})

        audit_event(
            cur,
            module="bank_reconciliation",
            action="PAYMENT_REVERSED",
            entity_type="incoming_payments",
            entity_id=cash_app_id,
            performed_by=performed_by,
            performed_role=performed_role,
            reason=reason,
            before=before,
            metadata={"comment": comment},
        )

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
