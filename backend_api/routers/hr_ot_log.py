from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import date, datetime
import unicodedata

from database import get_db
from security.rbac import require_permission
from security.auth import get_current_user


router = APIRouter(
    prefix="/hr/ot-log",
    tags=["HHRR - REGISTRO DE HORAS"]
)

# ============================================================
# HELPERS
# ============================================================

def _ensure_ot_log_schema(conn):
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hr_ot_log (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL,
            tipo TEXT NOT NULL,
            fecha_inicio TIMESTAMP NOT NULL,
            fecha_fin TIMESTAMP NOT NULL,
            duracion_horas NUMERIC(10,2) NOT NULL DEFAULT 0,
            buque TEXT,
            contenedor TEXT,
            referencia TEXT,
            actividad_detalle TEXT,
            comentario TEXT,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    for ddl in (
        "ALTER TABLE hr_ot_log ADD COLUMN IF NOT EXISTS contenedor TEXT",
        "ALTER TABLE hr_ot_log ADD COLUMN IF NOT EXISTS referencia TEXT",
        "ALTER TABLE hr_ot_log ADD COLUMN IF NOT EXISTS actividad_detalle TEXT",
        "ALTER TABLE hr_ot_log ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT now()",
    ):
        cur.execute(ddl)
    conn.commit()


def _clean_text(value) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.lower().split())


def _employee_hours_policy(emp: dict) -> dict:
    full_name = _clean_text(f"{emp.get('nombre', '')} {emp.get('apellidos', '')}")
    contracted = float(emp.get("horas_contratadas") or 0)
    salary = float(emp.get("salario") or 0)

    policy = {
        "tope_ordinario": contracted,
        "tope_maximo": 0,
        "tarifa_hora_extra": 0,
        "salario_base_mensual": salary,
        "pago_minimo_garantizado": bool(contracted),
    }

    if "manfred" in full_name:
        policy.update({
            "tope_ordinario": 150,
            "tope_maximo": 192,
            "tarifa_hora_extra": 2800,
            "salario_base_mensual": 600000,
            "pago_minimo_garantizado": True,
        })
    elif "erasmo" in full_name:
        policy.update({
            "tope_ordinario": 60,
            "tope_maximo": 120,
            "tarifa_hora_extra": 0,
            "salario_base_mensual": 425000,
            "pago_minimo_garantizado": True,
        })
    elif "jafeth" in full_name:
        policy.update({
            "tarifa_hora_extra": 2800,
            "pago_minimo_garantizado": bool(contracted),
        })

    return policy


def _normalize_rol(user: dict, conn) -> str:
    rol = (user.get("rol") or "").strip().lower()
    if rol:
        user["rol"] = rol
        return rol

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT rol FROM usuarios WHERE usuario = %s LIMIT 1",
        (user["usuario"],)
    )
    row = cur.fetchone()
    rol_db = (row["rol"] or "").lower() if row else ""
    user["rol"] = rol_db
    return rol_db


