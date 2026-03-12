from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

router = APIRouter(
    prefix="/weight-certificates",
    tags=["Weight Certificates"]
)


# =========================================================
# CREATE (POST)
# =========================================================

@router.post("")
def create_weight_certificate(payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        payload["created_at"] = datetime.utcnow()
        payload["updated_at"] = datetime.utcnow()

        # status SIEMPRE Pending for review
        payload["status"] = "Pending for review"

        columns = []
        values = []
        params = []

        for k, v in payload.items():

            columns.append(k)
            values.append("%s")
            params.append(v)

        query = f"""
        INSERT INTO weight_certificates
        ({",".join(columns)})
        VALUES ({",".join(values)})
        RETURNING *
        """

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(query, params)

        row = cursor.fetchone()

        conn.commit()

        cursor.close()

        return row

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# UPDATE (PUT)
# =========================================================

@router.put("/{record_id}")
def update_weight_certificate(record_id: int, payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # ========================================
        # STATUS CONTROL
        # ========================================

        action = payload.pop("action", None)

        if action:

            if action.lower() == "approve":
                payload["status"] = "Approved"

            elif action.lower() == "reject":
                payload["status"] = "Rejected"

        payload["updated_at"] = datetime.utcnow()

        # ========================================
        # BUILD UPDATE
        # ========================================

        sets = []
        params = []

        for k, v in payload.items():

            sets.append(f"{k}=%s")
            params.append(v)

        params.append(record_id)

        query = f"""
        UPDATE weight_certificates
        SET {",".join(sets)}
        WHERE id=%s
        RETURNING *
        """

        cursor.execute(query, params)

        row = cursor.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        conn.commit()

        cursor.close()

        return row

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GET ALL
# =========================================================

@router.get("")
def get_weight_certificates(conn=Depends(get_db)):

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT *
        FROM weight_certificates
        ORDER BY created_at DESC
        """
    )

    rows = cursor.fetchall()

    cursor.close()

    return rows


# =========================================================
# GET BY ID
# =========================================================

@router.get("/{record_id}")
def get_weight_certificate(record_id: int, conn=Depends(get_db)):

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT *
        FROM weight_certificates
        WHERE id=%s
        """,
        (record_id,)
    )

    row = cursor.fetchone()

    cursor.close()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    return row