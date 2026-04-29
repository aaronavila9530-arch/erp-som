from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from typing import Optional
from datetime import datetime
from fastapi.responses import FileResponse
from services.vessel_truck_supervision_pdf_service import generate_vessel_truck_supervision_pdf
from services.presentation_truck_supervision_service import (
    generate_truck_supervision_presentation_pdf
)
from services.pdf_merge_service import merge_pdfs





from database import get_db


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/vessel-truck-supervision",
    tags=["Vessel Truck Supervision"]
)


# =========================================================
# FILTER SERVICIOS (CASCADE + FILTERS + DATA)
# =========================================================

from psycopg2.extras import RealDictCursor
from fastapi import Query, Depends, HTTPException


@router.get("/servicios-filter")
def filter_servicios(
    continente: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    cliente: str | None = None,
    buque_contenedor: str | None = None,
    operacion: str | None = None,
    anio: int | None = Query(None, ge=1900, le=2100),
    mes: int | None = Query(None, ge=1, le=12),
    conn=Depends(get_db)
):

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
        # YEAR / MONTH (PRINCIPALES)
        # =====================================================

        if anio is not None:
            base_query += " AND EXTRACT(YEAR FROM fecha_inicio) = %s"
            params.append(anio)

        if mes is not None:
            base_query += " AND EXTRACT(MONTH FROM fecha_inicio) = %s"
            params.append(mes)

        # =====================================================
        # RESTO FILTROS
        # =====================================================

        if continente:
            base_query += " AND continente = %s"
            params.append(continente.strip())

        if pais:
            base_query += " AND pais = %s"
            params.append(pais.strip())

        if puerto:
            base_query += " AND puerto = %s"
            params.append(puerto.strip())

        if cliente:
            base_query += " AND cliente = %s"
            params.append(cliente.strip())

        if buque_contenedor:
            base_query += " AND buque_contenedor = %s"
            params.append(buque_contenedor.strip())

        if operacion:
            base_query += " AND operacion = %s"
            params.append(operacion.strip())

        # =====================================================
        # DATA QUERY
        # =====================================================

        data_query = """
            SELECT
                consec AS id,
                num_informe,
                buque_contenedor,
                cliente,
                continente,
                pais,
                puerto,
                operacion,
                EXTRACT(YEAR FROM fecha_inicio)::int AS anio,
                EXTRACT(MONTH FROM fecha_inicio)::int AS mes
        """ + base_query + """
            ORDER BY fecha_inicio DESC NULLS LAST
            LIMIT 500
        """

        cur.execute(data_query, params)
        rows = cur.fetchall() or []

        # =====================================================
        # FILTERS QUERY (MISMO BASE QUERY)
        # =====================================================

        filters_query = """
            SELECT
                ARRAY_AGG(DISTINCT EXTRACT(YEAR FROM fecha_inicio)::int) AS years,
                ARRAY_AGG(DISTINCT EXTRACT(MONTH FROM fecha_inicio)::int) AS months,
                ARRAY_AGG(DISTINCT continente) AS continentes,
                ARRAY_AGG(DISTINCT pais) AS paises,
                ARRAY_AGG(DISTINCT puerto) AS puertos,
                ARRAY_AGG(DISTINCT cliente) AS clientes,
                ARRAY_AGG(DISTINCT buque_contenedor) AS buques,
                ARRAY_AGG(DISTINCT operacion) AS operaciones
        """ + base_query

        cur.execute(filters_query, params)
        filters_raw = cur.fetchone() or {}

        filters = {
            "years": sorted([y for y in filters_raw.get("years") or [] if y]),
            "months": sorted([m for m in filters_raw.get("months") or [] if m]),
            "continentes": sorted([c for c in filters_raw.get("continentes") or [] if c]),
            "paises": sorted([p for p in filters_raw.get("paises") or [] if p]),
            "puertos": sorted([p for p in filters_raw.get("puertos") or [] if p]),
            "clientes": sorted([c for c in filters_raw.get("clientes") or [] if c]),
            "buques": sorted([b for b in filters_raw.get("buques") or [] if b]),
            "operaciones": sorted([o for o in filters_raw.get("operaciones") or [] if o]),
        }

        return {
            "filters": filters,
            "data": rows,
            "count": len(rows)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error filtering servicios: {str(e)}"
        )

    finally:
        cur.close()


from datetime import datetime

# =========================================================
# CREATE
# =========================================================

@router.post("/")
def create_vessel_truck_supervision(
    payload: dict,
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    def safe(key, default=None):
        value = payload.get(key, default)
        return value if value not in ["", None] else default

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.strptime(value, "%d-%m-%Y").date()
        except:
            return None

    try:
        cert_no = safe("cert_no")

        if cert_no:
            cur.execute(
                """
                SELECT id
                FROM vessel_truck_supervision_reports
                WHERE cert_no = %s
                LIMIT 1
                """,
                (cert_no,)
            )
            existing = cur.fetchone()

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Truck Supervision report already exists for this "
                        "cert_no. Open it from Review to update it."
                    )
                )

        cur.execute("""
            INSERT INTO vessel_truck_supervision_reports (

                cert_no,
                customer,
                port,
                country,
                report_date,

                vessel_name,
                flag_port_registry,
                grt,
                nrt,
                imo_no,
                build_year,

                captain,
                chief_officer,

                arrival_date,
                inspection_date,
                supervision_completed_date,

                process_text,
                conclusion_text,

                findings_documental_text,
                findings_operational_text,
                incidents_text,

                status,
                created_at,
                updated_at

            ) VALUES (

                %(cert_no)s,
                %(customer)s,
                %(port)s,
                %(country)s,
                %(report_date)s,

                %(vessel_name)s,
                %(flag_port_registry)s,
                %(grt)s,
                %(nrt)s,
                %(imo_no)s,
                %(build_year)s,

                %(captain)s,
                %(chief_officer)s,

                %(arrival_date)s,
                %(inspection_date)s,
                %(supervision_completed_date)s,

                %(process_text)s,
                %(conclusion_text)s,

                %(findings_documental_text)s,
                %(findings_operational_text)s,
                %(incidents_text)s,

                'Pending for review',
                NOW(),
                NOW()

            )
            RETURNING id, created_at, updated_at, status
        """, {

            "cert_no": cert_no,
            "customer": safe("customer"),
            "port": safe("port"),
            "country": safe("country"),

            "report_date": parse_date(payload.get("report_date")),

            "vessel_name": safe("vessel_name"),
            "flag_port_registry": safe("flag_port_registry"),
            "grt": safe("grt"),
            "nrt": safe("nrt"),
            "imo_no": safe("imo_no"),
            "build_year": safe("build_year"),

            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            "arrival_date": parse_date(payload.get("arrival_date")),
            "inspection_date": parse_date(payload.get("inspection_date")),
            "supervision_completed_date": parse_date(payload.get("supervision_completed_date")),

            "process_text": safe("process_text"),
            "conclusion_text": safe("conclusion_text"),

            "findings_documental_text": safe("findings_documental_text"),
            "findings_operational_text": safe("findings_operational_text"),
            "incidents_text": safe("incidents_text"),
        })

        new_record = cur.fetchone()

        conn.commit()

        return {
            "success": True,
            "data": new_record
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating report: {str(e)}"
        )

    finally:
        cur.close()

# =========================================================
# LIST ALL (OPTIONAL STATUS FILTER)
# =========================================================

