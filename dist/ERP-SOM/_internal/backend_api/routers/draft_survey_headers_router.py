from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from database import get_db

router = APIRouter(
    prefix="/draft-survey-headers",
    tags=["Draft Survey Headers"]
)

# =========================================================
# GET HEADERS LIST (SIN COLISIONES)
# GET /draft-survey-headers/
# =========================================================
@router.get("/")
def get_draft_survey_headers_list(conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                draft_report_number,
                status,
                year,
                month,
                continent,
                country,
                port,
                client
            FROM general_draft_survey
            ORDER BY draft_report_number DESC
        """)

        rows = cur.fetchall() or []

        return {
            "success": True,
            "data": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Headers fetch error: {e}"
        )
    finally:
        cur.close()