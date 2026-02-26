from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import os
import logging

from services.draft_survey_word_pdf_service import DraftSurveyWordPdfService


router = APIRouter(
    prefix="/draft-survey-word",
    tags=["Draft Survey Word PDF"]
)

logger = logging.getLogger(__name__)


@router.get("/generate/{draft_report_number}")
def generate_word_pdf(draft_report_number: str):

    # =========================================================
    # 1️⃣ VALIDACIÓN INPUT
    # =========================================================
    if not draft_report_number or not draft_report_number.strip():
        raise HTTPException(
            status_code=422,
            detail="draft_report_number is required"
        )

    try:
        # =====================================================
        # 2️⃣ GENERAR PDF
        # =====================================================
        service = DraftSurveyWordPdfService()
        pdf_path = service.generate_pdf_by_report_number(
            draft_report_number.strip()
        )

        if not pdf_path:
            raise HTTPException(
                status_code=500,
                detail="Service did not return a file path"
            )

        file_path = Path(pdf_path)

        # =====================================================
        # 3️⃣ VALIDAR EXISTENCIA
        # =====================================================
        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Generated PDF file does not exist"
            )

        # =====================================================
        # 4️⃣ RESPUESTA SEGURA
        # =====================================================
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=f"{draft_report_number}.pdf"
        )

    except HTTPException:
        raise

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(status_code=404, detail=str(ve))

    except FileNotFoundError as fnf:
        logger.error(f"Template missing: {fnf}")
        raise HTTPException(status_code=500, detail="Word template not found")

    except Exception as e:
        logger.exception("Unexpected error generating Word PDF")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )