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

# ============================================================
# POST — CREAR REPORTE
# ============================================================

@router.post("")
def create_container_report(payload: dict, conn=Depends(get_db)):
    cur = conn.cursor()

    payload["created_at"] = datetime.utcnow()
    payload["updated_at"] = datetime.utcnow()

    columns = ", ".join(payload.keys())
    values = ", ".join([f"%({k})s" for k in payload.keys()])

    sql = f"""
        INSERT INTO public.container_reports ({columns})
        VALUES ({values})
        RETURNING id;
    """

    cur.execute(sql, payload)
    row = cur.fetchone()
    conn.commit()
    cur.close()

    return {"success": True, "id": row[0]}

# ============================================================
# GET — FILTROS PARA COMBOBOX (SERVICIOS → INFORMES)
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
                        SELECT DISTINCT buque_contenedor
                        FROM public.servicios
                        WHERE num_informe IS NOT NULL
                          AND buque_contenedor IS NOT NULL
                        ORDER BY buque_contenedor
                    ),
                    ARRAY[]::TEXT[]
                ) AS buques_contenedor,

                COALESCE(
                    ARRAY(
                        SELECT DISTINCT EXTRACT(YEAR FROM fecha_inicio)::INT
                        FROM public.servicios
                        WHERE num_informe IS NOT NULL
                          AND fecha_inicio IS NOT NULL
                        ORDER BY 1 DESC
                    ),
                    ARRAY[]::INT[]
                ) AS anios,

                COALESCE(
                    ARRAY(
                        SELECT DISTINCT EXTRACT(MONTH FROM fecha_inicio)::INT
                        FROM public.servicios
                        WHERE num_informe IS NOT NULL
                          AND fecha_inicio IS NOT NULL
                        ORDER BY 1
                    ),
                    ARRAY[]::INT[]
                ) AS meses
        """)

        row = cur.fetchone() or {}

        return {
            "clientes": row.get("clientes", []),
            "buques_contenedor": row.get("buques_contenedor", []),
            "anios": row.get("anios", []),
            "meses": row.get("meses", [])
        }

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

    if not all([cliente, buque_contenedor, anio, mes]):
        return {"total": 0, "data": []}

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                id,
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


