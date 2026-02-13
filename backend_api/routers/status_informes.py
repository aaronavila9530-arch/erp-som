# ============================================================
# ROUTER — STATUS INFORMES (SERVICIOS)
# Archivo: status_informes.py
# Alineado a estructura real del backend (database.get_db)
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from typing import Optional

from database import get_db   # 🔥 CORRECTO (NO db)


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
    ✔ Default: solo status_informe = 'Pending'
    ✔ Filtros dinámicos
    ✔ Año/Mes derivados desde fecha_inicio
    ✔ Solo tipo = 'Buque'
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
@router.get("/statuses")
def get_available_statuses(conn=Depends(get_db)):

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT DISTINCT status_informe
            FROM servicios
            WHERE status_informe IS NOT NULL
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
