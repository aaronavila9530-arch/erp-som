from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db
from security.rbac import require_permission
from security.auth import get_current_user


router = APIRouter(
    prefix="/hr/ot-log",
    tags=["HHRR - OT LOG"]
)

# ============================================================
# CREATE OT LOG
# ACTION: ot_log
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
    required = [
        "tipo",
        "fecha_inicio",
        "fecha_fin",
        "duracion_horas"
    ]

    if not all(k in data for k in required):
        raise HTTPException(
            status_code=400,
            detail="Datos incompletos para OT LOG"
        )

    if data["tipo"] not in ("OPERACION", "INFORME"):
        raise HTTPException(
            status_code=400,
            detail="Tipo inválido"
        )

    try:
        fecha_inicio = datetime.fromisoformat(data["fecha_inicio"])
        fecha_fin = datetime.fromisoformat(data["fecha_fin"])
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Formato de fecha inválido"
        )

    if fecha_fin <= fecha_inicio:
        raise HTTPException(
            status_code=400,
            detail="La fecha_fin debe ser mayor a fecha_inicio"
        )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        INSERT INTO hr_ot_log (
            usuario,
            tipo,
            fecha_inicio,
            fecha_fin,
            duracion_horas,
            buque,
            comentario,
            created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,now())
        RETURNING *
    """, (
        user["usuario"],
        data["tipo"],
        fecha_inicio,
        fecha_fin,
        data["duracion_horas"],
        data.get("buque"),
        data.get("comentario")
    ))

    row = cur.fetchone()
    conn.commit()
    return row


# ============================================================
# LIST OT LOGS
# ACTION: ot_log
# ============================================================
@router.get(
    "/",
    dependencies=[Depends(require_permission("hhrr", "ot_log"))]
)
def list_ot_logs(
    usuario: str | None = None,
    tipo: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    query = "SELECT * FROM hr_ot_log WHERE 1=1"
    params = []

    if usuario:
        query += " AND usuario = %s"
        params.append(usuario)

    if tipo:
        query += " AND tipo = %s"
        params.append(tipo)

    if fecha_desde:
        query += " AND fecha_inicio >= %s"
        params.append(fecha_desde)

    if fecha_hasta:
        query += " AND fecha_fin <= %s"
        params.append(fecha_hasta)

    query += " ORDER BY fecha_inicio DESC"

    cur.execute(query, params)
    return cur.fetchall()


# ============================================================
# DELETE OT LOG
# ACTION: delete
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
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        DELETE FROM hr_ot_log
        WHERE id = %s
        RETURNING id
    """, (log_id,))

    row = cur.fetchone()
    conn.commit()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Registro OT no encontrado"
        )

    return {"deleted_id": row["id"]}
