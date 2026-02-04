# ============================================================
# ROUTER — CONTAINER REPORTS (ERP-SOM)
# Archivo: backend_api/routers/container_reports.py
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

router = APIRouter(
    prefix="/container-reports",
    tags=["Informes — Container Reports"]
)

from datetime import datetime
from fastapi import Depends
from psycopg2.extras import RealDictCursor

# ============================================================
# POST — CREAR CONTAINER REPORT (ALINEADO 1:1 · BLINDADO)
# ============================================================

@router.post("")
def create_container_report(payload: dict, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        # ====================================================
        # COLUMNAS PERMITIDAS (1:1 CON TABLA)
        # ====================================================
        ALLOWED_FIELDS = {
            # META
            "linked_report_number",
            "container_type_text",
            "user",     # ⚠️ palabra reservada en PostgreSQL
            "status",

            # GENERAL INFORMATION
            "report_no",
            "bl",
            "seals",
            "appointment",
            "shippers",
            "inspection_place",
            "contact_person",
            "on_behalf_of",
            "consignee_notify",
            "vessel",
            "contact_datetime",
            "init_inspection_datetime",
            "init_to",
            "final_inspection_datetime",
            "final_to",

            # CONTAINER DESCRIPTION
            "container_size_20",
            "container_size_40",
            "container_type_dry",
            "container_type_reefer",
            "container_type_iso",
            "container_type_flat_rack",
            "container_load_fcl",
            "container_load_lcl",

            # CAUSE
            "cause_seals_bl",
            "cause_change_seals",
            "cause_customs",
            "cause_transfer",
            "cause_leaking",
            "cause_damage",
            "cause_stuff_condition",
            "cause_detail",

            # GOODS & PACKAGES
            "goods_description",
            "package_carton",
            "package_bags",
            "package_boxes",
            "package_drums",
            "package_pallets",
            "package_bulk",
            "package_bales",
            "package_crates",
            "package_other",
            "qty_1_left",
            "qty_1_right",
            "qty_2_left",
            "qty_2_right",
            "qty_3_left",
            "qty_3_right",
            "package_marking",
            "goods_condition",

            # NARRATIVES
            "damage_details",
            "remarks",
            "conclusion",

            # LINKS & DOCS
            "picture_link",
            "doc_bl",
            "doc_packing_list",
            "doc_shipping_invoice",
            "doc_cargo_manifest",
            "doc_commercial_invoice",
            "doc_delivery_record",
            "doc_notice_loss",
            "doc_insurance_policy",
            "doc_other",

            # QUALITY
            "quality_packing_exam",
            "quality_un_witness",
            "quality_visual_exam",
            "quality_product_exam",
            "quality_documents",
            "quality_sanitary_cert",
            "quality_phytosanitary_cert",
            "quality_factory_cert",
            "quality_origin_cert",

            # PERSONS
            "person_1_name",
            "person_1_position",
            "person_2_name",
            "person_2_position",
            "person_3_name",
            "person_3_position",

            # INSPECTED CONTAINER
            "ic_manuf",
            "ic_csc",
            "ic_max_gw",
            "ic_tare",

            # GENERAL DETAILS
            "new_commodity",
            "used_commodity",
            "net_weight",
            "gross_weight",
            "volume",

            # TRANSFER
            "tr_number",
            "tr_manuf",
            "tr_csc",
            "tr_seal",
            "tr_max_gw",
            "tr_tare",

            # SCOPE
            "scope_100",
            "scope_random",
            "scope_items",
        }

        # ====================================================
        # LIMPIAR PAYLOAD
        # ====================================================
        clean_payload = {
            k: payload.get(k)
            for k in ALLOWED_FIELDS
            if k in payload
        }

        # ====================================================
        # DEFAULTS DE SISTEMA
        # ====================================================
        clean_payload["status"] = clean_payload.get("status") or "draft"
        clean_payload["user"] = clean_payload.get("user") or "system"

        clean_payload["created_at"] = datetime.utcnow()
        clean_payload["updated_at"] = datetime.utcnow()

        # ====================================================
        # NORMALIZAR BOOLEANOS
        # ====================================================
        for k, v in clean_payload.items():
            if isinstance(v, bool):
                continue
            if v is None and k.startswith((
                "container_",
                "cause_",
                "package_",
                "doc_",
                "quality_",
                "scope_",
                "new_",
                "used_"
            )):
                clean_payload[k] = False

        # ====================================================
        # INSERT DINÁMICO (ESCAPANDO "user")
        # ====================================================
        columns = []
        values = []

        for k in clean_payload.keys():
            if k == "user":
                columns.append('"user"')  # 🔒 escape keyword
            else:
                columns.append(k)
            values.append(f"%({k})s")

        sql = f"""
            INSERT INTO public.container_reports ({", ".join(columns)})
            VALUES ({", ".join(values)})
            RETURNING id;
        """

        cur.execute(sql, clean_payload)
        row = cur.fetchone()
        conn.commit()

        return {
            "success": True,
            "id": row[0],
            "status": clean_payload["status"]
        }

    except Exception as e:
        conn.rollback()
        return {
            "success": False,
            "detail": str(e)
        }

    finally:
        cur.close()

# ============================================================
# GET — FILTROS BASE PARA COMBOBOX (SERVICIOS → INFORMES)
# ============================================================

@router.get("/filters")
def get_container_report_filters(conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                COALESCE(
                    ARRAY(
                        SELECT DISTINCT cliente
                        FROM public.servicios
                        WHERE num_informe IS NOT NULL
                          AND cliente IS NOT NULL
                        ORDER BY cliente
                    ),
                    ARRAY[]::TEXT[]
                ) AS clientes,

                COALESCE(
                    ARRAY(
                        SELECT DISTINCT EXTRACT(YEAR FROM fecha_inicio)::INT
                        FROM public.servicios
                        WHERE num_informe IS NOT NULL
                          AND fecha_inicio IS NOT NULL
                        ORDER BY 1 DESC
                    ),
                    ARRAY[]::INT[]
                ) AS anios
        """)

        row = cur.fetchone() or {}

        return {
            "clientes": row.get("clientes", []),
            "anios": row.get("anios", [])
        }

    finally:
        cur.close()


# ============================================================
# GET — MESES DISPONIBLES POR CLIENTE / AÑO
# ============================================================

@router.get("/filters/months")
def get_container_report_months(
    cliente: str | None = None,
    anio: int | None = None,
    conn=Depends(get_db)
):

    if not all([cliente, anio]):
        return {"meses": []}

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT EXTRACT(MONTH FROM fecha_inicio)::INT AS mes
            FROM public.servicios
            WHERE num_informe IS NOT NULL
              AND cliente = %s
              AND fecha_inicio IS NOT NULL
              AND EXTRACT(YEAR FROM fecha_inicio) = %s
            ORDER BY mes
        """, (cliente.strip(), anio))

        meses = [r[0] for r in cur.fetchall()]

        return {"meses": meses}

    finally:
        cur.close()


# ============================================================
# GET — VESSELS DISPONIBLES POR CLIENTE / AÑO / MES
# ============================================================

@router.get("/filters/vessels")
def get_container_report_vessels(
    cliente: str | None = None,
    anio: int | None = None,
    mes: int | None = None,
    conn=Depends(get_db)
):

    if not all([cliente, anio, mes]):
        return {"buques_contenedor": []}

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT buque_contenedor
            FROM public.servicios
            WHERE num_informe IS NOT NULL
              AND cliente = %s
              AND buque_contenedor IS NOT NULL
              AND fecha_inicio IS NOT NULL
              AND EXTRACT(YEAR FROM fecha_inicio) = %s
              AND EXTRACT(MONTH FROM fecha_inicio) = %s
            ORDER BY buque_contenedor
        """, (cliente.strip(), anio, mes))

        vessels = [r[0] for r in cur.fetchall()]

        return {"buques_contenedor": vessels}

    finally:
        cur.close()


# ============================================================
# GET — INFORMES DISPONIBLES (num_informe)
# ============================================================

@router.get("/informes")
def get_container_reports_by_servicio(
    cliente: str | None = None,
    buque_contenedor: str | None = None,
    anio: int | None = None,
    mes: int | None = None,
    conn=Depends(get_db)
):

    # 🔒 Blindaje contra llamadas incompletas
    if not all([cliente, buque_contenedor, anio, mes]):
        return {"total": 0, "data": []}

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                consec,
                num_informe,
                fecha_inicio
            FROM public.servicios
            WHERE cliente = %(cliente)s
              AND buque_contenedor = %(buque)s
              AND EXTRACT(YEAR FROM fecha_inicio) = %(anio)s
              AND EXTRACT(MONTH FROM fecha_inicio) = %(mes)s
              AND num_informe IS NOT NULL
            ORDER BY fecha_inicio
        """, {
            "cliente": cliente.strip(),
            "buque": buque_contenedor.strip(),
            "anio": anio,
            "mes": mes
        })

        rows = cur.fetchall() or []

        return {
            "total": len(rows),
            "data": rows
        }

    finally:
        cur.close()


# ============================================================
# PUT — ACTUALIZAR REPORTE
# ============================================================

@router.put("/{report_id}")
def update_container_report(report_id: int, payload: dict, conn=Depends(get_db)):
    if not payload:
        raise HTTPException(status_code=400, detail="No data provided")

    payload["updated_at"] = datetime.utcnow()
    payload["id"] = report_id

    fields = [f"{k} = %({k})s" for k in payload.keys() if k != "id"]

    sql = f"""
        UPDATE public.container_reports
        SET {", ".join(fields)}
        WHERE id = %(id)s;
    """

    cur = conn.cursor()
    cur.execute(sql, payload)

    if cur.rowcount == 0:
        cur.close()
        raise HTTPException(status_code=404, detail="Report not found")

    conn.commit()
    cur.close()

    return {"success": True}

# ============================================================
# DELETE — ELIMINAR REPORTE
# ============================================================

@router.delete("/{report_id}")
def delete_container_report(report_id: int, conn=Depends(get_db)):
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM public.container_reports WHERE id = %s;",
        (report_id,)
    )

    if cur.rowcount == 0:
        cur.close()
        raise HTTPException(status_code=404, detail="Report not found")

    conn.commit()
    cur.close()

    return {"success": True}

# ============================================================
# GET — LISTAR REPORTES
# ============================================================

