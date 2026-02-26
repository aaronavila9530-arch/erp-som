from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Dict
import logging
import os

from services.draft_survey_word_pdf_service import generate_draft_survey_word_pdf


router = APIRouter(
    prefix="/draft-survey-word",
    tags=["Draft Survey Word PDF"]
)

logger = logging.getLogger(__name__)


# =========================================================
# GENERATE WORD PDF FROM PAYLOAD (NO DB)
# =========================================================
@router.post("/generate")
def generate_word_pdf(
    payload: Dict,
    background_tasks: BackgroundTasks
):

    # =====================================================
    # 1️⃣ VALIDACIÓN PAYLOAD
    # =====================================================
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=422,
            detail="Invalid payload format"
        )

    if not payload:
        raise HTTPException(
            status_code=422,
            detail="Payload cannot be empty"
        )

    try:
        # =================================================
        # 2️⃣ GENERAR PDF DESDE SERVICE
        # =================================================
        pdf_path = generate_draft_survey_word_pdf(payload)

        if not pdf_path:
            raise HTTPException(
                status_code=500,
                detail="Service did not return a file path"
            )

        file_path = Path(pdf_path)

        # =================================================
        # 3️⃣ VALIDAR EXISTENCIA
        # =================================================
        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Generated PDF file does not exist"
            )

        # =================================================
        # 4️⃣ LIMPIEZA AUTOMÁTICA (TEMP FILE)
        # =================================================
        def cleanup_file(path: Path):
            try:
                if path.exists():
                    path.unlink()

                # borrar carpeta temporal si está vacía
                parent = path.parent
                if parent.exists():
                    try:
                        parent.rmdir()
                    except Exception:
                        pass
            except Exception:
                pass

        background_tasks.add_task(cleanup_file, file_path)

        # =================================================
        # 5️⃣ RESPUESTA SEGURA
        # =================================================
        return FileResponse(
            path=str(file_path),
            media_type="application/pdf",
            filename="draft_word.pdf"
        )

    except HTTPException:
        raise

    except FileNotFoundError as fnf:
        logger.error(f"Template missing: {fnf}")
        raise HTTPException(
            status_code=500,
            detail="Word template not found"
        )

    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )

    except Exception as e:
        logger.exception("Unexpected error generating Word PDF")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )