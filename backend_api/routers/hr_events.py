from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import date, datetime


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
    if fecha_ingreso > hoy:
        return 0.0

    delta = relativedelta(hoy, fecha_ingreso)
    meses = delta.years * 12 + delta.months

    dias_acumulados = meses * (14 / 12)
    return round(dias_acumulados, 2)


# ============================================================
# LISTAR SOLICITUDES
# ============================================================
@router.get("")
def listar_eventos(
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    rol = current_user["rol"]
    usuario = current_user["usuario"]

    if rol == "user":
        cur.execute("""
            SELECT e.*
            FROM hr_events e
            JOIN empleados emp ON emp.id = e.empleado_id
            WHERE emp.usuario = %s
            ORDER BY e.created_at DESC
        """, (usuario,))
    else:
        cur.execute("""
            SELECT *
            FROM hr_events
            ORDER BY created_at DESC
        """)

    return cur.fetchall()


# ============================================================
# CREAR SOLICITUD
# ============================================================
@router.post("")
def crear_evento(
    payload: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    event_type = payload.get("event_type")
    event_date = payload.get("event_date")
    event_payload = payload.get("payload")

    if not event_type or not isinstance(event_payload, dict):
        raise HTTPException(400, "Datos incompletos")

    # --------------------------------------------------------
    # OBTENER EMPLEADO
    # --------------------------------------------------------
    cur.execute("""
        SELECT id
        FROM empleados
        WHERE usuario = %s
    """, (current_user["usuario"],))
    empleado = cur.fetchone()

    if not empleado:
        raise HTTPException(404, "Empleado no encontrado")

    empleado_id = empleado["id"]

    # --------------------------------------------------------
    # INSERT (SIN VALIDACIONES DE NEGOCIO)
    # --------------------------------------------------------
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
        RETURNING *
    """, (
        empleado_id,
        event_type,
        event_date or date.today(),
        date.today().year,
        date.today().month,
        event_payload,
        current_user["usuario"]
    ))

    conn.commit()
    return cur.fetchone()


# ============================================================
# APROBAR SOLICITUD
# ============================================================
@router.patch("/{event_id}/approve")
def aprobar_evento(
    event_id: int,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    if current_user["rol"] not in ("admin", "master"):
        raise HTTPException(403, "No autorizado")

    cur = conn.cursor()

    cur.execute("""
        UPDATE hr_events
        SET status = 'APPROVED',
            approved_by = %s,
            approved_at = NOW()
        WHERE id = %s
    """, (current_user["usuario"], event_id))

    conn.commit()
    return {"status": "OK"}


# ============================================================
# RECHAZAR SOLICITUD
# ============================================================
@router.patch("/{event_id}/reject")
def rechazar_evento(
    event_id: int,
    motivo: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    if current_user["rol"] not in ("admin", "master"):
        raise HTTPException(403, "No autorizado")

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
        {"motivo_rechazo": motivo.get("comentario")},
        event_id
    ))

    conn.commit()
    return cur.fetchone()

# ============================================================
# CONSULTAR + ACTUALIZAR VACACIONES DISPONIBLES
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

    # 🔎 Buscar empleado REAL
    cur.execute("""
        SELECT id, fecha_ingreso, vacaciones
        FROM empleados
        WHERE usuario = %s
    """, (usuario,))

    emp = cur.fetchone()

    if not emp:
        raise HTTPException(
            404,
            f"Empleado no encontrado para usuario '{usuario}'"
        )

    if not emp["fecha_ingreso"]:
        raise HTTPException(400, "Empleado sin fecha de ingreso")

    # 🧮 Calcular vacaciones
    dias_calculados = calcular_vacaciones(emp["fecha_ingreso"])

    # 🔁 Solo actualizar si cambió
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