# ============================================================
# 🔥 FIX CRÍTICO — EMPLEADO POR USUARIO (SIN ROMPER 404)
# ============================================================
def _get_empleado_by_usuario(usuario: str, conn) -> dict:
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            id,
            nombre,
            apellidos,
            jornada,
            salario,
            pago,
            horas_contratadas,
            usuario
        FROM empleados
        WHERE lower(usuario) = lower(%s)
        LIMIT 1
        """,
        (usuario,)
    )

    emp = cur.fetchone()

    # 🔥 FIX: NO REVENTAR 404 → devolver estructura segura
    if not emp:
        return {
            "id": None,
            "nombre": "",
            "apellidos": "",
            "jornada": "",
            "salario": 0,
            "pago": "",
            "horas_contratadas": 0,
            "usuario": usuario
        }

    return emp


def _sumar_horas(usuario: str, conn, year=None, month=None) -> float:
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _ensure_ot_log_schema(conn)

    query = """
        SELECT COALESCE(SUM(duracion_horas), 0) AS total
        FROM hr_ot_log
        WHERE usuario = %s
          AND COALESCE(estado, 'PENDIENTE') <> 'RECHAZADO'
    """
    params = [usuario]

    if year:
        query += " AND EXTRACT(YEAR FROM fecha_inicio) = %s"
        params.append(year)

    if month:
        query += " AND EXTRACT(MONTH FROM fecha_inicio) = %s"
        params.append(month)

    cur.execute(query, params)
    return float(cur.fetchone()["total"] or 0)


def _build_hours_summary(usuario: str, conn, year=None, month=None) -> dict:
    today = date.today()
    year = year or today.year
    month = month or today.month
    emp = _get_empleado_by_usuario(usuario, conn)
    policy = _employee_hours_policy(emp)
    horas_usadas = _sumar_horas(usuario, conn, year, month)

    tope_ordinario = float(policy.get("tope_ordinario") or 0)
    tope_maximo = float(policy.get("tope_maximo") or 0)
    tarifa_extra = float(policy.get("tarifa_hora_extra") or 0)
    horas_extra = max(horas_usadas - tope_ordinario, 0) if tope_ordinario else 0
    excede_maximo = bool(tope_maximo and horas_usadas > tope_maximo)

    if excede_maximo:
        alert_level = "OVER_MAX"
        mensaje = f"{usuario} excedio el segundo tope de {tope_maximo:.2f} horas."
    elif tope_ordinario and horas_usadas >= tope_ordinario:
        alert_level = "LIMIT"
        mensaje = f"{usuario} ya cumplio el tope ordinario de {tope_ordinario:.2f} horas."
    elif tope_ordinario and horas_usadas >= tope_ordinario * 0.85:
        alert_level = "WARNING"
        mensaje = f"{usuario} esta cerca del tope ordinario."
    else:
        alert_level = "OK"
        mensaje = f"{usuario} tiene horas ordinarias disponibles."

    return {
        "usuario": usuario,
        "empleado": emp,
        "year": year,
        "month": month,
        "horas_contratadas": round(tope_ordinario, 2),
        "horas_registradas": round(horas_usadas, 2),
        "horas_pendientes": round(max(tope_ordinario - horas_usadas, 0), 2),
        "tope_ordinario": round(tope_ordinario, 2),
        "tope_maximo": round(tope_maximo, 2),
        "horas_extra": round(horas_extra, 2),
        "tarifa_hora_extra": round(tarifa_extra, 2),
        "monto_extra_estimado": round(horas_extra * tarifa_extra, 2),
        "salario_base_mensual": round(float(policy.get("salario_base_mensual") or 0), 2),
        "pago_minimo_garantizado": bool(policy.get("pago_minimo_garantizado")),
        "alert_level": alert_level,
        "mensaje": mensaje,
    }


# ============================================================
# RESUMEN SUPERIOR (HEADER HORAS)
# ============================================================
@router.get(
    "/me/summary",
    dependencies=[Depends(require_permission("hhrre", "hours_view"))]
)
def my_hours_summary(
    year: int | None = None,
    month: int | None = None,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    rol = _normalize_rol(user, conn)
    summary = _build_hours_summary(user["usuario"], conn, year, month)
    summary["rol"] = rol
    return summary


@router.get(
    "/summary",
    dependencies=[Depends(require_permission("hhrre", "hours_view"))]
)
def hours_summary(
    year: int | None = None,
    month: int | None = None,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    rol = _normalize_rol(user, conn)
    is_admin = rol in ("admin", "master")

    if not is_admin:
        return {"data": [_build_hours_summary(user["usuario"], conn, year, month)]}

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT usuario
        FROM empleados
        WHERE usuario IS NOT NULL
          AND TRIM(usuario) <> ''
          AND COALESCE(estado, 'Activo') = 'Activo'
        ORDER BY usuario
        """
    )
    rows = cur.fetchall() or []
    return {"data": [_build_hours_summary(row["usuario"], conn, year, month) for row in rows]}


# ============================================================
# CREAR REGISTRO DE HORAS
# ============================================================
@router.post(
    "/",
    dependencies=[Depends(require_permission("hhrre", "hours_register"))]
)
@router.post(
    "",
    dependencies=[Depends(require_permission("hhrre", "hours_register"))]
)
def create_ot_log(
    data: dict,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _ensure_ot_log_schema(conn)
    _normalize_rol(user, conn)

    _get_empleado_by_usuario(user["usuario"], conn)

    for k in ("tipo", "fecha_inicio", "fecha_fin"):
        if k not in data:
            raise HTTPException(400, "Datos incompletos")

    tipo = data["tipo"].upper()
    if tipo not in ("OPERACION", "INFORME"):
        raise HTTPException(400, "Tipo inválido")

    try:
        inicio = datetime.fromisoformat(data["fecha_inicio"])
        fin = datetime.fromisoformat(data["fecha_fin"])
    except Exception:
        raise HTTPException(400, "Formato de fecha inválido")

    if fin <= inicio:
        raise HTTPException(400, "fecha_fin debe ser mayor a fecha_inicio")

    duracion = round((fin - inicio).total_seconds() / 3600, 2)
    if duracion <= 0:
        raise HTTPException(400, "Duración inválida")

    referencia_tipo = (data.get("referencia_tipo") or "").strip().upper()
    referencia = (data.get("referencia") or data.get("buque") or data.get("contenedor") or "").strip() or None
    buque = (data.get("buque") or "").strip() or None
    contenedor = (data.get("contenedor") or "").strip() or None

    if referencia_tipo == "CONTENEDOR" and referencia and not contenedor:
        contenedor = referencia
    elif referencia and not buque:
        buque = referencia

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        INSERT INTO hr_ot_log (
            usuario,
            tipo,
            fecha_inicio,
            fecha_fin,
            duracion_horas,
            buque,
            contenedor,
            referencia,
            actividad_detalle,
            comentario,
            estado,
            created_at,
            updated_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDIENTE',now(),now())
        RETURNING *
        """,
        (
            user["usuario"],
            tipo,
            inicio,
            fin,
            duracion,
            buque,
            contenedor,
            referencia,
            data.get("actividad_detalle"),
            data.get("comentario")
        )
    )

    row = cur.fetchone()
    conn.commit()
    row["hours_status"] = _build_hours_summary(user["usuario"], conn, inicio.year, inicio.month)
    return row


# ============================================================
# LISTADO PAGINADO
# ============================================================
@router.get(
    "/",
    dependencies=[Depends(require_permission("hhrre", "hours_view"))]
)
@router.get(
    "",
    dependencies=[Depends(require_permission("hhrre", "hours_view"))]
)
def list_ot_logs(
    page: int = 1,
    page_size: int = 50,
    usuario: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    year: int | None = None,
    month: int | None = None,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _ensure_ot_log_schema(conn)
    rol = _normalize_rol(user, conn)
    is_admin = rol in ("admin", "master")

    page_size = min(max(page_size, 1), 200)
    offset = (page - 1) * page_size

    where = ["1=1"]
    params = []

    if is_admin and usuario:
        where.append("usuario = %s")
        params.append(usuario)
    elif not is_admin:
        where.append("usuario = %s")
        params.append(user["usuario"])

    if tipo:
        where.append("tipo = %s")
        params.append(tipo.upper())

    if estado:
        where.append("estado = %s")
        params.append(estado.upper())

    if year:
        where.append("EXTRACT(YEAR FROM fecha_inicio) = %s")
        params.append(year)

    if month:
        where.append("EXTRACT(MONTH FROM fecha_inicio) = %s")
        params.append(month)

    where_sql = " AND ".join(where)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        f"SELECT COUNT(*) AS total FROM hr_ot_log WHERE {where_sql}",
        params
    )
    total = cur.fetchone()["total"]

    cur.execute(
        f"""
        SELECT *
        FROM hr_ot_log
        WHERE {where_sql}
        ORDER BY fecha_inicio DESC
        LIMIT %s OFFSET %s
        """,
        params + [page_size, offset]
    )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": cur.fetchall()
    }


@router.put(
    "/{log_id}",
    dependencies=[Depends(require_permission("hhrre", "hours_register"))]
)
def update_ot_log(
    log_id: int,
    data: dict,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _ensure_ot_log_schema(conn)
    rol = _normalize_rol(user, conn)
    is_admin = rol in ("admin", "master")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM hr_ot_log WHERE id = %s", (log_id,))
    current = cur.fetchone()
    if not current:
        raise HTTPException(404, "Registro no encontrado")
    if not is_admin and current["usuario"] != user["usuario"]:
        raise HTTPException(403, "No autorizado para modificar este registro")

    tipo = (data.get("tipo") or current.get("tipo") or "").upper()
    if tipo not in ("OPERACION", "INFORME"):
        raise HTTPException(400, "Tipo inválido")

    try:
        inicio = datetime.fromisoformat(data.get("fecha_inicio") or str(current["fecha_inicio"]))
        fin = datetime.fromisoformat(data.get("fecha_fin") or str(current["fecha_fin"]))
    except Exception:
        raise HTTPException(400, "Formato de fecha inválido")

    if fin <= inicio:
        raise HTTPException(400, "fecha_fin debe ser mayor a fecha_inicio")

    duracion = round((fin - inicio).total_seconds() / 3600, 2)
    referencia_tipo = (data.get("referencia_tipo") or "").strip().upper()
    referencia = (data.get("referencia") or data.get("buque") or data.get("contenedor") or current.get("referencia") or "").strip() or None
    buque = (data.get("buque") or current.get("buque") or "").strip() or None
    contenedor = (data.get("contenedor") or current.get("contenedor") or "").strip() or None

    if referencia_tipo == "CONTENEDOR" and referencia and not contenedor:
        contenedor = referencia
    elif referencia and not buque:
        buque = referencia

    cur.execute(
        """
        UPDATE hr_ot_log
        SET tipo = %s,
            fecha_inicio = %s,
            fecha_fin = %s,
            duracion_horas = %s,
            buque = %s,
            contenedor = %s,
            referencia = %s,
            actividad_detalle = %s,
            comentario = %s,
            updated_at = now()
        WHERE id = %s
        RETURNING *
        """,
        (
            tipo,
            inicio,
            fin,
            duracion,
            buque,
            contenedor,
            referencia,
            data.get("actividad_detalle", current.get("actividad_detalle")),
            data.get("comentario", current.get("comentario")),
            log_id,
        )
    )
    updated = cur.fetchone()
    conn.commit()
    return updated


# ============================================================
# ELIMINAR REGISTRO
# ============================================================
@router.delete(
    "/{log_id}",
    dependencies=[Depends(require_permission("hhrre", "hours_approve"))]
)
def delete_ot_log(
    log_id: int,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    rol = _normalize_rol(user, conn)
    is_admin = rol in ("admin", "master")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "SELECT usuario FROM hr_ot_log WHERE id = %s",
        (log_id,)
    )
    row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Registro no encontrado")

    if not is_admin and row["usuario"] != user["usuario"]:
        raise HTTPException(403, "No autorizado para eliminar este registro")

    cur.execute(
        "DELETE FROM hr_ot_log WHERE id = %s RETURNING id",
        (log_id,)
    )
    conn.commit()
    return {"deleted_id": log_id}


# ============================================================
# UPDATE OT LOG STATUS
# ============================================================
@router.put(
    "/{log_id}/estado",
    dependencies=[Depends(require_permission("hhrre", "hours_approve"))]
)
def update_ot_log_estado(
    log_id: int,
    payload: dict,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _normalize_rol(user, conn)

    estado = (payload.get("estado") or "").strip().upper()

    if estado not in ("PENDIENTE", "APROBADO", "RECHAZADO"):
        raise HTTPException(
            status_code=400,
            detail="Estado inválido"
        )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT id FROM hr_ot_log WHERE id = %s",
        (log_id,)
    )

    if not cur.fetchone():
        raise HTTPException(404, "Registro no encontrado")

    cur.execute(
        """
        UPDATE hr_ot_log
        SET estado = %s
        WHERE id = %s
        RETURNING *
        """,
        (estado, log_id)
    )

    updated = cur.fetchone()
    conn.commit()

    return updated
