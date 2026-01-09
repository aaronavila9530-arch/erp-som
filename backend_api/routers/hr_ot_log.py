from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db
from backend_api.security.rbac import require_permission

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
    dependencies=[Depends(require_permission("hhrre", "ot_log"))]
)
def create_ot_log(data: dict, conn=Depends(get_db)):

    required = [
        "usuario",
        "tipo",
        "fecha_inicio",
        "fecha_fin",
        "duracion_horas"
    ]

    if not all(k in data for k in required):
        raise HTTPException(400, "Datos incompletos para OT LOG")

    if data["tipo"] not in ("OPERACION", "INFORME"):
        raise HTTPException(400, "Tipo inválido (OPERACION / INFORME)")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        INSERT INTO hr_ot_log (
            usuario,
            tipo,
            fecha_inicio,
            fecha_fin,
            duracion_horas,
            buque,
            comentario
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        RETURNING *
    """, (
        data["usuario"],
        data["tipo"],
        data["fecha_inicio"],
        data["fecha_fin"],
        data["duracion_horas"],
        data.get("buque"),
        data.get("comentario")
    ))

    row = cur.fetchone()
    conn.commit()

    return row


# ============================================================
# LIST OT LOGS (filters)
# ACTION: ot_log
# ============================================================
@router.get(
    "/",
    dependencies=[Depends(require_permission("hhrre", "ot_log"))]
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
    dependencies=[Depends(require_permission("hhrre", "delete"))]
)
def delete_ot_log(log_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        DELETE FROM hr_ot_log
        WHERE id = %s
        RETURNING id
    """, (log_id,))

    row = cur.fetchone()
    conn.commit()

    if not row:
        raise HTTPException(404, "Registro OT no encontrado")

    return {"deleted_id": row["id"]}
