from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import logging

from database import get_db
from services.draft_survey_word_pdf_service import (
    generate_draft_survey_word_pdf
)
from services.draft_survey_word_data_service import (
    get_draft_word_data_by_report_number
)

router = APIRouter(
    prefix="/draft-survey-word",
    tags=["Draft Survey Word PDF"]
)

logger = logging.getLogger(__name__)


@router.get("/generate/{draft_report_number}")
def generate_word_pdf(
    draft_report_number: str,
    background_tasks: BackgroundTasks,
    conn=Depends(get_db)
):

    draft_report_number = str(draft_report_number or "").strip()

    if not draft_report_number:
        raise HTTPException(
            status_code=422,
            detail="draft_report_number is required"
        )

    try:

        # 🔥 AQUÍ ESTÁ LA DIFERENCIA
        data = get_draft_word_data_by_report_number(
            conn,
            draft_report_number
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Draft Word record not found"
            )

        pdf_path = generate_draft_survey_word_pdf(data)

        file_path = Path(pdf_path)

        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Generated PDF file does not exist"
            )

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
            detail="Error generating Word PDF"
        )