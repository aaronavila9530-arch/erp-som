from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import logging

from services.draft_survey_word_pdf_service import generate_draft_survey_word_pdf
from services.draft_survey_unified_service import get_full_draft_survey_by_report_number


router = APIRouter(
    prefix="/draft-survey-word",
    tags=["Draft Survey Word PDF"]
)

logger = logging.getLogger(__name__)


# =========================================================
# GENERATE WORD PDF FROM DB (ERP FLOW)
# =========================================================
@router.get("/generate/{draft_report_number}")
def generate_word_pdf_from_db(
    draft_report_number: str,
    background_tasks: BackgroundTasks
):

    draft_report_number = str(draft_report_number or "").strip()

    if not draft_report_number:
        raise HTTPException(
            status_code=422,
            detail="draft_report_number is required"
        )

    try:
        # =================================================
        # 1️⃣ GET FULL MERGED DATA FROM DB
        # =================================================
        data = get_full_draft_survey_by_report_number(
            draft_report_number
        )

        if not data:
            raise HTTPException(
                status_code=404,
                detail="Draft Survey not found"
            )

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid data structure from unified service"
            )

        # =================================================
        # 2️⃣ GENERATE PDF
        # =================================================
        pdf_path = generate_draft_survey_word_pdf(data)

        if not pdf_path:
            raise HTTPException(
                status_code=500,
                detail="Service did not return a file path"
            )

        file_path = Path(pdf_path)

        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Generated PDF file does not exist"
            )

        if file_path.stat().st_size == 0:
            raise HTTPException(
                status_code=500,
                detail="Generated PDF file is empty"
            )

        # =================================================
        # 3️⃣ CLEANUP TEMP FILES
        # =================================================
        def cleanup_files(path: Path):
            try:
                if path.exists():
                    path.unlink()

                parent = path.parent
                if parent.exists():
                    try:
                        parent.rmdir()
                    except Exception:
                        pass
            except Exception:
                pass

        background_tasks.add_task(cleanup_files, file_path)

        # =================================================
        # 4️⃣ RETURN FILE
        # =================================================
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename=f"{draft_report_number}_WORD.pdf"
        )

    except HTTPException:
        raise

    except FileNotFoundError as fnf:
        logger.error(f"Template missing: {fnf}")
        raise HTTPException(
            status_code=500,
            detail="Word template not found"
        )

    except Exception:
        logger.exception("Unexpected error generating Word PDF")
        raise HTTPException(
            status_code=500,
            detail="Internal server error generating Word PDF"
        )