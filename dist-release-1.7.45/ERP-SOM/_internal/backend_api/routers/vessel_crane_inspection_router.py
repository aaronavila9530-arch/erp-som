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


FORM_TEXT_COLUMNS = {
    "vessel", "intro_text", "intro_inspection_date", "intro_inspection_hour",
    "intro_inspection_minute", "gear_condition", "gear_wires", "gear_sheaves",
    "gear_operability", "gear_start_date", "gear_start_hour", "gear_start_minute",
    "gear_end_date", "gear_end_hour", "gear_end_minute", "link_picture",
}
for _item in CHECKLIST_ITEMS:
    FORM_TEXT_COLUMNS.update({
        f"{_item}_status", f"{_item}_status1", f"{_item}_status2", f"{_item}_status3"
    })
for _crane in range(1, 5):
    FORM_TEXT_COLUMNS.update({f"crane{_crane}_remark_{i}" for i in range(1, 11)})
FORM_TEXT_COLUMNS.update({f"grabs_condition_{i}" for i in range(1, 11)})

FORM_BOOLEAN_COLUMNS = {f"{item}_done" for item in CHECKLIST_ITEMS}
FORM_ALLOWED_COLUMNS = {
    "report_number", "client", "port", "country", "report_date", "grt", "nrt",
    "status", *FORM_TEXT_COLUMNS, *FORM_BOOLEAN_COLUMNS,
    *{f"recommendation_{i}" for i in range(1, 11)},
    *{f"conclusion_{i}" for i in range(1, 21)},
}


