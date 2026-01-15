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
    if rol == "user":
        base_sql += """
            WHERE e.created_by = %s
            ORDER BY e.created_at DESC
        """
        cur.execute(base_sql, (usuario,))
    else:
        base_sql += """
            ORDER BY e.created_at DESC
        """
        cur.execute(base_sql)

    return cur.fetchall()


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
    # LÓGICA ESPECÍFICA VACACIONES (BLINDADA)
    # --------------------------------------------------------
    dias_vacaciones = None

    if event_type.upper() == "VACACIONES":

        dias_vacaciones = payload.get("dias")

        # Si no viene "dias", calcular por fechas
        if dias_vacaciones is None:

            fecha_inicio = payload.get("fecha_inicio")
            fecha_fin = payload.get("fecha_fin")

            if not fecha_inicio or not fecha_fin:
                raise HTTPException(
                    400,
                    "VACACIONES requiere payload.dias o payload.fecha_inicio y payload.fecha_fin"
                )

            try:
                fi = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                ff = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

                if ff < fi:
                    raise ValueError

                dias_vacaciones = (ff - fi).days + 1

            except Exception:
                raise HTTPException(
                    400,
                    "Fechas de vacaciones inválidas (YYYY-MM-DD)"
                )

        # Validación final
        try:
            dias_vacaciones = float(dias_vacaciones)
            if dias_vacaciones <= 0:
                raise ValueError
        except Exception:
            raise HTTPException(
                400,
                "Días de vacaciones inválidos"
            )

    # --------------------------------------------------------
    # OBTENER EMPLEADO
    # --------------------------------------------------------
    cur.execute("""
        SELECT nombre, apellidos
        FROM empleados
        WHERE usuario = %s
    """, (usuario,))

    emp = cur.fetchone()
    if not emp:
        raise HTTPException(
            404,
            f"Empleado no encontrado para usuario '{usuario}'"
        )

    empleado_nombre = f"{emp['nombre']} {emp['apellidos']}".strip()
    if not empleado_nombre:
        raise HTTPException(400, "Nombre del empleado inválido")

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
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise HTTPException(500, f"Error creando solicitud: {str(e)}")

    return {
        "status": "OK",
        "id": row["id"],
        "empleado": empleado_nombre
    }


# ============================================================
# APROBAR SOLICITUD
# PATCH /hr/events/{id}/approve
# ============================================================
@router.patch("/{event_id}/approve")
def aprobar_evento(
    event_id: int,
    motivo: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    if current_user.get("rol") not in ("admin", "master"):
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
    cur.execute("""
        SELECT
            id,
            fecha_ingreso,
            vacaciones
        FROM empleados
        WHERE usuario = %s
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
    dias_disponibles = dias_generados - dias_solicitados
    if dias_disponibles < 0:
        dias_disponibles = 0.0

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