@router.get("")
def get_container_reports(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM public.container_reports
        ORDER BY created_at DESC;
    """)

    data = cur.fetchall()
    cur.close()

    return {"total": len(data), "data": data}

# ============================================================
# GET — REPORTE POR ID
# ============================================================

@router.get("/{report_id}")
def get_container_report_by_id(report_id: int, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM public.container_reports WHERE id = %s;",
        (report_id,)
    )

    row = cur.fetchone()
    cur.close()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"data": row}

# ============================================================
# GET — EXPORTAR REPORTE A EXCEL (TEMPLATE)
# ============================================================

@router.get("/{report_id}/excel")
def download_container_report_excel(report_id: int, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM public.container_reports WHERE id = %s;",
        (report_id,)
    )

    report = cur.fetchone()
    cur.close()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # --------------------------------------------------------
    # IMPORT DIFERIDO (EVITA CRASH EN RAILWAY)
    # --------------------------------------------------------
    try:
        from services.container_report_excel_service import (
            generate_container_report_excel
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=(
                "Excel export service unavailable. "
                "Missing dependency: openpyxl.\n"
                f"Detail: {e}"
            )
        )

    # --------------------------------------------------------
    # GENERAR EXCEL DESDE TEMPLATE
    # --------------------------------------------------------
    try:
        file_path = generate_container_report_excel(report)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating Excel file: {e}"
        )

    filename = f"Container_Report_{report.get('report_no') or report_id}.xlsx"

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )


