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

REPORT_NUMBER_CANDIDATES = [
    ("container_reports", "report_no"),
    ("container_reports", "linked_report_number"),
    ("vessel_grain_sampling_reports", "cert_no"),
    ("vessel_truck_supervision_reports", "cert_no"),
    ("general_draft_survey", "draft_report_number"),
    ("draft_survey", "draft_report_number"),
    ("vessel_bunker_reports", "bunker_cert_no"),
    ("vessel_cargo_condition_surveys", "report_number"),
    ("vessel_crane_inspection_reports", "report_number"),
    ("vessel_condition_surveys", "report_number"),
    ("port_captancy_reports", "report_number"),
    ("weight_certificates", "report_number"),
    ("vessel_holds_inspection_certificates", "report_number"),
    ("sampling_certificates", "report_number"),
    ("sampling_certificates", "certificate_no"),
    ("sealing_certificates", "report_number"),
    ("sealing_certificates", "certificate_no"),
    ("lashing_certificates", "report_no"),
]


def _existing_reports_sql(cur):
    selects = []

    for table_name, column_name in REPORT_NUMBER_CANDIDATES:
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
            LIMIT 1
            """,
            (table_name, column_name)
        )

        if cur.fetchone():
            selects.append(
                f"""
                SELECT NULLIF(TRIM({column_name}::text), '') AS num_informe
                FROM {table_name}
                WHERE {column_name} IS NOT NULL
                  AND TRIM({column_name}::text) <> ''
                  AND LOWER(TRIM({column_name}::text)) <> 'none'
                """
            )

    if not selects:
        return "SELECT NULL::text AS num_informe WHERE FALSE"

    return "\nUNION\n".join(selects)


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

        existing_reports = _existing_reports_sql(cur)

        # ====================================================
        # BASE QUERY
        # ====================================================
        query = f"""
            WITH existing_reports AS (
                {existing_reports}
            )
            SELECT
                s.consec,
                s.num_informe,
                s.buque_contenedor,
                s.cliente,
                s.detalle,
                s.continente,
                s.pais,
                s.puerto,
                s.operacion,
                s.fecha_inicio,
                EXTRACT(YEAR FROM s.fecha_inicio)  AS year,
                EXTRACT(MONTH FROM s.fecha_inicio) AS month,
                COALESCE(NULLIF(TRIM(s.status_informe), ''), 'Pending') AS status_informe
            FROM servicios s
            WHERE LOWER(TRIM(COALESCE(s.estado, ''))) = 'finalizado'
              AND s.num_informe IS NOT NULL
              AND TRIM(s.num_informe) <> ''
              AND LOWER(TRIM(s.num_informe)) <> 'none'
              AND NOT EXISTS (
                  SELECT 1
                  FROM existing_reports er
                  WHERE TRIM(er.num_informe) = TRIM(s.num_informe)
              )
        """

        conditions = []
        params = []

        # ====================================================
        # STATUS
        # ====================================================
        if status:
            conditions.append("COALESCE(NULLIF(TRIM(s.status_informe), ''), 'Pending') = %s")
            params.append(status)

        # ====================================================
        # OPTIONAL FILTERS
        # ====================================================
        if continente:
            conditions.append("s.continente = %s")
            params.append(continente)

        if pais:
            conditions.append("s.pais = %s")
            params.append(pais)

        if puerto:
            conditions.append("s.puerto = %s")
            params.append(puerto)

        if operacion:
            conditions.append("s.operacion = %s")
            params.append(operacion)

        if year:
            conditions.append("EXTRACT(YEAR FROM s.fecha_inicio) = %s")
            params.append(year)

        if month:
            conditions.append("EXTRACT(MONTH FROM s.fecha_inicio) = %s")
            params.append(month)

        # ====================================================
        # APPLY CONDITIONS
        # ====================================================
        if conditions:
            query += " AND " + " AND ".join(conditions)

        query += """
            ORDER BY s.fecha_inicio DESC NULLS LAST,
                     s.consec DESC
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
