from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from security.auth import get_current_user
from services.notifications import ensure_notifications_table, fetch_notifications, unread_count


router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


@router.get("")
@router.get("/")
def list_notifications(
    unread_only: bool = False,
    limit: int = 100,
    current_user=Depends(get_current_user),
    conn=Depends(get_db),
):
    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        rows = fetch_notifications(cur, usuario, unread_only=unread_only, limit=limit)
        count = unread_count(cur, usuario)
        conn.commit()
        return {"data": rows, "unread_count": count}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"No se pudieron cargar notificaciones: {exc}")


@router.get("/unread-count")
def get_unread_count(
    current_user=Depends(get_current_user),
    conn=Depends(get_db),
):
    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        count = unread_count(cur, usuario)
        conn.commit()
        return {"unread_count": count}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"No se pudo cargar conteo de notificaciones: {exc}")


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user=Depends(get_current_user),
    conn=Depends(get_db),
):
    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_notifications_table(cur)
        cur.execute(
            """
            UPDATE app_notifications
            SET status = 'READ',
                read_at = NOW()
            WHERE id = %s
              AND LOWER(recipient_user) = LOWER(%s)
            RETURNING id
            """,
            (notification_id, usuario),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Notificación no encontrada")
        conn.commit()
        return {"status": "OK", "id": notification_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"No se pudo marcar notificación: {exc}")


@router.patch("/read-all")
def mark_all_notifications_read(
    current_user=Depends(get_current_user),
    conn=Depends(get_db),
):
    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_notifications_table(cur)
        cur.execute(
            """
            UPDATE app_notifications
            SET status = 'READ',
                read_at = COALESCE(read_at, NOW())
            WHERE LOWER(recipient_user) = LOWER(%s)
              AND status = 'UNREAD'
            """,
            (usuario,),
        )
        updated = cur.rowcount
        conn.commit()
        return {"status": "OK", "updated": updated}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"No se pudieron marcar notificaciones: {exc}")
