from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db
from services.presentation_doc_service import generate_presentation_pdf
from services.pdf_merge_service import merge_pdfs
from services.container_report_pdf_service import generate_container_report_pdf


router = APIRouter(
    prefix="/container-presentation-pdf",
    tags=["Container Presentation PDF"]
)


# =====================================================
# INTERNAL — GET PRESENTATION DATA (RAW & SAFE)
# =====================================================
def _get_presentation_data(container_report_id: int, conn) -> dict:
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                linked_report_number,
                report_no,
                inspection_place,
                init_inspection_datetime
            FROM container_reports
            WHERE id = %s
        """, (container_report_id,))

        report = cur.fetchone()
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Container report not found"
            )

        cliente = None
        linked = report["linked_report_number"]

        if linked:
            cur.execute("""
                SELECT cliente
                FROM servicios
                WHERE num_informe = %s
                LIMIT 1
            """, (linked,))
            row = cur.fetchone()
            if row:
                cliente = row["cliente"]

        # 👉 BLINDAJE DE FECHA
        date_value = report["init_inspection_datetime"]
        if isinstance(date_value, datetime):
            date_fmt = date_value.strftime("%d-%m-%Y")
        else:
            date_fmt = None

        return {
            "cert_no": linked,
            "container": report["report_no"],
            "to": cliente,
            "place": report["inspection_place"],
            "date": date_fmt
        }

    finally:
        cur.close()


# =====================================================
# PRESENTATION ONLY
# =====================================================
@router.get("/{container_report_id}/presentation")
def generate_presentation_only(
    container_report_id: int,
    conn=Depends(get_db)
):
    try:
        data = _get_presentation_data(container_report_id, conn)
        pdf_path = generate_presentation_pdf(data)

        return FileResponse(
            pdf_path,
            filename="presentation.pdf",
            media_type="application/pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating presentation PDF: {e}"
        )


# =====================================================
# UNIFIED PDF (Presentation + Container Report)
# =====================================================
@router.get("/{container_report_id}/unified")
def generate_unified_pdf(
    container_report_id: int,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # -------------------------------------------------
        # 1️⃣ OBTENER REPORTE COMPLETO (OBLIGATORIO PARA EXCEL)
        # -------------------------------------------------
        cur.execute("""
            SELECT *
            FROM container_reports
            WHERE id = %s
        """, (container_report_id,))

        report = cur.fetchone()
        if not report:
            raise HTTPException(
                status_code=404,
                detail="Container report not found"
            )

        # -------------------------------------------------
        # 🔒 BLINDAJE EXCEL — NORMALIZAR BOOLEANOS NULL
        # (NO afecta presentación ni BD)
        # -------------------------------------------------
        for k, v in report.items():
            if k.startswith((
                "container_",
                "cause_",
                "package_",
                "doc_",
                "quality_",
                "scope_",
                "new_",
                "used_"
            )) and v is None:
                report[k] = False

        linked = report.get("linked_report_number")

        # -------------------------------------------------
        # 2️⃣ OBTENER CLIENTE (servicios)
        # -------------------------------------------------
        cliente = None
        if linked:
            cur.execute("""
                SELECT cliente
                FROM servicios
                WHERE num_informe = %s
                LIMIT 1
            """, (linked,))
            row = cur.fetchone()
            if row:
                cliente = row.get("cliente")

        # -------------------------------------------------
        # 3️⃣ NORMALIZAR FECHA (BLINDADO)
        # -------------------------------------------------
        raw_date = report.get("init_inspection_datetime")
        date_fmt = None

        if raw_date:
            if isinstance(raw_date, datetime):
                date_fmt = raw_date.strftime("%d-%m-%Y")
            elif isinstance(raw_date, str):
                try:
                    parsed = datetime.strptime(raw_date, "%Y-%m-%d %H:%M")
                    date_fmt = parsed.strftime("%d-%m-%Y")
                except ValueError:
                    date_fmt = raw_date.split(" ")[0]

        # -------------------------------------------------
        # 4️⃣ DATA FINAL PARA PRESENTATION
        # -------------------------------------------------
        data = {
            "cert_no": str(linked or ""),
            "container": str(report.get("report_no") or ""),
            "to": str(cliente or ""),
            "place": str(report.get("inspection_place") or ""),
            "date": str(date_fmt or "")
        }

        # -------------------------------------------------
        # 5️⃣ GENERAR PRESENTATION PDF (PATH)
        # -------------------------------------------------
        presentation_pdf = generate_presentation_pdf(data)

        if not isinstance(presentation_pdf, str) or not presentation_pdf:
            raise RuntimeError(
                "Presentation PDF service did not return a valid file path"
            )

        # -------------------------------------------------
        # 6️⃣ GENERAR CONTAINER REPORT PDF (EXCEL → PDF)
        # -------------------------------------------------
        report_pdf = generate_container_report_pdf(report)

        if not isinstance(report_pdf, str) or not report_pdf:
            raise RuntimeError(
                "Container report PDF service did not return a valid file path"
            )

        # -------------------------------------------------
        # 7️⃣ MERGE PDFs
        # -------------------------------------------------
        unified_pdf = merge_pdfs(
            presentation_pdf,
            report_pdf
        )

        if not isinstance(unified_pdf, str) or not unified_pdf:
            raise RuntimeError("Merged PDF path is invalid")

        return FileResponse(
            unified_pdf,
            filename="container_report_unified.pdf",
            media_type="application/pdf"
        )

    except HTTPException:
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating unified PDF: {str(e)}"
        )

    finally:
        cur.close()
