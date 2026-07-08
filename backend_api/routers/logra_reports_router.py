from datetime import datetime
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from psycopg2.extras import Json, RealDictCursor

from database import get_db


router = APIRouter(
    prefix="/logra-reports",
    tags=["LOGRA Reports"]
)

STORAGE_ROOT = Path("storage") / "logra"
MAX_AGENDA_ITEMS = 150
MAX_ATTACHMENTS_PER_QUESTION = 10


def _ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logra_reports (
                id SERIAL PRIMARY KEY,
                title TEXT,
                category TEXT DEFAULT 'ONG',
                meeting_date DATE DEFAULT CURRENT_DATE,
                meeting_time TEXT DEFAULT '00:00',
                meeting_start_time TEXT DEFAULT '',
                meeting_end_time TEXT DEFAULT '',
                meeting_location TEXT DEFAULT '',
                meeting_person TEXT DEFAULT '',
                status TEXT DEFAULT 'Pending',
                agenda_items JSONB NOT NULL DEFAULT '[]'::jsonb,
                agenda_notes TEXT DEFAULT '',
                created_by TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS title TEXT
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'ONG'
        """)
        cur.execute("""
            UPDATE logra_reports
            SET category = 'ONG'
            WHERE category IS NULL OR UPPER(category) = 'LOGRA'
        """)
        cur.execute("""
            UPDATE logra_reports
            SET title = REPLACE(title, 'LOGRA', 'ONG')
            WHERE title LIKE '%LOGRA%'
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN category SET DEFAULT 'ONG'
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'Pending'
        """)
        cur.execute("""
            UPDATE logra_reports
            SET status = 'Pending'
            WHERE category = 'ONG'
              AND (status IS NULL OR UPPER(status) = 'DRAFT')
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN status SET DEFAULT 'Pending'
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS meeting_date DATE DEFAULT CURRENT_DATE
        """)
        cur.execute("""
            UPDATE logra_reports
            SET meeting_date = CURRENT_DATE
            WHERE meeting_date IS NULL
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN meeting_date SET DEFAULT CURRENT_DATE
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS meeting_time TEXT DEFAULT '00:00'
        """)
        cur.execute("""
            UPDATE logra_reports
            SET meeting_time = '00:00'
            WHERE meeting_time IS NULL
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN meeting_time SET DEFAULT '00:00'
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS meeting_start_time TEXT DEFAULT ''
        """)
        cur.execute("""
            UPDATE logra_reports
            SET meeting_start_time = ''
            WHERE meeting_start_time IS NULL
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN meeting_start_time SET DEFAULT ''
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS meeting_end_time TEXT DEFAULT ''
        """)
        cur.execute("""
            UPDATE logra_reports
            SET meeting_end_time = ''
            WHERE meeting_end_time IS NULL
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN meeting_end_time SET DEFAULT ''
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS meeting_location TEXT DEFAULT ''
        """)
        cur.execute("""
            UPDATE logra_reports
            SET meeting_location = ''
            WHERE meeting_location IS NULL
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN meeting_location SET DEFAULT ''
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS meeting_person TEXT DEFAULT ''
        """)
        cur.execute("""
            UPDATE logra_reports
            SET meeting_person = ''
            WHERE meeting_person IS NULL
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN meeting_person SET DEFAULT ''
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS agenda_items JSONB NOT NULL DEFAULT '[]'::jsonb
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS agenda_notes TEXT DEFAULT ''
        """)
        cur.execute("""
            UPDATE logra_reports
            SET agenda_notes = ''
            WHERE agenda_notes IS NULL
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ALTER COLUMN agenda_notes SET DEFAULT ''
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS created_by TEXT
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()
        """)
        cur.execute("""
            ALTER TABLE logra_reports
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logra_answers (
                id SERIAL PRIMARY KEY,
                report_id INTEGER NOT NULL REFERENCES logra_reports(id) ON DELETE CASCADE,
                form_slug TEXT NOT NULL,
                form_title TEXT,
                section TEXT NOT NULL,
                item_key TEXT NOT NULL,
                question_text TEXT NOT NULL,
                bullets JSONB NOT NULL DEFAULT '[]'::jsonb,
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(report_id, form_slug, section, item_key)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logra_attachments (
                id SERIAL PRIMARY KEY,
                report_id INTEGER NOT NULL REFERENCES logra_reports(id) ON DELETE CASCADE,
                form_slug TEXT NOT NULL,
                section TEXT NOT NULL,
                item_key TEXT NOT NULL,
                bullet_index INTEGER,
                original_filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                content_type TEXT,
                file_size BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_logra_answers_report
            ON logra_answers(report_id)
        """)
        cur.execute("""
            UPDATE logra_answers
            SET form_title = REPLACE(form_title, 'LOGRA', 'ONG')
            WHERE form_title LIKE '%LOGRA%'
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_logra_attachments_lookup
            ON logra_attachments(report_id, form_slug, section, item_key)
        """)
    conn.commit()


def _safe_filename(filename: str) -> str:
    base = os.path.basename(filename or "attachment")
    safe = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in base).strip()
    return safe or "attachment"


@router.get("")
def list_logra_reports(conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                r.id,
                r.title,
                r.category,
                r.status,
                r.agenda_items,
                r.agenda_notes,
                r.created_by,
                r.created_at,
                r.updated_at,
                COALESCE(a.attachment_count, 0) AS attachment_count
            FROM logra_reports r
            LEFT JOIN (
                SELECT report_id, COUNT(*) AS attachment_count
                FROM logra_attachments
                GROUP BY report_id
            ) a ON a.report_id = r.id
            ORDER BY r.updated_at DESC, r.id DESC
            LIMIT 200
        """)
        return {"data": cur.fetchall()}


@router.post("/agenda-only")
def save_logra_agenda_only(payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    payload = payload or {}
    agenda_items = payload.get("agenda_items") or []
    agenda_notes = payload.get("agenda_notes") or ""
    created_by = payload.get("created_by")
    if not isinstance(agenda_items, list):
        agenda_items = []
    if len(agenda_items) > MAX_AGENDA_ITEMS:
        raise HTTPException(status_code=400, detail="LOGRA agenda supports up to 150 items")

    clean_items = []
    for index, raw_item in enumerate(agenda_items):
        if not isinstance(raw_item, dict):
            continue
        item = dict(raw_item)
        item["report_title"] = "ONG - Agenda"
        item["agenda_index"] = index
        clean_items.append(item)

    first_meeting = clean_items[0] if clean_items else {}
    meeting_date = first_meeting.get("date_iso") or datetime.utcnow().date().isoformat()
    meeting_start_time = first_meeting.get("start_time") or ""
    meeting_end_time = first_meeting.get("end_time") or ""
    meeting_time = meeting_start_time or "00:00"
    meeting_location = first_meeting.get("place") or ""
    meeting_person = first_meeting.get("person") or ""

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id
                FROM logra_reports
                WHERE category = 'ONG'
                  AND title = 'ONG - Agenda'
                ORDER BY id ASC
                LIMIT 1
            """)
            existing = cur.fetchone()

            if existing:
                report_id = existing["id"]
                cur.execute("""
                    UPDATE logra_reports
                    SET status = 'Pending',
                        meeting_date = %s,
                        meeting_time = %s,
                        meeting_start_time = %s,
                        meeting_end_time = %s,
                        meeting_location = %s,
                        meeting_person = %s,
                        agenda_items = %s,
                        agenda_notes = %s,
                        updated_at = %s
                    WHERE id = %s
                    RETURNING *
                """, (
                    meeting_date, meeting_time, meeting_start_time, meeting_end_time,
                    meeting_location, meeting_person, Json(clean_items), agenda_notes,
                    datetime.utcnow(), report_id,
                ))
                report = cur.fetchone()
            else:
                cur.execute("""
                    INSERT INTO logra_reports (
                        title, category, status, meeting_date, meeting_time, meeting_start_time,
                        meeting_end_time, meeting_location, meeting_person, agenda_items,
                        agenda_notes, created_by, created_at, updated_at
                    )
                    VALUES ('ONG - Agenda', 'ONG', 'Pending', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    meeting_date, meeting_time, meeting_start_time, meeting_end_time,
                    meeting_location, meeting_person, Json(clean_items), agenda_notes,
                    created_by, datetime.utcnow(), datetime.utcnow(),
                ))
                report = cur.fetchone()
                report_id = report["id"]

            for index, item in enumerate(clean_items):
                item["report_id"] = report_id
                item["agenda_index"] = index

            cur.execute("""
                UPDATE logra_reports
                SET agenda_items = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING *
            """, (Json(clean_items), datetime.utcnow(), report_id))
            report = cur.fetchone()

        conn.commit()
        return {"success": True, "report": report}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA agenda save error: {exc}")





@router.get("/{report_id}")
def get_logra_report(report_id: int, conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM logra_reports WHERE id = %s", (report_id,))
        report = cur.fetchone()
        if not report:
            raise HTTPException(status_code=404, detail="LOGRA report not found")

        cur.execute("""
            SELECT form_slug, form_title, section, item_key, question_text, bullets
            FROM logra_answers
            WHERE report_id = %s
            ORDER BY form_slug, section, item_key
        """, (report_id,))
        answers = cur.fetchall()

        cur.execute("""
            SELECT id, form_slug, section, item_key, bullet_index, original_filename,
                   content_type, file_size, created_at
            FROM logra_attachments
            WHERE report_id = %s
            ORDER BY created_at DESC, id DESC
        """, (report_id,))
        attachments = cur.fetchall()

    return {"report": report, "answers": answers, "attachments": attachments}


@router.post("")
def save_logra_report(payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    payload = payload or {}
    report_id = payload.get("id")
    title = (payload.get("title") or "ONG Questionnaire").replace("LOGRA", "ONG")
    category = (payload.get("category") or "ONG").replace("LOGRA", "ONG")
    status = (payload.get("status") or "Pending").replace("Draft", "Pending")
    created_by = payload.get("created_by")
    answers = payload.get("answers") or []
    agenda_items = payload.get("agenda_items") or []
    agenda_notes = payload.get("agenda_notes") or ""
    if not isinstance(agenda_items, list):
        agenda_items = []
    if len(agenda_items) > MAX_AGENDA_ITEMS:
        raise HTTPException(status_code=400, detail="LOGRA agenda supports up to 150 items")
    first_meeting = agenda_items[0] if agenda_items and isinstance(agenda_items[0], dict) else {}
    meeting_date = first_meeting.get("date_iso") or datetime.utcnow().date().isoformat()
    meeting_start_time = first_meeting.get("start_time") or ""
    meeting_end_time = first_meeting.get("end_time") or ""
    meeting_time = meeting_start_time or "00:00"
    meeting_location = first_meeting.get("place") or ""
    meeting_person = first_meeting.get("person") or ""

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if report_id:
                cur.execute("""
                    UPDATE logra_reports
                    SET title = %s,
                        category = %s,
                        status = %s,
                        meeting_date = %s,
                        meeting_time = %s,
                        meeting_start_time = %s,
                        meeting_end_time = %s,
                        meeting_location = %s,
                        meeting_person = %s,
                        agenda_items = %s,
                        agenda_notes = %s,
                        updated_at = %s
                    WHERE id = %s
                    RETURNING *
                """, (
                    title, category, status, meeting_date, meeting_time, meeting_start_time, meeting_end_time,
                    meeting_location, meeting_person, Json(agenda_items), agenda_notes,
                    datetime.utcnow(), report_id
                ))
                report = cur.fetchone()
                if not report:
                    raise HTTPException(status_code=404, detail="LOGRA report not found")
            else:
                cur.execute("""
                    INSERT INTO logra_reports (
                        title, category, status, meeting_date, meeting_time, meeting_start_time, meeting_end_time,
                        meeting_location, meeting_person, agenda_items, agenda_notes,
                        created_by, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    title, category, status, meeting_date, meeting_time, meeting_start_time, meeting_end_time,
                    meeting_location, meeting_person, Json(agenda_items), agenda_notes,
                    created_by, datetime.utcnow(), datetime.utcnow()
                ))
                report = cur.fetchone()
                report_id = report["id"]

            if answers:
                cur.execute("DELETE FROM logra_answers WHERE report_id = %s", (report_id,))

                for item in answers:
                    bullets = item.get("bullets") or []
                    if not isinstance(bullets, list):
                        bullets = []
                    bullets = [str(value).strip() for value in bullets[:20] if str(value or "").strip()]
                    cur.execute("""
                        INSERT INTO logra_answers (
                            report_id, form_slug, form_title, section, item_key,
                            question_text, bullets, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (report_id, form_slug, section, item_key)
                        DO UPDATE SET
                            form_title = EXCLUDED.form_title,
                            question_text = EXCLUDED.question_text,
                            bullets = EXCLUDED.bullets,
                            updated_at = EXCLUDED.updated_at
                    """, (
                        report_id,
                        item.get("form_slug"),
                        (item.get("form_title") or "").replace("LOGRA", "ONG"),
                        item.get("section"),
                        item.get("item_key"),
                        item.get("question_text") or "",
                        Json(bullets),
                        datetime.utcnow(),
                    ))

        conn.commit()
        return {"success": True, "report": report}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA save error: {exc}")


@router.put("/{report_id}")
def update_logra_report(report_id: int, payload: dict, conn=Depends(get_db)):
    payload = dict(payload or {})
    payload["id"] = report_id
    return save_logra_report(payload, conn)


@router.put("/{report_id}/answers")
def update_logra_answer(report_id: int, payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    payload = payload or {}
    form_slug = str(payload.get("form_slug") or "").strip()
    section = str(payload.get("section") or "").strip()
    item_key = str(payload.get("item_key") or "").strip()
    if not form_slug or not section or not item_key:
        raise HTTPException(status_code=400, detail="form_slug, section and item_key are required")

    bullets = payload.get("bullets") or []
    if not isinstance(bullets, list):
        bullets = []
    bullets = [str(value).strip() for value in bullets[:20] if str(value or "").strip()]

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id FROM logra_reports WHERE id = %s", (report_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="LOGRA report not found")

            cur.execute("""
                INSERT INTO logra_answers (
                    report_id, form_slug, form_title, section, item_key,
                    question_text, bullets, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (report_id, form_slug, section, item_key)
                DO UPDATE SET
                    form_title = EXCLUDED.form_title,
                    question_text = EXCLUDED.question_text,
                    bullets = EXCLUDED.bullets,
                    updated_at = EXCLUDED.updated_at
                RETURNING form_slug, form_title, section, item_key, question_text, bullets, updated_at
            """, (
                report_id,
                form_slug,
                payload.get("form_title") or "",
                section,
                item_key,
                payload.get("question_text") or "",
                Json(bullets),
                datetime.utcnow(),
            ))
            answer = cur.fetchone()
            cur.execute("UPDATE logra_reports SET updated_at = %s WHERE id = %s", (datetime.utcnow(), report_id))
        conn.commit()
        return {"success": True, "answer": answer}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA answer update error: {exc}")


@router.put("/{report_id}/agenda-items/{agenda_index}")
def update_logra_agenda_item(report_id: int, agenda_index: int, payload: dict, conn=Depends(get_db)):
    _ensure_schema(conn)
    payload = payload or {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT agenda_items FROM logra_reports WHERE id = %s", (report_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="LOGRA report not found")

            items = row.get("agenda_items") or []
            if not isinstance(items, list):
                items = []
            if agenda_index < 0 or agenda_index >= len(items):
                raise HTTPException(status_code=404, detail="Agenda item not found")

            current = items[agenda_index] if isinstance(items[agenda_index], dict) else {}
            updated_item = {**current, **payload}
            items[agenda_index] = updated_item

            first_meeting = items[0] if items and isinstance(items[0], dict) else {}
            cur.execute("""
                UPDATE logra_reports
                SET agenda_items = %s,
                    meeting_date = %s,
                    meeting_time = %s,
                    meeting_start_time = %s,
                    meeting_end_time = %s,
                    meeting_location = %s,
                    meeting_person = %s,
                    updated_at = %s
                WHERE id = %s
                RETURNING id, agenda_items, updated_at
            """, (
                Json(items),
                first_meeting.get("date_iso") or datetime.utcnow().date().isoformat(),
                first_meeting.get("start_time") or "00:00",
                first_meeting.get("start_time") or "",
                first_meeting.get("end_time") or "",
                first_meeting.get("place") or "",
                first_meeting.get("person") or "",
                datetime.utcnow(),
                report_id,
            ))
            updated = cur.fetchone()
        conn.commit()
        return {"success": True, "report": updated, "item": updated_item}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA agenda update error: {exc}")


@router.post("/{report_id}/attachments")
def upload_logra_attachment(
    report_id: int,
    form_slug: str = Form(...),
    section: str = Form(...),
    item_key: str = Form(...),
    bullet_index: int | None = Form(None),
    file: UploadFile = File(...),
    conn=Depends(get_db)
):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id FROM logra_reports WHERE id = %s", (report_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="LOGRA report not found")
        cur.execute("""
            SELECT COUNT(*) AS total
            FROM logra_attachments
            WHERE report_id = %s
              AND form_slug = %s
              AND section = %s
              AND item_key = %s
        """, (report_id, form_slug, section, item_key))
        total = (cur.fetchone() or {}).get("total") or 0
        if total >= MAX_ATTACHMENTS_PER_QUESTION:
            raise HTTPException(status_code=400, detail="Each LOGRA question supports up to 10 attachments")

    folder = STORAGE_ROOT / str(report_id) / form_slug / section / item_key
    folder.mkdir(parents=True, exist_ok=True)

    original = _safe_filename(file.filename)
    stored_name = f"{int(datetime.utcnow().timestamp())}_{original}"
    stored_path = folder / stored_name

    try:
        with open(stored_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_size = stored_path.stat().st_size

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO logra_attachments (
                    report_id, form_slug, section, item_key, bullet_index,
                    original_filename, stored_path, content_type, file_size, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, original_filename, content_type, file_size, created_at
            """, (
                report_id,
                form_slug,
                section,
                item_key,
                bullet_index,
                original,
                str(stored_path),
                file.content_type,
                file_size,
                datetime.utcnow(),
            ))
            row = cur.fetchone()
        conn.commit()
        return {"success": True, "attachment": row}

    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA upload error: {exc}")


@router.get("/{report_id}/attachments")
def list_logra_attachments(
    report_id: int,
    form_slug: str | None = Query(None),
    section: str | None = Query(None),
    item_key: str | None = Query(None),
    conn=Depends(get_db)
):
    _ensure_schema(conn)
    filters = ["report_id = %s"]
    params = [report_id]
    if form_slug:
        filters.append("form_slug = %s")
        params.append(form_slug)
    if section:
        filters.append("section = %s")
        params.append(section)
    if item_key:
        filters.append("item_key = %s")
        params.append(item_key)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""
            SELECT id, form_slug, section, item_key, bullet_index, original_filename,
                   content_type, file_size, created_at
            FROM logra_attachments
            WHERE {" AND ".join(filters)}
            ORDER BY created_at DESC, id DESC
        """, params)
        return {"data": cur.fetchall()}


@router.delete("/{report_id}/agenda-items/{agenda_index}")
def delete_logra_agenda_item(report_id: int, agenda_index: int, conn=Depends(get_db)):
    _ensure_schema(conn)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT agenda_items FROM logra_reports WHERE id = %s", (report_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="LOGRA report not found")

            items = row.get("agenda_items") or []
            if not isinstance(items, list):
                items = []
            if agenda_index < 0 or agenda_index >= len(items):
                raise HTTPException(status_code=404, detail="Agenda item not found")

            items.pop(agenda_index)
            cur.execute("""
                UPDATE logra_reports
                SET agenda_items = %s, updated_at = %s
                WHERE id = %s
                RETURNING id, agenda_items, updated_at
            """, (Json(items), datetime.utcnow(), report_id))
            updated = cur.fetchone()
        conn.commit()
        return {"success": True, "report": updated}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA agenda delete error: {exc}")


@router.delete("/{report_id}")
def delete_logra_report(report_id: int, conn=Depends(get_db)):
    _ensure_schema(conn)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT stored_path
                FROM logra_attachments
                WHERE report_id = %s
            """, (report_id,))
            attachment_paths = [row.get("stored_path") for row in cur.fetchall()]
            cur.execute("""
                DELETE FROM logra_reports
                WHERE id = %s
                RETURNING id
            """, (report_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise HTTPException(status_code=404, detail="LOGRA report not found")

        conn.commit()

        for raw_path in attachment_paths:
            try:
                path = Path(raw_path or "")
                if path.exists():
                    path.unlink()
            except Exception:
                pass

        return {"success": True, "id": report_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA report delete error: {exc}")


@router.delete("/attachments/{attachment_id}")
def delete_logra_attachment(attachment_id: int, conn=Depends(get_db)):
    _ensure_schema(conn)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, stored_path
                FROM logra_attachments
                WHERE id = %s
            """, (attachment_id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Attachment not found")

            cur.execute("DELETE FROM logra_attachments WHERE id = %s", (attachment_id,))

        conn.commit()

        path = Path(row["stored_path"])
        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass

        return {"success": True}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"LOGRA attachment delete error: {exc}")


@router.get("/attachments/{attachment_id}/download")
def download_logra_attachment(attachment_id: int, conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT original_filename, stored_path, content_type
            FROM logra_attachments
            WHERE id = %s
        """, (attachment_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Attachment not found")

    path = Path(row["stored_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Attachment file is missing")

    return FileResponse(
        path=str(path),
        filename=row["original_filename"],
        media_type=row.get("content_type") or "application/octet-stream"
    )
