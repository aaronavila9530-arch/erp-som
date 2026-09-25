from __future__ import annotations

import os
import threading
import time
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from psycopg2.extras import RealDictCursor

from database import get_conn, get_db, release_conn
from security.auth import get_current_user
from services.notifications import (
    create_notifications,
    ensure_notifications_table,
    get_admin_master_users,
    fetch_notifications,
    unread_count,
    upsert_push_subscription,
    vapid_public_key,
    vapid_ready,
)
from services.tenanting import company_code


router = APIRouter(prefix="/notifications", tags=["Notificaciones"])
_scheduler_started = False
_scheduler_lock = threading.Lock()


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


@router.get("/push/config")
def push_config():
    return {
        "enabled": vapid_ready(),
        "public_key": vapid_public_key(),
        "message": "Configure VAPID_PUBLIC_KEY y VAPID_PRIVATE_KEY para push aun con SOM Web cerrado." if not vapid_ready() else "Web Push disponible.",
    }


@router.post("/push/subscribe")
async def subscribe_push(
    request: Request,
    current_user=Depends(get_current_user),
    conn=Depends(get_db),
):
    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")
    payload = await request.json()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        subscription_id = upsert_push_subscription(cur, usuario, payload, request.headers.get("user-agent"))
        if not subscription_id:
            raise HTTPException(400, "Suscripción push inválida")
        conn.commit()
        return {"status": "OK", "id": subscription_id, "push_enabled": vapid_ready()}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"No se pudo guardar suscripción push: {exc}")


def _money(value) -> str:
    try:
        return f"{float(value or 0):,.2f}"
    except Exception:
        return str(value or 0)


def _scan_report_alerts(cur, company: str) -> int:
    recipients = get_admin_master_users(cur)
    if not recipients:
        return 0
    cur.execute(
        """
        SELECT consec, num_informe, cliente, tipo, surveyor, buque_contenedor
        FROM servicios
        WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %s
          AND COALESCE(NULLIF(TRIM(num_informe), ''), '') <> ''
          AND LOWER(TRIM(COALESCE(num_informe,''))) <> 'none'
          AND UPPER(COALESCE(NULLIF(TRIM(status_informe), ''), 'PENDING')) IN ('PENDING','ENVIADO','SENT','SUBMITTED')
        ORDER BY consec DESC
        LIMIT 100
        """,
        (company,),
    )
    inserted = 0
    for row in cur.fetchall() or []:
        person = row.get("surveyor") or "Un usuario"
        service = row.get("tipo") or row.get("buque_contenedor") or row.get("consec")
        client = row.get("cliente") or "cliente sin nombre"
        message = f"{person} envió informe {row.get('num_informe')} de {service} para {client}."
        inserted += create_notifications(
            cur,
            recipients,
            "Informe enviado a revisión",
            message,
            module_code="informes",
            entity_type="servicio_informe",
            entity_id=row.get("consec"),
            metadata={"company_code": company, "service_id": row.get("consec"), "num_informe": row.get("num_informe"), "cliente": client},
            dedupe_key=f"report-review:{company}:{row.get('consec')}:{row.get('num_informe')}",
        )
    return inserted


def _scan_finance_alerts(cur, company: str, days_ahead: int = 3) -> int:
    recipients = get_admin_master_users(cur)
    if not recipients:
        return 0
    today = date.today()
    until = today + timedelta(days=max(1, min(int(days_ahead or 3), 30)))
    inserted = 0

    cur.execute(
        """
        SELECT id, payee_name, currency, balance, due_date, status
        FROM payment_obligations
        WHERE COALESCE(active, TRUE) = TRUE
          AND company_code = %s
          AND status IN ('PENDING','PARTIAL')
          AND COALESCE(balance, 0) > 0
          AND due_date IS NOT NULL
          AND due_date <= %s
        ORDER BY due_date ASC
        LIMIT 150
        """,
        (company, until),
    )
    for row in cur.fetchall() or []:
        due = row.get("due_date")
        overdue = due and due < today
        title = "Pago vencido por realizar" if overdue else "Pago próximo a vencer"
        message = f"{row.get('payee_name') or 'Proveedor'}: {row.get('currency') or ''} {_money(row.get('balance'))} vence {due}."
        inserted += create_notifications(
            cur,
            recipients,
            title,
            message,
            module_code="finanzas",
            entity_type="payment_obligation",
            entity_id=row.get("id"),
            metadata={"company_code": company, "due_date": str(due), "balance": float(row.get("balance") or 0), "currency": row.get("currency")},
            dedupe_key=f"itp-due:{company}:{row.get('id')}:{today.isoformat()}",
        )

    cur.execute(
        """
        SELECT id, numero_documento, nombre_cliente, moneda, saldo_pendiente, fecha_vencimiento, estado_factura
        FROM collections
        WHERE company_code = %s
          AND COALESCE(saldo_pendiente, 0) > 0
          AND fecha_vencimiento IS NOT NULL
          AND fecha_vencimiento <= %s
        ORDER BY fecha_vencimiento ASC
        LIMIT 150
        """,
        (company, until),
    )
    for row in cur.fetchall() or []:
        due = row.get("fecha_vencimiento")
        overdue = due and due < today
        title = "Factura pendiente de cobro vencida" if overdue else "Factura próxima a vencer"
        message = f"{row.get('nombre_cliente') or 'Cliente'} factura {row.get('numero_documento')}: {row.get('moneda') or ''} {_money(row.get('saldo_pendiente'))} vence {due}."
        inserted += create_notifications(
            cur,
            recipients,
            title,
            message,
            module_code="finanzas",
            entity_type="collection_invoice",
            entity_id=row.get("id"),
            metadata={"company_code": company, "due_date": str(due), "balance": float(row.get("saldo_pendiente") or 0), "currency": row.get("moneda")},
            dedupe_key=f"collections-due:{company}:{row.get('id')}:{today.isoformat()}",
        )
    return inserted


def _scheduler_companies(cur) -> list[str]:
    configured = os.getenv("SOM_NOTIFICATION_COMPANIES", "").strip()
    if configured:
        return [item.strip().upper() for item in configured.split(",") if item.strip()]
    try:
        cur.execute(
            """
            SELECT DISTINCT company_code
            FROM companies
            WHERE COALESCE(active, TRUE) = TRUE
              AND COALESCE(NULLIF(TRIM(company_code), ''), '') <> ''
            ORDER BY company_code
            """
        )
        rows = [str(row["company_code"]).strip().upper() for row in cur.fetchall() or [] if row.get("company_code")]
        if rows:
            return rows
    except Exception:
        pass
    return ["MSL-CR", "MCI-CR"]


def run_notification_scan_once(days_ahead: int = 3) -> dict:
    conn = None
    inserted = 0
    companies: list[str] = []
    try:
        conn = get_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        ensure_notifications_table(cur)
        companies = _scheduler_companies(cur)
        for company in companies:
            inserted += _scan_report_alerts(cur, company)
            inserted += _scan_finance_alerts(cur, company, days_ahead)
        conn.commit()
        return {"status": "OK", "created": inserted, "companies": companies}
    except Exception as exc:
        if conn:
            conn.rollback()
        print(f"Notificaciones SOM: escaneo falló: {exc}")
        return {"status": "ERROR", "created": inserted, "companies": companies, "error": str(exc)}
    finally:
        if conn:
            release_conn(conn)


def _notification_scheduler_loop():
    interval = max(300, int(os.getenv("SOM_NOTIFICATION_SCAN_SECONDS", "900") or "900"))
    while True:
        run_notification_scan_once(days_ahead=int(os.getenv("SOM_NOTIFICATION_DAYS_AHEAD", "3") or "3"))
        time.sleep(interval)


def start_notification_scheduler():
    global _scheduler_started
    if os.getenv("SOM_DISABLE_NOTIFICATION_SCHEDULER", "").strip() == "1":
        print("Notificaciones SOM: scheduler desactivado por SOM_DISABLE_NOTIFICATION_SCHEDULER=1")
        return
    with _scheduler_lock:
        if _scheduler_started:
            return
        _scheduler_started = True
        thread = threading.Thread(target=_notification_scheduler_loop, name="som-notification-scheduler", daemon=True)
        thread.start()
        print("Notificaciones SOM: scheduler automático iniciado")


@router.post("/scan")
def scan_notifications(
    days_ahead: int = 3,
    current_user=Depends(get_current_user),
    conn=Depends(get_db),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    rol = str(current_user.get("rol") or "").lower()
    if rol not in {"admin", "master"}:
        raise HTTPException(403, "Solo admin/master puede generar alertas globales")
    selected_company = company_code(header_value=x_company_code)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        ensure_notifications_table(cur)
        inserted = _scan_report_alerts(cur, selected_company) + _scan_finance_alerts(cur, selected_company, days_ahead)
        conn.commit()
        return {"status": "OK", "created": inserted, "company_code": selected_company}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500, f"No se pudieron generar alertas: {exc}")


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
