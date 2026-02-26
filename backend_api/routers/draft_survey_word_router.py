from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import logging

from services.draft_survey_word_pdf_service import (
    generate_draft_survey_word_pdf
)

router = APIRouter(
    prefix="/draft-survey-word",
    tags=["Draft Survey Word PDF"]
)

logger = logging.getLogger(__name__)


@router.post("/generate")
def generate_word_pdf(
    payload: dict,
    background_tasks: BackgroundTasks
):

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=422,
            detail="Invalid payload"
        )

    draft_report_number = str(
        payload.get("draft_report_number") or ""
    ).strip()

    if not draft_report_number:
        raise HTTPException(
            status_code=422,
            detail="draft_report_number is required"
        )

    try:

        # 🔥 GENERA PDF DIRECTAMENTE
        pdf_path = generate_draft_survey_word_pdf(payload)

        file_path = Path(pdf_path)

        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Generated PDF file does not exist"
            )

        # Cleanup automático
        def cleanup(path: Path):
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass

        background_tasks.add_task(cleanup, file_path)

        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=f"{draft_report_number}_WORD.pdf"
        )

    except HTTPException:
        raise

    except Exception:
        logger.exception("Unexpected error generating Word PDF")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )