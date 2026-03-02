from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import Dict, Any
import os

from fastapi.responses import FileResponse
from services.vessel_cargo_condition_word_service import (
    VesselCargoConditionWordService
)

from database import get_db

router = APIRouter(
    prefix="/vessel-cargo-condition-surveys",
    tags=["Vessel Cargo Condition Surveys"]
)

TABLE_NAME = "vessel_cargo_condition_surveys"


# =========================================================
# UTIL
# =========================================================
def normalize_status(incoming_status: str | None) -> str:
    if not incoming_status:
        return "Pending for review"

    s = incoming_status.strip().lower()

    if s == "approved":
        return "Approved"

    if s == "rejected":
        return "Rejected"

    return "Pending for review"


def build_full_column_list():
    """
    Ordered exactly as DB structure (except id/created_at/updated_at)
    """

    base_columns = [
        "report_number",
        "continent",
        "operation",
        "service_start_date",
        "vessel",
        "port",
        "country",
        "requested_by",
        "master",
        "chief_officer",
        "arrival_date",
        "arrival_hour",
        "arrival_minute",
        "inspection_date",
        "inspection_hour",
        "inspection_minute",
    ]

    # Time sheet 0..7
    for i in range(8):
        base_columns.extend([
            f"time_{i}_date",
            f"time_{i}_hour",
            f"time_{i}_minute"
        ])

    # Bullets
    sections = ["narrative", "findings", "remarks", "conclusion"]

    for sec in sections:
        for n in range(1, 11):
            base_columns.append(f"{sec}_{n}")

    # Status + review metadata
    base_columns.extend([
        "status",
        "sent_to_review_at",
        "link_picture",
        "cargo_type"  # <-- NUEVO (alineado al final según DB)
    ])

    return base_columns


ALL_COLUMNS = build_full_column_list()


# =========================================================
# POST
# =========================================================
@router.post("/")
def create_vessel_cargo_condition(payload: Dict[str, Any], conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        payload = payload or {}

        # STATUS LOGIC
        final_status = normalize_status(payload.get("status"))
        payload["status"] = final_status

        if final_status in ["Pending for review", "Approved", "Rejected"]:
            payload["sent_to_review_at"] = datetime.utcnow()

        # Ensure all columns exist
        for col in ALL_COLUMNS:
            payload.setdefault(col, None)

        columns_sql = ", ".join(ALL_COLUMNS)
        values_sql = ", ".join(["%s"] * len(ALL_COLUMNS))

        insert_sql = f"""
            INSERT INTO {TABLE_NAME} ({columns_sql})
            VALUES ({values_sql})
            RETURNING id
        """

        cur.execute(insert_sql, [payload[col] for col in ALL_COLUMNS])
        new_id = cur.fetchone()[0]

        conn.commit()

        return {"success": True, "id": new_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GET ALL
# =========================================================
@router.get("/")
def get_all_vessel_cargo_condition(conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        cur.execute(f"""
            SELECT *
            FROM {TABLE_NAME}
            ORDER BY created_at DESC
        """)

        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        result = [dict(zip(columns, row)) for row in rows]

        return {"success": True, "data": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# GENERATE WORD
# GET /vessel-cargo-condition-surveys/word/{id}
# =========================================================
@router.get("/word/{record_id}")
def generate_cargo_condition_word(
    record_id: int,
    conn=Depends(get_db)
):

    try:
        service = VesselCargoConditionWordService()

        file_path = service.generate_word_by_id(
            conn,
            record_id
        )

        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# GET BY ID
# =========================================================
@router.get("/{record_id}")
def get_vessel_cargo_condition(record_id: int, conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        cur.execute(f"""
            SELECT *
            FROM {TABLE_NAME}
            WHERE id = %s
        """, (record_id,))

        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Not found")

        columns = [desc[0] for desc in cur.description]

        return {"success": True, "data": dict(zip(columns, row))}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# PUT (SAFE PARTIAL UPDATE)
# =========================================================
@router.put("/{record_id}")
def update_vessel_cargo_condition(
    record_id: int,
    payload: Dict[str, Any],
    conn=Depends(get_db)
):

    cur = conn.cursor()

    try:
        payload = payload or {}

        if not payload:
            raise HTTPException(status_code=400, detail="Empty payload")

        # --------------------------------------------
        # STATUS UPDATE LOGIC
        # --------------------------------------------
        if "status" in payload:
            final_status = normalize_status(payload.get("status"))
            payload["status"] = final_status

            if final_status in ["Approved", "Rejected"]:
                payload["sent_to_review_at"] = datetime.utcnow()

        # --------------------------------------------
        # ONLY allow updating known columns (anti-bug)
        # --------------------------------------------
        allowed = set(ALL_COLUMNS)
        safe_payload = {k: v for k, v in payload.items() if k in allowed}

        if not safe_payload:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        set_clause = ", ".join([f"{k}=%s" for k in safe_payload.keys()])
        values = list(safe_payload.values())

        update_sql = f"""
            UPDATE {TABLE_NAME}
            SET {set_clause},
                updated_at = NOW()
            WHERE id = %s
        """

        values.append(record_id)

        cur.execute(update_sql, values)

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found")

        conn.commit()

        return {"success": True}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))