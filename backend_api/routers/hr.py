from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import date

from database import get_db
from security.rbac import require_permission

router = APIRouter(
    prefix="/hr",
    tags=["HHRR"]
)

# ============================================================
# CREATE EVENT
# ACTION: create
# ============================================================
@router.post(
    "/events",
    dependencies=[Depends(require_permission("hhrre", "create"))]
)
def create_hr_event(payload: dict, conn=Depends(get_db)):

    required = ["empleado_id", "event_type", "event_date", "payload"]
    if not all(k in payload for k in required):
        raise HTTPException(400, "Datos incompletos")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        INSERT INTO hr_events (
            empleado_id,
            event_type,
            event_date,
            period_year,
            period_month,
            status,
            payload,
            created_by
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING *
    """, (
        payload["empleado_id"],
        payload["event_type"],
        payload["event_date"],
        payload.get("period_year"),
        payload.get("period_month"),
        payload.get("status", "PENDING"),
        payload["payload"],
        payload.get("created_by")
    ))

    row = cur.fetchone()
    conn.commit()

    return row


# ============================================================
# LIST EVENTS
# ACTION: view
# ============================================================
@router.get(
    "/events",
    dependencies=[Depends(require_permission("hhrre", "view"))]
)
def list_hr_events(
    event_type: str | None = None,
    status: str | None = None,
    empleado_id: int | None = None,
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT * FROM hr_events WHERE 1=1"
    params = []

    if event_type:
        query += " AND event_type = %s"
        params.append(event_type)

    if status:
        query += " AND status = %s"
        params.append(status)

    if empleado_id:
        query += " AND empleado_id = %s"
        params.append(empleado_id)

    query += " ORDER BY created_at DESC"

    cur.execute(query, params)
    return cur.fetchall()


# ============================================================
# APPROVE / REJECT / PAY / CLOSE EVENT
# ACTION: approve
# ============================================================
@router.post(
    "/events/{event_id}/status",
    dependencies=[Depends(require_permission("hhrre", "approve"))]
)
def update_event_status(
    event_id: int,
    payload: dict,
    conn=Depends(get_db)
):

    status = payload.get("status")
    approved_by = payload.get("approved_by")

    if status not in ("APPROVED", "REJECTED", "PAID", "CLOSED"):
        raise HTTPException(400, "Estado inválido")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        UPDATE hr_events
        SET status = %s,
            approved_by = %s,
            approved_at = now()
        WHERE id = %s
        RETURNING *
    """, (status, approved_by, event_id))

    row = cur.fetchone()
    conn.commit()

    if not row:
        raise HTTPException(404, "Evento no encontrado")

    return row
