from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, Any
import psycopg2

from services.sealing_certificate_excel_service import SealingCertificateExcelService


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/sealing-certificates",
    tags=["Sealing Certificates"]
)

excel_service = SealingCertificateExcelService()


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def get_conn():

    try:
        return psycopg2.connect(DATABASE_URL)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {str(e)}"
        )


# =========================================================
# GET ALL
# =========================================================

@router.get("")
def get_all_sealing_certificates():

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT *
            FROM sealing_certificates
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        return rows or []

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# GET BY ID
# =========================================================

@router.get("/{record_id}")
def get_sealing_certificate(record_id: int):

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT *
            FROM sealing_certificates
            WHERE id = %s
        """, (record_id,))

        row = cursor.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Sealing Certificate not found"
            )

        return row

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# CREATE
# =========================================================

@router.post("")
def create_sealing_certificate(payload: Dict[str, Any]):

    conn = None
    cursor = None

    try:

        if not isinstance(payload, dict):

            raise HTTPException(
                status_code=400,
                detail="Payload must be a dictionary"
            )

        payload = payload.copy()

        payload["created_at"] = datetime.utcnow()
        payload["status"] = "Pending for review"

        columns = []
        values = []
        params = []

        for k, v in payload.items():

            columns.append(k)
            values.append("%s")
            params.append(v)

        query = f"""
            INSERT INTO sealing_certificates
            ({",".join(columns)})
            VALUES ({",".join(values)})
            RETURNING id
        """

        conn = get_conn()

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(query, params)

        record = cursor.fetchone()

        conn.commit()

        if not record:

            raise HTTPException(
                status_code=500,
                detail="Failed to create sealing certificate"
            )

        return record

    except HTTPException:
        raise

    except Exception as e:

        if conn:
            conn.rollback()

        raise HTTPException(status_code=500, detail=str(e))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# UPDATE
# =========================================================

@router.put("/{record_id}")
def update_sealing_certificate(record_id: int, payload: Dict[str, Any]):

    conn = None
    cursor = None

    try:

        if not isinstance(payload, dict):

            raise HTTPException(
                status_code=400,
                detail="Payload must be a dictionary"
            )

        status_action = payload.get("status")

        new_status = "Pending for review"

        if status_action == "Approve":

            new_status = "Approved"

        elif status_action == "Reject":

            new_status = "Rejected"

        payload["status"] = new_status
        payload["id"] = record_id

        conn = get_conn()

        cursor = conn.cursor()

        cursor.execute("""
            UPDATE sealing_certificates SET

                report_no = %(report_no)s,
                port = %(port)s,
                country = %(country)s,
                customer = %(customer)s,

                certificate_no = %(certificate_no)s,
                vessel = %(vessel)s,
                date = %(date)s,
                location = %(location)s,
                cargo = %(cargo)s,

                hold_1_fwd_escape = %(hold_1_fwd_escape)s,
                hold_1_fwd_aft_hatch = %(hold_1_fwd_aft_hatch)s,
                hold_1_aft_escape = %(hold_1_aft_escape)s,

                hold_2_fwd_escape = %(hold_2_fwd_escape)s,
                hold_2_fwd_aft_hatch = %(hold_2_fwd_aft_hatch)s,
                hold_2_aft_escape = %(hold_2_aft_escape)s,

                hold_3_fwd_escape = %(hold_3_fwd_escape)s,
                hold_3_fwd_aft_hatch = %(hold_3_fwd_aft_hatch)s,
                hold_3_aft_escape = %(hold_3_aft_escape)s,

                hold_4_fwd_escape = %(hold_4_fwd_escape)s,
                hold_4_fwd_aft_hatch = %(hold_4_fwd_aft_hatch)s,
                hold_4_aft_escape = %(hold_4_aft_escape)s,

                hold_5_fwd_escape = %(hold_5_fwd_escape)s,
                hold_5_fwd_aft_hatch = %(hold_5_fwd_aft_hatch)s,
                hold_5_aft_escape = %(hold_5_aft_escape)s,

                hold_6_fwd_escape = %(hold_6_fwd_escape)s,
                hold_6_fwd_aft_hatch = %(hold_6_fwd_aft_hatch)s,
                hold_6_aft_escape = %(hold_6_aft_escape)s,

                remarks = %(remarks)s,
                chief_officer = %(chief_officer)s,
                closing_date = %(closing_date)s,
                closing_time = %(closing_time)s,

                status = %(status)s

            WHERE id = %(id)s
        """, payload)

        conn.commit()

        return {
            "message": "Sealing Certificate updated",
            "status": new_status,
            "id": record_id
        }

    except HTTPException:
        raise

    except Exception as e:

        if conn:
            conn.rollback()

        raise HTTPException(status_code=500, detail=str(e))

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# GENERATE EXCEL
# =========================================================

@router.get("/{record_id}/excel")
def generate_sealing_excel(record_id: int):

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT *
            FROM sealing_certificates
            WHERE id = %s
        """, (record_id,))

        row = cursor.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        file_path = excel_service.generate_excel(row)

        return FileResponse(
            path=file_path,
            filename=f"sealing_certificate_{record_id}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# GENERATE PDF
# =========================================================

@router.get("/{record_id}/pdf")
def generate_sealing_pdf(record_id: int):

    conn = None
    cursor = None

    try:

        conn = get_conn()

        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT *
            FROM sealing_certificates
            WHERE id = %s
        """, (record_id,))

        row = cursor.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        file_path = excel_service.generate_pdf(row)

        return FileResponse(
            path=file_path,
            filename=f"sealing_certificate_{record_id}.pdf",
            media_type="application/pdf"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()