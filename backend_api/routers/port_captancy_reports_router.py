from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db

from services.port_captancy_word_service import (
    PortCaptancyWordService
)

from services.port_captancy_presentation_service import (
    PortCaptancyPresentationService
)


router = APIRouter(
    prefix="/port-captancy-reports",
    tags=["Port Captancy Reports"]
)


# =========================================================
# WORD SERVICE
# =========================================================

word_service = PortCaptancyWordService()
presentation_service = PortCaptancyPresentationService()

# =========================================================
# TABLE / ALLOWED FIELDS
# =========================================================

TABLE_NAME = "port_captancy_reports"

BASE_FIELDS = [
    "report_number",
    "continent",
    "country",
    "port",
    "operation",
    "report_type",
    "vessel",
    "requested_by",
    "arrival_date",
    "arrival_hour",
    "arrival_minute",
    "inspection_date",
    "inspection_hour",
    "inspection_minute",
    "master",
    "chief",
    "flag",
    "grt",
    "nrt",
    "imo",
    "year_built",
    "ts_date_0",
    "ts_hour_0",
    "ts_min_0",
    "ts_date_1",
    "ts_hour_1",
    "ts_min_1",
    "ts_date_2",
    "ts_hour_2",
    "ts_min_2",
    "ts_date_3",
    "ts_hour_3",
    "ts_min_3",
    "ts_date_4",
    "ts_hour_4",
    "ts_min_4",
    "link_picture",
]

DYNAMIC_FIELDS = []

for i in range(1, 16):
    DYNAMIC_FIELDS.append(f"operation_summary_{i}")

for i in range(1, 16):
    DYNAMIC_FIELDS.append(f"remarks_{i}")

for i in range(1, 16):
    DYNAMIC_FIELDS.append(f"conclusion_{i}")

ALLOWED_FIELDS = BASE_FIELDS + DYNAMIC_FIELDS


# =========================================================
# HELPERS
# =========================================================

def _clean_payload(payload: dict) -> dict:

    payload = payload or {}
    clean = {}

    for field in ALLOWED_FIELDS:
        clean[field] = payload.get(field)

    return clean


def _resolve_status_for_update(payload: dict, current_status: str | None) -> str | None:

    action = (
        payload.get("action")
        or payload.get("review_action")
        or payload.get("decision")
        or payload.get("approval_action")
        or payload.get("status_action")
        or ""
    )

    action = str(action).strip().lower()

    if action == "approve":
        return "Approved"

    if action == "reject":
        return "Rejected"

    return current_status


# =========================================================
# POST - CREATE
# =========================================================

@router.post("")
def create_port_captancy_report(payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}
        clean = _clean_payload(payload)

        report_number = clean.get("report_number")

        if not report_number:
            raise HTTPException(
                status_code=400,
                detail="report_number is required."
            )

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                f"""
                SELECT id
                FROM {TABLE_NAME}
                WHERE report_number = %s
                """,
                (report_number,)
            )
            existing = cur.fetchone()

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=f"Report {report_number} already exists."
                )

            clean["created_at"] = datetime.utcnow()
            clean["updated_at"] = datetime.utcnow()
            clean["status"] = "Pending for review"

            columns = list(clean.keys())
            values = [clean[col] for col in columns]
            placeholders = ", ".join(["%s"] * len(columns))
            columns_sql = ", ".join(columns)

            cur.execute(
                f"""
                INSERT INTO {TABLE_NAME} ({columns_sql})
                VALUES ({placeholders})
                RETURNING *
                """,
                values
            )

            created = cur.fetchone()
            conn.commit()

            return {
                "success": True,
                "message": "Port Captancy report created successfully.",
                "data": created
            }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# PUT - UPDATE
# =========================================================

@router.put("/{report_number}")
def update_port_captancy_report(report_number: str, payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                f"""
                SELECT *
                FROM {TABLE_NAME}
                WHERE report_number = %s
                """,
                (report_number,)
            )
            existing = cur.fetchone()

            if not existing:
                raise HTTPException(
                    status_code=404,
                    detail=f"Report {report_number} not found."
                )

            clean = _clean_payload(payload)

            new_status = _resolve_status_for_update(payload, existing.get("status"))

            set_parts = []
            values = []

            for field in ALLOWED_FIELDS:

                if field == "report_number":
                    continue

                set_parts.append(f"{field} = %s")
                values.append(clean.get(field))

            set_parts.append("updated_at = %s")
            values.append(datetime.utcnow())

            set_parts.append("status = %s")
            values.append(new_status)

            values.append(report_number)

            set_sql = ", ".join(set_parts)

            cur.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET {set_sql}
                WHERE report_number = %s
                RETURNING *
                """,
                values
            )

            updated = cur.fetchone()
            conn.commit()

            return {
                "success": True,
                "message": "Port Captancy report updated successfully.",
                "data": updated
            }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GET BY REPORT NUMBER
# =========================================================

@router.get("/{report_number}")
def get_port_captancy_report(report_number: str, conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                f"""
                SELECT *
                FROM {TABLE_NAME}
                WHERE report_number = %s
                """,
                (report_number,)
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Report {report_number} not found."
                )

            return {
                "success": True,
                "data": row
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GET ALL
# =========================================================

@router.get("")
def get_all_port_captancy_reports(conn=Depends(get_db)):

    try:

        with conn.cursor(cursor_factory=RealDictCursor) as cur:

            cur.execute(
                f"""
                SELECT
                    id,
                    report_number,
                    vessel,
                    port,
                    country,
                    arrival_date,
                    status
                FROM {TABLE_NAME}
                ORDER BY id DESC
                """
            )

            rows = cur.fetchall()

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
# WORD EXPORT
# =========================================================

@router.get("/{record_id}/word")
def generate_port_captancy_word(record_id: int, conn=Depends(get_db)):

    try:

        file_path = word_service.generate_word_by_id(
            conn,
            record_id
        )

        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="port_captancy_report.docx"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================================================
# GENERATE PRESENTATION PDF
# =========================================================

@router.get("/presentation/{record_id}")
def generate_port_captancy_presentation(record_id: int, conn=Depends(get_db)):

    try:

        file_path = presentation_service.generate_pdf_by_id(
            conn,
            record_id
        )

        if not file_path:

            raise HTTPException(
                status_code=404,
                detail="Presentation not generated"
            )

        import os

        return FileResponse(
            file_path,
            filename=os.path.basename(file_path),
            media_type="application/pdf"
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


