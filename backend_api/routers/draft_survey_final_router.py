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