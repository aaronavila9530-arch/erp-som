from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import logging

from database import get_db
from services.draft_survey_final_pdf_service import DraftSurveyFinalPdfService

router = APIRouter(
    prefix="/draft-survey-final",
    tags=["Draft Survey Final PDF"]
)

logger = logging.getLogger(__name__)


@router.get("/generate/{draft_report_number}")
def generate_final_pdf(
    draft_report_number: str,
    conn=Depends(get_db)
):

    draft_report_number = str(draft_report_number or "").strip()
    if not draft_report_number:
        raise HTTPException(status_code=422, detail="draft_report_number is required")

    try:
        service = DraftSurveyFinalPdfService()
        pdf_path = service.generate_final_pdf_by_report_number(conn, draft_report_number)

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"{draft_report_number}_FINAL.pdf"
        )

    except Exception as e:
        logger.exception("Unexpected error generating FINAL PDF")
        raise HTTPException(status_code=500, detail=f"Error generating FINAL PDF: {e}")



@router.get("/unified/{draft_report_number}")
def generate_unified_final_pdf(
    draft_report_number: str,
    conn=Depends(get_db)
):

    from services.draft_survey_presentation_service import (
        generate_draft_survey_presentation_pdf
    )
    from services.draft_survey_final_pdf_service import (
        DraftSurveyFinalPdfService
    )
    from psycopg2.extras import RealDictCursor
    import tempfile
    import os

    draft_report_number = str(draft_report_number or "").strip()
    if not draft_report_number:
        raise HTTPException(status_code=422, detail="draft_report_number is required")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # -------------------------------------------------
        # 1️⃣ Obtener data para Presentation
        # -------------------------------------------------
        cur.execute("""
            SELECT
                draft_report_number,
                word_vessel,
                word_grt,
                word_nrt,
                word_survey_requested_by,
                word_port,
                word_country,
                word_commenced
            FROM draft_survey_word_report
            WHERE draft_report_number = %s
        """, (draft_report_number,))

        presentation_data = cur.fetchone()

        if not presentation_data:
            raise HTTPException(
                status_code=404,
                detail="Draft Survey Word report not found"
            )

        # -------------------------------------------------
        # 2️⃣ Generar Presentation PDF
        # -------------------------------------------------
        presentation_pdf = generate_draft_survey_presentation_pdf(
            presentation_data
        )

        # -------------------------------------------------
        # 3️⃣ Generar Final PDF (Word + Excel merged)
        # -------------------------------------------------
        final_service = DraftSurveyFinalPdfService()
        final_pdf = final_service.generate_final_pdf_by_report_number(
            conn,
            draft_report_number
        )

        # -------------------------------------------------
        # 4️⃣ MERGE PRESENTATION + FINAL
        # -------------------------------------------------
        out_dir = tempfile.mkdtemp(prefix="draft_unified_")
        out_path = os.path.join(
            out_dir,
            f"{draft_report_number}_UNIFIED.pdf"
        )

        unified_path = final_service._merge_pdfs(
            pdf_paths=[presentation_pdf, final_pdf],
            out_path=out_path
        )

        return FileResponse(
            path=unified_path,
            media_type="application/pdf",
            filename=f"{draft_report_number}_UNIFIED.pdf"
        )

    except Exception as e:
        logger.exception("Unexpected error generating UNIFIED PDF")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating UNIFIED PDF: {e}"
        )

    finally:
        cur.close()