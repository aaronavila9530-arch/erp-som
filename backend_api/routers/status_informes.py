# ============================================================
# ROUTER — STATUS INFORMES (SERVICIOS)
# Archivo: status_informes.py
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from typing import Optional

from database import get_db


router = APIRouter(
    prefix="/status-informes",
    tags=["Status Informes"]
)


# ============================================================
# GET — GRID SERVICIOS INFORMES
# ============================================================
@router.get("")
def list_status_informes(
    status: Optional[str] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    puerto: Optional[str] = Query(None),
    operacion: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    conn=Depends(get_db)
):
    """
    ✔ Solo tipo = 'Buque'
    ✔ Solo num_informe válido (no NULL, no vacío, no 'None')
    ✔ Default: status_informe = 'Pending'
    ✔ Filtros dinámicos
    ✔ Año/Mes derivados desde fecha_inicio
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # ====================================================
        # BASE QUERY
        # ====================================================
        query = """
            SELECT
                consec,
                num_informe,
                buque_contenedor,
                cliente,
                detalle,
                continente,
                pais,
                puerto,
                operacion,
                fecha_inicio,
                EXTRACT(YEAR FROM fecha_inicio)  AS year,
                EXTRACT(MONTH FROM fecha_inicio) AS month,
                status_informe
            FROM servicios
            WHERE tipo = 'Buque'
              AND num_informe IS NOT NULL
              AND TRIM(num_informe) <> ''
              AND LOWER(TRIM(num_informe)) <> 'none'
        """

        conditions = []
        params = []

        # ====================================================
        # STATUS (DEFAULT: Pending)
        # ====================================================
        if status:
            conditions.append("status_informe = %s")
            params.append(status)
        else:
            conditions.append("status_informe = 'Pending'")

        # ====================================================
        # OPTIONAL FILTERS
        # ====================================================
        if continente:
            conditions.append("continente = %s")
            params.append(continente)

        if pais:
            conditions.append("pais = %s")
            params.append(pais)

        if puerto:
            conditions.append("puerto = %s")
            params.append(puerto)

        if operacion:
            conditions.append("operacion = %s")
            params.append(operacion)

        if year:
            conditions.append("EXTRACT(YEAR FROM fecha_inicio) = %s")
            params.append(year)

        if month:
            conditions.append("EXTRACT(MONTH FROM fecha_inicio) = %s")
            params.append(month)

        # ====================================================
        # APPLY CONDITIONS
        # ====================================================
        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += """
            ORDER BY fecha_inicio DESC NULLS LAST,
                     consec DESC
        """

        # ====================================================
        # EXECUTE
        # ====================================================
        cur.execute(query, tuple(params))

        rows = cur.fetchall() or []

        return {
            "success": True,
            "count": len(rows),
            "data": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing status informes: {str(e)}"
        )

    finally:
        cur.close()


# ============================================================
# GET — STATUS DISPONIBLES (COMBOBOX)
# ============================================================
@router.get("/record/{consec}")
def get_status_informe(consec: int, conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                consec,
                num_informe,
                buque_contenedor,
                cliente,
                detalle,
                continente,
                pais,
                puerto,
                operacion,
                fecha_inicio,
                hora_inicio,
                fecha_fin,
                hora_fin,
                EXTRACT(YEAR FROM fecha_inicio)  AS year,
                EXTRACT(MONTH FROM fecha_inicio) AS month,
                status_informe
            FROM servicios
            WHERE consec = %s
        """, (consec,))

        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Status informe not found")

        return row

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving status informe: {str(e)}"
        )

    finally:
        cur.close()


@router.put("/record/{consec}")
def update_status_informe(consec: int, payload: dict, conn=Depends(get_db)):
    allowed = {
        "num_informe",
        "buque_contenedor",
        "cliente",
        "detalle",
        "continente",
        "pais",
        "puerto",
        "operacion",
        "fecha_inicio",
        "hora_inicio",
        "fecha_fin",
        "hora_fin",
        "status_informe",
    }

    updates = []
    params = []

    for key, value in payload.items():
        if key in allowed:
            updates.append(f"{key} = %s")
            params.append(value if value != "" else None)

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    params.append(consec)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            f"""
            UPDATE servicios
            SET {", ".join(updates)}
            WHERE consec = %s
            RETURNING
                consec,
                num_informe,
                buque_contenedor,
                cliente,
                detalle,
                continente,
                pais,
                puerto,
                operacion,
                fecha_inicio,
                hora_inicio,
                fecha_fin,
                hora_fin,
                status_informe
            """,
            tuple(params)
        )

        row = cur.fetchone()
        if not row:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Status informe not found")

        conn.commit()
        return {
            "success": True,
            "data": row
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating status informe: {str(e)}"
        )

    finally:
        cur.close()


@router.get("/statuses")
def get_available_statuses(conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT status_informe
            FROM servicios
            WHERE status_informe IS NOT NULL
              AND TRIM(status_informe) <> ''
            ORDER BY status_informe
        """)

        rows = cur.fetchall() or []

        statuses = [r[0] for r in rows if r[0]]

        return {
            "success": True,
            "data": statuses
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statuses: {str(e)}"
        )

    finally:
        cur.close()
