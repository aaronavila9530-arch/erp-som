from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
from typing import Optional
from datetime import datetime

from database import get_db


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/vessel-truck-supervision",
    tags=["Vessel Truck Supervision"]
)


# =========================================================
# FILTER SERVICIOS (PARA POPUP BUSQUEDA)
# =========================================================
from psycopg2.extras import RealDictCursor
from fastapi import Query

@router.get("/servicios-filter")
def filter_servicios(
    num_informe: str | None = None,
    buque_contenedor: str | None = None,
    cliente: str | None = None,
    continente: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    anio: int | None = Query(None),
    mes: int | None = Query(None),
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        base_query = """
            FROM servicios
            WHERE tipo = 'Buque'
              AND num_informe IS NOT NULL
        """

        params = []

        if num_informe:
            base_query += " AND num_informe = %s"
            params.append(num_informe)

        if buque_contenedor:
            base_query += " AND buque_contenedor = %s"
            params.append(buque_contenedor)

        if cliente:
            base_query += " AND cliente = %s"
            params.append(cliente)

        if continente:
            base_query += " AND continente = %s"
            params.append(continente)

        if pais:
            base_query += " AND pais = %s"
            params.append(pais)

        if puerto:
            base_query += " AND puerto = %s"
            params.append(puerto)

        if anio:
            base_query += " AND EXTRACT(YEAR FROM fecha_inicio) = %s"
            params.append(anio)

        if mes:
            base_query += " AND EXTRACT(MONTH FROM fecha_inicio) = %s"
            params.append(mes)

        query = """
            SELECT
                consec AS id,
                num_informe,
                buque_contenedor,
                cliente,
                continente,
                pais,
                puerto,
                EXTRACT(YEAR FROM fecha_inicio) AS anio,
                EXTRACT(MONTH FROM fecha_inicio) AS mes
        """ + base_query + """
            ORDER BY fecha_inicio DESC NULLS LAST
            LIMIT 500
        """

        cur.execute(query, params)
        rows = cur.fetchall() or []

        return {
            "success": True,
            "count": len(rows),
            "data": rows
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error filtering servicios: {str(e)}"
        )

    finally:
        cur.close()


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

    try:

        cur.execute("""
            INSERT INTO vessel_truck_supervision_reports (

                cert_no,
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
                findings_text,
                conclusion_text,

                created_at,
                updated_at

            ) VALUES (

                %(cert_no)s,
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
                %(findings_text)s,
                %(conclusion_text)s,

                NOW(),
                NOW()

            )
            RETURNING id, created_at, updated_at
        """, {

            "cert_no": safe("cert_no"),
            "port": safe("port"),
            "country": safe("country"),
            "report_date": safe("report_date"),

            "vessel_name": safe("vessel_name"),
            "flag_port_registry": safe("flag_port_registry"),
            "grt": safe("grt"),
            "nrt": safe("nrt"),
            "imo_no": safe("imo_no"),
            "build_year": safe("build_year"),

            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            "arrival_date": safe("arrival_date"),
            "inspection_date": safe("inspection_date"),
            "supervision_completed_date": safe("supervision_completed_date"),

            "process_text": safe("process_text"),
            "findings_text": safe("findings_text"),
            "conclusion_text": safe("conclusion_text"),
        })

        new_record = cur.fetchone()

        conn.commit()

        return {
            "success": True,
            "data": new_record
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating report: {str(e)}"
        )

    finally:
        cur.close()


# =========================================================
# LIST ALL
# =========================================================

@router.get("/")
def list_vessel_truck_supervision(
    conn=Depends(get_db)
):

    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:

        cur.execute("""
            SELECT *
            FROM vessel_truck_supervision_reports
            ORDER BY id DESC
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

    cur = conn.cursor()

    def safe(key, default=None):
        value = payload.get(key, default)
        return value if value not in ["", None] else default

    try:

        cur.execute("""
            UPDATE vessel_truck_supervision_reports
            SET

                cert_no = %(cert_no)s,
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
                findings_text = %(findings_text)s,
                conclusion_text = %(conclusion_text)s,

                updated_at = NOW()

            WHERE id = %(id)s
        """, {

            "id": report_id,

            "cert_no": safe("cert_no"),
            "port": safe("port"),
            "country": safe("country"),
            "report_date": safe("report_date"),

            "vessel_name": safe("vessel_name"),
            "flag_port_registry": safe("flag_port_registry"),
            "grt": safe("grt"),
            "nrt": safe("nrt"),
            "imo_no": safe("imo_no"),
            "build_year": safe("build_year"),

            "captain": safe("captain"),
            "chief_officer": safe("chief_officer"),

            "arrival_date": safe("arrival_date"),
            "inspection_date": safe("inspection_date"),
            "supervision_completed_date": safe("supervision_completed_date"),

            "process_text": safe("process_text"),
            "findings_text": safe("findings_text"),
            "conclusion_text": safe("conclusion_text"),
        })

        if cur.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
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
            detail=f"Error updating report: {str(e)}"
        )

    finally:
        cur.close()


