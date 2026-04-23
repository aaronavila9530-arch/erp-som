from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime
from fastapi.responses import FileResponse

from database import get_db

from services.vessel_condition_survey_word_service import (
    VesselConditionSurveyWordService
)

from services.vessel_condition_survey_presentation_service import (
    VesselConditionSurveyPresentationService
)

router = APIRouter(
    prefix="/vessel-condition-surveys",
    tags=["Vessel Condition Surveys"]
)

word_service = VesselConditionSurveyWordService()
presentation_service = VesselConditionSurveyPresentationService()

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

# =========================================================
# GET
# =========================================================

@router.get("/{report_number}")
def get_vessel_condition_survey(report_number: str, conn=Depends(get_db)):

    try:

        # -------------------------------------------------
        # VALIDACIÓN BÁSICA
        # -------------------------------------------------
        report_number = str(report_number or "").strip()

        if not report_number:
            raise HTTPException(
                status_code=400,
                detail="Report number is required"
            )

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM vessel_condition_surveys
            WHERE report_number = %s
            LIMIT 1
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

        # -------------------------------------------------
        # RECONSTRUIR BULLETS DINÁMICOS
        # -------------------------------------------------
        try:
            row = _collapse_dynamic_bullets(row)
        except Exception:
            # Evita que un problema en bullets rompa el GET completo
            pass

        return {
            "success": True,
            "data": row
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving vessel condition survey: {str(e)}"
        )


# =========================================================
# GET BY ID (PARA POPUPS)
# =========================================================

@router.get("/id/{record_id}")
def get_vessel_condition_survey_by_id(record_id: int, conn=Depends(get_db)):

    try:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM vessel_condition_surveys
            WHERE id = %s
            """,
            (record_id,)
        )

        row = cur.fetchone()

        if not row:

            return {
                "success": False,
                "error": "Report not found"
            }

        row = dict(row)

        try:
            row = _collapse_dynamic_bullets(row)
        except Exception:
            # evita crash si faltan columnas
            pass

        return {
            "success": True,
            "data": row
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


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


# =========================================================
# GENERATE WORD REPORT
# =========================================================

@router.get("/word/{record_id}")
def generate_vessel_condition_word(record_id: int, conn=Depends(get_db)):

    try:

        file_path = word_service.generate_word_by_id(conn, record_id)

        if not file_path:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        return FileResponse(
            file_path,
            filename=file_path.split("\\")[-1],
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/by-id/{report_id}")
def get_vessel_condition_by_id(report_id: int, conn=Depends(get_db)):

    try:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM vessel_condition_surveys
            WHERE id = %s
            """,
            (report_id,)
        )

        row = cur.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        record = dict(row)

        return {
            "success": True,
            "data": record
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# GENERATE PRESENTATION PDF
# =========================================================

@router.get("/presentation/{record_id}")
def generate_vessel_condition_presentation(record_id: int, conn=Depends(get_db)):

    try:

        file_path = presentation_service.generate_pdf_by_id(conn, record_id)

        if not file_path:
            raise HTTPException(
                status_code=404,
                detail="Presentation not generated"
            )

        return FileResponse(
            file_path,
            filename=file_path.split("\\")[-1],
            media_type="application/pdf"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )