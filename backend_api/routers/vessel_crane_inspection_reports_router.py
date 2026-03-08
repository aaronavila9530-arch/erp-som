from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

from services.vessel_crane_inspection_word_service import (
    VesselCraneInspectionWordService
)

router = APIRouter(
    prefix="/vessel-crane-inspection-reports",
    tags=["Vessel Crane Inspection Reports"]
)

word_service = VesselCraneInspectionWordService()


# =========================================================
# CREATE
# =========================================================

@router.post("")
def create_crane_inspection(payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        payload["created_at"] = datetime.utcnow()
        payload["updated_at"] = datetime.utcnow()

        columns = []
        values = []
        params = []

        for k, v in payload.items():

            columns.append(k)
            values.append("%s")
            params.append(v)

        sql = f"""
        INSERT INTO vessel_crane_inspection_reports
        ({",".join(columns)})
        VALUES ({",".join(values)})
        RETURNING id
        """

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)

        new_id = cur.fetchone()["id"]

        conn.commit()

        return {
            "success": True,
            "id": new_id
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# UPDATE
# =========================================================

@router.put("/{record_id}")
def update_crane_inspection(
        record_id: int,
        payload: dict,
        conn=Depends(get_db)
):

    try:

        payload = payload or {}

        payload["updated_at"] = datetime.utcnow()

        sets = []
        params = []

        for k, v in payload.items():

            sets.append(f"{k}=%s")
            params.append(v)

        params.append(record_id)

        sql = f"""
        UPDATE vessel_crane_inspection_reports
        SET {",".join(sets)}
        WHERE id=%s
        """

        cur = conn.cursor()
        cur.execute(sql, params)

        conn.commit()

        return {"success": True}

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GET FULL REPORT
# =========================================================

@router.get("/{record_id}")
def get_full_crane_inspection(
        record_id: int,
        conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT *
        FROM vessel_crane_inspection_reports
        WHERE id = %s
        """,
        (record_id,)
    )

    row = cur.fetchone()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Report not found"
        )

    return row


# =========================================================
# GENERATE WORD
# =========================================================

@router.get("/{record_id}/generate-word")
def generate_crane_inspection_word(
        record_id: int,
        conn=Depends(get_db)
):

    try:

        path = word_service.generate_word_by_id(
            conn,
            record_id
        )

        return FileResponse(
            path,
            filename=f"Crane_Inspection_{record_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )