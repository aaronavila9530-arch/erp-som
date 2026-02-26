from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import logging

from database import get_db
from services.draft_survey_excel_pdf_service import DraftSurveyExcelPdfService

router = APIRouter(
    prefix="/draft-survey-excel",
    tags=["Draft Survey Excel/PDF"]
)

logger = logging.getLogger(__name__)


@router.get("/generate-pdf/{draft_report_number}")
def generate_draft_survey_excel_pdf(
    draft_report_number: str,
    conn=Depends(get_db)
):

    draft_report_number = str(draft_report_number or "").strip()
    if not draft_report_number:
        raise HTTPException(status_code=422, detail="draft_report_number is required")

    try:
        service = DraftSurveyExcelPdfService()
        pdf_path = service.generate_pdf_by_report_number(conn, draft_report_number)

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"{draft_report_number}_DRAFT_SURVEY.pdf"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Unexpected error generating Draft Survey Excel/PDF")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating Draft Survey PDF: {e}"
        )