from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db


router = APIRouter(
    prefix="/vessel-grain-sampling",
    tags=["Vessel Grain Sampling"]
)


# ============================================================
# CREATE — NEW GRAIN SAMPLING REPORT
# ============================================================
@router.post("")
def create_vessel_grain_sampling_report(
    payload: dict,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            INSERT INTO vessel_grain_sampling_reports (
                cert_no,
                place_date,
                purpose,
                requested_by,
                arrival_info,
                inspection_info,
                captain,
                chief_officer,
                vessel_name,
                flag_port,
                grt,
                nrt,
                imo,
                build_year,
                times,
                products_summary,
                products_table,
                supervision,
                sampling,
                procedure,
                conclusion,
                created_at,
                updated_at
            ) VALUES (
                %(cert_no)s,
                %(place_date)s,
                %(purpose)s,
                %(requested_by)s,
                %(arrival_info)s,
                %(inspection_info)s,
                %(captain)s,
                %(chief_officer)s,
                %(vessel_name)s,
                %(flag_port)s,
                %(grt)s,
                %(nrt)s,
                %(imo)s,
                %(build_year)s,
                %(times)s,
                %(products_summary)s,
                %(products_table)s,
                %(supervision)s,
                %(sampling)s,
                %(procedure)s,
                %(conclusion)s,
                NOW(),
                NOW()
            )
            RETURNING id
        """, payload)

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
            detail=f"Error creating grain sampling report: {str(e)}"
        )

    finally:
        cur.close()


# ============================================================
# GET — LIST ALL REPORTS
# ============================================================
@router.get("")
def list_vessel_grain_sampling_reports(
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                id,
                created_at,
                updated_at,
                cert_no,
                place_date,
                vessel_name
            FROM vessel_grain_sampling_reports
            ORDER BY created_at DESC
        """)

        rows = cur.fetchall()

        return {
            "success": True,
            "data": rows
        }

    finally:
        cur.close()


# ============================================================
# GET — SINGLE REPORT BY ID
# ============================================================
@router.get("/{report_id}")
def get_vessel_grain_sampling_report(
    report_id: int,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                id,
                created_at,
                updated_at,
                cert_no,
                place_date,
                purpose,
                requested_by,
                arrival_info,
                inspection_info,
                captain,
                chief_officer,
                vessel_name,
                flag_port,
                grt,
                nrt,
                imo,
                build_year,
                times,
                products_summary,
                products_table,
                supervision,
                sampling,
                procedure,
                conclusion
            FROM vessel_grain_sampling_reports
            WHERE id = %s
        """, (report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Grain sampling report not found"
            )

        return {
            "success": True,
            "data": report
        }

    finally:
        cur.close()


# ============================================================
# UPDATE — FULL UPDATE (PUT)
# ============================================================
@router.put("/{report_id}")
def update_vessel_grain_sampling_report(
    report_id: int,
    payload: dict,
    conn=Depends(get_db)
):
    cur = conn.cursor()

    try:
        payload["id"] = report_id

        cur.execute("""
            UPDATE vessel_grain_sampling_reports
            SET
                cert_no = %(cert_no)s,
                place_date = %(place_date)s,
                purpose = %(purpose)s,
                requested_by = %(requested_by)s,
                arrival_info = %(arrival_info)s,
                inspection_info = %(inspection_info)s,
                captain = %(captain)s,
                chief_officer = %(chief_officer)s,
                vessel_name = %(vessel_name)s,
                flag_port = %(flag_port)s,
                grt = %(grt)s,
                nrt = %(nrt)s,
                imo = %(imo)s,
                build_year = %(build_year)s,
                times = %(times)s,
                products_summary = %(products_summary)s,
                products_table = %(products_table)s,
                supervision = %(supervision)s,
                sampling = %(sampling)s,
                procedure = %(procedure)s,
                conclusion = %(conclusion)s,
                updated_at = NOW()
            WHERE id = %(id)s
        """)

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Grain sampling report not found"
            )

        conn.commit()

        return {
            "success": True,
            "id": report_id
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating grain sampling report: {str(e)}"
        )

    finally:
        cur.close()
