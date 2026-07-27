from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Header,
    UploadFile,
    File,
    Form
)
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from typing import Optional
import os
import shutil

from database import get_db
from rbac_service import has_permission
from services.finance_audit import actor_from_headers, audit_event, row_to_dict


router = APIRouter(
    prefix="/invoice-to-pay",
    tags=["Finance - Invoice to Pay"]
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
# 🔁 SYNC SERVICIOS → PAYMENT OBLIGATIONS
# ============================================================
def _sync_servicios_to_itp(cur):
    """
    Sincroniza obligaciones desde servicios hacia Invoice To Pay.

    Reglas:
    - INSERTA si no existe
    - ACTUALIZA solo si:
        • origin = 'SERVICIOS'
        • status = 'PENDING' o 'PARTIAL'
        • el monto cambió
    - Respeta pagos parciales recalculando balance
    """

    # ============================================================
    # 1️⃣ INSERTAR HONORARIOS (SURVEYOR_FEE)
    # ============================================================
    cur.execute("""
        INSERT INTO payment_obligations (
            record_type,
            payee_type,
            payee_name,
            obligation_type,
            reference,
            vessel,
            country,
            operation,
            service_id,
            issue_date,
            due_date,
            currency,
            total,
            balance,
            status,
            origin,
            notes,
            created_at
        )
        SELECT
            'OBLIGATION',
            'SURVEYOR',
            s.surveyor,
            'SURVEYOR_FEE',
            s.consec,
            s.buque_contenedor,
            s.pais,
            s.operacion,
            s.consec,
            s.fecha_fin,
            (s.fecha_fin + INTERVAL '15 days'),
            'USD',
            s.honorarios,
            s.honorarios,
            'PENDING',
            'SERVICIOS',
            s.detalle,
            NOW()
        FROM servicios s
        WHERE
            s.surveyor IS NOT NULL
            AND s.honorarios IS NOT NULL
            AND s.honorarios > 0
            AND s.fecha_fin IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM payment_obligations po
                WHERE po.service_id = s.consec
                  AND po.origin = 'SERVICIOS'
                  AND po.obligation_type = 'SURVEYOR_FEE'
            )
    """)

    # ============================================================
    # 2️⃣ INSERTAR COSTO TARJETAS (CARD_PROCESSING)
    # ============================================================
    cur.execute("""
        INSERT INTO payment_obligations (
            record_type,
            payee_type,
            payee_name,
            obligation_type,
            reference,
            vessel,
            country,
            operation,
            service_id,
            issue_date,
            due_date,
            currency,
            total,
            balance,
            status,
            origin,
            notes,
            created_at
        )
        SELECT
            'OBLIGATION',
            'SUPPLIER',
            'CARD PROCESSOR',
            'CARD_PROCESSING',
            s.consec,
            s.buque_contenedor,
            s.pais,
            s.operacion,
            s.consec,
            s.fecha_fin,
            (s.fecha_fin + INTERVAL '15 days'),
            'USD',
            s.costo_tarjetas,
            s.costo_tarjetas,
            'PENDING',
            'SERVICIOS',
            'Costo tarjetas - ' || COALESCE(s.detalle,''),
            NOW()
        FROM servicios s
        WHERE
            s.costo_tarjetas IS NOT NULL
            AND s.costo_tarjetas > 0
            AND s.fecha_fin IS NOT NULL
            AND NOT EXISTS (
                SELECT 1
                FROM payment_obligations po
                WHERE po.service_id = s.consec
                  AND po.origin = 'SERVICIOS'
                  AND po.obligation_type = 'CARD_PROCESSING'
            )
    """)

    # ============================================================
    # 3️⃣ ACTUALIZAR HONORARIOS MODIFICADOS
    # ============================================================
    cur.execute("""
        UPDATE payment_obligations po
        SET
            total = s.honorarios,
            balance = GREATEST(
                s.honorarios - (po.total - po.balance),
                0
            ),
            payee_name = COALESCE(s.surveyor, po.payee_name),
            vessel = COALESCE(s.buque_contenedor, po.vessel),
            country = COALESCE(s.pais, po.country),
            operation = COALESCE(s.operacion, po.operation),
            issue_date = COALESCE(s.fecha_fin, po.issue_date),
            due_date = COALESCE((s.fecha_fin + INTERVAL '15 days'), po.due_date),
            notes = COALESCE(s.detalle, po.notes),
            updated_at = NOW()
        FROM servicios s
        WHERE
            po.service_id = s.consec
            AND po.origin = 'SERVICIOS'
            AND po.obligation_type = 'SURVEYOR_FEE'
            AND s.honorarios IS NOT NULL
            AND s.honorarios > 0
            AND po.status IN ('PENDING', 'PARTIAL')
            AND po.total IS DISTINCT FROM s.honorarios
    """)

    # ============================================================
    # 4️⃣ ACTUALIZAR COSTO TARJETAS MODIFICADO
    # ============================================================
    cur.execute("""
        UPDATE payment_obligations po
        SET
            total = s.costo_tarjetas,
            balance = GREATEST(
                s.costo_tarjetas - (po.total - po.balance),
                0
            ),
            vessel = COALESCE(s.buque_contenedor, po.vessel),
            country = COALESCE(s.pais, po.country),
            operation = COALESCE(s.operacion, po.operation),
            issue_date = COALESCE(s.fecha_fin, po.issue_date),
            due_date = COALESCE((s.fecha_fin + INTERVAL '15 days'), po.due_date),
            notes = 'Costo tarjetas - ' || COALESCE(s.detalle,''),
            updated_at = NOW()
        FROM servicios s
        WHERE
            po.service_id = s.consec
            AND po.origin = 'SERVICIOS'
            AND po.obligation_type = 'CARD_PROCESSING'
            AND s.costo_tarjetas IS NOT NULL
            AND s.costo_tarjetas > 0
            AND po.status IN ('PENDING', 'PARTIAL')
            AND po.total IS DISTINCT FROM s.costo_tarjetas
    """)

@router.get("/search")
def search_invoice_to_pay(
    obligation_type: Optional[str] = Query(None),
    payee: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    issue_date_from: Optional[date] = Query(None),
    issue_date_to: Optional[date] = Query(None),
    payment_date_from: Optional[date] = Query(None),
    payment_date_to: Optional[date] = Query(None),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 🔁 Sync servicios → Invoice To Pay
    _sync_servicios_to_itp(cur)
    conn.commit()

    filters = []
    params = []

    # =================
    # FILTRO POR ESTADO
    # =================
    if status:
        status = status.upper()

        if status == "ALL":
            # 🔥 Sin filtro: trae TODOS los registros
            pass
        else:
            filters.append("status = %s")
            params.append(status)

    # =================================
    # FILTRO POR TIPO DE OBLIGACIÓN
    # (basado en payee_type REAL)
    # =================================
    if obligation_type:
        if obligation_type.upper() == "SURVEYOR":
            filters.append("payee_type = 'SURVEYOR'")
        elif obligation_type.upper() == "SUPPLIER":
            filters.append("payee_type = 'SUPPLIER'")
        elif obligation_type.upper() == "MANUAL":
            filters.append("origin = 'MANUAL'")

    # =================
    # FILTRO BENEFICIARIO
    # =================
    if payee:
        filters.append("payee_name ILIKE %s")
        params.append(f"%{payee}%")

    # ================================
    # FILTROS POR RANGOS DE FECHA
    # ================================
    if issue_date_from:
        filters.append("issue_date >= %s")
        params.append(issue_date_from)

    if issue_date_to:
        filters.append("issue_date <= %s")
        params.append(issue_date_to)

    if payment_date_from:
        filters.append("last_payment_date >= %s")
        params.append(payment_date_from)

    if payment_date_to:
        filters.append("last_payment_date <= %s")
        params.append(payment_date_to)

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    # ========================================
    # SELECT FINAL CORRECTO
    # ========================================
    sql = f"""
        SELECT
            id,
            payee_name,

            -- ✅ COLUMNA Obligación = payee_type REAL
            payee_type AS obligation_type,

            -- ✅ COLUMNA Referencia (regla de negocio)
            CASE
                WHEN origin = 'SERVICIOS' THEN notes
                ELSE reference
            END AS referencia,

            vessel,
            country,
            operation,
            currency,
            total,
            balance,
            status,
            last_payment_date,
            issue_date,
            due_date,
            origin

        FROM payment_obligations
        {where_clause}
        ORDER BY issue_date DESC
    """

    try:
        cur.execute(sql, params)
        rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"InvoiceToPay search error: {str(e)}"
        )

    return {"data": rows}


# ============================================================
# 2️⃣ KPIs — CONVERSIÓN CRC → USD (TC = 500)
# ============================================================
@router.get("/kpis")
def invoice_to_pay_kpis(conn=Depends(get_db)):
    cur = conn.cursor()

    cur.execute("""
        SELECT
            -- =====================================
            -- PENDING (TOTAL ACTUAL, NO HISTÓRICO)
            -- =====================================
            COALESCE(
                SUM(
                    CASE
                        WHEN status IN ('PENDING','PARTIAL') THEN
                            CASE
                                WHEN currency = 'CRC' THEN balance / 500.0
                                ELSE balance
                            END
                    END
                ), 0
            ) AS pending_usd,

            -- =====================================
            -- PAID (SOLO PAGOS DEL MES EN CURSO)
            -- =====================================
            COALESCE(
                SUM(
                    CASE
                        WHEN status IN ('PAID','PARTIAL')
                         AND last_payment_date IS NOT NULL
                         AND DATE_TRUNC('month', last_payment_date) = DATE_TRUNC('month', CURRENT_DATE)
                        THEN
                            CASE
                                WHEN currency = 'CRC' THEN (total - balance) / 500.0
                                ELSE (total - balance)
                            END
                    END
                ), 0
            ) AS paid_usd,

            -- =====================================
            -- DPO (SOLO FACTURAS PAGADAS ESTE MES)
            -- =====================================
            ROUND(
                AVG(
                    CASE
                        WHEN status = 'PAID'
                         AND last_payment_date IS NOT NULL
                         AND DATE_TRUNC('month', last_payment_date) = DATE_TRUNC('month', CURRENT_DATE)
                         AND issue_date IS NOT NULL
                        THEN (last_payment_date - issue_date)
                    END
                ), 2
            ) AS dpo,

            -- =====================================
            -- OVERDUE COUNT (ACTUAL)
            -- =====================================
            COUNT(
                CASE
                    WHEN balance > 0
                     AND due_date IS NOT NULL
                     AND due_date < CURRENT_DATE
                    THEN 1
                END
            ) AS overdue,

            -- =====================================
            -- OVERDUE AMOUNT (USD)
            -- =====================================
            COALESCE(
                SUM(
                    CASE
                        WHEN balance > 0
                         AND due_date IS NOT NULL
                         AND due_date < CURRENT_DATE
                        THEN
                            CASE
                                WHEN currency = 'CRC' THEN balance / 500.0
                                ELSE balance
                            END
                    END
                ), 0
            ) AS overdue_amount_usd

        FROM payment_obligations
        WHERE record_type = 'OBLIGATION'
    """)

    pending, paid, dpo, overdue, overdue_amount = cur.fetchone()

    return {
        "pending": round(pending, 2),
        "paid": round(paid, 2),
        "dpo": dpo,
        "overdue": overdue,
        "overdue_amount": round(overdue_amount, 2),
        "currency": "USD",
        "exchange_rate": 500,
        "scope": "CURRENT_MONTH"
    }

# ============================================================
# 3️⃣ APPLY PAYMENT — BLINDADO FINANCIERO
# ============================================================
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

@router.post("/apply-payment")
def apply_payment(
    obligation_id: int,
    amount: float,
    payment_date: date,
    bank_account_code: Optional[str] = Query(None),
    bank_account_name: Optional[str] = Query(None),
    bank_name: Optional[str] = Query(None),
    conn=Depends(get_db),
    x_user: str | None = Header(None, alias="X-User"),
    x_role: str | None = Header(None, alias="X-Role"),
    x_user_role: str | None = Header(None, alias="X-User-Role"),
):
    cur = None

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        bank_account_code = str(bank_account_code or "").strip()
        bank_account_name = str(bank_account_name or "").strip()
        bank_name = str(bank_name or bank_account_name or "").strip()
        performed_by, performed_role = actor_from_headers(x_user, x_role, x_user_role)

        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS payment_bank TEXT
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS payment_bank_account_code TEXT
        """)
        cur.execute("""
            ALTER TABLE payment_obligations
            ADD COLUMN IF NOT EXISTS payment_bank_account_name TEXT
        """)

        if bank_account_code:
            cur.execute("""
                SELECT account_code, account_name
                FROM accounting_ledger
                WHERE account_code = %s
                  AND active = TRUE
                LIMIT 1
            """, (bank_account_code,))
            bank_row = cur.fetchone()
            if not bank_row:
                raise HTTPException(
                    status_code=400,
                    detail="Selected bank account does not exist or is inactive"
                )
            bank_account_name = bank_account_name or bank_row["account_name"]
            bank_name = bank_name or bank_account_name

        # =====================================================
        # 1️⃣ BLOQUEAR FILA (ANTI CONCURRENCIA)
        # =====================================================
        cur.execute("""
            SELECT *
            FROM payment_obligations
            WHERE id = %s
              AND record_type = 'OBLIGATION'
            FOR UPDATE
        """, (obligation_id,))

        obligation = cur.fetchone()

        if not obligation:
            raise HTTPException(
                status_code=404,
                detail="Obligation not found"
            )

        before_obligation = row_to_dict(obligation)

        # =====================================================
        # 2️⃣ CONVERTIR A DECIMAL (FINANCIERO CORRECTO)
        # =====================================================
        try:
            balance = Decimal(str(obligation["balance"])).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            amount_decimal = Decimal(str(amount)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

        except InvalidOperation:
            raise HTTPException(
                status_code=400,
                detail="Invalid monetary format"
            )

        # =====================================================
        # 3️⃣ VALIDACIONES DE NEGOCIO
        # =====================================================
        if amount_decimal <= Decimal("0.00"):
            raise HTTPException(
                status_code=400,
                detail="Payment amount must be greater than zero"
            )

        if obligation["status"] == "PAID":
            raise HTTPException(
                status_code=400,
                detail="Obligation is already fully paid"
            )

        if amount_decimal > balance:
            raise HTTPException(
                status_code=400,
                detail="Payment exceeds outstanding balance"
            )

        # =====================================================
        # 4️⃣ CÁLCULO SEGURO DE NUEVO SALDO
        # =====================================================
        new_balance = (balance - amount_decimal).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if new_balance < Decimal("0.00"):
            # Protección extrema (nunca debería pasar)
            raise HTTPException(
                status_code=400,
                detail="Resulting balance cannot be negative"
            )

        new_status = (
            "PAID"
            if new_balance == Decimal("0.00")
            else "PARTIAL"
        )

        # =====================================================
        # 5️⃣ UPDATE TRANSACCIONAL
        # =====================================================
        cur.execute("""
            UPDATE payment_obligations
            SET
                balance = %s,
                status = %s,
                last_payment_date = %s,
                payment_bank = %s,
                payment_bank_account_code = %s,
                payment_bank_account_name = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            new_balance,
            new_status,
            payment_date,
            bank_name or None,
            bank_account_code or None,
            bank_account_name or None,
            obligation_id
        ))

        cur.execute("SELECT * FROM payment_obligations WHERE id = %s", (obligation_id,))
        after_obligation = row_to_dict(cur.fetchone())

        audit_event(
            cur,
            module="itp",
            action="PAYMENT_APPLIED",
            entity_type="payment_obligation",
            entity_id=obligation_id,
            performed_by=performed_by,
            performed_role=performed_role,
            before=before_obligation,
            after=after_obligation,
            metadata={
                "applied_amount": str(amount_decimal),
                "payment_date": payment_date,
                "bank_account_code": bank_account_code or None,
                "bank_account_name": bank_account_name or None,
                "new_balance": str(new_balance),
            },
        )

        conn.commit()

        accounting_warning = None
        try:
            from services.accounting_auto import sync_itp_to_accounting
            sync_itp_to_accounting(conn)
        except Exception as sync_error:
            accounting_warning = str(sync_error)

        return {
            "message": "Payment applied successfully",
            "obligation_id": obligation_id,
            "previous_balance": float(balance),
            "applied_amount": float(amount_decimal),
            "new_balance": float(new_balance),
            "status": new_status,
            "accounting_warning": accounting_warning
        }

    except HTTPException:
        if conn:
            conn.rollback()
        raise

    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error applying payment: {repr(e)}"
        )

    finally:
        if cur:
            cur.close()

# ============================================================
# 4️⃣ MANUAL OBLIGATION
# ============================================================
@router.post("/manual")
def create_manual_obligation(
    payee_name: str,
    obligation_type: str,
    total: float,
    currency: str,
    reference: Optional[str] = None,
    notes: Optional[str] = None,
    payee_type: str = "OTHER",
    conn=Depends(get_db)
):
    if total <= 0:
        raise HTTPException(
            status_code=400,
            detail="Total must be greater than zero"
        )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            INSERT INTO payment_obligations (
                record_type,
                payee_type,
                payee_name,
                obligation_type,
                reference,
                currency,
                total,
                balance,
                status,
                origin,
                notes,
                active,
                created_at
            )
            VALUES (
                'OBLIGATION',
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'PENDING',
                'MANUAL',
                %s,
                TRUE,
                NOW()
            )
            RETURNING id
        """, (
            payee_type,
            payee_name,
            obligation_type,
            reference,
            currency,
            total,
            total,
            notes
        ))

        new_id = cur.fetchone()["id"]
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating manual obligation: {str(e)}"
        )

    return {
        "message": "Manual obligation created successfully",
        "id": new_id
    }

# ============================================================
# 📥 UPLOAD XML (FACTURA / NC) — 100% BLINDADO
# ============================================================
@router.post("/upload/xml")
def upload_invoice_xml(
    file: UploadFile = File(...),
    conn=Depends(get_db)
):
    from xml.etree import ElementTree as ET
    from datetime import datetime, date, timedelta
    import os
    import shutil

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ============================================================
    # GUARDAR ARCHIVO
    # ============================================================
    os.makedirs("storage/invoice_to_pay/xml", exist_ok=True)

    ts = int(datetime.now().timestamp())
    safe_name = file.filename.replace(" ", "_")
    filepath = f"storage/invoice_to_pay/xml/{ts}_{safe_name}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # ============================================================
    # PARSE XML (TOLERANTE)
    # ============================================================
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Namespace dinámico
        if "}" in root.tag:
            ns_uri = root.tag.split("}")[0].strip("{")
            ns = {"fe": ns_uri}
            p = "fe:"
        else:
            ns = {}
            p = ""

        def find_text(paths, default=None):
            for path in paths:
                node = root.find(path, ns)
                if node is not None and node.text:
                    return node.text.strip()
            return default

        # ------------------------------------------------------------
        # TIPO DOCUMENTO
        # ------------------------------------------------------------
        is_credit_note = root.find(f".//{p}NotaCreditoElectronica", ns) is not None \
                         or "NotaCredito" in root.tag

        obligation_type = (
            "SUPPLIER_CREDIT_NOTE" if is_credit_note else "SUPPLIER_INVOICE"
        )

        # ------------------------------------------------------------
        # CLAVE
        # ------------------------------------------------------------
        clave = find_text([
            f".//{p}Clave",
            ".//Clave"
        ])
        if not clave:
            raise ValueError("XML sin Clave")

        # ------------------------------------------------------------
        # FECHA EMISIÓN
        # ------------------------------------------------------------
        fecha_raw = find_text([
            f".//{p}FechaEmision",
            ".//FechaEmision"
        ])
        if not fecha_raw:
            raise ValueError("XML sin FechaEmision")

        issue_date = date.fromisoformat(fecha_raw.split("T")[0])

        # ------------------------------------------------------------
        # EMISOR
        # ------------------------------------------------------------
        emisor = find_text([
            f".//{p}Emisor/{p}Nombre",
            f".//{p}Nombre"
        ], "PROVEEDOR DESCONOCIDO")

        # ------------------------------------------------------------
        # MONEDA
        # ------------------------------------------------------------
        moneda = find_text([
            f".//{p}CodigoMoneda",
            ".//CodigoMoneda"
        ], "CRC")

        # ------------------------------------------------------------
        # TOTAL (FACTURA / NC)
        # ------------------------------------------------------------
        total_raw = find_text([
            f".//{p}TotalComprobante",
            f".//{p}MontoTotal",
            ".//TotalComprobante"
        ])

        if not total_raw:
            raise ValueError("XML sin TotalComprobante")

        total = float(total_raw)

        if is_credit_note:
            total = total * -1  # NC = negativo

        # ------------------------------------------------------------
        # PLAZO
        # ------------------------------------------------------------
        plazo_raw = find_text([
            f".//{p}PlazoCredito",
            ".//PlazoCredito"
        ])

        term_days = int(plazo_raw) if plazo_raw and plazo_raw.isdigit() else 30
        due_date = issue_date + timedelta(days=term_days)

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error parsing XML: {str(e)}"
        )

    # ============================================================
    # INSERTAR payment_obligations
    # ============================================================
    try:
        cur.execute("""
            INSERT INTO payment_obligations (
                record_type,
                payee_type,
                payee_id,
                payee_name,
                obligation_type,
                reference,
                issue_date,
                due_date,
                country,
                currency,
                total,
                balance,
                status,
                origin,
                file_xml,
                active,
                notes,
                created_at,
                updated_at
            )
            VALUES (
                'OBLIGATION',
                'SUPPLIER',
                NULL,
                %s,
                %s,
                %s,
                %s,
                %s,
                'Costa Rica',
                %s,
                %s,
                %s,
                'PENDING',
                'UPLOAD',
                %s,
                TRUE,
                %s,
                NOW(),
                NOW()
            )
        """, (
            emisor,
            obligation_type,
            clave,
            issue_date,
            due_date,
            moneda,
            total,
            total,
            filepath,
            f"Documento cargado por XML ({clave})"
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"DB insert error: {str(e)}"
        )

    return {
        "message": "XML procesado correctamente",
        "type": obligation_type,
        "reference": clave,
        "supplier": emisor,
        "total": total,
        "currency": moneda
    }


# ============================================================
# 📥 UPLOAD PDF (ADJUNTO) con issue_date y due_date
# ============================================================
@router.post("/upload/pdf")
def upload_invoice_pdf(
    file: UploadFile = File(...),
    reference: str = Form(...),
    issue_date: Optional[date] = Form(None),
    due_date: Optional[date] = Form(None),
    conn=Depends(get_db)
):
    """
    Carga un PDF y crea una obligación en payment_obligations
    Usará la lógica:
      - issue_date: si provisto por UI, si no, fecha actual
      - due_date: si provisto por UI, si no, same day (contado)
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Normalizar fechas
    issue_val = issue_date or date.today()
    due_val = due_date or issue_val

    os.makedirs("storage/invoice_to_pay/pdf", exist_ok=True)
    timestamp = int(datetime.now().timestamp())
    filename = f"pdf_{timestamp}_{file.filename}"
    filepath = os.path.join("storage/invoice_to_pay/pdf", filename)

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        cur.execute("""
            INSERT INTO payment_obligations (
                record_type,
                obligation_type,
                reference,
                issue_date,
                due_date,
                currency,
                total,
                balance,
                status,
                origin,
                file_pdf,
                notes,
                active,
                created_at
            )
            VALUES (
                'OBLIGATION',
                'PDF_ONLY',
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'PENDING',
                'UPLOAD',
                %s,
                %s,
                TRUE,
                NOW()
            )
        """, (
            reference,
            issue_val,
            due_val,
            "USD",         # Por defecto USD (puedes ajustar luego)
            0.0,           # Sin monto explícito para PDF
            0.0,
            filepath,
            f"PDF adjunto para {reference}"
        ))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"PDF upload error: {str(e)}"
        )

    return {"message": "PDF uploaded and obligation created successfully"}


@router.delete("/{obligation_id}")
def delete_invoice_to_pay(obligation_id: int, conn=Depends(get_db)):
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM payment_obligations WHERE id = %s",
        (obligation_id,)
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Obligation not found")

    cur.execute(
        "DELETE FROM payment_obligations WHERE id = %s",
        (obligation_id,)
    )

    conn.commit()

    return {"status": "ok"}
