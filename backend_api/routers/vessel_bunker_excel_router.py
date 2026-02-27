from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import datetime
import logging
import os

from database import get_db
from services.vessel_bunker_excel_service import VesselBunkerExcelGenerator


router = APIRouter(
    prefix="/vessel-bunker-excel",
    tags=["Vessel Bunker Excel"]
)

logger = logging.getLogger(__name__)


# =========================================================
# GENERATE EXCEL BY REPORT ID
# =========================================================
@router.get("/generate/{report_id}")
def generate_vessel_bunker_excel(report_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # -------------------------------------------------
        # 1️⃣ VALIDAR QUE EXISTA
        # -------------------------------------------------
        cur.execute(
            "SELECT * FROM vessel_bunker_reports WHERE id=%s",
            (report_id,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Report not found")

        payload = dict(row)

        # -------------------------------------------------
        # 2️⃣ GENERAR EXCEL
        # -------------------------------------------------
        generator = VesselBunkerExcelGenerator()
        excel_path = generator.generate(payload)

        if not excel_path or not os.path.exists(excel_path):
            raise HTTPException(status_code=500, detail="Excel generation failed")

        # -------------------------------------------------
        # 3️⃣ DEVOLVER ARCHIVO
        # -------------------------------------------------
        filename = f"vessel_bunker_report_{report_id}.xlsx"

        return FileResponse(
            path=excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Error generating bunker Excel")
        raise HTTPException(status_code=500, detail=str(e))




@router.get("/generate-pdf/{report_id}")
def generate_vessel_bunker_pdf(report_id: int, conn=Depends(get_db)):

    try:
        # 1️⃣ Generar Excel
        excel_service = VesselBunkerExcelService()
        excel_path = excel_service.generate_excel_by_report_id(conn, report_id)

        # 2️⃣ Generar PDF Final (3 hojas merge)
        pdf_service = VesselBunkerExcelPdfService()
        pdf_path = pdf_service.generate_pdf_from_excel(excel_path)

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"Vessel_Bunker_{report_id}.pdf"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


