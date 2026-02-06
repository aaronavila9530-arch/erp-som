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
# POST — CREAR PROYECTO / CALCULO (MULTI-LINE)
# ============================================================
@router.post("")
def create_proyecto_calculo(payload: dict, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # ---------------- VALIDACIONES ----------------
        nombre_proyecto = payload.get("nombre_proyecto")
        if not nombre_proyecto:
            raise HTTPException(
                status_code=400,
                detail="nombre_proyecto is required"
            )

        personal_costos = payload.get("personal_costos")
        if not isinstance(personal_costos, list) or not personal_costos:
            raise HTTPException(
                status_code=400,
                detail="personal_costos must be a non-empty list"
            )

        tiempo = float(payload.get("tiempo", 0))

        # ---------------- SQL ----------------
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

        inserted_ids = []

        # ---------------- MULTI INSERT (1 PERSONA = 1 FILA) ----------------
        for costo_persona in personal_costos:

            if not isinstance(costo_persona, (int, float)):
                continue

            total_honorarios = round(costo_persona * tiempo, 2)

            data = {
                "nombre_proyecto": nombre_proyecto,
                "personal": 1,  # 🔴 CLAVE: 1 FILA = 1 PERSONA
                "costo": costo_persona,
                "moneda": payload.get("moneda", "USD"),
                "tiempo": tiempo,
                "total_honorarios": total_honorarios,
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
            inserted_ids.append(cur.fetchone()["id"])

        conn.commit()

        return {
            "success": True,
            "rows_created": len(inserted_ids),
            "ids": inserted_ids
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
        SELECT
            nombre_proyecto,
            moneda,
            tiempo,
            COUNT(*)                     AS personas,
            SUM(costo)                   AS costo_hora_total,
            SUM(total_honorarios)        AS total_honorarios,
            MAX(gasto_alimentacion)      AS gasto_alimentacion,
            MAX(gasto_comunicacion)      AS gasto_comunicacion,
            MAX(gasto_transporte)        AS gasto_transporte,
            MAX(total_gastos)            AS total_gastos,
            MAX(margen)                  AS margen,
            MAX(precio)                  AS precio,
            MAX(utilidad)                AS utilidad,
            MAX(creado_el)               AS creado_el
        FROM proyectos_calculo
        GROUP BY nombre_proyecto, moneda, tiempo
        ORDER BY creado_el DESC;
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
@router.get("/{nombre_proyecto}")
def get_proyecto_calculo(
    nombre_proyecto: str,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # ---- Cabecera agregada ----
    cur.execute("""
        SELECT
            nombre_proyecto,
            moneda,
            tiempo,
            SUM(total_honorarios)   AS total_honorarios,
            MAX(gasto_alimentacion) AS gasto_alimentacion,
            MAX(gasto_comunicacion) AS gasto_comunicacion,
            MAX(gasto_transporte)   AS gasto_transporte,
            MAX(total_gastos)       AS total_gastos,
            MAX(margen)             AS margen,
            MAX(precio)             AS precio,
            MAX(utilidad)           AS utilidad
        FROM proyectos_calculo
        WHERE nombre_proyecto = %s
        GROUP BY nombre_proyecto, moneda, tiempo;
    """, (nombre_proyecto,))

    header = cur.fetchone()
    if not header:
        cur.close()
        raise HTTPException(
            status_code=404,
            detail="Proyecto no encontrado"
        )

    # ---- Detalle personas ----
    cur.execute("""
        SELECT
            id,
            costo,
            total_honorarios
        FROM proyectos_calculo
        WHERE nombre_proyecto = %s
        ORDER BY id;
    """, (nombre_proyecto,))

    personas = cur.fetchall() or []
    cur.close()

    return {
        "data": {
            "header": header,
            "personas": personas
        }
    }


# ============================================================
# PUT — ACTUALIZAR PROYECTO
# ============================================================
@router.put("/{nombre_proyecto}")
def update_proyecto_calculo(
    nombre_proyecto: str,
    payload: dict,
    conn=Depends(get_db)
):
    if not payload:
        raise HTTPException(
            status_code=400,
            detail="No data provided"
        )

    allowed_fields = {
        "moneda",
        "tiempo",
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

    fields_sql = ", ".join(
        f"{k} = %({k})s" for k in clean_payload
    )

    clean_payload["nombre_proyecto"] = nombre_proyecto

    sql = f"""
        UPDATE proyectos_calculo
        SET {fields_sql}
        WHERE nombre_proyecto = %(nombre_proyecto)s;
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
        "rows_updated": cur.rowcount
    }


# ============================================================
# DELETE — ELIMINAR PROYECTO
# ============================================================
@router.delete("/{nombre_proyecto}")
def delete_proyecto_calculo(
    nombre_proyecto: str,
    conn=Depends(get_db)
):
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM proyectos_calculo WHERE nombre_proyecto = %s;",
        (nombre_proyecto,)
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
        "success": True,
        "rows_deleted": cur.rowcount
    }
