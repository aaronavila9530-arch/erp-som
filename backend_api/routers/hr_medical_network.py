from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query
from psycopg2.extras import RealDictCursor

from database import get_db
from services.tenanting import company_code


router = APIRouter(prefix="/hr/medical-network", tags=["HHRR - Medical Network"])


def ensure_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS hr_medical_network (
            id SERIAL PRIMARY KEY,
            company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR',
            tasacion_id TEXT,
            professional_name TEXT NOT NULL,
            specialty TEXT,
            consultation_type TEXT,
            service_type TEXT,
            clinic_name TEXT,
            province TEXT,
            canton TEXT,
            district TEXT,
            search_text TEXT,
            source_file TEXT,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            imported_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_hr_medical_network_company_tasacion
        ON hr_medical_network(company_code, tasacion_id)
        WHERE tasacion_id IS NOT NULL AND TRIM(tasacion_id) <> ''
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_hr_medical_network_filters
        ON hr_medical_network(company_code, province, canton, specialty, consultation_type)
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_hr_medical_network_search
        ON hr_medical_network USING gin(to_tsvector('simple', COALESCE(search_text, '')))
        """
    )


def _norm(value):
    text = str(value or "").strip()
    return text or None


def _search_blob(row: dict) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in (
            "tasacion_id",
            "professional_name",
            "specialty",
            "consultation_type",
            "service_type",
            "clinic_name",
            "province",
            "canton",
            "district",
        )
    )


def _param(value):
    text = str(value or "").strip() if isinstance(value, str) else ""
    return text or None


@router.post("/bulk-upsert")
def bulk_upsert_medical_network(
    payload: dict,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    company = company_code(payload.get("company_code"), x_company_code)
    rows = payload.get("items") or []
    source_file = _norm(payload.get("source_file"))
    inserted = 0
    updated = 0
    skipped = 0

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        for item in rows:
            row = {
                "company_code": company,
                "tasacion_id": _norm(item.get("tasacion_id")),
                "professional_name": _norm(item.get("professional_name")),
                "specialty": _norm(item.get("specialty")),
                "consultation_type": _norm(item.get("consultation_type")),
                "service_type": _norm(item.get("service_type")),
                "clinic_name": _norm(item.get("clinic_name")),
                "province": _norm(item.get("province")),
                "canton": _norm(item.get("canton")),
                "district": _norm(item.get("district")),
                "source_file": source_file,
            }
            if not row["professional_name"]:
                skipped += 1
                continue
            row["search_text"] = _search_blob(row)
            cur.execute(
                """
                INSERT INTO hr_medical_network (
                    company_code, tasacion_id, professional_name, specialty, consultation_type,
                    service_type, clinic_name, province, canton, district, search_text,
                    source_file, active, imported_at, updated_at
                ) VALUES (
                    %(company_code)s, %(tasacion_id)s, %(professional_name)s, %(specialty)s,
                    %(consultation_type)s, %(service_type)s, %(clinic_name)s, %(province)s,
                    %(canton)s, %(district)s, %(search_text)s, %(source_file)s, TRUE, NOW(), NOW()
                )
                ON CONFLICT (company_code, tasacion_id) WHERE tasacion_id IS NOT NULL AND TRIM(tasacion_id) <> ''
                DO UPDATE SET
                    professional_name=EXCLUDED.professional_name,
                    specialty=EXCLUDED.specialty,
                    consultation_type=EXCLUDED.consultation_type,
                    service_type=EXCLUDED.service_type,
                    clinic_name=EXCLUDED.clinic_name,
                    province=EXCLUDED.province,
                    canton=EXCLUDED.canton,
                    district=EXCLUDED.district,
                    search_text=EXCLUDED.search_text,
                    source_file=EXCLUDED.source_file,
                    active=TRUE,
                    updated_at=NOW()
                RETURNING (xmax = 0) AS inserted
                """,
                row,
            )
            if cur.fetchone()["inserted"]:
                inserted += 1
            else:
                updated += 1
        conn.commit()
    return {"status": "ok", "inserted": inserted, "updated": updated, "skipped": skipped}


@router.get("/filters")
def medical_network_filters(
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    company = company_code(header_value=x_company_code)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        result = {}
        for key, col in (
            ("provinces", "province"),
            ("cantons", "canton"),
            ("districts", "district"),
            ("specialties", "specialty"),
            ("consultation_types", "consultation_type"),
            ("service_types", "service_type"),
            ("clinics", "clinic_name"),
        ):
            cur.execute(
                f"""
                SELECT DISTINCT {col} AS value
                FROM hr_medical_network
                WHERE company_code=%s AND active=TRUE AND COALESCE(TRIM({col}), '') <> ''
                ORDER BY {col}
                """,
                (company,),
            )
            result[key] = [row["value"] for row in cur.fetchall()]
        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   COUNT(DISTINCT specialty) AS specialties,
                   COUNT(DISTINCT province) AS provinces,
                   COUNT(DISTINCT professional_name) AS professionals
            FROM hr_medical_network
            WHERE company_code=%s AND active=TRUE
            """,
            (company,),
        )
        result["summary"] = dict(cur.fetchone() or {})
    return result


@router.get("/search")
def search_medical_network(
    q: str | None = Query(None),
    province: str | None = Query(None),
    canton: str | None = Query(None),
    district: str | None = Query(None),
    specialty: str | None = Query(None),
    consultation_type: str | None = Query(None),
    service_type: str | None = Query(None),
    clinic: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    q = _param(q)
    province = _param(province)
    canton = _param(canton)
    district = _param(district)
    specialty = _param(specialty)
    consultation_type = _param(consultation_type)
    service_type = _param(service_type)
    clinic = _param(clinic)
    company = company_code(header_value=x_company_code)
    filters = ["company_code=%(company)s", "active=TRUE"]
    params = {"company": company, "limit": page_size, "offset": (page - 1) * page_size}
    for key, col, value in (
        ("province", "province", province),
        ("canton", "canton", canton),
        ("district", "district", district),
        ("specialty", "specialty", specialty),
        ("consultation_type", "consultation_type", consultation_type),
        ("service_type", "service_type", service_type),
        ("clinic", "clinic_name", clinic),
    ):
        if value:
            filters.append(f"{col} = %({key})s")
            params[key] = value
    if q:
        filters.append("search_text ILIKE %(q)s")
        params["q"] = f"%{q.strip()}%"
    where_sql = " AND ".join(filters)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        ensure_schema(cur)
        cur.execute(f"SELECT COUNT(*) AS total FROM hr_medical_network WHERE {where_sql}", params)
        total = cur.fetchone()["total"]
        cur.execute(
            f"""
            SELECT id, tasacion_id, professional_name, specialty, consultation_type,
                   service_type, clinic_name, province, canton, district
            FROM hr_medical_network
            WHERE {where_sql}
            ORDER BY province NULLS LAST, canton NULLS LAST, specialty NULLS LAST, professional_name
            LIMIT %(limit)s OFFSET %(offset)s
            """,
            params,
        )
        data = [dict(row) for row in cur.fetchall()]
    return {"total": total, "page": page, "page_size": page_size, "data": data}
