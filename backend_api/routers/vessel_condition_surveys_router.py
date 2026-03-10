from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

router = APIRouter(
    prefix="/vessel-condition-surveys",
    tags=["Vessel Condition Surveys"]
)

# =========================================================
# HELPERS
# =========================================================

SECTIONS = [
    "narrative",
    "survey_findings",
    "remarks",
    "conclusion"
]

MAX_BULLETS = 20


def _expand_dynamic_bullets(payload: dict):
    """
    Convierte listas dinámicas del frontend en columnas planas:
    narrative -> narrative_1..20
    survey_findings -> survey_findings_1..20
    remarks -> remarks_1..20
    conclusion -> conclusion_1..20
    """

    for section in SECTIONS:

        bullets = payload.get(section)

        if bullets and isinstance(bullets, list):

            for i in range(1, MAX_BULLETS + 1):
                payload[f"{section}_{i}"] = None

            for idx, value in enumerate(bullets[:MAX_BULLETS], start=1):
                payload[f"{section}_{idx}"] = value

        payload.pop(section, None)


def _collapse_dynamic_bullets(row: dict):
    """
    Reconstruye listas dinámicas para el frontend.
    Excluye columnas NULL.
    """

    for section in SECTIONS:

        bullets = []

        for i in range(1, MAX_BULLETS + 1):

            val = row.get(f"{section}_{i}")

            if val:
                bullets.append(val)

        row[section] = bullets

    return row


# =========================================================
# POST
# CREATE
# =========================================================

@router.post("")
def create_vessel_condition_survey(payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        _expand_dynamic_bullets(payload)

        payload["created_at"] = datetime.utcnow()
        payload["updated_at"] = datetime.utcnow()

        # status SIEMPRE Pending for review en POST
        payload["status"] = "Pending for review"

        columns = []
        values = []
        params = []

        for k, v in payload.items():
            columns.append(k)
            values.append("%s")
            params.append(v)

        sql = f"""
        INSERT INTO vessel_condition_surveys
        ({",".join(columns)})
        VALUES ({",".join(values)})
        RETURNING report_number
        """

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)
        row = cur.fetchone()

        conn.commit()

        return {
            "success": True,
            "report_number": row["report_number"]
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# PUT
# UPDATE
# =========================================================

@router.put("/{report_number}")
def update_vessel_condition_survey(report_number: str, payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        _expand_dynamic_bullets(payload)

        payload["updated_at"] = datetime.utcnow()

        # status permitido solo si viene Approved o Rejected
        status = payload.get("status")

        if status not in ["Approved", "Rejected", None]:
            payload.pop("status", None)

        sets = []
        params = []

        for k, v in payload.items():
            sets.append(f"{k} = %s")
            params.append(v)

        params.append(report_number)

        sql = f"""
        UPDATE vessel_condition_surveys
        SET {",".join(sets)}
        WHERE report_number = %s
        RETURNING report_number
        """

        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params)

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        conn.commit()

        return {
            "success": True,
            "report_number": row["report_number"]
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GET
# =========================================================

@router.get("/{report_number}")
def get_vessel_condition_survey(report_number: str, conn=Depends(get_db)):

    try:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM vessel_condition_surveys
            WHERE report_number = %s
            """,
            (report_number,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        row = dict(row)

        # reconstruir bullets dinámicos
        row = _collapse_dynamic_bullets(row)

        return row

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



# =========================================================
# GET ALL
# =========================================================

@router.get("")
def get_all_vessel_condition_surveys(conn=Depends(get_db)):

    try:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT
                id,
                report_number,
                vessel,
                port,
                country,
                service_start_date,
                status
            FROM vessel_condition_surveys
            ORDER BY id DESC
        """)

        rows = cur.fetchall() or []

        return {
            "success": True,
            "data": rows
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )