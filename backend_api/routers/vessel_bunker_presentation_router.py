from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import logging

from database import get_db
from psycopg2.extras import RealDictCursor


router = APIRouter(
    prefix="/vessel-bunker-reports",
    tags=["Vessel Bunker Presentation"]
)

logger = logging.getLogger(__name__)


@router.get("/presentation/{report_id}")
def generate_bunker_presentation(report_id: int, conn=Depends(get_db)):

    from services.bunker_presentation_service import generate_bunker_presentation_pdf

    report_id = int(report_id)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                id,
                bunker_cert_no,
                ship_name,
                port_of_registry,
                gross_tonnage,
                report_date,
                certificate,
                report_category,
                client,
                port,
                country,
                berthing_date,
                commenced_date,
                dslop_date,
                dslop_port,
                dslop_country
            FROM vessel_bunker_reports
            WHERE id = %s
        """, (report_id,))

        data = cur.fetchone()

        if not data:
            raise HTTPException(status_code=404, detail="Vessel bunker report not found")

        pdf_path = generate_bunker_presentation_pdf(data)

        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"BUNKER_PRESENTATION_{report_id}.pdf"
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Unexpected error generating bunker presentation PDF")
        raise HTTPException(status_code=500, detail=f"Error generating presentation PDF: {e}")

    finally:
        cur.close()