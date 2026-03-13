from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import psycopg2
import psycopg2.extras


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/sealing-certificates",
    tags=["Sealing Certificates"]
)


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def get_conn():
    return psycopg2.connect(DATABASE_URL)


# =========================================================
# GET ALL
# =========================================================

@router.get("/")
def get_all_sealing_certificates():

    try:

        conn = get_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT *
            FROM sealing_certificates
            ORDER BY id DESC
        """)

        rows = cursor.fetchall()

        cursor.close()
        conn.close()

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
def get_sealing_certificate(record_id: int):

    try:

        conn = get_conn()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cursor.execute("""
            SELECT *
            FROM sealing_certificates
            WHERE id = %s
        """, (record_id,))

        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Sealing Certificate not found"
            )

        return row

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# POST
# =========================================================

@router.post("/")
def create_sealing_certificate(payload: Dict[str, Any]):

    try:

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sealing_certificates (

                report_no,
                port,
                country,
                customer,

                certificate_no,
                vessel,
                date,
                location,
                cargo,

                hold_1_fwd_escape,
                hold_1_fwd_aft_hatch,
                hold_1_aft_escape,

                hold_2_fwd_escape,
                hold_2_fwd_aft_hatch,
                hold_2_aft_escape,

                hold_3_fwd_escape,
                hold_3_fwd_aft_hatch,
                hold_3_aft_escape,

                hold_4_fwd_escape,
                hold_4_fwd_aft_hatch,
                hold_4_aft_escape,

                hold_5_fwd_escape,
                hold_5_fwd_aft_hatch,
                hold_5_aft_escape,

                hold_6_fwd_escape,
                hold_6_fwd_aft_hatch,
                hold_6_aft_escape,

                remarks,
                chief_officer,
                closing_date,
                closing_time,

                status

            ) VALUES (

                %(report_no)s,
                %(port)s,
                %(country)s,
                %(customer)s,

                %(certificate_no)s,
                %(vessel)s,
                %(date)s,
                %(location)s,
                %(cargo)s,

                %(hold_1_fwd_escape)s,
                %(hold_1_fwd_aft_hatch)s,
                %(hold_1_aft_escape)s,

                %(hold_2_fwd_escape)s,
                %(hold_2_fwd_aft_hatch)s,
                %(hold_2_aft_escape)s,

                %(hold_3_fwd_escape)s,
                %(hold_3_fwd_aft_hatch)s,
                %(hold_3_aft_escape)s,

                %(hold_4_fwd_escape)s,
                %(hold_4_fwd_aft_hatch)s,
                %(hold_4_aft_escape)s,

                %(hold_5_fwd_escape)s,
                %(hold_5_fwd_aft_hatch)s,
                %(hold_5_aft_escape)s,

                %(hold_6_fwd_escape)s,
                %(hold_6_fwd_aft_hatch)s,
                %(hold_6_aft_escape)s,

                %(remarks)s,
                %(chief_officer)s,
                %(closing_date)s,
                %(closing_time)s,

                'Pending for review'

            )
            RETURNING id
        """, payload)

        new_id = cursor.fetchone()[0]

        conn.commit()

        cursor.close()
        conn.close()

        return {
            "message": "Sealing Certificate created",
            "id": new_id
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# PUT
# =========================================================

@router.put("/{record_id}")
def update_sealing_certificate(record_id: int, payload: Dict[str, Any]):

    try:

        status_action = payload.get("status")

        new_status = "Pending for review"

        if status_action == "Approve":
            new_status = "Approved"

        elif status_action == "Reject":
            new_status = "Rejected"

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

                status = %s

            WHERE id = %s
        """, (*payload.values(), new_status, record_id))

        conn.commit()

        cursor.close()
        conn.close()

        return {
            "message": "Sealing Certificate updated",
            "status": new_status
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )