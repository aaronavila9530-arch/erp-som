from fastapi import APIRouter, Depends, Query, HTTPException, Header
from psycopg2.extras import RealDictCursor
from typing import Optional
from datetime import date
import os

from database import get_db
from rbac_service import has_permission
from services.tenanting import company_code, ensure_company_column
from fastapi.responses import FileResponse


router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
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
# GET /billing/search
# ============================================================
@router.get("/search")
def buscar_billing(
    cliente: Optional[str] = Query(None),
    fecha_desde: Optional[date] = Query(None),
    fecha_hasta: Optional[date] = Query(None),
    tipo_factura: Optional[str] = Query(None),
    tipo_documento: Optional[str] = Query(None),
    company_code_param: Optional[str] = Query(None, alias="company_code"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=10000),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db)
):
    offset = (page - 1) * page_size
    cur = conn.cursor(cursor_factory=RealDictCursor)
    company = company_code(company_code_param, x_company_code)
    ensure_company_column("invoicing")

    filtros = ["company_code = %(company_code)s"]
    params = {"company_code": company}

    if cliente and cliente.upper() != "ALL":
        filtros.append("nombre_cliente ILIKE %(cliente)s")
        params["cliente"] = f"%{cliente}%"

    if tipo_factura:
        filtros.append("tipo_factura = %(tipo_factura)s")
        params["tipo_factura"] = tipo_factura

    if tipo_documento:
        filtros.append("tipo_documento = %(tipo_documento)s")
        params["tipo_documento"] = tipo_documento

    if fecha_desde:
        filtros.append("fecha_emision >= %(fecha_desde)s")
        params["fecha_desde"] = fecha_desde

    if fecha_hasta:
        filtros.append("fecha_emision <= %(fecha_hasta)s")
        params["fecha_hasta"] = fecha_hasta

    where_sql = "WHERE " + " AND ".join(filtros) if filtros else ""

    # -------- TOTAL --------
    cur.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM invoicing
        {where_sql}
        """,
        params
    )
    total = cur.fetchone()["total"]

    # -------- DATA --------
    cur.execute(
        f"""
        SELECT
            id,
            tipo_factura,
            tipo_documento,
            numero_documento,
            nombre_cliente,
            fecha_emision,
            moneda,
            total,
            estado
        FROM invoicing
        {where_sql}
        ORDER BY fecha_emision DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {**params, "limit": page_size, "offset": offset}
    )

    data = cur.fetchall()
    cur.close()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": data
    }


