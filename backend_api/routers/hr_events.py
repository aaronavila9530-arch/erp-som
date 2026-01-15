from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json

from database import get_db
from security.auth import get_current_user


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
    dias_acumulados = meses * (14 / 12)

    return round(dias_acumulados, 2)


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

    # --------------------------------------------------------
    # USER → solo sus solicitudes
    # ADMIN / MASTER → todas
    # --------------------------------------------------------
    if rol == "user":
        cur.execute("""
            SELECT
                e.id,
                emp.nombre || ' ' || emp.apellidos AS empleado,
                e.event_type,
                e.event_date,
                (e.period_year || '-' || e.period_month) AS period,
                e.status,
                e.created_at
            FROM hr_events e
            JOIN empleados emp ON emp.id = e.empleado_id
            WHERE emp.usuario = %s
            ORDER BY e.created_at DESC
        """, (usuario,))
    else:
        cur.execute("""
            SELECT
                e.id,
                emp.nombre || ' ' || emp.apellidos AS empleado,
                e.event_type,
                e.event_date,
                (e.period_year || '-' || e.period_month) AS period,
                e.status,
                e.created_at
            FROM hr_events e
            JOIN empleados emp ON emp.id = e.empleado_id
            ORDER BY e.created_at DESC
        """)

    return cur.fetchall()


# ============================================================
# CREAR SOLICITUD
# POST /hr/events/
# ============================================================
@router.post("/")
async def crear_evento(
    request: Request,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # VALIDAR USUARIO
    # --------------------------------------------------------
    usuario = current_user.get("usuario")
    if not usuario:
        raise HTTPException(401, "Usuario no autenticado")

    # --------------------------------------------------------
    # LEER BODY CRUDO (100% CONTROLADO)
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
    # VALIDAR CAMPOS BASE
    # --------------------------------------------------------
    event_type = body.get("event_type")
    payload = body.get("payload", {})
    event_date = body.get("event_date")

    if not event_type or not isinstance(event_type, str):
        raise HTTPException(400, "event_type requerido y debe ser string")

    if payload is not None and not isinstance(payload, dict):
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
    # OBTENER EMPLEADO
    # --------------------------------------------------------
    cur.execute("""
        SELECT id
        FROM empleados
        WHERE usuario = %s
    """, (usuario,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(
            404,
            f"Empleado no encontrado para usuario '{usuario}'"
        )

    # --------------------------------------------------------
    # INSERT TRANSACCIONAL
    # --------------------------------------------------------
    try:
        cur.execute("""
            INSERT INTO hr_events (
                empleado_id,
                event_type,
                event_date,
                period_year,
                period_month,
                status,
                payload,
                created_by,
                created_at
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                'PENDING',
                %s,
                %s,
                NOW()
            )
            RETURNING id
        """, (
            emp["id"],
            event_type.strip(),
            event_date,
            event_date.year,
            event_date.month,
            json.dumps(payload),
            usuario
        ))

        row = cur.fetchone()
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error creando solicitud: {str(e)}")

    return {
        "status": "OK",
        "id": row["id"]
    }


# ============================================================
# APROBAR SOLICITUD
# PATCH /hr/events/{id}/approve
# ============================================================
@router.patch("/{event_id}/approve")
def aprobar_evento(
    event_id: int,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    if current_user.get("rol") not in ("admin", "master"):
        raise HTTPException(403, "No autorizado")

    cur = conn.cursor()

    cur.execute("""
        UPDATE hr_events
        SET status = 'APPROVED',
            approved_by = %s,
            approved_at = NOW()
        WHERE id = %s
    """, (current_user["usuario"], event_id))

    if cur.rowcount == 0:
        raise HTTPException(404, "Solicitud no encontrada")

    conn.commit()
    return {"status": "OK"}


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
    if current_user.get("rol") not in ("admin", "master"):
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
            payload = payload || %s::jsonb
        WHERE id = %s
        RETURNING *
    """, (
        current_user["usuario"],
        json.dumps({"motivo_rechazo": comentario}),
        event_id
    ))

    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Solicitud no encontrada")

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

    cur.execute("""
        SELECT id, fecha_ingreso, vacaciones
        FROM empleados
        WHERE usuario = %s
    """, (usuario,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")

    if not emp["fecha_ingreso"]:
        raise HTTPException(400, "Empleado sin fecha de ingreso")

    dias_calculados = calcular_vacaciones(emp["fecha_ingreso"])

    if emp["vacaciones"] != dias_calculados:
        cur.execute("""
            UPDATE empleados
            SET vacaciones = %s
            WHERE id = %s
        """, (dias_calculados, emp["id"]))
        conn.commit()

    return {
        "dias_disponibles": dias_calculados
    }
