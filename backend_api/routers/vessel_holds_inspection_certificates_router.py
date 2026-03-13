from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db
from services.vessel_holds_excel_service import VesselHoldsInspectionExcelService


router = APIRouter(
    prefix="/vessel-holds-inspection-certificates",
    tags=["Vessel Holds Inspection Certificates"]
)

excel_service = VesselHoldsInspectionExcelService()


# =========================================================
# CREATE
# =========================================================

@router.post("")
def create_vessel_holds_certificate(payload: dict, conn=Depends(get_db)):

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
            INSERT INTO vessel_holds_inspection_certificates
            ({",".join(columns)})
            VALUES ({",".join(values)})
            RETURNING id
        """

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(query, params)

            new_id = cur.fetchone()["id"]

        conn.commit()

        return {
            "message": "Vessel Holds Inspection Certificate created",
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
def update_vessel_holds_certificate(record_id: int, payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        payload["updated_at"] = datetime.utcnow()

        # =====================================================
        # STATUS CONTROL
        # =====================================================

        if "status" in payload:

            if payload["status"] == "Approve":
                payload["status"] = "Approved"

            elif payload["status"] == "Reject":
                payload["status"] = "Rejected"

        # =====================================================
        # BUILD UPDATE
        # =====================================================

        sets = []
        params = []

        for k, v in payload.items():

            sets.append(f"{k}=%s")
            params.append(v)

        params.append(record_id)

        query = f"""
            UPDATE vessel_holds_inspection_certificates
            SET {",".join(sets)}
            WHERE id=%s
        """

        with conn.cursor() as cur:

            cur.execute(query, params)

        conn.commit()

        return {
            "message": "Vessel Holds Inspection Certificate updated"
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GET ALL
# =========================================================

@router.get("")
def get_all_vessel_holds_certificates(conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT
                    id,
                    report_number,
                    port,
                    country,
                    vessel,
                    voyage,
                    load_port,
                    place,
                    installation,
                    product,
                    date,
                    inspection_time,
                    vessel_holds,
                    vessel_holds_status,
                    cargo_holds,
                    accepted_time,
                    place_location,
                    place_date,
                    hose_test_start,
                    hose_test_end,
                    remarks,
                    created_at,
                    updated_at,
                    status
                FROM vessel_holds_inspection_certificates
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
def get_vessel_holds_certificate(record_id: int, conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT
                    id,
                    report_number,
                    port,
                    country,
                    vessel,
                    voyage,
                    load_port,
                    place,
                    installation,
                    product,
                    date,
                    inspection_time,
                    vessel_holds,
                    vessel_holds_status,
                    cargo_holds,
                    accepted_time,
                    place_location,
                    place_date,
                    hose_test_start,
                    hose_test_end,
                    remarks,
                    created_at,
                    updated_at,
                    status
                FROM vessel_holds_inspection_certificates
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
# GENERATE EXCEL
# =========================================================

@router.get("/{record_id}/excel")
def generate_vessel_holds_excel(record_id: int, conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT *
                FROM vessel_holds_inspection_certificates
                WHERE id=%s

            """, (record_id,))

            row = cur.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        file_path = excel_service.generate_excel(row)

        return FileResponse(
            path=file_path,
            filename=f"holds_inspection_certificate_{record_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GENERATE PDF
# =========================================================

@router.get("/{record_id}/pdf")
def generate_vessel_holds_pdf(record_id: int, conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute("""

                SELECT *
                FROM vessel_holds_inspection_certificates
                WHERE id=%s

            """, (record_id,))

            row = cur.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        file_path = excel_service.generate_pdf(row)

        return FileResponse(
            path=file_path,
            filename=f"holds_inspection_certificate_{record_id}.pdf",
            media_type="application/pdf"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



