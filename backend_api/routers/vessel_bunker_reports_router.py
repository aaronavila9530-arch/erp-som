from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from database import get_db
from datetime import datetime

router = APIRouter(
    prefix="/vessel-bunker-reports",
    tags=["Vessel Bunker Reports"]
)

# =========================================================
# CREATE
# =========================================================
@router.post("/")
def create_vessel_bunker_report(payload: dict, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        payload = payload or {}

        # status default
        payload.setdefault("status", "Pending")

        # timestamps
        payload["created_at"] = datetime.utcnow()
        payload["updated_at"] = datetime.utcnow()

        columns = []
        values = []
        placeholders = []

        for key, value in payload.items():
            columns.append(key)
            values.append(value)
            placeholders.append("%s")

        query = f"""
            INSERT INTO vessel_bunker_reports
            ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
            RETURNING *
        """

        cur.execute(query, values)
        new_row = cur.fetchone()
        conn.commit()

        return {"success": True, "data": new_row}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# UPDATE
# =========================================================
@router.put("/{report_id}")
def update_vessel_bunker_report(report_id: int, payload: dict, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        payload = payload or {}

        # bloquear si Approved
        cur.execute(
            "SELECT status FROM vessel_bunker_reports WHERE id=%s",
            (report_id,)
        )
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Report not found")

        if row["status"] == "Approved":
            raise HTTPException(status_code=403, detail="Already approved")

        payload["updated_at"] = datetime.utcnow()

        set_clauses = []
        values = []

        for key, value in payload.items():
            set_clauses.append(f"{key} = %s")
            values.append(value)

        values.append(report_id)

        query = f"""
            UPDATE vessel_bunker_reports
            SET {", ".join(set_clauses)}
            WHERE id = %s
            RETURNING *
        """

        cur.execute(query, values)
        updated = cur.fetchone()
        conn.commit()

        return {"success": True, "data": updated}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# GET BY ID
# =========================================================
@router.get("/{report_id}")
def get_vessel_bunker_report(report_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM vessel_bunker_reports WHERE id=%s",
        (report_id,)
    )

    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"success": True, "data": row}


# =========================================================
# GET ALL
# =========================================================
@router.get("/")
def get_all_vessel_bunker_reports(conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM vessel_bunker_reports
        ORDER BY created_at DESC
    """)

    rows = cur.fetchall()

    return {"success": True, "data": rows}