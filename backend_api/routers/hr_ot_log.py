from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

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

    query = """
        SELECT COALESCE(SUM(duracion_horas), 0) AS total
        FROM hr_ot_log
        WHERE usuario = %s
    """
    params = [usuario]

    if year:
        query += " AND EXTRACT(YEAR FROM created_at) = %s"
        params.append(year)

    if month:
        query += " AND EXTRACT(MONTH FROM created_at) = %s"
        params.append(month)

    cur.execute(query, params)
    return float(cur.fetchone()["total"] or 0)


# ============================================================
# RESUMEN SUPERIOR (HEADER HORAS)
# ============================================================
@router.get(
    "/me/summary",
    dependencies=[Depends(require_permission("hhrr", "ot_log"))]
)
def my_hours_summary(
    year: int | None = None,
    month: int | None = None,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
    rol = _normalize_rol(user, conn)

    emp = _get_empleado_by_usuario(user["usuario"], conn)

    horas_contratadas = float(emp["horas_contratadas"] or 0)
    horas_usadas = _sumar_horas(user["usuario"], conn, year, month)

    return {
        "usuario": user["usuario"],
        "rol": rol,
        "empleado": emp,
        "horas_contratadas": horas_contratadas,
        "horas_registradas": round(horas_usadas, 2),
        "horas_pendientes": round(max(horas_contratadas - horas_usadas, 0), 2)
    }


# ============================================================
# CREAR REGISTRO DE HORAS
# ============================================================
@router.post(
    "/",
    dependencies=[Depends(require_permission("hhrr", "ot_log"))]
)
def create_ot_log(
    data: dict,
    user=Depends(get_current_user),
    conn=Depends(get_db)
):
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
            comentario,
            estado,
            created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,'PENDIENTE',now())
        RETURNING *
        """,
        (
            user["usuario"],
            tipo,
            inicio,
            fin,
            duracion,
            data.get("buque"),
            data.get("comentario")
        )
    )

    row = cur.fetchone()
    conn.commit()
    return row


# ============================================================
# LISTADO PAGINADO
# ============================================================
@router.get(
    "/",
    dependencies=[Depends(require_permission("hhrr", "ot_log"))]
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
        where.append("EXTRACT(YEAR FROM created_at) = %s")
        params.append(year)

    if month:
        where.append("EXTRACT(MONTH FROM created_at) = %s")
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


# ============================================================
# ELIMINAR REGISTRO
# ============================================================
@router.delete(
    "/{log_id}",
    dependencies=[Depends(require_permission("hhrr", "delete"))]
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
    dependencies=[Depends(require_permission("hhrr", "approve"))]
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