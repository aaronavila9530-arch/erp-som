from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from services.draft_survey_word_pdf_service import DraftSurveyWordPdfService

router = APIRouter(
    prefix="/draft-survey-word",
    tags=["Draft Survey Word PDF"]
)


@router.get("/generate/{draft_report_number}")
def generate_word_pdf(draft_report_number: str):

    try:
        service = DraftSurveyWordPdfService()
        pdf_path = service.generate_pdf_by_report_number(draft_report_number)

        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"{draft_report_number}.pdf"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))