@router.get("/")
def list_vessel_truck_supervision(
    status: str | None = None,
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        base_query = """
            SELECT
                id,
                created_at,
                updated_at,

                cert_no,
                customer,
                port,
                country,
                report_date,

                vessel_name,
                flag_port_registry,
                grt,
                nrt,
                imo_no,
                build_year,

                captain,
                chief_officer,

                arrival_date,
                inspection_date,
                supervision_completed_date,

                process_text,
                findings_documental_text,
                findings_operational_text,
                incidents_text,
                conclusion_text,

                status
            FROM vessel_truck_supervision_reports
        """

        params = []

        if status:
            base_query += " WHERE status = %s"
            params.append(status)

        base_query += " ORDER BY id DESC"

        cur.execute(base_query, params)

        rows = cur.fetchall() or []

        return {
            "success": True,
            "count": len(rows),
            "data": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing reports: {str(e)}"
        )

    finally:
        cur.close()


# =========================================================
# GET BY ID
# =========================================================

@router.get("/{report_id}")
def get_vessel_truck_supervision(
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
                customer,
                port,
                country,
                report_date,

                vessel_name,
                flag_port_registry,
                grt,
                nrt,
                imo_no,
                build_year,

                captain,
                chief_officer,

                arrival_date,
                inspection_date,
                supervision_completed_date,

                process_text,
                findings_documental_text,
                findings_operational_text,
                incidents_text,
                conclusion_text,

                status

            FROM vessel_truck_supervision_reports
            WHERE id = %s
        """, (report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
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
            detail=f"Error retrieving report: {str(e)}"
        )

    finally:
        cur.close()


# =========================================================
# UPDATE
# =========================================================

@router.put("/{report_id}")
def update_vessel_truck_supervision(
    report_id: int,
    payload: dict,
    conn=Depends(get_db)
):
    from datetime import datetime, date
    from fastapi import HTTPException

    cur = conn.cursor()

    def safe(key, default=None):
        value = payload.get(key, default)
        return value if value not in ["", None] else default

    def parse_date(value):
        """
        Acepta:
        - dd-mm-YYYY   -> 22-04-2026
        - YYYY-mm-dd   -> 2026-04-22
        - date/datetime nativo
        - "", None     -> None
        """
        if value in ("", None):
            return None

        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        if isinstance(value, datetime):
            return value.date()

        if not isinstance(value, str):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid date type: {value}"
            )

        value = value.strip()

        for fmt in ("%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid date format '{value}'. "
                f"Use 'dd-mm-yyyy' or 'yyyy-mm-dd'."
            )
        )

    def parse_bool(value):
        """
        Soporta:
        True / False
        'true' / 'false'
        '1' / '0'
        'yes' / 'no'
        'on' / 'off'
        """
        if isinstance(value, bool):
            return value

        if value is None:
            return False

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "1", "yes", "y", "si", "sí", "on"):
                return True
            if normalized in ("false", "0", "no", "n", "off", ""):
                return False

        return False

    try:
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid payload. Expected JSON object."
            )

        # =====================================================
        # DETECT APPROVAL ACTION
        # =====================================================
        approve = parse_bool(payload.get("approve", False))
        status_value = "Approved" if approve else None

        # =====================================================
        # NORMALIZE DATES
        # =====================================================
        report_date = parse_date(payload.get("report_date"))
        arrival_date = parse_date(payload.get("arrival_date"))
        inspection_date = parse_date(payload.get("inspection_date"))
        supervision_completed_date = parse_date(
            payload.get("supervision_completed_date")
        )

        # =====================================================
        # BASE UPDATE
        # =====================================================
        update_query = """
            UPDATE vessel_truck_supervision_reports
            SET
                cert_no = %(cert_no)s,
                customer = %(customer)s,
                port = %(port)s,
                country = %(country)s,
                report_date = %(report_date)s,

                vessel_name = %(vessel_name)s,
                flag_port_registry = %(flag_port_registry)s,
                grt = %(grt)s,
                nrt = %(nrt)s,
                imo_no = %(imo_no)s,
                build_year = %(build_year)s,

                captain = %(captain)s,
                chief_officer = %(chief_officer)s,

                arrival_date = %(arrival_date)s,
                inspection_date = %(inspection_date)s,
                supervision_completed_date = %(supervision_completed_date)s,

                process_text = %(process_text)s,
                findings_documental_text = %(findings_documental_text)s,
                findings_operational_text = %(findings_operational_text)s,
                incidents_text = %(incidents_text)s,
                conclusion_text = %(conclusion_text)s,
        """

        # =====================================================
        # CONDITIONAL STATUS UPDATE
        # =====================================================
        if status_value:
            update_query += " status = %(status)s, "

        update_query += """
                updated_at = NOW()
            WHERE id = %(id)s
        """

        params = {
            "id": report_id,

            "cert_no": safe("cert_no"),
            "customer": safe("customer"),
            "port": safe("port"),
            "country": safe("country"),
            "report_date": report_date,

            "vessel_name": safe("vessel_name"),
            "flag_port_registry": safe("flag_port_registry"),
            "grt": safe("grt"),
            "nrt": safe("nrt"),
            "imo_no": safe("imo_no"),
            "build_year": safe("build_year"),

            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            "arrival_date": arrival_date,
            "inspection_date": inspection_date,
            "supervision_completed_date": supervision_completed_date,

            "process_text": safe("process_text"),
            "findings_documental_text": safe("findings_documental_text"),
            "findings_operational_text": safe("findings_operational_text"),
            "incidents_text": safe("incidents_text"),
            "conclusion_text": safe("conclusion_text"),
        }

        if status_value:
            params["status"] = status_value

        cur.execute(update_query, params)

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        conn.commit()

        return {
            "success": True,
            "id": report_id,
            "approved": approve
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating report: {str(e)}"
        )

    finally:
        cur.close()



# =========================================================
# approve generar reporte
# =========================================================

@router.post("/{report_id}/approve")
def approve_vessel_truck_supervision(
    report_id: int,
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        # =====================================================
        # 1️⃣ Obtener reporte
        # =====================================================
        cur.execute("""
            SELECT *
            FROM vessel_truck_supervision_reports
            WHERE id = %s
        """, (report_id,))

        report = cur.fetchone()

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        # =====================================================
        # 2️⃣ Generar PDF (Word + LibreOffice)
        # =====================================================
        pdf_path = generate_vessel_truck_supervision_pdf(report)

        # =====================================================
        # 3️⃣ Actualizar status del reporte
        # =====================================================
        cur.execute("""
            UPDATE vessel_truck_supervision_reports
            SET status = 'Approved',
                updated_at = NOW()
            WHERE id = %s
        """, (report_id,))

        # =====================================================
        # 4️⃣ Actualizar servicios.status_informe
        # =====================================================
        cert_no = report.get("cert_no")

        if cert_no:
            cur.execute("""
                UPDATE servicios
                SET status_informe = 'Approved'
                WHERE num_informe = %s
            """, (cert_no,))

        conn.commit()

        # =====================================================
        # 5️⃣ Devolver PDF al frontend
        # =====================================================
        return FileResponse(
            path=pdf_path,
            filename=f"{report.get('cert_no')}_Truck_Supervision_Report.pdf",
            media_type="application/pdf"
        )

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error approving report: {str(e)}"
        )

    finally:
        cur.close()




# =========================================================
# crear presentación
# =========================================================

@router.get("/{report_id}/presentation")
def generate_truck_presentation(report_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            "SELECT * FROM vessel_truck_supervision_reports WHERE id = %s",
            (report_id,)
        )
        report = cur.fetchone()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        pdf_path = generate_truck_supervision_presentation_pdf(report)

        return FileResponse(
            pdf_path,
            filename=f"Presentation_{report.get('cert_no')}.pdf",
            media_type="application/pdf"
        )

    finally:
        cur.close()



# =========================================================
# merge unificado reporte
# =========================================================

@router.get("/{report_id}/unified")
def generate_truck_unified(report_id: int, conn=Depends(get_db)):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cur.execute(
            "SELECT * FROM vessel_truck_supervision_reports WHERE id = %s",
            (report_id,)
        )
        report = cur.fetchone()

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        presentation_pdf = generate_truck_supervision_presentation_pdf(report)

        # Aquí debes generar o localizar el PDF principal del reporte
        report_pdf = generate_vessel_truck_supervision_pdf(report)

        unified_pdf = merge_pdfs(presentation_pdf, report_pdf)

        return FileResponse(
            unified_pdf,
            filename=f"Unified_{report.get('cert_no')}.pdf",
            media_type="application/pdf"
        )

    finally:
        cur.close()
