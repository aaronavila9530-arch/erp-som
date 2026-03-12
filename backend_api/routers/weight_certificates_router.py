from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

# ================================
# NUEVO SERVICE
# ================================
from services.weight_certificate_word_service import (
    WeightCertificateWordService
)

router = APIRouter(
    prefix="/weight-certificates",
    tags=["Weight Certificates"]
)

word_service = WeightCertificateWordService()


# =========================================================
# CREATE (POST)
# =========================================================

@router.post("")
def create_weight_certificate(payload: dict, conn=Depends(get_db)):

    try:

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = """
        INSERT INTO weight_certificates (
            report_number,
            continent,
            country,
            port,
            operation,
            vessel,
            voyage,
            commodity,
            bl_figure,
            cargo_hold,
            shipper,
            consignee,
            terminal,
            loading_port,
            weight_determination,
            date,
            quantity,
            remarks,
            created_at,
            updated_at,
            status
        )
        VALUES (
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,%s,%s,
            %s,%s,%s,
            NOW(),NOW(),
            'Pending for review'
        )
        RETURNING *
        """

        cursor.execute(
            query,
            (
                payload.get("report_number"),
                payload.get("continent"),
                payload.get("country"),
                payload.get("port"),
                payload.get("operation"),
                payload.get("vessel"),
                payload.get("voyage"),
                payload.get("commodity"),
                payload.get("bl_figure"),
                payload.get("cargo_hold"),
                payload.get("shipper"),
                payload.get("consignee"),
                payload.get("terminal"),
                payload.get("loading_port"),
                payload.get("weight_determination"),
                payload.get("date"),
                payload.get("quantity"),
                payload.get("remarks"),
            )
        )

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


# =========================================================
# GENERATE WORD REPORT
# =========================================================

@router.get("/{record_id}/word")
def generate_weight_certificate_word(record_id: int, conn=Depends(get_db)):

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT *
        FROM weight_certificates
        WHERE id=%s
        """,
        (record_id,)
    )

    data = cursor.fetchone()

    cursor.close()

    if not data:

        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    return word_service.generate_word(data)


# =========================================================
# GENERATE PDF REPORT
# =========================================================

@router.get("/{record_id}/pdf")
def generate_weight_certificate_pdf(record_id: int, conn=Depends(get_db)):

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        SELECT *
        FROM weight_certificates
        WHERE id=%s
        """,
        (record_id,)
    )

    data = cursor.fetchone()

    cursor.close()

    if not data:

        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    return word_service.generate_pdf(data)