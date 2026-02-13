from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Optional
import json

from database import get_db


router = APIRouter(
    prefix="/vessel-grain-sampling",
    tags=["Vessel Grain Sampling"]
)


# ============================================================
# CREATE — NEW GRAIN SAMPLING REPORT (ALIGNED 1:1 WITH UI)
# ============================================================

@router.post("")
def create_vessel_grain_sampling_report(
    payload: dict,
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    def safe(key, default=None):
        value = payload.get(key, default)
        return value if value not in ["", None] else default

    def safe_list(key):
        value = payload.get(key, [])
        return value if isinstance(value, list) else []

    try:

        # ====================================================
        # INSERT VESSEL GRAIN SAMPLING
        # ====================================================
        cur.execute("""
            INSERT INTO vessel_grain_sampling_reports (

                cert_no,
                place_date,

                vessel_name,
                requested_by,

                captain,
                chief_officer,

                arrival_buoy_time,
                nor_tendered_time,
                holds_opening_time,
                sampling_start_time,
                sampling_end_time,

                products,
                products_total,

                supervision,
                conclusion,

                created_at,
                updated_at

            ) VALUES (

                %(cert_no)s,
                %(place_date)s,

                %(vessel_name)s,
                %(requested_by)s,

                %(captain)s,
                %(chief_officer)s,

                %(arrival_buoy_time)s,
                %(nor_tendered_time)s,
                %(holds_opening_time)s,
                %(sampling_start_time)s,
                %(sampling_end_time)s,

                %(products)s,
                %(products_total)s,

                %(supervision)s,
                %(conclusion)s,

                NOW(),
                NOW()
            )
            RETURNING id
        """, {

            "cert_no": safe("cert_no"),
            "place_date": safe("place_date"),

            "vessel_name": safe("vessel_name"),
            "requested_by": safe("requested_by"),

            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            "arrival_buoy_time": safe("arrival_buoy_time"),
            "nor_tendered_time": safe("nor_tendered_time"),
            "holds_opening_time": safe("holds_opening_time"),
            "sampling_start_time": safe("sampling_start_time"),
            "sampling_end_time": safe("sampling_end_time"),

            "products": json.dumps(safe_list("products")),
            "products_total": safe("products_total"),

            "supervision": safe("supervision"),
            "conclusion": safe("conclusion"),
        })

        row = cur.fetchone()
        new_id = row["id"]

        # ====================================================
        # 🔥 UPDATE SERVICIOS.STATUS_INFORME = 'Created'
        # Basado en cert_no → servicios.num_informe
        # ====================================================
        cert_no = safe("cert_no")

        if cert_no:
            cur.execute("""
                UPDATE servicios
                SET status_informe = 'Created'
                WHERE num_informe = %s
            """, (cert_no,))

        # ====================================================
        # COMMIT FINAL (AMBAS OPERACIONES)
        # ====================================================
        conn.commit()

        return {
            "success": True,
            "id": new_id
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating grain sampling report: {str(e)}"
        )

    finally:
        cur.close()


# ============================================================
# GET — LIST ALL GRAIN SAMPLING REPORTS (ALIGNED)
# ============================================================
@router.get("")
def list_vessel_grain_sampling_reports(
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                id,
                cert_no,
                place_date,
                vessel_name,
                requested_by,
                products_total,
                supervision,
                created_at,
                updated_at
            FROM vessel_grain_sampling_reports
            ORDER BY created_at DESC NULLS LAST, id DESC
        """)

        rows = cur.fetchall() or []

        return {
            "success": True,
            "count": len(rows),
            "data": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing grain sampling reports: {str(e)}"
        )

    finally:
        cur.close()

# ============================================================
# GET — SELECTOR SERVICIOS (dinámico + año + mes + operacion)
# ============================================================
from typing import Optional
from fastapi import Query, Depends, HTTPException
from psycopg2.extras import RealDictCursor

@router.get("/services-selector")
def get_services_for_grain_sampling(
    continente: Optional[str] = None,
    pais: Optional[str] = None,
    puerto: Optional[str] = None,
    cliente: Optional[str] = None,
    buque: Optional[str] = None,
    operacion: Optional[str] = None,
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    conn=Depends(get_db)
):
    """
    Selector dinámico de servicios tipo Buque.
    Filtros dependientes simultáneos.
    Año y mes basados en fecha_inicio.
    Estado fue reemplazado por operacion.
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # =====================================================
        # BASE QUERY
        # =====================================================
        base_query = """
            FROM servicios
            WHERE tipo = 'Buque'
              AND num_informe IS NOT NULL
        """

        params = []

        # =====================================================
        # FILTROS DINÁMICOS
        # =====================================================
        if continente:
            base_query += " AND continente = %s"
            params.append(continente)

        if pais:
            base_query += " AND pais = %s"
            params.append(pais)

        if puerto:
            base_query += " AND puerto = %s"
            params.append(puerto)

        if cliente:
            base_query += " AND cliente = %s"
            params.append(cliente)

        if buque:
            base_query += " AND buque_contenedor = %s"
            params.append(buque)

        if operacion:
            base_query += " AND operacion = %s"
            params.append(operacion)

        # =====================================================
        # FILTRO AÑO / MES (fecha_inicio)
        # =====================================================
        if year:
            base_query += " AND EXTRACT(YEAR FROM fecha_inicio) = %s"
            params.append(year)

        if month:
            base_query += " AND EXTRACT(MONTH FROM fecha_inicio) = %s"
            params.append(month)

        # =====================================================
        # 1️⃣ RESULTADOS PARA TABLA
        # =====================================================
        results_query = """
            SELECT
                consec,
                num_informe,
                buque_contenedor,
                cliente,
                continente,
                pais,
                puerto,
                operacion,
                fecha_inicio
        """ + base_query + """
            ORDER BY fecha_inicio DESC NULLS LAST
        """

        cur.execute(results_query, params)
        rows = cur.fetchall() or []

        # =====================================================
        # 2️⃣ VALORES ÚNICOS DINÁMICOS
        # =====================================================
        filters_query = """
            SELECT DISTINCT
                continente,
                pais,
                puerto,
                cliente,
                buque_contenedor,
                operacion,
                EXTRACT(YEAR FROM fecha_inicio) AS year,
                EXTRACT(MONTH FROM fecha_inicio) AS month
        """ + base_query

        cur.execute(filters_query, params)
        filter_rows = cur.fetchall() or []

        unique_values = {
            "continentes": sorted({r["continente"] for r in filter_rows if r["continente"]}),
            "paises": sorted({r["pais"] for r in filter_rows if r["pais"]}),
            "puertos": sorted({r["puerto"] for r in filter_rows if r["puerto"]}),
            "clientes": sorted({r["cliente"] for r in filter_rows if r["cliente"]}),
            "buques": sorted({r["buque_contenedor"] for r in filter_rows if r["buque_contenedor"]}),
            "operaciones": sorted({r["operacion"] for r in filter_rows if r["operacion"]}),
            "years": sorted({int(r["year"]) for r in filter_rows if r["year"]}),
            "months": sorted({int(r["month"]) for r in filter_rows if r["month"]})
        }

        return {
            "success": True,
            "count": len(rows),
            "data": rows,
            "filters": unique_values
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching services selector: {str(e)}"
        )

    finally:
        cur.close()


# ============================================================
# GET — SINGLE GRAIN SAMPLING REPORT BY ID (ALIGNED)
# ============================================================
@router.get("/{report_id}")
def get_vessel_grain_sampling_report(
    report_id: int,
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                id,
                created_at,
                updated_at,

                cert_no,
                place_date,

                vessel_name,
                requested_by,

                captain,
                chief_officer,

                arrival_buoy_time,
                nor_tendered_time,
                holds_opening_time,
                sampling_start_time,
                sampling_end_time,

                products,
                products_total,

                supervision,
                conclusion

            FROM vessel_grain_sampling_reports
            WHERE id = %s
        """, (report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Grain sampling report not found"
            )

        # Convert JSONB (psycopg already handles this normally,
        # but we harden just in case legacy rows exist)
        if report.get("products") and isinstance(report["products"], str):
            import json
            report["products"] = json.loads(report["products"])

        return {
            "success": True,
            "data": report
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving grain sampling report: {str(e)}"
        )

    finally:
        cur.close()


# ============================================================
# UPDATE — FULL UPDATE (PUT) ALIGNED WITH CURRENT FRONTEND
# ============================================================
@router.put("/{report_id}")
def update_vessel_grain_sampling_report(
    report_id: int,
    payload: dict,
    conn=Depends(get_db)
):

    cur = conn.cursor()

    def safe(key, default=None):
        value = payload.get(key, default)
        return value if value not in ["", None] else default

    def safe_list(key):
        value = payload.get(key, [])
        return value if isinstance(value, list) else []

    try:

        cur.execute("""
            UPDATE vessel_grain_sampling_reports
            SET
                cert_no = %(cert_no)s,
                place_date = %(place_date)s,

                vessel_name = %(vessel_name)s,
                requested_by = %(requested_by)s,

                captain = %(captain)s,
                chief_officer = %(chief_officer)s,

                arrival_buoy_time = %(arrival_buoy_time)s,
                nor_tendered_time = %(nor_tendered_time)s,
                holds_opening_time = %(holds_opening_time)s,
                sampling_start_time = %(sampling_start_time)s,
                sampling_end_time = %(sampling_end_time)s,

                products = %(products)s,
                products_total = %(products_total)s,

                supervision = %(supervision)s,
                conclusion = %(conclusion)s,

                updated_at = NOW()

            WHERE id = %(id)s
        """, {

            "id": report_id,

            "cert_no": safe("cert_no"),
            "place_date": safe("place_date"),

            "vessel_name": safe("vessel_name"),
            "requested_by": safe("requested_by"),

            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            "arrival_buoy_time": safe("arrival_buoy_time"),
            "nor_tendered_time": safe("nor_tendered_time"),
            "holds_opening_time": safe("holds_opening_time"),
            "sampling_start_time": safe("sampling_start_time"),
            "sampling_end_time": safe("sampling_end_time"),

            "products": json.dumps(safe_list("products")),
            "products_total": safe("products_total"),

            "supervision": safe("supervision"),
            "conclusion": safe("conclusion"),
        })

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Grain sampling report not found"
            )

        conn.commit()

        return {
            "success": True,
            "id": report_id
        }

    except HTTPException:
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating grain sampling report: {str(e)}"
        )

    finally:
        cur.close()