def _ensure_form_schema(conn):
    """Añade de forma segura las columnas utilizadas por el formulario vigente."""
    cur = conn.cursor()
    try:
        for column in sorted(FORM_TEXT_COLUMNS):
            cur.execute(
                f'ALTER TABLE vessel_crane_inspection_reports ADD COLUMN IF NOT EXISTS "{column}" TEXT'
            )
        for column in sorted(FORM_BOOLEAN_COLUMNS):
            cur.execute(
                f'ALTER TABLE vessel_crane_inspection_reports ADD COLUMN IF NOT EXISTS "{column}" BOOLEAN DEFAULT FALSE'
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def _validate_payload_columns(payload):
    unknown = sorted(set(payload) - FORM_ALLOWED_COLUMNS - {
        "approve", "recommendations", "grabs_condition", "conclusion",
        "crane1_remarks", "crane2_remarks", "crane3_remarks", "crane4_remarks",
    })
    if unknown:
        raise HTTPException(status_code=400, detail=f"Campos Crane no soportados: {', '.join(unknown)}")


def _clean(value):
    """
    Normaliza valores para evitar problemas JSON.
    """
    if value in ("", "None", None):
        return None
    return value


def _expand_dynamic_bullets(payload: dict):

    # ---------------------------------------------------------
    # REMARKS BY CRANE
    # ---------------------------------------------------------

    for crane in range(1, 5):

        source_key = f"crane{crane}_remarks"
        if source_key not in payload:
            continue

        remarks = payload.get(source_key) or []

        if not isinstance(remarks, list):
            remarks = []

        for i in range(10):

            value = remarks[i] if i < len(remarks) else None
            payload[f"crane{crane}_remark_{i+1}"] = _clean(value)

    # ---------------------------------------------------------
    # RECOMMENDATIONS
    # ---------------------------------------------------------

    recs = payload.get("recommendations") or []

    if "recommendations" not in payload:
        recs = None
    elif not isinstance(recs, list):
        recs = []

    for i in range(10) if recs is not None else ():

        value = recs[i] if i < len(recs) else None
        payload[f"recommendation_{i+1}"] = _clean(value)

    # ---------------------------------------------------------
    # GRABS CONDITION
    # ---------------------------------------------------------

    grabs = payload.get("grabs_condition") or []

    if "grabs_condition" not in payload:
        grabs = None
    elif not isinstance(grabs, list):
        grabs = []

    for i in range(10) if grabs is not None else ():

        value = grabs[i] if i < len(grabs) else None
        payload[f"grabs_condition_{i+1}"] = _clean(value)

    # ---------------------------------------------------------
    # CONCLUSION
    # ---------------------------------------------------------

    conclusions = payload.get("conclusion") or []

    if "conclusion" not in payload:
        conclusions = None
    elif not isinstance(conclusions, list):
        conclusions = []

    for i in range(20) if conclusions is not None else ():

        value = conclusions[i] if i < len(conclusions) else None
        payload[f"conclusion_{i+1}"] = _clean(value)


# ============================================================
# CREATE
# POST /vessel-crane-inspection
# ============================================================

@router.post("")
def create_crane_inspection(payload: dict, conn=Depends(get_db)):

    try:

        payload = payload or {}
        _validate_payload_columns(payload)
        _ensure_form_schema(conn)

        # ----------------------------------------------------
        # EXPAND BULLETS (recommendation_1, crane1_remark_1...)
        # ----------------------------------------------------

        _expand_dynamic_bullets(payload)

        # ----------------------------------------------------
        # REMOVE ORIGINAL LISTS (Postgres cannot insert lists)
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
        # FORCE STATUS (CLIENT CANNOT OVERRIDE)
        # ----------------------------------------------------

        payload.pop("status", None)
        payload["status"] = "Pending for review"

        # ----------------------------------------------------
        # META
        # ----------------------------------------------------

        payload["created_at"] = datetime.utcnow()
        payload["updated_at"] = datetime.utcnow()

        # ----------------------------------------------------
        # BUILD INSERT
        # ----------------------------------------------------

        columns = []
        values = []
        placeholders = []

        for k, v in payload.items():

            columns.append(k)
            values.append(v)
            placeholders.append("%s")

        query = f"""
        INSERT INTO vessel_crane_inspection_reports
        ({",".join(columns)})
        VALUES ({",".join(placeholders)})
        RETURNING id
        """

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(query, values)

        row = cur.fetchone()

        conn.commit()

        return {
            "success": True,
            "id": row["id"]
        }

    except HTTPException:

        conn.rollback()
        raise

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
        _validate_payload_columns(payload)
        _ensure_form_schema(conn)

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

    except HTTPException:

        conn.rollback()
        raise

    except Exception as e:

        conn.rollback()

        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# GET LIST
# GET /vessel-crane-inspection
# ============================================================

@router.get("")
def get_crane_inspections(conn=Depends(get_db)):

    try:

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

        rows = cur.fetchall() or []

        data = []

        for row in rows:

            record = dict(row)

            for k, v in record.items():
                if v is None:
                    record[k] = None

            data.append(record)

        return {
            "success": True,
            "data": data
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============================================================
# GET ONE
# GET /vessel-crane-inspection/{id}
# ============================================================

@router.get("/{report_id}")
def get_crane_inspection(report_id: int, conn=Depends(get_db)):

    try:

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT *
            FROM vessel_crane_inspection_reports
            WHERE id = %s
            """,
            (report_id,)
        )

        row = cur.fetchone()

        if not row:

            raise HTTPException(
                status_code=404,
                detail="Crane inspection report not found."
            )

        record = dict(row)

        # ====================================================
        # SAFE NORMALIZATION (JSON SAFE)
        # ====================================================

        from decimal import Decimal
        from datetime import datetime, date

        for key, value in record.items():

            # NULL stays NULL
            if value is None:
                record[key] = None
                continue

            # Decimal → float
            if isinstance(value, Decimal):
                record[key] = float(value)
                continue

            # datetime → ISO
            if isinstance(value, datetime):
                record[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                continue

            # date → ISO
            if isinstance(value, date):
                record[key] = value.strftime("%Y-%m-%d")
                continue

            # fallback → string
            if not isinstance(value, (str, int, float, bool)):
                record[key] = str(value)

        # ====================================================
        # RESPONSE
        # ====================================================

        return {
            "success": True,
            "data": record
        }

    except HTTPException:
        raise

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
