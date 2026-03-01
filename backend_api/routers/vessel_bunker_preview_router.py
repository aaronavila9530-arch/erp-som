from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import logging

from services.vessel_bunker_excel_service import VesselBunkerExcelService


router = APIRouter(
    prefix="/vessel-bunker-preview",
    tags=["Vessel Bunker Preview"]
)

logger = logging.getLogger(__name__)


# =========================================================
# PREVIEW EXCEL (NO DB — SOLO PAYLOAD)
# =========================================================
@router.post("/excel")
def preview_vessel_bunker_excel(payload: dict):

    try:
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=422,
                detail="Invalid payload"
            )

        service = VesselBunkerExcelService()

        # 🔥 Usa el método nuevo del service
        file_path = service.generate_excel_from_payload(payload)

        if not file_path or not os.path.exists(file_path):
            raise HTTPException(
                status_code=500,
                detail="Excel generation failed"
            )

        return FileResponse(
            path=file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="vessel_bunker_preview.xlsx"
        )

    except Exception as e:
        logger.exception("Preview Excel error")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )