from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json

from database import get_db
from security.auth import get_current_user
from services.notifications import create_notification, create_notifications, get_admin_master_users


router = APIRouter(
    prefix="/hr/events",
    tags=["HHRR - Solicitudes"]
)

# ============================================================
# UTILIDAD: calcular vacaciones acumuladas
# ============================================================
def calcular_vacaciones(fecha_ingreso: date) -> float:
    hoy = date.today()

    if not fecha_ingreso or fecha_ingreso > hoy:
        return 0.0

    delta = relativedelta(hoy, fecha_ingreso)
    meses = delta.years * 12 + delta.months
    dias_acumulados = meses * 1

    return round(dias_acumulados, 2)


def _parse_positive_days(value, field_name: str) -> float:
    try:
        days = float(value)
        if days <= 0:
            raise ValueError
        return days
    except Exception:
        raise HTTPException(400, f"{field_name} inválido")


def _vacation_balance_for_user(cur, usuario: str, fecha_ingreso: date) -> dict:
    dias_generados = calcular_vacaciones(fecha_ingreso)
    cur.execute("""
        SELECT COALESCE(SUM(vacaciones), 0) AS dias_solicitados
        FROM hr_events
        WHERE created_by = %s
          AND event_type = 'VACACIONES'
          AND status IN ('PENDING', 'APPROVED')
    """, (usuario,))
    row = cur.fetchone() or {}
    dias_solicitados = float(row.get("dias_solicitados") or 0)
    return {
        "dias_generados": dias_generados,
        "dias_solicitados": dias_solicitados,
        "dias_disponibles": round(dias_generados - dias_solicitados, 2),
    }


def _event_label(event_type: str | None) -> str:
    value = str(event_type or "SOLICITUD").strip().upper()
    labels = {
        "VACACIONES": "vacaciones",
        "CONSTANCIA_SALARIAL": "constancia salarial",
        "CONSTANCIA_LABORAL": "constancia laboral",
        "INCAPACIDAD": "incapacidad",
        "LICENCIA": "licencia",
    }
    return labels.get(value, value.replace("_", " ").lower())


def _notify_new_request(cur, row_id: int, empleado_nombre: str, event_type: str, usuario: str, payload: dict) -> int:
    recipients = get_admin_master_users(cur)
    label = _event_label(event_type)
    title = "Nueva solicitud HHRR pendiente"
    message = f"{empleado_nombre or usuario} registró una solicitud de {label} pendiente de revisión."
    return create_notifications(
        cur,
        recipients,
        title,
        message,
        module_code="hhrre",
        entity_type="hr_event",
        entity_id=row_id,
        metadata={
            "event_type": event_type,
            "empleado": empleado_nombre,
            "created_by": usuario,
            "payload": payload or {},
        },
        created_by=usuario,
    )


def _notify_request_resolution(cur, row: dict, action_label: str, resolved_by: str, comentario: str | None) -> int | None:
    recipient = str(row.get("created_by") or "").strip().lower()
    if not recipient:
        return None
    event_id = row.get("id")
    label = _event_label(row.get("event_type"))
    empleado = row.get("empleado") or recipient
    title = f"Solicitud HHRR {action_label}"
    message = f"Tu solicitud de {label} fue {action_label.lower()}."
    if comentario:
        message = f"{message} Comentario: {comentario}"
    return create_notification(
        cur,
        recipient,
        title,
        message,
        module_code="hhrre",
        entity_type="hr_event",
        entity_id=event_id,
        metadata={
            "event_type": row.get("event_type"),
            "empleado": empleado,
            "status": row.get("status"),
            "approved_by": resolved_by,
            "comentario": comentario,
        },
        created_by=resolved_by,
    )


# ============================================================
# LISTAR SOLICITUDES
# GET /hr/events/
# ============================================================
@router.get("/")
def listar_eventos(
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    rol = current_user.get("rol")
    usuario = current_user.get("usuario")

    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    base_sql = """
        SELECT
            e.id,

            -- =============================================
            -- EMPLEADO (YA MATERIALIZADO)
            -- =============================================
            COALESCE(
                NULLIF(TRIM(e.empleado), ''),
                'SIN EMPLEADO'
            ) AS empleado,

            e.event_type,
            e.event_date,

            -- =============================================
            -- PERIODO (DESGLOSADO PARA UI)
            -- =============================================
            e.period_year,
            e.period_month,

            e.status,

            -- =============================================
            -- PAYLOAD ORIGINAL (PARA DETALLE DE SOLICITUD)
            -- =============================================
            e.payload,

            -- =============================================
            -- DIAS DE VACACIONES CALCULADOS
            -- =============================================
            e.vacaciones,

            -- =============================================
            -- CAMPOS CLAVE PARA LA TABLA
            -- =============================================
            e.comentario_solicitud,
            e.created_by,
            e.approved_by,
            e.created_at,
            e.approved_at

        FROM hr_events e
    """

    # ---------------------------------------------------------
    # USER → solo sus solicitudes
    # ADMIN / MASTER → todas
    # ---------------------------------------------------------
    rol = (rol or "").lower().strip()

    if rol not in ("admin", "master"):
        base_sql += """
            WHERE LOWER(e.created_by) = LOWER(%s)
            ORDER BY e.created_at DESC
        """
        cur.execute(base_sql, (usuario,))
    else:
        base_sql += """
            ORDER BY e.created_at DESC
        """
        cur.execute(base_sql)

    rows = cur.fetchall()   # 🔥 FALTABA ESTO

    # ---------------------------------------------------------
    # BLINDAJE FINAL (evita nulls que rompan frontend)
    # ---------------------------------------------------------
    for r in rows:
        if r.get("payload") is None:
            r["payload"] = {}

        if r.get("vacaciones") is None:
            r["vacaciones"] = 0

    return rows


# ============================================================
# CREAR SOLICITUD
# POST /hr/events/
# ============================================================
@router.post("/")
@router.post("")
async def crear_evento(
    request: Request,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # VALIDAR USUARIO LOGEADO
    # --------------------------------------------------------
    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    # --------------------------------------------------------
    # LEER BODY
    # --------------------------------------------------------
    try:
        raw_body = await request.body()
        if not raw_body:
            raise HTTPException(400, "Body vacío")

        body = json.loads(raw_body.decode("utf-8"))
        if not isinstance(body, dict):
            raise HTTPException(400, "Body debe ser un objeto JSON")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "Body no es JSON válido")

    # --------------------------------------------------------
    # CAMPOS BASE
    # --------------------------------------------------------
    event_type = body.get("event_type")
    payload = body.get("payload") or {}
    event_date = body.get("event_date")

    if not event_type or not isinstance(event_type, str):
        raise HTTPException(400, "event_type requerido")

    if not isinstance(payload, dict):
        raise HTTPException(400, "payload debe ser un objeto JSON")

    # --------------------------------------------------------
    # NORMALIZAR FECHA
    # --------------------------------------------------------
    try:
        if event_date:
            event_date = datetime.strptime(event_date, "%Y-%m-%d").date()
        else:
            event_date = date.today()
    except Exception:
        raise HTTPException(400, "event_date inválida (YYYY-MM-DD)")

    # --------------------------------------------------------
    # OBTENER EMPLEADO (FIX SIN ROMPER VALIDACIONES)
    # --------------------------------------------------------
    cur.execute("ALTER TABLE empleados ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE")
    cur.execute("UPDATE empleados SET activo = TRUE WHERE activo IS NULL")
    cur.execute("""
        SELECT nombre, apellidos, fecha_ingreso
        FROM empleados
        WHERE LOWER(usuario) = LOWER(%s)
          AND COALESCE(activo, TRUE) = TRUE
    """, (usuario,))

    emp = cur.fetchone()

    # 🔥 SOLO CAMBIO: evitar 404 pero mantener control
    if not emp:
        empleado_nombre = usuario  # fallback seguro (NO rompe flujo)
    else:
        empleado_nombre = f"{emp.get('nombre','')} {emp.get('apellidos','')}".strip()

        if not empleado_nombre:
            empleado_nombre = usuario  # fallback adicional seguro

    # --------------------------------------------------------
    # LÓGICA ESPECÍFICA VACACIONES (BLINDADA)
    # --------------------------------------------------------
    dias_vacaciones = None

    if event_type.upper() == "VACACIONES":
        dias_solicitados = payload.get("dias_solicitados", payload.get("dias"))

        if dias_solicitados is None:
            fecha_inicio = payload.get("fecha_inicio")
            fecha_fin = payload.get("fecha_fin")

            if not fecha_inicio or not fecha_fin:
                raise HTTPException(
                    400,
                    "VACACIONES requiere payload.dias_solicitados, payload.dias o payload.fecha_inicio y payload.fecha_fin"
                )

            try:
                fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

                if ff < fi:
                    raise ValueError

                dias_solicitados = (ff - fi).days + 1

            except Exception:
                raise HTTPException(
                    400,
                    "Fechas de vacaciones inválidas (YYYY-MM-DD)"
                )

        dias_solicitados = _parse_positive_days(dias_solicitados, "Días de vacaciones")
        tratamiento = str(payload.get("tratamiento_excedente") or "ADELANTO").strip().upper()
        if tratamiento not in {"ADELANTO", "SIN_GOCE"}:
            tratamiento = "ADELANTO"

        disponibles = 0.0
        if emp and emp.get("fecha_ingreso"):
            disponibles = float(_vacation_balance_for_user(cur, usuario, emp["fecha_ingreso"])["dias_disponibles"])

        saldo_usable = max(disponibles, 0)
        if dias_solicitados <= saldo_usable:
            dias_vacaciones = dias_solicitados
            dias_sin_goce = 0.0
            dias_adelanto = 0.0
        elif tratamiento == "SIN_GOCE":
            dias_vacaciones = saldo_usable
            dias_sin_goce = dias_solicitados - saldo_usable
            dias_adelanto = 0.0
        else:
            dias_vacaciones = dias_solicitados
            dias_sin_goce = 0.0
            dias_adelanto = dias_solicitados - saldo_usable

        payload.update({
            "dias_solicitados": dias_solicitados,
            "tratamiento_excedente": tratamiento,
            "dias_vacaciones_aplicadas": round(dias_vacaciones, 2),
            "dias_sin_goce": round(dias_sin_goce, 2),
            "dias_adelanto": round(dias_adelanto, 2),
            "saldo_vacaciones_antes": round(disponibles, 2),
            "saldo_vacaciones_despues": round(disponibles - dias_vacaciones, 2),
        })

    # --------------------------------------------------------
    # INSERT EN hr_events
    # --------------------------------------------------------
    try:
        cur.execute("""
            INSERT INTO hr_events (
                empleado,
                event_type,
                event_date,
                period_year,
                period_month,
                status,
                payload,
                comentario_solicitud,
                vacaciones,
                created_by,
                created_at
            ) VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                'PENDING',
                %s,
                %s,
                %s,
                %s,
                NOW()
            )
            RETURNING id
        """, (
            empleado_nombre,
            event_type.strip(),
            event_date,
            event_date.year,
            event_date.month,
            json.dumps(payload),
            payload.get("motivo"),
            dias_vacaciones,
            usuario
        ))

        row = cur.fetchone()
        notifications_created = _notify_new_request(
            cur,
            row["id"],
            empleado_nombre,
            event_type.strip(),
            usuario,
            payload,
        )
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error creando solicitud: {str(e)}")

    return {
        "status": "OK",
        "id": row["id"],
        "empleado": empleado_nombre,
        "notifications_created": notifications_created
    }


# ============================================================
# APROBAR SOLICITUD
# PATCH /hr/events/{id}/approve
# ============================================================
@router.patch("/{event_id}/approve")
def aprobar_evento(
    event_id: int,
    motivo: dict | None = None,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    rol = (current_user.get("rol") or "").lower()
    if rol not in ("admin", "master"):
        raise HTTPException(403, "No autorizado")

    comentario = motivo.get("comentario") if isinstance(motivo, dict) else None

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        UPDATE hr_events
        SET status = 'APPROVED',
            approved_by = %s,
            approved_at = NOW(),
            comentario_apro_rech = %s
        WHERE id = %s
        RETURNING *
    """, (
        current_user["usuario"],
        comentario,
        event_id
    ))

    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Solicitud no encontrada")

    _notify_request_resolution(cur, row, "Aprobada", current_user["usuario"], comentario)
    conn.commit()
    return row


# ============================================================
# RECHAZAR SOLICITUD
# PATCH /hr/events/{id}/reject
# ============================================================
@router.patch("/{event_id}/reject")
def rechazar_evento(
    event_id: int,
    motivo: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    rol = (current_user.get("rol") or "").lower()
    if rol not in ("admin", "master"):
        raise HTTPException(403, "No autorizado")

    comentario = motivo.get("comentario") if isinstance(motivo, dict) else None
    if not comentario:
        raise HTTPException(400, "comentario requerido para rechazo")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        UPDATE hr_events
        SET status = 'REJECTED',
            approved_by = %s,
            approved_at = NOW(),
            comentario_apro_rech = %s
        WHERE id = %s
        RETURNING *
    """, (
        current_user["usuario"],
        comentario,
        event_id
    ))

    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Solicitud no encontrada")

    _notify_request_resolution(cur, row, "Rechazada", current_user["usuario"], comentario)
    conn.commit()
    return row


# ============================================================
# VACACIONES DISPONIBLES
# GET /hr/events/vacaciones/disponibles
# ============================================================
@router.get("/vacaciones/disponibles")
def vacaciones_disponibles(
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    # ---------------------------------------------------------
    # DATOS DEL EMPLEADO
    # ---------------------------------------------------------
    cur.execute("ALTER TABLE empleados ADD COLUMN IF NOT EXISTS activo BOOLEAN NOT NULL DEFAULT TRUE")
    cur.execute("UPDATE empleados SET activo = TRUE WHERE activo IS NULL")
    cur.execute("""
        SELECT
            id,
            fecha_ingreso,
            vacaciones
        FROM empleados
        WHERE usuario = %s
          AND COALESCE(activo, TRUE) = TRUE
    """, (usuario,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")

    if not emp["fecha_ingreso"]:
        raise HTTPException(400, "Empleado sin fecha de ingreso")

    # ---------------------------------------------------------
    # VACACIONES GENERADAS
    # ---------------------------------------------------------
    dias_generados = calcular_vacaciones(emp["fecha_ingreso"])

    # ---------------------------------------------------------
    # VACACIONES YA SOLICITADAS (PENDING + APPROVED)
    # ---------------------------------------------------------
    cur.execute("""
        SELECT
            COALESCE(SUM(vacaciones), 0) AS dias_solicitados
        FROM hr_events
        WHERE created_by = %s
          AND event_type = 'VACACIONES'
          AND status IN ('PENDING', 'APPROVED')
    """, (usuario,))

    row = cur.fetchone()
    dias_solicitados = float(row["dias_solicitados"] or 0)

    # ---------------------------------------------------------
    # VACACIONES DISPONIBLES REALES
    # ---------------------------------------------------------
    dias_disponibles = round(dias_generados - dias_solicitados, 2)

    # ---------------------------------------------------------
    # SINCRONIZAR EMPLEADOS (OPCIONAL, COMO YA LO TENÍAS)
    # ---------------------------------------------------------
    if emp["vacaciones"] != dias_disponibles:
        cur.execute("""
            UPDATE empleados
            SET vacaciones = %s
            WHERE id = %s
        """, (dias_disponibles, emp["id"]))
        conn.commit()

    return {
        "dias_generados": round(dias_generados, 2),
        "dias_solicitados": round(dias_solicitados, 2),
        "dias_disponibles": round(dias_disponibles, 2)
    }
