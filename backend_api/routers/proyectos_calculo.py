# ============================================================
# ROUTER — PROYECTOS CALCULO
# Tabla: proyectos_calculo
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db


router = APIRouter(
    prefix="/proyectos-calculo",
    tags=["Proyectos — Cálculo"]
)

# ============================================================
# POST — CREAR PROYECTO / CALCULO
# ============================================================
@router.post("")
def create_proyecto_calculo(payload: dict, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        if not payload.get("nombre_proyecto"):
            raise HTTPException(
                status_code=400,
                detail="nombre_proyecto is required"
            )

        sql = """
        INSERT INTO proyectos_calculo (
            nombre_proyecto,
            personal,
            costo,
            moneda,
            tiempo,
            total_honorarios,
            gasto_alimentacion,
            gasto_comunicacion,
            gasto_transporte,
            total_gastos,
            margen,
            precio,
            utilidad,
            comentarios
        )
        VALUES (
            %(nombre_proyecto)s,
            %(personal)s,
            %(costo)s,
            %(moneda)s,
            %(tiempo)s,
            %(total_honorarios)s,
            %(gasto_alimentacion)s,
            %(gasto_comunicacion)s,
            %(gasto_transporte)s,
            %(total_gastos)s,
            %(margen)s,
            %(precio)s,
            %(utilidad)s,
            %(comentarios)s
        )
        RETURNING id;
        """

        # Defaults seguros
        data = {
            "nombre_proyecto": payload.get("nombre_proyecto"),
            "personal": payload.get("personal", 0),
            "costo": payload.get("costo", 0),
            "moneda": payload.get("moneda", "USD"),
            "tiempo": payload.get("tiempo", 0),
            "total_honorarios": payload.get("total_honorarios", 0),
            "gasto_alimentacion": payload.get("gasto_alimentacion", 0),
            "gasto_comunicacion": payload.get("gasto_comunicacion", 0),
            "gasto_transporte": payload.get("gasto_transporte", 0),
            "total_gastos": payload.get("total_gastos", 0),
            "margen": payload.get("margen", 0),
            "precio": payload.get("precio", 0),
            "utilidad": payload.get("utilidad", 0),
            "comentarios": payload.get("comentarios"),
        }

        cur.execute(sql, data)
        new_id = cur.fetchone()["id"]
        conn.commit()

        return {
            "success": True,
            "id": new_id
        }

    except HTTPException:
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cur.close()


# ============================================================
# GET — LISTAR PROYECTOS
# ============================================================
@router.get("")
def list_proyectos_calculo(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM proyectos_calculo
        ORDER BY creado_el DESC
    """)

    rows = cur.fetchall() or []
    cur.close()

    return {
        "total": len(rows),
        "data": rows
    }


# ============================================================
# GET — OBTENER POR ID
# ============================================================
@router.get("/{proyecto_id}")
def get_proyecto_calculo(
    proyecto_id: int,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT * FROM proyectos_calculo WHERE id = %s;",
        (proyecto_id,)
    )

    row = cur.fetchone()
    cur.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Proyecto no encontrado"
        )

    return {
        "data": row
    }


# ============================================================
# PUT — ACTUALIZAR PROYECTO
# ============================================================
@router.put("/{proyecto_id}")
def update_proyecto_calculo(
    proyecto_id: int,
    payload: dict,
    conn=Depends(get_db)
):
    if not payload:
        raise HTTPException(
            status_code=400,
            detail="No data provided"
        )

    allowed_fields = {
        "nombre_proyecto",
        "personal",
        "costo",
        "moneda",
        "tiempo",
        "total_honorarios",
        "gasto_alimentacion",
        "gasto_comunicacion",
        "gasto_transporte",
        "total_gastos",
        "margen",
        "precio",
        "utilidad",
        "comentarios",
    }

    clean_payload = {
        k: v for k, v in payload.items()
        if k in allowed_fields
    }

    if not clean_payload:
        raise HTTPException(
            status_code=400,
            detail="No valid fields to update"
        )

    clean_payload["id"] = proyecto_id

    fields_sql = ", ".join(
        f"{k} = %({k})s" for k in clean_payload if k != "id"
    )

    sql = f"""
        UPDATE proyectos_calculo
        SET {fields_sql}
        WHERE id = %(id)s;
    """

    cur = conn.cursor()
    cur.execute(sql, clean_payload)

    if cur.rowcount == 0:
        cur.close()
        raise HTTPException(
            status_code=404,
            detail="Proyecto no encontrado"
        )

    conn.commit()
    cur.close()

    return {
        "success": True,
        "id": proyecto_id
    }


# ============================================================
# DELETE — ELIMINAR PROYECTO
# ============================================================
@router.delete("/{proyecto_id}")
def delete_proyecto_calculo(
    proyecto_id: int,
    conn=Depends(get_db)
):
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM proyectos_calculo WHERE id = %s;",
        (proyecto_id,)
    )

    if cur.rowcount == 0:
        cur.close()
        raise HTTPException(
            status_code=404,
            detail="Proyecto no encontrado"
        )

    conn.commit()
    cur.close()

    return {
        "success": True
    }
