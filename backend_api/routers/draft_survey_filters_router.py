from fastapi import APIRouter, Depends, Query
from typing import Optional
from database import get_db

router = APIRouter(prefix="/draft-survey-filters", tags=["Draft Survey Filters"])


# =========================================================
# CASCADE FILTER ENDPOINT
# =========================================================
@router.get("/")
def get_draft_filters(
    continent: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    port: Optional[str] = Query(None),
    client: Optional[str] = Query(None),
    conn=Depends(get_db)
):

    cur = conn.cursor()

    try:

        # =====================================================
        # 1️⃣ BASE QUERY UNIFICADA
        # =====================================================
        base_query = """
            SELECT continent, country, year, month, port, client, draft_report_number
            FROM draft_survey
            UNION
            SELECT continent, country, year, month, port, client, draft_report_number
            FROM draft_survey_ballast
            UNION
            SELECT continent, country, year, month, port, client, draft_report_number
            FROM draft_survey_word_report
            UNION
            SELECT continent, country, year, month, port, client, draft_report_number
            FROM general_draft_survey
        """

        filters = []
        values = []

        # =====================================================
        # 2️⃣ FILTROS DINÁMICOS
        # =====================================================
        if continent:
            filters.append("continent = %s")
            values.append(continent)

        if country:
            filters.append("country = %s")
            values.append(country)

        if year:
            filters.append("year = %s")
            values.append(year)

        if month:
            filters.append("month = %s")
            values.append(month)

        if port:
            filters.append("port = %s")
            values.append(port)

        if client:
            filters.append("client = %s")
            values.append(client)

        final_query = f"SELECT DISTINCT * FROM ({base_query}) AS unified"

        if filters:
            final_query += " WHERE " + " AND ".join(filters)

        cur.execute(final_query, values)
        rows = cur.fetchall()

        # =====================================================
        # 3️⃣ CONSTRUIR RESPUESTA EN CASCADA
        # =====================================================
        continents = set()
        countries = set()
        years = set()
        months = set()
        ports = set()
        clients = set()
        reports = set()

        for r in rows:
            continents.add(r[0])
            countries.add(r[1])
            years.add(r[2])
            months.add(r[3])
            ports.add(r[4])
            clients.add(r[5])
            reports.add(r[6])

        return {
            "continents": sorted(filter(None, continents)),
            "countries": sorted(filter(None, countries)),
            "years": sorted(filter(None, years)),
            "months": sorted(filter(None, months)),
            "ports": sorted(filter(None, ports)),
            "clients": sorted(filter(None, clients)),
            "draft_reports": sorted(filter(None, reports))
        }

    finally:
        cur.close()