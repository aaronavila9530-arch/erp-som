from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Header, HTTPException
from psycopg2.extras import RealDictCursor

import database
from services.tenanting import company_code


router = APIRouter(prefix="/companies", tags=["Companies"])


DEFAULT_COMPANIES = [
    {
        "company_code": "MSL-CR",
        "company_name": "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL",
        "legal_name": "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL",
        "trade_name": "MSL",
        "country": "Costa Rica",
    },
    {
        "company_code": "MMS-CR",
        "company_name": "MMS MARITIME MASTER SURVEYORS SRL",
        "legal_name": "MMS MARITIME MASTER SURVEYORS SRL",
        "trade_name": "MMS",
        "country": "Costa Rica",
    },
]

PROFILE_FIELDS = (
    "company_code",
    "company_name",
    "legal_name",
    "trade_name",
    "tax_id",
    "economic_activity",
    "phone",
    "billing_email",
    "email",
    "country",
    "province",
    "canton",
    "district",
    "address",
    "notes",
)


def _ensure_schema() -> None:
    database.sql(
        """
        CREATE TABLE IF NOT EXISTS company_profiles (
            company_code VARCHAR(30) PRIMARY KEY,
            company_name TEXT NOT NULL,
            legal_name TEXT,
            trade_name TEXT,
            tax_id TEXT,
            economic_activity TEXT,
            phone TEXT,
            billing_email TEXT,
            email TEXT,
            country TEXT,
            province TEXT,
            canton TEXT,
            district TEXT,
            address TEXT,
            notes TEXT,
            updated_by TEXT,
            updated_at TIMESTAMP
        )
        """
    )
    for item in DEFAULT_COMPANIES:
        database.sql(
            """
            INSERT INTO company_profiles (
                company_code, company_name, legal_name, trade_name, country, updated_at
            )
            VALUES (%(company_code)s, %(company_name)s, %(legal_name)s, %(trade_name)s, %(country)s, %(updated_at)s)
            ON CONFLICT (company_code) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                legal_name = COALESCE(NULLIF(company_profiles.legal_name, ''), EXCLUDED.legal_name),
                trade_name = COALESCE(NULLIF(company_profiles.trade_name, ''), EXCLUDED.trade_name),
                country = COALESCE(NULLIF(company_profiles.country, ''), EXCLUDED.country)
            """,
            {**item, "updated_at": datetime.now()},
        )


def _row_for_company(code: str) -> dict:
    _ensure_schema()
    conn = database.get_conn()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT *
            FROM company_profiles
            WHERE company_code = %s
            """,
            (company_code(code),),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Empresa no existe")
        return dict(row)
    finally:
        if cur:
            cur.close()
        database.release_conn(conn)


@router.get("/")
def list_companies():
    _ensure_schema()
    conn = database.get_conn()
    cur = None
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT *
            FROM company_profiles
            ORDER BY company_code
            """
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        if cur:
            cur.close()
        database.release_conn(conn)


@router.get("/current")
def get_current_company(x_company_code: str | None = Header(None, alias="X-Company-Code")):
    return _row_for_company(company_code(header_value=x_company_code))


@router.get("/{code}")
def get_company(code: str):
    return _row_for_company(code)


@router.put("/{code}")
def update_company_profile(
    code: str,
    payload: dict,
    x_user: str | None = Header(None, alias="X-User"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_schema()
    target_code = company_code(code, x_company_code)
    clean = {field: str((payload or {}).get(field) or "").strip() for field in PROFILE_FIELDS if field != "company_code"}
    clean["company_code"] = target_code
    clean["company_name"] = clean.get("company_name") or clean.get("legal_name") or target_code
    clean["updated_by"] = str(x_user or "").strip() or None
    clean["updated_at"] = datetime.now()

    database.sql(
        """
        INSERT INTO company_profiles (
            company_code, company_name, legal_name, trade_name, tax_id, economic_activity,
            phone, billing_email, email, country, province, canton, district, address,
            notes, updated_by, updated_at
        )
        VALUES (
            %(company_code)s, %(company_name)s, %(legal_name)s, %(trade_name)s, %(tax_id)s, %(economic_activity)s,
            %(phone)s, %(billing_email)s, %(email)s, %(country)s, %(province)s, %(canton)s, %(district)s, %(address)s,
            %(notes)s, %(updated_by)s, %(updated_at)s
        )
        ON CONFLICT (company_code) DO UPDATE SET
            company_name = EXCLUDED.company_name,
            legal_name = EXCLUDED.legal_name,
            trade_name = EXCLUDED.trade_name,
            tax_id = EXCLUDED.tax_id,
            economic_activity = EXCLUDED.economic_activity,
            phone = EXCLUDED.phone,
            billing_email = EXCLUDED.billing_email,
            email = EXCLUDED.email,
            country = EXCLUDED.country,
            province = EXCLUDED.province,
            canton = EXCLUDED.canton,
            district = EXCLUDED.district,
            address = EXCLUDED.address,
            notes = EXCLUDED.notes,
            updated_by = EXCLUDED.updated_by,
            updated_at = EXCLUDED.updated_at
        """,
        clean,
    )
    return _row_for_company(target_code)
