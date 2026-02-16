from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Optional
import json
import os

from database import get_db


router = APIRouter(
    prefix="/vessel-grain-sampling",
    tags=["Vessel Grain Sampling"]
)


# ============================================================
# CREATE — NEW GRAIN SAMPLING REPORT (FULLY ALIGNED 1:1)
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

    try:

        cur.execute("""
            INSERT INTO vessel_grain_sampling_reports (

                cert_no,
                place_date,

                requested_by,
                captain,
                chief_officer,
                vessel_name,

                -- SHIP DATA
                ship_flag,
                ship_grt,
                ship_nrt,
                ship_imo,
                ship_year,

                -- TIMES
                arrival_buoy_time,
                nor_tendered_time,
                holds_opening_time,
                surveyors_onboard_time,
                seals_verification_time,
                sampling_start_time,
                sampling_end_time,
                surveyors_disembark_time,

                -- PRODUCTS (5)
                hold1_product,
                hold1_tonnage,
                hold2_product,
                hold2_tonnage,
                hold3_product,
                hold3_tonnage,
                hold4_product,
                hold4_tonnage,
                hold5_product,
                hold5_tonnage,

                products_total,

                -- SAMPLING (3 x 5)
                sample1_hold,
                sample1_proa_babor,
                sample1_proa_estribor,
                sample1_centro,
                sample1_popa_babor,
                sample1_popa_estribor,

                sample2_hold,
                sample2_proa_babor,
                sample2_proa_estribor,
                sample2_centro,
                sample2_popa_babor,
                sample2_popa_estribor,

                sample3_hold,
                sample3_proa_babor,
                sample3_proa_estribor,
                sample3_centro,
                sample3_popa_babor,
                sample3_popa_estribor,

                supervision,
                conclusion,

                status,
                created_at,
                updated_at

            ) VALUES (

                %(cert_no)s,
                %(place_date)s,

                %(requested_by)s,
                %(captain)s,
                %(chief_officer)s,
                %(vessel_name)s,

                %(ship_flag)s,
                %(ship_grt)s,
                %(ship_nrt)s,
                %(ship_imo)s,
                %(ship_year)s,

                %(arrival_buoy_time)s,
                %(nor_tendered_time)s,
                %(holds_opening_time)s,
                %(surveyors_onboard_time)s,
                %(seals_verification_time)s,
                %(sampling_start_time)s,
                %(sampling_end_time)s,
                %(surveyors_disembark_time)s,

                %(hold1_product)s,
                %(hold1_tonnage)s,
                %(hold2_product)s,
                %(hold2_tonnage)s,
                %(hold3_product)s,
                %(hold3_tonnage)s,
                %(hold4_product)s,
                %(hold4_tonnage)s,
                %(hold5_product)s,
                %(hold5_tonnage)s,

                %(products_total)s,

                %(sample1_hold)s,
                %(sample1_proa_babor)s,
                %(sample1_proa_estribor)s,
                %(sample1_centro)s,
                %(sample1_popa_babor)s,
                %(sample1_popa_estribor)s,

                %(sample2_hold)s,
                %(sample2_proa_babor)s,
                %(sample2_proa_estribor)s,
                %(sample2_centro)s,
                %(sample2_popa_babor)s,
                %(sample2_popa_estribor)s,

                %(sample3_hold)s,
                %(sample3_proa_babor)s,
                %(sample3_proa_estribor)s,
                %(sample3_centro)s,
                %(sample3_popa_babor)s,
                %(sample3_popa_estribor)s,

                %(supervision)s,
                %(conclusion)s,

                %(status)s,
                NOW(),
                NOW()
            )
            RETURNING id
        """, {

            # HEADER
            "cert_no": safe("cert_no"),
            "place_date": safe("place_date"),

            "requested_by": safe("requested_by"),
            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),
            "vessel_name": safe("vessel_name"),

            # SHIP
            "ship_flag": safe("ship_flag"),
            "ship_grt": safe("ship_grt"),
            "ship_nrt": safe("ship_nrt"),
            "ship_imo": safe("ship_imo"),
            "ship_year": safe("ship_year"),

            # TIMES
            "arrival_buoy_time": safe("arrival_buoy_time"),
            "nor_tendered_time": safe("nor_tendered_time"),
            "holds_opening_time": safe("holds_opening_time"),
            "surveyors_onboard_time": safe("surveyors_onboard_time"),
            "seals_verification_time": safe("seals_verification_time"),
            "sampling_start_time": safe("sampling_start_time"),
            "sampling_end_time": safe("sampling_end_time"),
            "surveyors_disembark_time": safe("surveyors_disembark_time"),

            # PRODUCTS
            "hold1_product": safe("hold1_product"),
            "hold1_tonnage": safe("hold1_tonnage"),
            "hold2_product": safe("hold2_product"),
            "hold2_tonnage": safe("hold2_tonnage"),
            "hold3_product": safe("hold3_product"),
            "hold3_tonnage": safe("hold3_tonnage"),
            "hold4_product": safe("hold4_product"),
            "hold4_tonnage": safe("hold4_tonnage"),
            "hold5_product": safe("hold5_product"),
            "hold5_tonnage": safe("hold5_tonnage"),

            "products_total": safe("products_total"),

            # SAMPLING 1
            "sample1_hold": safe("sample1_hold"),
            "sample1_proa_babor": safe("sample1_proa_babor"),
            "sample1_proa_estribor": safe("sample1_proa_estribor"),
            "sample1_centro": safe("sample1_centro"),
            "sample1_popa_babor": safe("sample1_popa_babor"),
            "sample1_popa_estribor": safe("sample1_popa_estribor"),

            # SAMPLING 2
            "sample2_hold": safe("sample2_hold"),
            "sample2_proa_babor": safe("sample2_proa_babor"),
            "sample2_proa_estribor": safe("sample2_proa_estribor"),
            "sample2_centro": safe("sample2_centro"),
            "sample2_popa_babor": safe("sample2_popa_babor"),
            "sample2_popa_estribor": safe("sample2_popa_estribor"),

            # SAMPLING 3
            "sample3_hold": safe("sample3_hold"),
            "sample3_proa_babor": safe("sample3_proa_babor"),
            "sample3_proa_estribor": safe("sample3_proa_estribor"),
            "sample3_centro": safe("sample3_centro"),
            "sample3_popa_babor": safe("sample3_popa_babor"),
            "sample3_popa_estribor": safe("sample3_popa_estribor"),

            "supervision": safe("supervision"),
            "conclusion": safe("conclusion"),

            # STATUS SIEMPRE
            "status": safe("status", "Created"),
        })

        row = cur.fetchone()
        new_id = row["id"]

        # UPDATE SERVICIOS
        cert_no = safe("cert_no")
        if cert_no:
            cur.execute("""
                UPDATE servicios
                SET status_informe = 'Created'
                WHERE num_informe = %s
            """, (cert_no,))

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
# GET — LIST ALL GRAIN SAMPLING REPORTS (FULLY ALIGNED 1:1)
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

                requested_by,
                captain,
                chief_officer,
                vessel_name,

                -- SHIP DATA
                ship_flag,
                ship_grt,
                ship_nrt,
                ship_imo,
                ship_year,

                -- TIMES
                arrival_buoy_time,
                nor_tendered_time,
                holds_opening_time,
                surveyors_onboard_time,
                seals_verification_time,
                sampling_start_time,
                sampling_end_time,
                surveyors_disembark_time,

                -- PRODUCTS (5)
                hold1_product,
                hold1_tonnage,
                hold2_product,
                hold2_tonnage,
                hold3_product,
                hold3_tonnage,
                hold4_product,
                hold4_tonnage,
                hold5_product,
                hold5_tonnage,

                products_total,

                -- SAMPLING (3 x 5)
                sample1_hold,
                sample1_proa_babor,
                sample1_proa_estribor,
                sample1_centro,
                sample1_popa_babor,
                sample1_popa_estribor,

                sample2_hold,
                sample2_proa_babor,
                sample2_proa_estribor,
                sample2_centro,
                sample2_popa_babor,
                sample2_popa_estribor,

                sample3_hold,
                sample3_proa_babor,
                sample3_proa_estribor,
                sample3_centro,
                sample3_popa_babor,
                sample3_popa_estribor,

                supervision,
                conclusion,

                status,

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
# GET — SINGLE GRAIN SAMPLING REPORT BY ID (FULL 1:1 ALIGNED)
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

                requested_by,
                captain,
                chief_officer,
                vessel_name,

                -- SHIP DATA
                ship_flag,
                ship_grt,
                ship_nrt,
                ship_imo,
                ship_year,

                -- TIMES
                arrival_buoy_time,
                nor_tendered_time,
                holds_opening_time,
                surveyors_onboard_time,
                seals_verification_time,
                sampling_start_time,
                sampling_end_time,
                surveyors_disembark_time,

                -- PRODUCTS
                hold1_product,
                hold1_tonnage,
                hold2_product,
                hold2_tonnage,
                hold3_product,
                hold3_tonnage,
                hold4_product,
                hold4_tonnage,
                hold5_product,
                hold5_tonnage,

                products_total,

                -- SAMPLING
                sample1_hold,
                sample1_proa_babor,
                sample1_proa_estribor,
                sample1_centro,
                sample1_popa_babor,
                sample1_popa_estribor,

                sample2_hold,
                sample2_proa_babor,
                sample2_proa_estribor,
                sample2_centro,
                sample2_popa_babor,
                sample2_popa_estribor,

                sample3_hold,
                sample3_proa_babor,
                sample3_proa_estribor,
                sample3_centro,
                sample3_popa_babor,
                sample3_popa_estribor,

                supervision,
                conclusion,
                status

            FROM vessel_grain_sampling_reports
            WHERE id = %s
        """, (report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Grain sampling report not found"
            )

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
# UPDATE — FULL UPDATE (PUT) ALIGNED 100% WITH CURRENT TABLE
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

    try:

        cur.execute("""
            UPDATE vessel_grain_sampling_reports
            SET

                -- HEADER
                cert_no = %(cert_no)s,
                place_date = %(place_date)s,

                -- MAIN
                vessel_name = %(vessel_name)s,
                requested_by = %(requested_by)s,
                captain = %(captain)s,
                chief_officer = %(chief_officer)s,

                -- SHIP DATA
                ship_flag = %(ship_flag)s,
                ship_grt = %(ship_grt)s,
                ship_nrt = %(ship_nrt)s,
                ship_imo = %(ship_imo)s,
                ship_year = %(ship_year)s,

                -- TIMES
                arrival_buoy_time = %(arrival_buoy_time)s,
                nor_tendered_time = %(nor_tendered_time)s,
                holds_opening_time = %(holds_opening_time)s,
                surveyors_onboard_time = %(surveyors_onboard_time)s,
                seals_verification_time = %(seals_verification_time)s,
                sampling_start_time = %(sampling_start_time)s,
                sampling_end_time = %(sampling_end_time)s,
                surveyors_disembark_time = %(surveyors_disembark_time)s,

                -- HOLDS (5)
                hold1_product = %(hold1_product)s,
                hold1_tonnage = %(hold1_tonnage)s,
                hold2_product = %(hold2_product)s,
                hold2_tonnage = %(hold2_tonnage)s,
                hold3_product = %(hold3_product)s,
                hold3_tonnage = %(hold3_tonnage)s,
                hold4_product = %(hold4_product)s,
                hold4_tonnage = %(hold4_tonnage)s,
                hold5_product = %(hold5_product)s,
                hold5_tonnage = %(hold5_tonnage)s,

                products_total = %(products_total)s,

                -- SAMPLING (3)
                sample1_hold = %(sample1_hold)s,
                sample1_proa_babor = %(sample1_proa_babor)s,
                sample1_proa_estribor = %(sample1_proa_estribor)s,
                sample1_centro = %(sample1_centro)s,
                sample1_popa_babor = %(sample1_popa_babor)s,
                sample1_popa_estribor = %(sample1_popa_estribor)s,

                sample2_hold = %(sample2_hold)s,
                sample2_proa_babor = %(sample2_proa_babor)s,
                sample2_proa_estribor = %(sample2_proa_estribor)s,
                sample2_centro = %(sample2_centro)s,
                sample2_popa_babor = %(sample2_popa_babor)s,
                sample2_popa_estribor = %(sample2_popa_estribor)s,

                sample3_hold = %(sample3_hold)s,
                sample3_proa_babor = %(sample3_proa_babor)s,
                sample3_proa_estribor = %(sample3_proa_estribor)s,
                sample3_centro = %(sample3_centro)s,
                sample3_popa_babor = %(sample3_popa_babor)s,
                sample3_popa_estribor = %(sample3_popa_estribor)s,

                supervision = %(supervision)s,
                conclusion = %(conclusion)s,
                status = %(status)s,

                updated_at = NOW()

            WHERE id = %(id)s
        """, {

            "id": report_id,

            # HEADER
            "cert_no": safe("cert_no"),
            "place_date": safe("place_date"),

            # MAIN
            "vessel_name": safe("vessel_name"),
            "requested_by": safe("requested_by"),
            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            # SHIP
            "ship_flag": safe("ship_flag"),
            "ship_grt": safe("ship_grt"),
            "ship_nrt": safe("ship_nrt"),
            "ship_imo": safe("ship_imo"),
            "ship_year": safe("ship_year"),

            # TIMES
            "arrival_buoy_time": safe("arrival_buoy_time"),
            "nor_tendered_time": safe("nor_tendered_time"),
            "holds_opening_time": safe("holds_opening_time"),
            "surveyors_onboard_time": safe("surveyors_onboard_time"),
            "seals_verification_time": safe("seals_verification_time"),
            "sampling_start_time": safe("sampling_start_time"),
            "sampling_end_time": safe("sampling_end_time"),
            "surveyors_disembark_time": safe("surveyors_disembark_time"),

            # HOLDS
            "hold1_product": safe("hold1_product"),
            "hold1_tonnage": safe("hold1_tonnage"),
            "hold2_product": safe("hold2_product"),
            "hold2_tonnage": safe("hold2_tonnage"),
            "hold3_product": safe("hold3_product"),
            "hold3_tonnage": safe("hold3_tonnage"),
            "hold4_product": safe("hold4_product"),
            "hold4_tonnage": safe("hold4_tonnage"),
            "hold5_product": safe("hold5_product"),
            "hold5_tonnage": safe("hold5_tonnage"),

            "products_total": safe("products_total"),

            # SAMPLING
            "sample1_hold": safe("sample1_hold"),
            "sample1_proa_babor": safe("sample1_proa_babor"),
            "sample1_proa_estribor": safe("sample1_proa_estribor"),
            "sample1_centro": safe("sample1_centro"),
            "sample1_popa_babor": safe("sample1_popa_babor"),
            "sample1_popa_estribor": safe("sample1_popa_estribor"),

            "sample2_hold": safe("sample2_hold"),
            "sample2_proa_babor": safe("sample2_proa_babor"),
            "sample2_proa_estribor": safe("sample2_proa_estribor"),
            "sample2_centro": safe("sample2_centro"),
            "sample2_popa_babor": safe("sample2_popa_babor"),
            "sample2_popa_estribor": safe("sample2_popa_estribor"),

            "sample3_hold": safe("sample3_hold"),
            "sample3_proa_babor": safe("sample3_proa_babor"),
            "sample3_proa_estribor": safe("sample3_proa_estribor"),
            "sample3_centro": safe("sample3_centro"),
            "sample3_popa_babor": safe("sample3_popa_babor"),
            "sample3_popa_estribor": safe("sample3_popa_estribor"),

            "supervision": safe("supervision"),
            "conclusion": safe("conclusion"),
            "status": safe("status", "Created")
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



# ============================================================
# APPROVE REPORT + GENERATE PDF
# ============================================================

@router.put("/{report_id}/approve")
def approve_vessel_grain_sampling_report(
    report_id: int,
    conn=Depends(get_db)
):

    from services.grain_sampling_pdf_service import generate_grain_sampling_pdf
    from fastapi.responses import FileResponse
    from psycopg2.extras import RealDictCursor

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # 1️⃣ Obtener reporte completo
        cur.execute("""
            SELECT *
            FROM vessel_grain_sampling_reports
            WHERE id = %s
        """, (report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        # 2️⃣ Cambiar status
        cur.execute("""
            UPDATE vessel_grain_sampling_reports
            SET status = 'Approved',
                updated_at = NOW()
            WHERE id = %s
        """, (report_id,))

        conn.commit()

        # 3️⃣ Generar PDF REAL
        pdf_path = generate_grain_sampling_pdf(report)

        if not os.path.exists(pdf_path):
            raise RuntimeError("PDF file was not generated")

        # 4️⃣ Devolver PDF
        return FileResponse(
            path=pdf_path,
            filename=f"{report['cert_no']}_Grain_Sampling_Report.pdf",
            media_type="application/pdf"
        )

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cur.close()


# ============================================================
# GENERATE WORD (NO STATUS CHANGE)
# ============================================================

@router.post("/{report_id}/generate-word")
def generate_word_vessel_grain_sampling(
    report_id: int,
    conn=Depends(get_db)
):

    from services.grain_sampling_doc_service import generate_grain_sampling_doc
    from fastapi.responses import FileResponse

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        cur.execute("""
            SELECT *
            FROM vessel_grain_sampling_reports
            WHERE id = %s
        """, (report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        file_path = generate_grain_sampling_doc(report)

        return FileResponse(
            path=file_path,
            filename=f"{report['cert_no']}_Grain_Sampling_Report.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cur.close()

# =========================================================
# GET DATA FOR FINAL PRESENTATION POPUP
# =========================================================
@router.get("/{report_id}/presentation-data")
def get_vessel_presentation_data(
    report_id: int,
    db = Depends(get_db)
):
    try:

        query = """
            SELECT
                cert_no,
                requested_by,
                vessel_name,
                ship_grt,
                ship_nrt,
                sampling_start_time
            FROM vessel_grain_sampling_reports
            WHERE id = %s
        """

        cursor = db.cursor()
        cursor.execute(query, (report_id,))
        row = cursor.fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        sampling_date = None
        if row[5]:
            sampling_date = str(row[5]).split(" ")[0]

        return {
            "success": True,
            "data": {
                "cert_no": row[0],
                "requested_by": row[1],
                "vessel_name": row[2],
                "ship_grt": row[3],
                "ship_nrt": row[4],
                "sampling_start_time": sampling_date
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Presentation data error: {str(e)}"
        )
