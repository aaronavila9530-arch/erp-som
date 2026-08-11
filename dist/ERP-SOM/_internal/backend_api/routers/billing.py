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
