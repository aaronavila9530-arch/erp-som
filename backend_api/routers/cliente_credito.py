from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header
)
import psycopg2
from psycopg2.extras import RealDictCursor

from database import get_db
from rbac_service import has_permission
from services.credit_control import build_credit_decision
from services.tenanting import company_code


router = APIRouter(
    prefix="/cliente-credito",
    tags=["Cliente Crédito"]
)


@router.post("/order-to-cash/check")
def check_order_to_cash_credit(
    payload: dict,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    company = company_code(payload.get("company_code"), x_company_code)
    cliente = payload.get("codigo_cliente") or payload.get("cliente")
    if not cliente:
        raise HTTPException(400, "Cliente requerido para validar credito")
    return build_credit_decision(
        company=company,
        client_ref=cliente,
        projected_amount=payload.get("projected_amount") or payload.get("amount") or 0,
        projected_currency=payload.get("currency") or payload.get("moneda") or "USD",
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
# GET crédito por cliente
# ============================================================
@router.get("/{codigo_cliente}")
def get_credito_cliente(
    codigo_cliente: str,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    try:
        company = company_code(None, x_company_code)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                codigo_cliente,
                termino_pago,
                limite_credito,
                moneda,
                estado_credito,
                hold_manual,
                observaciones
            FROM cliente_credito
            WHERE codigo_cliente = %s
              AND company_code = %s
        """, (codigo_cliente, company))

        data = cur.fetchone()
        cur.close()

        if not data:
            return {
                "exists": False,
                "message": "Cliente sin configuración crediticia"
            }

        return {
            "exists": True,
            "data": data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# POST crear crédito inicial por cliente
# ============================================================
@router.post("/")
def create_credito_cliente(
    payload: dict,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    """
    payload esperado:
    {
        codigo_cliente,
        termino_pago,
        limite_credito,
        moneda,
        observaciones
    }
    """
    try:
        cur = conn.cursor()

        # Verificar si ya existe
        company = company_code(payload.get("company_code"), x_company_code)

        cur.execute("""
            SELECT 1 FROM cliente_credito
            WHERE codigo_cliente = %s
              AND company_code = %s
        """, (payload["codigo_cliente"], company))

        if cur.fetchone():
            raise HTTPException(
                status_code=400,
                detail="El cliente ya tiene configuración crediticia"
            )

        cur.execute("""
            INSERT INTO cliente_credito (
                codigo_cliente,
                termino_pago,
                limite_credito,
                moneda,
                observaciones,
                company_code
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            payload["codigo_cliente"],
            payload.get("termino_pago"),
            payload.get("limite_credito", 0),
            payload.get("moneda", "USD"),
            payload.get("observaciones"),
            company,
        ))

        conn.commit()
        cur.close()

        return {"message": "Configuración crediticia creada"}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# PUT actualizar crédito del cliente
# ============================================================
@router.put("/{codigo_cliente}")
def update_credito_cliente(
    codigo_cliente: str,
    payload: dict,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db)
):
    cur = conn.cursor()

    try:
        company = company_code(payload.get("company_code"), x_company_code)
        fields = []
        values = []

        def add(field, value):
            fields.append(f"{field} = %s")
            values.append(value)

        # ----------------------------
        # Normalización segura
        # ----------------------------
        if "termino_pago" in payload and payload["termino_pago"] not in ("", None):
            add("termino_pago", int(payload["termino_pago"]))

        if "limite_credito" in payload and payload["limite_credito"] not in ("", None):
            add("limite_credito", float(payload["limite_credito"]))

        if "moneda" in payload and payload["moneda"]:
            add("moneda", payload["moneda"].upper())

        if "estado_credito" in payload and payload["estado_credito"]:
            estado = payload["estado_credito"].upper()
            if estado not in ("ACTIVE", "INACTIVE", "HOLD"):
                raise HTTPException(400, "Estado de crédito inválido")
            add("estado_credito", estado)

        if "hold_manual" in payload:
            add("hold_manual", bool(payload["hold_manual"]))

        if "observaciones" in payload:
            add("observaciones", payload["observaciones"].strip())

        if not fields:
            raise HTTPException(400, "No hay datos para actualizar")

        fields.append("updated_at = CURRENT_TIMESTAMP")

        sql = f"""
            UPDATE cliente_credito
            SET {", ".join(fields)}
            WHERE codigo_cliente = %s
              AND company_code = %s
        """

        values.append(codigo_cliente)
        values.append(company)

        cur.execute(sql, values)

        if cur.rowcount == 0:
            raise HTTPException(404, "Cliente sin configuración crediticia")

        conn.commit()

        return {
            "status": "ok",
            "message": "Crédito actualizado correctamente"
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error actualizando crédito: {str(e)}"
        )

    finally:
        cur.close()

@router.delete("/{codigo_cliente}")
def delete_credito_cliente(
    codigo_cliente: str,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    company = company_code(None, x_company_code)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM cliente_credito WHERE codigo_cliente = %s AND company_code = %s",
        (codigo_cliente, company)
    )

    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="No existe configuración")

    conn.commit()
    cur.close()
    return {"message": "Configuración crediticia eliminada"}


# ============================================================
# GET /cliente-credito/exposure/{codigo_cliente}
# EXPOSICIÓN CREDITICIA CONSOLIDADA (FIX DEFINITIVO)
# ============================================================
@router.get("/exposure/{codigo_cliente}")
def get_credit_exposure(
    codigo_cliente: str,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db)
):
    company = company_code(None, x_company_code)
    decision = build_credit_decision(company, codigo_cliente, projected_amount=0, projected_currency="USD")
    return {
        "codigo_cliente": decision.get("codigo_cliente"),
        "limite_credito": decision.get("credit_limit"),
        "total_facturado": decision.get("open_ar"),
        "disponible": decision.get("available"),
        "exposicion": "OVERLIMIT" if decision.get("requires_release") and decision.get("reason_code") == "OVERLIMIT" else decision.get("status"),
        "semaforo": "ROJO" if decision.get("requires_release") else "VERDE",
        "payment_trend": {
            "avg_days_to_pay": None,
            "trend": "COLLECTIONS"
        },
        "order_to_cash": decision,
    }

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ====================================================
        # 1️⃣ CREDIT CONFIG
        # ====================================================
        cur.execute("""
            SELECT
                limite_credito,
                termino_pago
            FROM cliente_credito
            WHERE codigo_cliente = %s
        """, (codigo_cliente,))

        credit = cur.fetchone()
        if not credit:
            raise HTTPException(404, "Cliente sin configuración de crédito")

        limite_credito = float(credit["limite_credito"] or 0)
        termino_pago = int(credit["termino_pago"] or 0)

        # ====================================================
        # 2️⃣ TOTAL FACTURAS
        # ====================================================
        cur.execute("""
            SELECT
                COALESCE(SUM(total), 0) AS total_facturas
            FROM invoicing
            WHERE
                codigo_cliente = %s
                AND tipo_documento = 'FACTURA'
                AND estado = 'EMITIDA'
        """, (codigo_cliente,))

        total_facturas = float(cur.fetchone()["total_facturas"] or 0)

        # ====================================================
        # 3️⃣ TOTAL NOTAS DE CRÉDITO
        # ====================================================
        cur.execute("""
            SELECT
                COALESCE(SUM(total), 0) AS total_nc
            FROM invoicing
            WHERE
                codigo_cliente = %s
                AND tipo_documento = 'NOTA_CREDITO'
                AND estado = 'EMITIDA'
        """, (codigo_cliente,))

        total_nc = float(cur.fetchone()["total_nc"] or 0)

        # ====================================================
        # 4️⃣ EXPOSICIÓN REAL
        # ====================================================
        exposicion_real = total_facturas - total_nc
        disponible = limite_credito - exposicion_real

        # ====================================================
        # 5️⃣ SEMÁFORO
        # ====================================================
        if limite_credito <= 0:
            semaforo = "ROJO"
            exposicion_estado = "OVERLIMIT"
        else:
            pct = disponible / limite_credito
            if disponible <= 0:
                semaforo = "ROJO"
                exposicion_estado = "OVERLIMIT"
            elif pct <= 0.20:
                semaforo = "AMARILLO"
                exposicion_estado = "CRITICO"
            else:
                semaforo = "VERDE"
                exposicion_estado = "NORMAL"

        # ====================================================
        # 6️⃣ PAYMENT TREND (FIX FECHAS + TIPOS)
        # ====================================================
        avg_days = None
        trend = "SIN_DATOS"

        cur.execute("""
            SELECT
                AVG(
                    (p.fecha_pago::date - i.fecha_emision::date)
                ) AS avg_days
            FROM incoming_payments p
            JOIN invoicing i
                ON i.numero_documento::text = p.documento::text
            WHERE
                p.codigo_cliente = %s
                AND p.estado = 'APPLIED'
                AND p.fecha_pago IS NOT NULL
                AND i.fecha_emision IS NOT NULL
        """, (codigo_cliente,))

        row = cur.fetchone()

        if row and row["avg_days"] is not None:
            avg_days = int(round(row["avg_days"]))

            if avg_days <= termino_pago:
                trend = "BUENO"
            elif avg_days <= termino_pago + 15:
                trend = "MEDIO"
            else:
                trend = "LENTO"

        # ====================================================
        # RESPONSE
        # ====================================================
        return {
            "codigo_cliente": codigo_cliente,
            "limite_credito": limite_credito,
            "total_facturado": exposicion_real,
            "disponible": disponible,
            "exposicion": exposicion_estado,
            "semaforo": semaforo,
            "payment_trend": {
                "avg_days_to_pay": avg_days,
                "trend": trend
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            500,
            f"Error calculando exposición crediticia: {str(e)}"
        )
    finally:
        cur.close()


# ============================================================
# GET /cliente-credito/{codigo_cliente}
# Obtener configuración crediticia
# ============================================================
@router.get("/{codigo_cliente}")
def get_credito_cliente(
    codigo_cliente: str,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                codigo_cliente,
                termino_pago,
                limite_credito,
                moneda,
                estado_credito,
                hold_manual,
                observaciones
            FROM cliente_credito
            WHERE codigo_cliente = %s
            LIMIT 1
        """, (codigo_cliente,))

        data = cur.fetchone()

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Cliente sin configuración crediticia"
            )

        return data

    finally:
        cur.close()



