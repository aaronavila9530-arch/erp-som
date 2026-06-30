import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db


router = APIRouter(prefix="/logra-reports", tags=["LOGRA Reports"])


DEFAULT_QUESTIONS = {
    "capitanes": [
        "Condicion operativa observada durante la reunion",
        "Riesgos o restricciones comunicadas por capitania",
        "Acciones acordadas y responsables",
    ],
    "draga": [
        "Estado de avance de dragado informado",
        "Limitaciones operativas o climaticas",
        "Coordinaciones requeridas con terminal o autoridad",
    ],
    "naviera": [
        "Expectativas operativas de la naviera",
        "Riesgos comerciales u operativos levantados",
        "Compromisos y siguientes pasos",
    ],
}


def _ensure_table(db):
    with db.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS logra_reports (
                id SERIAL PRIMARY KEY,
                category VARCHAR(40) NOT NULL,
                meeting_date DATE NOT NULL,
                meeting_time TIME NOT NULL,
                location TEXT,
                subject TEXT,
                attendees JSONB NOT NULL DEFAULT '[]'::jsonb,
                questions JSONB NOT NULL DEFAULT '[]'::jsonb,
                status VARCHAR(30) NOT NULL DEFAULT 'Pending',
                created_by VARCHAR(120),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_logra_reports_category ON logra_reports(category);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_logra_reports_status ON logra_reports(status);"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_logra_reports_meeting_date ON logra_reports(meeting_date);"
        )
    db.commit()


def _json_value(value, fallback):
    if value in (None, ""):
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return fallback
    return value


def _normalize_category(value):
    category = (value or "").strip().lower()
    if category not in DEFAULT_QUESTIONS:
        raise HTTPException(status_code=400, detail="Invalid LOGRA category")
    return category


def _normalize_payload(payload):
    category = _normalize_category(payload.get("category"))
    questions = _json_value(payload.get("questions"), [])
    attendees = _json_value(payload.get("attendees"), [])

    if not isinstance(questions, list):
        questions = []
    if not isinstance(attendees, list):
        attendees = []

    meeting_date = payload.get("meeting_date")
    meeting_time = payload.get("meeting_time")
    if not meeting_date:
        raise HTTPException(status_code=400, detail="Meeting date is required")
    if not meeting_time:
        raise HTTPException(status_code=400, detail="Meeting time is required")

    return {
        "category": category,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "location": payload.get("location") or "",
        "subject": payload.get("subject") or "",
        "attendees": attendees,
        "questions": questions,
        "status": payload.get("status") or "Pending",
        "created_by": payload.get("created_by") or "",
    }


def _row_to_dict(row):
    data = dict(row)
    data["attendees"] = _json_value(data.get("attendees"), [])
    data["questions"] = _json_value(data.get("questions"), [])
    for key in ("meeting_date", "meeting_time", "created_at", "updated_at"):
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


@router.get("/defaults")
def get_logra_defaults():
    return {"categories": list(DEFAULT_QUESTIONS.keys()), "questions": DEFAULT_QUESTIONS}


@router.get("/")
def list_logra_reports(db=Depends(get_db)):
    _ensure_table(db)
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, category, meeting_date, meeting_time, location, subject,
                   status, created_by, created_at, updated_at
            FROM logra_reports
            ORDER BY meeting_date DESC, meeting_time DESC, id DESC;
            """
        )
        rows = [_row_to_dict(row) for row in cur.fetchall()]
    return {"data": rows}


@router.get("/{record_id}")
def get_logra_report(record_id: int, db=Depends(get_db)):
    _ensure_table(db)
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM logra_reports WHERE id = %s;", (record_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="LOGRA report not found")
    return _row_to_dict(row)


@router.post("/")
def create_logra_report(payload: dict, db=Depends(get_db)):
    _ensure_table(db)
    data = _normalize_payload(payload)
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            INSERT INTO logra_reports (
                category, meeting_date, meeting_time, location, subject,
                attendees, questions, status, created_by
            )
            VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s)
            RETURNING *;
            """,
            (
                data["category"],
                data["meeting_date"],
                data["meeting_time"],
                data["location"],
                data["subject"],
                json.dumps(data["attendees"], ensure_ascii=False),
                json.dumps(data["questions"], ensure_ascii=False),
                data["status"],
                data["created_by"],
            ),
        )
        row = cur.fetchone()
    db.commit()
    return _row_to_dict(row)


@router.put("/{record_id}")
def update_logra_report(record_id: int, payload: dict, db=Depends(get_db)):
    _ensure_table(db)
    data = _normalize_payload(payload)
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            UPDATE logra_reports
            SET category=%s,
                meeting_date=%s,
                meeting_time=%s,
                location=%s,
                subject=%s,
                attendees=%s::jsonb,
                questions=%s::jsonb,
                status=%s,
                updated_at=NOW()
            WHERE id=%s
            RETURNING *;
            """,
            (
                data["category"],
                data["meeting_date"],
                data["meeting_time"],
                data["location"],
                data["subject"],
                json.dumps(data["attendees"], ensure_ascii=False),
                json.dumps(data["questions"], ensure_ascii=False),
                data["status"],
                record_id,
            ),
        )
        row = cur.fetchone()
    if not row:
        db.rollback()
        raise HTTPException(status_code=404, detail="LOGRA report not found")
    db.commit()
    return _row_to_dict(row)

