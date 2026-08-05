from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from database import get_db


router = APIRouter(prefix="/accounting/fixed-assets", tags=["Accounting Fixed Assets"])


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) AS table_name", (table_name,))
    row = cur.fetchone() or {}
    return bool(row.get("table_name"))


@router.get("")
def list_fixed_assets(
    search: str | None = None,
    status: str | None = Query(default="ACTIVE"),
    classification: str | None = None,
    limit: int = Query(default=500, ge=1, le=2000),
    db=Depends(get_db),
):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        if not _table_exists(cur, "fixed_assets"):
            return {
                "summary": {
                    "assets": 0,
                    "value_crc": 0,
                    "accumulated_depreciation_crc": 0,
                    "book_value_crc": 0,
                },
                "data": [],
            }

        filters = []
        params = []
        if status and str(status).upper() != "TODOS":
            filters.append("status = %s")
            params.append(status)
        if classification:
            filters.append("classification ILIKE %s")
            params.append(f"%{classification}%")
        if search:
            filters.append(
                "(asset_code ILIKE %s OR description ILIKE %s OR serial ILIKE %s OR responsible ILIKE %s OR location ILIKE %s)"
            )
            like = f"%{search}%"
            params.extend([like, like, like, like, like])
        where = "WHERE " + " AND ".join(filters) if filters else ""

        cur.execute(
            f"""
            SELECT
                COALESCE(COUNT(*), 0) AS assets,
                COALESCE(SUM(value_crc), 0) AS value_crc,
                COALESCE(SUM(accumulated_depreciation_crc), 0) AS accumulated_depreciation_crc,
                COALESCE(SUM(book_value_crc), 0) AS book_value_crc
            FROM fixed_assets
            {where}
            """,
            params,
        )
        summary = dict(cur.fetchone() or {})

        cur.execute(
            f"""
            SELECT
                id, asset_code, description, serial, location, responsible, role, area,
                plate, condition, classification, notes, purchase_date, purchase_year,
                currency_code, original_amount, exchange_rate, exchange_rate_date,
                value_crc, useful_life_months, monthly_depreciation_crc,
                accumulated_depreciation_crc, book_value_crc,
                asset_account_code, accumulated_depreciation_account_code,
                depreciation_expense_account_code, status, source_file, updated_at
            FROM fixed_assets
            {where}
            ORDER BY classification NULLS LAST, asset_code
            LIMIT %s
            """,
            params + [limit],
        )
        return {"summary": summary, "data": cur.fetchall()}


@router.get("/{asset_id}/schedule")
def get_fixed_asset_schedule(asset_id: int, db=Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        if not _table_exists(cur, "fixed_asset_depreciation_schedule"):
            raise HTTPException(404, "No existe calendario de depreciacion.")
        cur.execute(
            """
            SELECT
                period, depreciation_date, depreciation_amount_crc,
                accumulated_depreciation_crc, book_value_crc, status,
                accounting_entry_id
            FROM fixed_asset_depreciation_schedule
            WHERE asset_id = %s
            ORDER BY period
            """,
            (asset_id,),
        )
        return {"data": cur.fetchall()}
