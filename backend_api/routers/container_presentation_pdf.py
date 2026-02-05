from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor

from database import get_db
from services.presentation_doc_service import generate_presentation_pdf
from services.pdf_merge_service import merge_pdfs
from services.container_report_pdf_service import generate_container_report_pdf


router = APIRouter(
    prefix="/container-presentation-pdf",
    tags=["Container Presentation PDF"]
)


# =====================================================
# PRESENTATION ONLY
# =====================================================
@router.get("/{container_report_id}/presentation")
def generate_presentation_only(
    container_report_id: int,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ---------------------------------------------
        # Obtener data base (MISMA lógica que router base)
        # ---------------------------------------------
        cur.execute("""
            SELECT
                id,
                linked_report_number,
                report_no,
                inspection_place,
                init_inspection_datetime
            FROM container_reports
            WHERE id = %s
        """, (container_report_id,))

        report = cur.fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="Container report not found")

        linked = report["linked_report_number"]

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
                cliente = row["cliente"]

        date_fmt = None
        if report["init_inspection_datetime"]:
            date_fmt = report["init_inspection_datetime"].strftime("%d-%m-%Y")

        data = {
            "cert_no": linked,
            "container": report["report_no"],
            "to": cliente,
            "place": report["inspection_place"],
            "date": date_fmt
        }

        pdf_path = generate_presentation_pdf(data)

        return FileResponse(
            pdf_path,
            filename="presentation.pdf",
            media_type="application/pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()


# =====================================================
# UNIFIED PDF (Presentation + Report)
# =====================================================
@router.get("/{container_report_id}/unified")
def generate_unified_pdf(
    container_report_id: int,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ---------------------------------------------
        # 1️⃣ Presentation
        # ---------------------------------------------
        cur.execute("""
            SELECT
                id,
                linked_report_number,
                report_no,
                inspection_place,
                init_inspection_datetime
            FROM container_reports
            WHERE id = %s
        """, (container_report_id,))

        report = cur.fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="Container report not found")

        linked = report["linked_report_number"]

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
                cliente = row["cliente"]

        date_fmt = None
        if report["init_inspection_datetime"]:
            date_fmt = report["init_inspection_datetime"].strftime("%d-%m-%Y")

        data = {
            "cert_no": linked,
            "container": report["report_no"],
            "to": cliente,
            "place": report["inspection_place"],
            "date": date_fmt
        }

        presentation_pdf = generate_presentation_pdf(data)

        # ---------------------------------------------
        # 2️⃣ Container Report PDF (SERVICE, NO ROUTER)
        # ---------------------------------------------
        report_pdf = generate_container_report_pdf(container_report_id)

        # ---------------------------------------------
        # 3️⃣ Merge
        # ---------------------------------------------
        unified_pdf = merge_pdfs(presentation_pdf, report_pdf)

        return FileResponse(
            unified_pdf,
            filename="container_report_unified.pdf",
            media_type="application/pdf"
        )

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