def _has_collection_payments(cur, numero_documento: str, codigo_cliente: str, company: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM cash_app
        WHERE ltrim(numero_documento, '0') = ltrim(%s, '0')
          AND codigo_cliente = %s
          AND company_code = %s
        LIMIT 1
        """,
        (numero_documento, codigo_cliente, company),
    )
    return cur.fetchone() is not None


def _sync_collection_from_invoice(cur, invoice: dict, old_numero: str | None = None) -> None:
    numero = str(invoice.get("numero_documento") or "").strip()
    codigo = str(invoice.get("codigo_cliente") or "").strip()
    company = str(invoice.get("company_code") or "").strip()
    if not numero or not codigo or not company:
        return

    target_numero = old_numero or numero
    if _has_collection_payments(cur, target_numero, codigo, company):
        cur.execute(
            """
            UPDATE collections
            SET nombre_cliente = %s,
                tipo_factura = %s,
                tipo_documento = %s,
                fecha_emision = %s,
                moneda = %s,
                total = %s,
                saldo_pendiente = GREATEST(%s - (
                    SELECT COALESCE(SUM(monto_pagado + comision), 0)
                    FROM cash_app ca
                    WHERE ltrim(ca.numero_documento, '0') = ltrim(%s, '0')
                      AND ca.codigo_cliente = %s
                      AND ca.company_code = %s
                ), 0),
                estado_factura = CASE WHEN %s <= 0 THEN 'PAGADA' ELSE estado_factura END,
                num_informe = %s,
                buque_contenedor = %s,
                operacion = %s,
                periodo_operacion = %s,
                descripcion_servicio = %s,
                numero_documento = %s
            WHERE ltrim(numero_documento, '0') = ltrim(%s, '0')
              AND codigo_cliente = %s
              AND company_code = %s
            """,
            (
                invoice.get("nombre_cliente"),
                invoice.get("tipo_factura"),
                invoice.get("tipo_documento"),
                invoice.get("fecha_emision"),
                invoice.get("moneda"),
                invoice.get("total"),
                invoice.get("total"),
                target_numero,
                codigo,
                company,
                float(invoice.get("total") or 0),
                invoice.get("num_informe"),
                invoice.get("buque_contenedor"),
                invoice.get("operacion"),
                invoice.get("periodo_operacion"),
                invoice.get("descripcion_servicio"),
                numero,
                target_numero,
                codigo,
                company,
            ),
        )
        return

    cur.execute(
        """
        UPDATE collections
        SET numero_documento = %s,
            nombre_cliente = %s,
            tipo_factura = %s,
            tipo_documento = %s,
            fecha_emision = %s,
            moneda = %s,
            total = %s,
            saldo_pendiente = %s,
            estado_factura = CASE WHEN estado_factura = 'ANULADA' THEN 'PENDIENTE_PAGO' ELSE estado_factura END,
            num_informe = %s,
            buque_contenedor = %s,
            operacion = %s,
            periodo_operacion = %s,
            descripcion_servicio = %s
        WHERE ltrim(numero_documento, '0') = ltrim(%s, '0')
          AND codigo_cliente = %s
          AND company_code = %s
        """,
        (
            numero,
            invoice.get("nombre_cliente"),
            invoice.get("tipo_factura"),
            invoice.get("tipo_documento"),
            invoice.get("fecha_emision"),
            invoice.get("moneda"),
            invoice.get("total"),
            invoice.get("total"),
            invoice.get("num_informe"),
            invoice.get("buque_contenedor"),
            invoice.get("operacion"),
            invoice.get("periodo_operacion"),
            invoice.get("descripcion_servicio"),
            target_numero,
            codigo,
            company,
        ),
    )


@router.put("/{invoice_id}")
def actualizar_billing(
    invoice_id: int,
    payload: dict,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    company = company_code(payload.get("company_code"), x_company_code)
    ensure_company_column("invoicing")
    ensure_company_column("collections")
    ensure_company_column("servicios")
    ensure_company_column("factura")
    ensure_company_column("cash_app")

    editable = {
        "tipo_factura",
        "tipo_documento",
        "numero_documento",
        "codigo_cliente",
        "nombre_cliente",
        "fecha_emision",
        "moneda",
        "total",
        "estado",
        "num_informe",
        "termino_pago",
        "buque_contenedor",
        "operacion",
        "periodo_operacion",
        "descripcion_servicio",
    }

    try:
        cur.execute(
            "SELECT * FROM invoicing WHERE id = %s AND company_code = %s FOR UPDATE",
            (invoice_id, company),
        )
        before = cur.fetchone()
        if not before:
            raise HTTPException(404, "Factura no encontrada")
        if before.get("estado") == "ANULADA":
            raise HTTPException(400, "No se puede editar una factura anulada")

        updates = {k: v for k, v in payload.items() if k in editable}
        if not updates:
            raise HTTPException(400, "Sin campos para actualizar")

        if "total" in updates:
            try:
                updates["total"] = float(updates["total"])
                if updates["total"] <= 0:
                    raise ValueError
            except Exception:
                raise HTTPException(400, "Total invalido")

        if "termino_pago" in updates and updates["termino_pago"] not in (None, ""):
            try:
                updates["termino_pago"] = int(float(updates["termino_pago"]))
            except Exception:
                raise HTTPException(400, "Termino de pago invalido")

        assignments = ", ".join(f"{field} = %({field})s" for field in updates)
        cur.execute(
            f"""
            UPDATE invoicing
            SET {assignments}
            WHERE id = %(id)s
              AND company_code = %(company_code)s
            RETURNING *
            """,
            {**updates, "id": invoice_id, "company_code": company},
        )
        after = cur.fetchone()

        if before.get("factura_id"):
            cur.execute(
                """
                UPDATE factura
                SET numero_factura = %s,
                    codigo_cliente = %s,
                    fecha_emision = %s,
                    termino_pago = %s,
                    moneda = %s,
                    total = %s
                WHERE id = %s
                  AND company_code = %s
                """,
                (
                    after.get("numero_documento"),
                    after.get("codigo_cliente"),
                    after.get("fecha_emision"),
                    after.get("termino_pago"),
                    after.get("moneda"),
                    after.get("total"),
                    before.get("factura_id"),
                    company,
                ),
            )

        cur.execute(
            """
            UPDATE servicios
            SET factura = %s,
                valor_factura = %s,
                fecha_factura = %s,
                terminos_pago = %s
            WHERE company_code = %s
              AND factura = %s
            """,
            (
                after.get("numero_documento"),
                after.get("total"),
                after.get("fecha_emision"),
                after.get("termino_pago"),
                company,
                before.get("numero_documento"),
            ),
        )

        _sync_collection_from_invoice(cur, after, old_numero=before.get("numero_documento"))
        conn.commit()
        return {"status": "ok", "data": after}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error actualizando billing: {str(e)}")
    finally:
        cur.close()


@router.delete("/{invoice_id}")
def eliminar_billing(
    invoice_id: int,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    company = company_code(header_value=x_company_code)
    ensure_company_column("invoicing")
    ensure_company_column("collections")
    ensure_company_column("servicios")
    ensure_company_column("cash_app")

    try:
        cur.execute(
            "SELECT * FROM invoicing WHERE id = %s AND company_code = %s FOR UPDATE",
            (invoice_id, company),
        )
        invoice = cur.fetchone()
        if not invoice:
            raise HTTPException(404, "Factura no encontrada")

        numero = str(invoice.get("numero_documento") or "")
        codigo = str(invoice.get("codigo_cliente") or "")
        has_payments = _has_collection_payments(cur, numero, codigo, company)

        cur.execute(
            "UPDATE invoicing SET estado = 'ANULADA' WHERE id = %s AND company_code = %s",
            (invoice_id, company),
        )

        cur.execute(
            """
            UPDATE servicios
            SET factura = NULL,
                valor_factura = NULL,
                fecha_factura = NULL,
                terminos_pago = NULL
            WHERE company_code = %s
              AND factura = %s
            """,
            (company, numero),
        )

        if has_payments:
            cur.execute(
                """
                UPDATE collections
                SET estado_factura = 'ANULADA',
                    saldo_pendiente = 0
                WHERE ltrim(numero_documento, '0') = ltrim(%s, '0')
                  AND codigo_cliente = %s
                  AND company_code = %s
                """,
                (numero, codigo, company),
            )
        else:
            cur.execute(
                """
                DELETE FROM collections
                WHERE ltrim(numero_documento, '0') = ltrim(%s, '0')
                  AND codigo_cliente = %s
                  AND company_code = %s
                """,
                (numero, codigo, company),
            )

        conn.commit()
        return {"status": "ok", "deleted": False, "estado": "ANULADA", "had_payments": has_payments}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error eliminando billing: {str(e)}")
    finally:
        cur.close()


# ============================================================
# GET /billing/{numero_documento}
# Preview de factura (PopupPreviewFactura)
# ============================================================
@router.get("/{numero_documento}")
def get_factura(
    numero_documento: str,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):

    cur = conn.cursor(cursor_factory=RealDictCursor)
    company = company_code(header_value=x_company_code)
    ensure_company_column("invoicing")

    cur.execute("""
        SELECT *
        FROM invoicing
        WHERE numero_documento = %s
          AND company_code = %s
    """, (numero_documento, company))

    factura = cur.fetchone()
    cur.close()

    if not factura:
        raise HTTPException(404, "Factura no encontrada")

    return factura


# ======================================================
# DESCARGAR PDF FACTURA
# ======================================================
@router.get("/pdf/{numero_documento}")
def obtener_pdf_factura(
    numero_documento: str,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)
    company = company_code(header_value=x_company_code)
    ensure_company_column("invoicing")

    cur.execute(
        """
        SELECT pdf_path
        FROM invoicing
        WHERE numero_documento = %s
          AND company_code = %s
        """,
        (numero_documento, company)
    )

    row = cur.fetchone()
    cur.close()

    if not row or not row.get("pdf_path"):
        raise HTTPException(
            status_code=404,
            detail="PDF no encontrado"
        )

    pdf_path = row["pdf_path"]

    if not os.path.exists(pdf_path):
        raise HTTPException(
            status_code=404,
            detail="El archivo PDF no existe en el servidor"
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=os.path.basename(pdf_path)
    )
