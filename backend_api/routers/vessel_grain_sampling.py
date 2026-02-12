from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from datetime import datetime

from database import get_db


router = APIRouter(
    prefix="/vessel-grain-sampling",
    tags=["Vessel Grain Sampling"]
)


# ============================================================
# CREATE — NEW GRAIN SAMPLING REPORT (1:1 WORD ALIGNED)
# ============================================================
@router.post("")
def create_vessel_grain_sampling_report(
    payload: dict,
    conn=Depends(get_db)
):
    """
    1:1 aligned with official Word template & UI structure.
    Fully hardened:
    - No KeyError
    - Safe defaults
    - Explicit field mapping
    - Rollback protected
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 🔒 BLINDAJE — Normalizar payload
    def safe(key, default=""):
        value = payload.get(key, default)
        return value if value is not None else default

    try:
        cur.execute("""
            INSERT INTO vessel_grain_sampling_reports (
                -- HEADER
                cert_no,
                place_date,

                -- INTRODUCCIÓN
                purpose,
                requested_by,
                arrival_info,
                inspection_info,
                captain,
                chief_officer,

                -- BUQUE
                vessel_name,
                flag_port,
                grt,
                nrt,
                imo,
                build_year,

                -- TIEMPOS
                arrival_buoy_time,
                nor_tendered_time,
                holds_opening_time,
                surveyors_onboard_time,
                seals_verification_time,
                sampling_start_time,
                sampling_end_time,
                surveyors_disembark_time,

                -- PRODUCTOS
                products_header_line,
                products,
                products_total,

                -- CUERPO TEXTO
                supervision,
                sampling,
                procedure,
                conclusion,

                -- DECLARACIÓN / FIRMA
                legal_text,
                attachments,
                surveyor_name,
                surveyor_position,

                created_at,
                updated_at
            ) VALUES (
                %(cert_no)s,
                %(place_date)s,

                %(purpose)s,
                %(requested_by)s,
                %(arrival_info)s,
                %(inspection_info)s,
                %(captain)s,
                %(chief_officer)s,

                %(vessel_name)s,
                %(flag_port)s,
                %(grt)s,
                %(nrt)s,
                %(imo)s,
                %(build_year)s,

                %(arrival_buoy_time)s,
                %(nor_tendered_time)s,
                %(holds_opening_time)s,
                %(surveyors_onboard_time)s,
                %(seals_verification_time)s,
                %(sampling_start_time)s,
                %(sampling_end_time)s,
                %(surveyors_disembark_time)s,

                %(products_header_line)s,
                %(products)s,
                %(products_total)s,

                %(supervision)s,
                %(sampling)s,
                %(procedure)s,
                %(conclusion)s,

                %(legal_text)s,
                %(attachments)s,
                %(surveyor_name)s,
                %(surveyor_position)s,

                NOW(),
                NOW()
            )
            RETURNING id
        """, {
            # HEADER
            "cert_no": safe("cert_no"),
            "place_date": safe("place_date"),

            # INTRO
            "purpose": safe("purpose"),
            "requested_by": safe("requested_by"),
            "arrival_info": safe("arrival_info"),
            "inspection_info": safe("inspection_info"),
            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            # BUQUE
            "vessel_name": safe("vessel_name"),
            "flag_port": safe("flag_port"),
            "grt": safe("grt"),
            "nrt": safe("nrt"),
            "imo": safe("imo"),
            "build_year": safe("build_year"),

            # TIEMPOS
            "arrival_buoy_time": safe("arrival_buoy_time"),
            "nor_tendered_time": safe("nor_tendered_time"),
            "holds_opening_time": safe("holds_opening_time"),
            "surveyors_onboard_time": safe("surveyors_onboard_time"),
            "seals_verification_time": safe("seals_verification_time"),
            "sampling_start_time": safe("sampling_start_time"),
            "sampling_end_time": safe("sampling_end_time"),
            "surveyors_disembark_time": safe("surveyors_disembark_time"),

            # PRODUCTOS
            "products_header_line": safe("products_header_line"),
            "products": safe("products"),  # JSON table
            "products_total": safe("products_total"),

            # TEXT
            "supervision": safe("supervision"),
            "sampling": safe("sampling"),
            "procedure": safe("procedure"),
            "conclusion": safe("conclusion"),

            # DECLARACIÓN
            "legal_text": safe("legal_text"),
            "attachments": safe("attachments"),
            "surveyor_name": safe("surveyor_name"),
            "surveyor_position": safe("surveyor_position"),
        })

        new_id = cur.fetchone()["id"]
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
# GET — LIST ALL GRAIN SAMPLING REPORTS (HARDENED)
# ============================================================
@router.get("")
def list_vessel_grain_sampling_reports(
    conn=Depends(get_db)
):
    """
    Returns lightweight list for grid/table view.
    1:1 aligned with report structure.
    Hardened:
    - Safe DB handling
    - Explicit fields
    - No SELECT *
    - Stable ordering
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                id,
                cert_no,
                place_date,
                vessel_name,
                surveyor_name,
                created_at,
                updated_at
            FROM vessel_grain_sampling_reports
            ORDER BY created_at DESC, id DESC
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
# GET — SINGLE GRAIN SAMPLING REPORT BY ID (1:1 ALIGNED)
# ============================================================
@router.get("/{report_id}")
def get_vessel_grain_sampling_report(
    report_id: int,
    conn=Depends(get_db)
):
    """
    Returns full report 1:1 aligned with Word template.
    Hardened:
    - Explicit field selection
    - 404 safe
    - Exception protected
    - No legacy fields
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute("""
            SELECT
                -- META
                id,
                created_at,
                updated_at,

                -- HEADER
                cert_no,
                place_date,

                -- INTRODUCCIÓN
                purpose,
                requested_by,
                arrival_info,
                inspection_info,
                captain,
                chief_officer,

                -- BUQUE
                vessel_name,
                flag_port,
                grt,
                nrt,
                imo,
                build_year,

                -- TIEMPOS
                arrival_buoy_time,
                nor_tendered_time,
                holds_opening_time,
                surveyors_onboard_time,
                seals_verification_time,
                sampling_start_time,
                sampling_end_time,
                surveyors_disembark_time,

                -- PRODUCTOS (1:1)
                products_header_line,
                products,
                products_total,

                -- CUERPO
                supervision,
                sampling,
                procedure,
                conclusion,

                -- DECLARACIÓN / FIRMA
                legal_text,
                attachments,
                surveyor_name,
                surveyor_position

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
# UPDATE — FULL UPDATE (PUT) 1:1 ALIGNED & HARDENED
# ============================================================
@router.put("/{report_id}")
def update_vessel_grain_sampling_report(
    report_id: int,
    payload: dict,
    conn=Depends(get_db)
):
    """
    Full update aligned 1:1 with Word template.
    Hardened:
    - Safe payload access
    - No KeyError
    - Explicit field mapping
    - Rollback protected
    - 404 safe
    """

    cur = conn.cursor()

    # 🔒 Safe getter
    def safe(key, default=""):
        value = payload.get(key, default)
        return value if value is not None else default

    try:
        cur.execute("""
            UPDATE vessel_grain_sampling_reports
            SET
                -- HEADER
                cert_no = %(cert_no)s,
                place_date = %(place_date)s,

                -- INTRODUCCIÓN
                purpose = %(purpose)s,
                requested_by = %(requested_by)s,
                arrival_info = %(arrival_info)s,
                inspection_info = %(inspection_info)s,
                captain = %(captain)s,
                chief_officer = %(chief_officer)s,

                -- BUQUE
                vessel_name = %(vessel_name)s,
                flag_port = %(flag_port)s,
                grt = %(grt)s,
                nrt = %(nrt)s,
                imo = %(imo)s,
                build_year = %(build_year)s,

                -- TIEMPOS
                arrival_buoy_time = %(arrival_buoy_time)s,
                nor_tendered_time = %(nor_tendered_time)s,
                holds_opening_time = %(holds_opening_time)s,
                surveyors_onboard_time = %(surveyors_onboard_time)s,
                seals_verification_time = %(seals_verification_time)s,
                sampling_start_time = %(sampling_start_time)s,
                sampling_end_time = %(sampling_end_time)s,
                surveyors_disembark_time = %(surveyors_disembark_time)s,

                -- PRODUCTOS
                products_header_line = %(products_header_line)s,
                products = %(products)s,
                products_total = %(products_total)s,

                -- CUERPO
                supervision = %(supervision)s,
                sampling = %(sampling)s,
                procedure = %(procedure)s,
                conclusion = %(conclusion)s,

                -- DECLARACIÓN / FIRMA
                legal_text = %(legal_text)s,
                attachments = %(attachments)s,
                surveyor_name = %(surveyor_name)s,
                surveyor_position = %(surveyor_position)s,

                updated_at = NOW()

            WHERE id = %(id)s
        """, {
            "id": report_id,

            # HEADER
            "cert_no": safe("cert_no"),
            "place_date": safe("place_date"),

            # INTRO
            "purpose": safe("purpose"),
            "requested_by": safe("requested_by"),
            "arrival_info": safe("arrival_info"),
            "inspection_info": safe("inspection_info"),
            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            # BUQUE
            "vessel_name": safe("vessel_name"),
            "flag_port": safe("flag_port"),
            "grt": safe("grt"),
            "nrt": safe("nrt"),
            "imo": safe("imo"),
            "build_year": safe("build_year"),

            # TIEMPOS
            "arrival_buoy_time": safe("arrival_buoy_time"),
            "nor_tendered_time": safe("nor_tendered_time"),
            "holds_opening_time": safe("holds_opening_time"),
            "surveyors_onboard_time": safe("surveyors_onboard_time"),
            "seals_verification_time": safe("seals_verification_time"),
            "sampling_start_time": safe("sampling_start_time"),
            "sampling_end_time": safe("sampling_end_time"),
            "surveyors_disembark_time": safe("surveyors_disembark_time"),

            # PRODUCTOS
            "products_header_line": safe("products_header_line"),
            "products": safe("products"),
            "products_total": safe("products_total"),

            # TEXT
            "supervision": safe("supervision"),
            "sampling": safe("sampling"),
            "procedure": safe("procedure"),
            "conclusion": safe("conclusion"),

            # DECLARACIÓN
            "legal_text": safe("legal_text"),
            "attachments": safe("attachments"),
            "surveyor_name": safe("surveyor_name"),
            "surveyor_position": safe("surveyor_position"),
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
# GET — SELECTOR SERVICIOS (para CERT Nº popup)
# ============================================================
@router.get("/services-selector")
def get_services_for_grain_sampling(
    continente: Optional[str] = None,
    pais: Optional[str] = None,
    puerto: Optional[str] = None,
    cliente: Optional[str] = None,
    buque: Optional[str] = None,
    estado: Optional[str] = None,
    conn=Depends(get_db)
):
    """
    Devuelve lista de servicios tipo Buque
    para seleccionar CERT Nº y autocompletar
    buque, cliente, continente, país y puerto.
    """

    from psycopg2.extras import RealDictCursor
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        query = """
            SELECT
                id,
                num_informe,
                buque_contenedor,
                cliente,
                continente,
                pais,
                puerto
            FROM servicios
            WHERE tipo = 'Buque'
              AND num_informe IS NOT NULL
        """

        params = []

        # 🔎 Filtros dinámicos
        if continente:
            query += " AND continente ILIKE %s"
            params.append(f"%{continente}%")

        if pais:
            query += " AND pais ILIKE %s"
            params.append(f"%{pais}%")

        if puerto:
            query += " AND puerto ILIKE %s"
            params.append(f"%{puerto}%")

        if cliente:
            query += " AND cliente ILIKE %s"
            params.append(f"%{cliente}%")

        if buque:
            query += " AND buque_contenedor ILIKE %s"
            params.append(f"%{buque}%")

        if estado:
            query += " AND estado ILIKE %s"
            params.append(f"%{estado}%")

        query += " ORDER BY fecha_inicio DESC NULLS LAST"

        cur.execute(query, params)
        rows = cur.fetchall()

        return {
            "success": True,
            "data": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching services selector: {str(e)}"
        )

    finally:
        cur.close()
