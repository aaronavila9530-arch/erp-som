from __future__ import annotations

import json
import os
from typing import Any

from psycopg2.extras import Json, RealDictCursor

try:
    from pywebpush import WebPushException, webpush
except Exception:  # pragma: no cover - optional dependency until Railway installs it
    WebPushException = Exception
    webpush = None


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
            dedupe_key TEXT,
            created_by TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            read_at TIMESTAMP
        )
        """
    )
    cur.execute("ALTER TABLE app_notifications ADD COLUMN IF NOT EXISTS dedupe_key TEXT")
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
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_app_notifications_dedupe
        ON app_notifications (LOWER(recipient_user), dedupe_key)
        WHERE dedupe_key IS NOT NULL
        """
    )


def ensure_push_subscriptions_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS app_push_subscriptions (
            id SERIAL PRIMARY KEY,
            recipient_user TEXT NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            user_agent TEXT,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            last_error TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_app_push_subscriptions_user_active
        ON app_push_subscriptions (LOWER(recipient_user), active)
        """
    )


def vapid_public_key() -> str:
    return os.getenv("VAPID_PUBLIC_KEY", "").strip()


def vapid_ready() -> bool:
    return bool(vapid_public_key() and os.getenv("VAPID_PRIVATE_KEY", "").strip() and webpush)


def upsert_push_subscription(cur, recipient_user: str, subscription: dict[str, Any], user_agent: str | None = None) -> int | None:
    recipient = (recipient_user or "").strip().lower()
    endpoint = str(subscription.get("endpoint") or "").strip()
    keys = subscription.get("keys") or {}
    p256dh = str(keys.get("p256dh") or "").strip()
    auth = str(keys.get("auth") or "").strip()
    if not recipient or not endpoint or not p256dh or not auth:
        return None
    ensure_push_subscriptions_table(cur)
    cur.execute(
        """
        INSERT INTO app_push_subscriptions (
            recipient_user, endpoint, p256dh, auth, user_agent, active, updated_at, last_error
        )
        VALUES (%s,%s,%s,%s,%s,TRUE,NOW(),NULL)
        ON CONFLICT (endpoint)
        DO UPDATE SET
            recipient_user = EXCLUDED.recipient_user,
            p256dh = EXCLUDED.p256dh,
            auth = EXCLUDED.auth,
            user_agent = EXCLUDED.user_agent,
            active = TRUE,
            updated_at = NOW(),
            last_error = NULL
        RETURNING id
        """,
        (recipient, endpoint, p256dh, auth, user_agent),
    )
    row = cur.fetchone()
    if isinstance(row, dict):
        return row.get("id")
    return row[0] if row else None


def _push_payload(title: str, message: str, metadata: dict[str, Any] | None = None) -> str:
    return json.dumps(
        {
            "title": title,
            "body": message,
            "icon": "/som/icon/msl-192.png",
            "badge": "/som/icon/msl-192.png",
            "url": "/som",
            "data": metadata or {},
        },
        ensure_ascii=False,
    )


def dispatch_push_notification(cur, recipient_user: str, title: str, message: str, metadata: dict[str, Any] | None = None) -> int:
    if not vapid_ready():
        return 0
    recipient = (recipient_user or "").strip().lower()
    if not recipient:
        return 0
    ensure_push_subscriptions_table(cur)
    cur.execute(
        """
        SELECT id, endpoint, p256dh, auth
        FROM app_push_subscriptions
        WHERE LOWER(recipient_user) = LOWER(%s)
          AND active = TRUE
        """,
        (recipient,),
    )
    rows = [dict(row) for row in cur.fetchall() or []]
    sent = 0
    vapid_claims = {"sub": os.getenv("VAPID_SUBJECT", "mailto:admin@mslogisticsgroup.com")}
    for row in rows:
        subscription_info = {
            "endpoint": row["endpoint"],
            "keys": {"p256dh": row["p256dh"], "auth": row["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=_push_payload(title, message, metadata),
                vapid_private_key=os.getenv("VAPID_PRIVATE_KEY", "").strip(),
                vapid_claims=vapid_claims,
            )
            sent += 1
        except WebPushException as exc:
            cur.execute(
                """
                UPDATE app_push_subscriptions
                SET active = FALSE,
                    last_error = %s,
                    updated_at = NOW()
                WHERE id = %s
                """,
                (str(exc)[:500], row["id"]),
            )
    return sent


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
    dedupe_key: str | None = None,
    send_push: bool = True,
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
            dedupe_key,
            created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (LOWER(recipient_user), dedupe_key)
        WHERE dedupe_key IS NOT NULL
        DO NOTHING
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
            dedupe_key,
            created_by,
        ),
    )
    row = cur.fetchone()
    notification_id = row.get("id") if isinstance(row, dict) else (row[0] if row else None)
    if notification_id and send_push:
        dispatch_push_notification(cur, recipient, title, message, metadata)
    return notification_id


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
    dedupe_key: str | None = None,
    send_push: bool = True,
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
            dedupe_key=f"{dedupe_key}:{key}" if dedupe_key else None,
            send_push=send_push,
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
