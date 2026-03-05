from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db


router = APIRouter(
    prefix="/vessel-crane-inspection",
    tags=["Vessel Crane Inspection"]
)


# ============================================================
# HELPERS
# ============================================================

CHECKLIST_ITEMS = [
    "crane_access",
    "crane_machinery_space",
    "crane_operator_cabin",
    "crane_jib_head_sheaves",
    "hoisting_wire_end_pin",
    "luffing_wire_end_pin",
    "crane_wire_visual",
    "crane_housing_sheaves",
    "luffing_center_sheave",
    "cargo_block_sheave",
    "slack_hoisting_limit",
    "crane_jib_angle_limits",
    "crane_jib_angle_indicator",
    "crane_hoisting_limits",
    "pedestal_light_project"
]


def _expand_dynamic_bullets(payload: dict):

    # ---------------------------------------------------------
    # REMARKS BY CRANE
    # ---------------------------------------------------------

    for crane in range(1, 5):

        remarks = payload.get(f"crane{crane}_remarks") or []

        for i in range(10):
            payload[f"crane{crane}_remark_{i+1}"] = remarks[i] if i < len(remarks) else None


    # ---------------------------------------------------------
    # RECOMMENDATIONS
    # ---------------------------------------------------------

    recs = payload.get("recommendations") or []

    for i in range(10):
        payload[f"recommendation_{i+1}"] = recs[i] if i < len(recs) else None


    # ---------------------------------------------------------
    # GRABS CONDITION
    # ---------------------------------------------------------

    grabs = payload.get("grabs_condition") or []

    for i in range(10):
        payload[f"grabs_condition_{i+1}"] = grabs[i] if i < len(grabs) else None


    # ---------------------------------------------------------
    # CONCLUSION
    # ---------------------------------------------------------

    conclusions = payload.get("conclusion") or []

    for i in range(20):
        payload[f"conclusion_{i+1}"] = conclusions[i] if i < len(conclusions) else None


@router.post("")
def create_crane_inspection(payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        # ----------------------------------------------------
        # EXPAND BULLETS
        # ----------------------------------------------------

        _expand_dynamic_bullets(payload)

        # ----------------------------------------------------
        # REMOVE ORIGINAL LISTS
        # ----------------------------------------------------

        for key in [
            "recommendations",
            "grabs_condition",
            "conclusion",
            "crane1_remarks",
            "crane2_remarks",
            "crane3_remarks",
            "crane4_remarks"
        ]:
            payload.pop(key, None)

        # ----------------------------------------------------
        # CLEAN EMPTY STRINGS
        # ----------------------------------------------------

        for k, v in list(payload.items()):

            if v == "":
                payload[k] = None

        # ----------------------------------------------------
        # META
        # ----------------------------------------------------

        payload["status"] = "pending for review"
        payload["created_at"] = datetime.utcnow()
        payload["updated_at"] = datetime.utcnow()

        # ----------------------------------------------------
        # VALID TABLE COLUMNS
        # ----------------------------------------------------

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'vessel_crane_inspection_reports'
        """)

        valid_columns = {r["column_name"] for r in cur.fetchall()}

        # ----------------------------------------------------
        # FILTER PAYLOAD
        # ----------------------------------------------------

        columns = []
        values = []
        placeholders = []

        for k, v in payload.items():

            if k not in valid_columns:
                continue

            columns.append(k)
            values.append(v)
            placeholders.append("%s")

        # ----------------------------------------------------
        # INSERT
        # ----------------------------------------------------

        query = f"""
        INSERT INTO vessel_crane_inspection_reports
        ({",".join(columns)})
        VALUES ({",".join(placeholders)})
        RETURNING id
        """

        cur.execute(query, values)

        row = cur.fetchone()

        conn.commit()

        return {
            "success": True,
            "id": row["id"]
        }

    except Exception as e:

        conn.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# UPDATE
# PUT /vessel-crane-inspection/{id}
# ============================================================

@router.put("/{report_id}")
def update_crane_inspection(report_id: int, payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}

        _expand_dynamic_bullets(payload)

        payload["updated_at"] = datetime.utcnow()

        # -----------------------------------------------------
        # STATUS APPROVAL
        # -----------------------------------------------------

        if payload.get("approve") is True:
            payload["status"] = "approved"

        set_parts = []
        values = []

        for k, v in payload.items():

            if k == "approve":
                continue

            set_parts.append(f"{k}=%s")
            values.append(v)

        values.append(report_id)

        query = f"""
        UPDATE vessel_crane_inspection_reports
        SET {",".join(set_parts)}
        WHERE id=%s
        """

        cur = conn.cursor()

        cur.execute(query, values)

        conn.commit()

        return {"success": True}

    except Exception as e:

        conn.rollback()

        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GET LIST
# GET /vessel-crane-inspection
# ============================================================

@router.get("")
def get_crane_inspections(conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            id,
            report_number,
            vessel,
            port,
            country,
            report_date,
            status,
            created_at
        FROM vessel_crane_inspection_reports
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    return {
        "success": True,
        "data": rows
    }


# ============================================================
# GET ONE
# GET /vessel-crane-inspection/{id}
# ============================================================

@router.get("/{report_id}")
def get_crane_inspection(report_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT *
        FROM vessel_crane_inspection_reports
        WHERE id=%s
        """,
        (report_id,)
    )

    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "success": True,
        "data": row
    }