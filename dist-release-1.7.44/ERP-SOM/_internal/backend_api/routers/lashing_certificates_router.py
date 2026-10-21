from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor
import psycopg2

from database import DATABASE_URL
from services.lashing_certificate_word_service import LashingCertificateWordService


# =========================================================
# DATABASE
# =========================================================

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


# =========================================================
# SERVICE
# =========================================================

word_service = LashingCertificateWordService()


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/lashing-certificates",
    tags=["Lashing Certificates"]
)


# =========================================================
# GET ALL
# =========================================================

@router.get("/")
def get_all_lashing_certificates():

    try:

        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM lashing_certificates
            ORDER BY id DESC
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return rows

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GET BY ID
# =========================================================

@router.get("/{record_id}")
def get_lashing_certificate(record_id: int):

    try:

        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM lashing_certificates
            WHERE id = %s
        """, (record_id,))

        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Record not found")

        return row

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# POST
# =========================================================

@router.post("/")
def create_lashing_certificate(payload: dict):

    conn = None
    cur = None

    try:

        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid payload format"
            )

        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            INSERT INTO lashing_certificates (

                report_no,
                customer,
                port,
                country,
                flat_rack_container,
                cargo_type,
                lashing_material,
                place,
                date,
                ratchet_quantity,
                where_carry_out,
                completion_date,
                status

            )
            VALUES (

                %(report_no)s,
                %(customer)s,
                %(port)s,
                %(country)s,
                %(flat_rack_container)s,
                %(cargo_type)s,
                %(lashing_material)s,
                %(place)s,
                %(date)s,
                %(ratchet_quantity)s,
                %(where_carry_out)s,
                %(completion_date)s,
                %(status)s

            )
            RETURNING id
        """, payload)

        result = cur.fetchone()

        if not result or "id" not in result:
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve inserted ID"
            )

        conn.commit()

        return {"id": result["id"]}

    except HTTPException:
        raise

    except Exception as e:

        if conn:
            conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if cur:
            cur.close()

        if conn:
            conn.close()


# =========================================================
# PUT UPDATE
# =========================================================

@router.put("/{record_id}")
def update_lashing_certificate(record_id: int, payload: dict):

    try:

        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        status = payload.get("status")

        if status == "Approve":
            payload["status"] = "Approved"

        elif status == "Reject":
            payload["status"] = "Rejected"

        cur.execute("""
            UPDATE lashing_certificates
            SET

                report_no = %(report_no)s,
                customer = %(customer)s,
                port = %(port)s,
                country = %(country)s,
                flat_rack_container = %(flat_rack_container)s,
                cargo_type = %(cargo_type)s,
                lashing_material = %(lashing_material)s,
                place = %(place)s,
                date = %(date)s,
                ratchet_quantity = %(ratchet_quantity)s,
                where_carry_out = %(where_carry_out)s,
                completion_date = %(completion_date)s,
                status = %(status)s

            WHERE id = %(id)s
        """, {**payload, "id": record_id})

        conn.commit()

        cur.close()
        conn.close()

        return {"message": "Record updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GENERATE WORD REPORT
# =========================================================

@router.get("/{record_id}/word")
def generate_lashing_certificate_word(record_id: int):

    try:

        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT *
            FROM lashing_certificates
            WHERE id=%s
            """,
            (record_id,)
        )

        data = cursor.fetchone()

        cursor.close()
        conn.close()

        if not data:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        return word_service.generate_word(data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GENERATE PDF REPORT
# =========================================================

@router.get("/{record_id}/pdf")
def generate_lashing_certificate_pdf(record_id: int):

    try:

        conn = get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(
            """
            SELECT *
            FROM lashing_certificates
            WHERE id=%s
            """,
            (record_id,)
        )

        data = cursor.fetchone()

        cursor.close()
        conn.close()

        if not data:

            raise HTTPException(
                status_code=404,
                detail="Record not found"
            )

        return word_service.generate_pdf(data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
