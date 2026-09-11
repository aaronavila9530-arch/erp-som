from __future__ import annotations

from typing import Any

from psycopg2.extras import Json, RealDictCursor


def ensure_notifications_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS app_notifications (
            id SERIAL PRIMARY KEY,
            recipient_user TEXT NOT NULL,
            module_code TEXT NOT NULL DEFAULT 'general',
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            status TEXT NOT NULL DEFAULT 'UNREAD',
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            read_at TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_app_notifications_recipient_status
        ON app_notifications (LOWER(recipient_user), status, created_at DESC)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_app_notifications_entity
        ON app_notifications (entity_type, entity_id)
        """
    )


def get_admin_master_users(cur) -> list[str]:
    cur.execute(
        """
        SELECT usuario
        FROM usuarios
        WHERE COALESCE(activo, TRUE) = TRUE
          AND LOWER(COALESCE(rol, '')) IN ('admin', 'master')
        ORDER BY usuario
        """
    )
    return [
        str(row["usuario"]).strip().lower()
        for row in cur.fetchall()
        if row.get("usuario")
    ]


def create_notification(
    cur,
    recipient_user: str,
    title: str,
    message: str,
    *,
    module_code: str = "general",
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> int | None:
    recipient = (recipient_user or "").strip().lower()
    if not recipient:
        return None
    ensure_notifications_table(cur)
    cur.execute(
        """
        INSERT INTO app_notifications (
            recipient_user,
            module_code,
            title,
            message,
            entity_type,
            entity_id,
            metadata,
            created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            recipient,
            module_code,
            title,
            message,
            entity_type,
            str(entity_id) if entity_id is not None else None,
            Json(metadata or {}),
            created_by,
        ),
    )
    row = cur.fetchone()
    if isinstance(row, dict):
        return row.get("id")
    if row:
        return row[0]
    return None


def create_notifications(
    cur,
    recipients: list[str],
    title: str,
    message: str,
    *,
    module_code: str = "general",
    entity_type: str | None = None,
    entity_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
    created_by: str | None = None,
) -> int:
    inserted = 0
    seen: set[str] = set()
    for recipient in recipients:
        key = (recipient or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        if create_notification(
            cur,
            key,
            title,
            message,
            module_code=module_code,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
            created_by=created_by,
        ):
            inserted += 1
    return inserted


def fetch_notifications(cur, recipient_user: str, unread_only: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    ensure_notifications_table(cur)
    limit = max(1, min(int(limit or 100), 250))
    if unread_only:
        cur.execute(
            """
            SELECT *
            FROM app_notifications
            WHERE LOWER(recipient_user) = LOWER(%s)
              AND status = 'UNREAD'
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (recipient_user, limit),
        )
    else:
        cur.execute(
            """
            SELECT *
            FROM app_notifications
            WHERE LOWER(recipient_user) = LOWER(%s)
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (recipient_user, limit),
        )
    return [dict(row) for row in cur.fetchall()]


def unread_count(cur, recipient_user: str) -> int:
    ensure_notifications_table(cur)
    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM app_notifications
        WHERE LOWER(recipient_user) = LOWER(%s)
          AND status = 'UNREAD'
        """,
        (recipient_user,),
    )
    row = cur.fetchone() or {}
    return int(row.get("total") or 0)
