from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

router = APIRouter(
    prefix="/sampling-certificates",
    tags=["Sampling Certificates"]
)


# =========================================================
# CREATE
# =========================================================

@router.post("")
def create_sampling_certificate(payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        payload["created_at"] = datetime.utcnow()
        payload["updated_at"] = datetime.utcnow()

        # STATUS DEFAULT
        payload["status"] = "Pending for review"

        columns = []
        values = []
        params = []

        for k, v in payload.items():

            columns.append(k)
            values.append("%s")
            params.append(v)

        query = f"""
            INSERT INTO sampling_certificates
            ({",".join(columns)})
            VALUES ({",".join(values)})
            RETURNING id
        """

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(query, params)

            record = cur.fetchone()

        conn.commit()

        return record

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# UPDATE
# =========================================================

@router.put("/{record_id}")
def update_sampling_certificate(record_id: int, payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        payload["updated_at"] = datetime.utcnow()

        status = payload.get("status")

        if status:

            if status.lower() == "approve":
                payload["status"] = "Approved"

            elif status.lower() == "reject":
                payload["status"] = "Rejected"

        sets = []
        params = []

        for k, v in payload.items():

            sets.append(f"{k}=%s")
            params.append(v)

        params.append(record_id)

        query = f"""
            UPDATE sampling_certificates
            SET {",".join(sets)}
            WHERE id=%s
        """

        with conn.cursor() as cur:

            cur.execute(query, params)

        conn.commit()

        return {"status": "updated"}

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GET ALL
# =========================================================

@router.get("")
def get_sampling_certificates(conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""
                SELECT *
                FROM sampling_certificates
                ORDER BY id DESC
            """)

            rows = cur.fetchall()

        return rows

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GET BY ID
# =========================================================

@router.get("/{record_id}")
def get_sampling_certificate(record_id: int, conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""
                SELECT *
                FROM sampling_certificates
                WHERE id=%s
            """, (record_id,))

            row = cur.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        return row

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GENERATE EXCEL (placeholder)
# =========================================================

@router.get("/{record_id}/excel")
def generate_sampling_excel(record_id: int):

    raise HTTPException(
        status_code=501,
        detail="Excel generation service not implemented yet"
    )


# =========================================================
# GENERATE PDF (placeholder)
# =========================================================

@router.get("/{record_id}/pdf")
def generate_sampling_pdf(record_id: int):

    raise HTTPException(
        status_code=501,
        detail="PDF generation service not implemented yet"
    )