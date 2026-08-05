from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import Json, RealDictCursor

from database import get_db


router = APIRouter(prefix="/accounting/fixed-assets", tags=["Accounting Fixed Assets"])


CLASS_MAP = {
    "muebles y enseres": ("120-001-000-001", "120-002-000-001", "500-001-001-041", 120),
    "equipos de oficina": ("120-001-000-001", "120-002-000-001", "500-001-001-041", 120),
    "equipos de cocina": ("120-001-000-001", "120-002-000-001", "500-001-001-041", 120),
    "maquinaria y equipo": ("120-001-000-001", "120-002-000-001", "500-001-001-041", 120),
    "equipos de comunicacion": ("120-005-000-001", "120-006-000-001", "500-001-001-041", 60),
    "equipos de comunicación": ("120-005-000-001", "120-006-000-001", "500-001-001-041", 60),
    "equipos de transporte": ("1.2.01.05", "1.2.01.06", "5.1.11", 120),
}


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(400, "Monto invalido")


def _parse_date(value, default=None) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        return date.fromisoformat(value[:10])
    return default or date.today()


def _normalize(value) -> str:
    text = str(value or "").strip().lower()
    for src, dst in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        text = text.replace(src, dst)
    return " ".join(text.split())


def _last_day(year: int, month: int) -> date:
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + month - 1 + delta
    return index // 12, index % 12 + 1


def _table_exists(cur, table_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) AS table_name", (table_name,))
    row = cur.fetchone() or {}
    return bool(row.get("table_name"))


def _ensure_inventory_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS accounting_inventory_items (
            id BIGSERIAL PRIMARY KEY,
            item_code TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            category TEXT,
            location TEXT,
            responsible TEXT,
            unit TEXT,
            quantity NUMERIC(18,2) NOT NULL DEFAULT 0,
            minimum_quantity NUMERIC(18,2) NOT NULL DEFAULT 0,
            currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
            unit_cost NUMERIC(18,2) NOT NULL DEFAULT 0,
            total_cost_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            notes TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )


def _asset_rule(classification):
    return CLASS_MAP.get(_normalize(classification), CLASS_MAP["muebles y enseres"])


def _exchange_rate(cur, currency_code, purchase_date):
    currency = str(currency_code or "CRC").upper().strip()
    if currency == "CRC":
        return Decimal("1.00"), purchase_date
    cur.execute(
        """
        SELECT rate, rate_date
        FROM exchange_rate
        WHERE rate_date <= %s
        ORDER BY rate_date DESC
        LIMIT 1
        """,
        (purchase_date,),
    )
    row = cur.fetchone() or {}
    rate = Decimal(str(row.get("rate") or 1))
    return rate, row.get("rate_date") or purchase_date


def _next_asset_code(cur):
    cur.execute(
        """
        SELECT asset_code
        FROM fixed_assets
        WHERE asset_code LIKE 'MSL-AUTO-%'
        ORDER BY asset_code DESC
        LIMIT 1
        """
    )
    row = cur.fetchone() or {}
    current = str(row.get("asset_code") or "MSL-AUTO-0000").split("-")[-1]
    try:
        number = int(current) + 1
    except Exception:
        number = 1
    return f"MSL-AUTO-{number:04d}"


def _next_inventory_code(cur):
    cur.execute(
        """
        SELECT item_code
        FROM accounting_inventory_items
        WHERE item_code LIKE 'INV-%'
        ORDER BY item_code DESC
        LIMIT 1
        """
    )
    row = cur.fetchone() or {}
    current = str(row.get("item_code") or "INV-0000").split("-")[-1]
    try:
        number = int(current) + 1
    except Exception:
        number = 1
    return f"INV-{number:04d}"


def _rebuild_schedule(cur, asset_id, purchase_date, value_crc, life_months):
    cur.execute("DELETE FROM fixed_asset_depreciation_schedule WHERE asset_id=%s", (asset_id,))
    monthly = (value_crc / Decimal(life_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    accum = Decimal("0.00")
    for i in range(life_months):
        y, m = _add_months(purchase_date.year, purchase_date.month, i)
        depreciation = value_crc - accum if i == life_months - 1 else monthly
        accum = (accum + depreciation).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if accum > value_crc:
            accum = value_crc
        period = f"{y:04d}-{m:02d}"
        cur.execute(
            """
            INSERT INTO fixed_asset_depreciation_schedule (
                asset_id, period, depreciation_date, depreciation_amount_crc,
                accumulated_depreciation_crc, book_value_crc, status
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(asset_id, period) DO UPDATE SET
                depreciation_amount_crc=EXCLUDED.depreciation_amount_crc,
                accumulated_depreciation_crc=EXCLUDED.accumulated_depreciation_crc,
                book_value_crc=EXCLUDED.book_value_crc,
                status=EXCLUDED.status
            """,
            (
                asset_id,
                period,
                _last_day(y, m),
                depreciation,
                accum,
                value_crc - accum,
                "POSTED_BASE" if period < date.today().strftime("%Y-%m") else "SCHEDULED",
            ),
        )


def _asset_values(cur, payload, existing=None):
    existing = existing or {}
    purchase_date = _parse_date(payload.get("purchase_date"), existing.get("purchase_date") or date.today())
    currency = str(payload.get("currency_code") or existing.get("currency_code") or "CRC").upper()
    original = _money(payload.get("original_amount", existing.get("original_amount", 0)))
    tc, tc_date = _exchange_rate(cur, currency, purchase_date)
    value_crc = original if currency == "CRC" else (original * tc).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    classification = payload.get("classification", existing.get("classification") or "Muebles y enseres")
    asset_account, depr_account, expense_account, life_months = _asset_rule(classification)
    monthly = (value_crc / Decimal(life_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    months_elapsed = max(0, (date.today().year - purchase_date.year) * 12 + date.today().month - purchase_date.month)
    months_elapsed = min(months_elapsed, life_months)
    accum = (monthly * Decimal(months_elapsed)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if accum > value_crc:
        accum = value_crc
    return {
        "purchase_date": purchase_date,
        "purchase_year": purchase_date.year,
        "currency_code": currency,
        "original_amount": original,
        "exchange_rate": tc,
        "exchange_rate_date": tc_date,
        "value_crc": value_crc,
        "useful_life_months": life_months,
        "monthly_depreciation_crc": monthly,
        "accumulated_depreciation_crc": accum,
        "book_value_crc": value_crc - accum,
        "asset_account_code": asset_account,
        "accumulated_depreciation_account_code": depr_account,
        "depreciation_expense_account_code": expense_account,
    }


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


@router.post("")
def create_fixed_asset(payload: dict, db=Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        if not _table_exists(cur, "fixed_assets"):
            raise HTTPException(400, "La tabla fixed_assets no existe. Cargue activos primero.")
        asset_code = payload.get("asset_code") or _next_asset_code(cur)
        calc = _asset_values(cur, payload)
        description = str(payload.get("description") or "").strip()
        if not description:
            raise HTTPException(400, "Descripcion requerida")
        cur.execute(
            """
            INSERT INTO fixed_assets (
                asset_code, description, serial, location, responsible, role, area,
                plate, condition, classification, notes, purchase_date, purchase_year,
                currency_code, original_amount, exchange_rate, exchange_rate_date,
                value_crc, salvage_value_crc, depreciable_base_crc, useful_life_months,
                monthly_depreciation_crc, accumulated_depreciation_crc, book_value_crc,
                asset_account_code, accumulated_depreciation_account_code,
                depreciation_expense_account_code, status, source_file, metadata, created_by
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE','ERP_MANUAL',%s,%s
            )
            RETURNING id, asset_code
            """,
            (
                asset_code,
                description,
                payload.get("serial"),
                payload.get("location"),
                payload.get("responsible"),
                payload.get("role"),
                payload.get("area"),
                payload.get("plate") or asset_code,
                payload.get("condition") or "Nuevo",
                payload.get("classification") or "Muebles y enseres",
                payload.get("notes"),
                calc["purchase_date"],
                calc["purchase_year"],
                calc["currency_code"],
                calc["original_amount"],
                calc["exchange_rate"],
                calc["exchange_rate_date"],
                calc["value_crc"],
                calc["value_crc"],
                calc["useful_life_months"],
                calc["monthly_depreciation_crc"],
                calc["accumulated_depreciation_crc"],
                calc["book_value_crc"],
                calc["asset_account_code"],
                calc["accumulated_depreciation_account_code"],
                calc["depreciation_expense_account_code"],
                Json({"source": "manual"}),
                payload.get("user") or "ERP_USER",
            ),
        )
        row = cur.fetchone()
        _rebuild_schedule(cur, row["id"], calc["purchase_date"], calc["value_crc"], calc["useful_life_months"])
        db.commit()
        return {"ok": True, "id": row["id"], "asset_code": row["asset_code"]}


@router.put("/{asset_id}")
def update_fixed_asset(asset_id: int, payload: dict, db=Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM fixed_assets WHERE id=%s", (asset_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(404, "Activo no encontrado")
        merged = dict(existing)
        merged.update({k: v for k, v in payload.items() if v is not None})
        calc = _asset_values(cur, merged, existing)
        description = str(merged.get("description") or "").strip()
        if not description:
            raise HTTPException(400, "Descripcion requerida")
        cur.execute(
            """
            UPDATE fixed_assets
            SET description=%s,
                serial=%s,
                location=%s,
                responsible=%s,
                role=%s,
                area=%s,
                plate=%s,
                condition=%s,
                classification=%s,
                notes=%s,
                purchase_date=%s,
                purchase_year=%s,
                currency_code=%s,
                original_amount=%s,
                exchange_rate=%s,
                exchange_rate_date=%s,
                value_crc=%s,
                depreciable_base_crc=%s,
                useful_life_months=%s,
                monthly_depreciation_crc=%s,
                accumulated_depreciation_crc=%s,
                book_value_crc=%s,
                asset_account_code=%s,
                accumulated_depreciation_account_code=%s,
                depreciation_expense_account_code=%s,
                status=%s,
                updated_at=NOW()
            WHERE id=%s
            """,
            (
                description,
                merged.get("serial"),
                merged.get("location"),
                merged.get("responsible"),
                merged.get("role"),
                merged.get("area"),
                merged.get("plate") or merged.get("asset_code"),
                merged.get("condition") or "Nuevo",
                merged.get("classification") or "Muebles y enseres",
                merged.get("notes"),
                calc["purchase_date"],
                calc["purchase_year"],
                calc["currency_code"],
                calc["original_amount"],
                calc["exchange_rate"],
                calc["exchange_rate_date"],
                calc["value_crc"],
                calc["value_crc"],
                calc["useful_life_months"],
                calc["monthly_depreciation_crc"],
                calc["accumulated_depreciation_crc"],
                calc["book_value_crc"],
                calc["asset_account_code"],
                calc["accumulated_depreciation_account_code"],
                calc["depreciation_expense_account_code"],
                merged.get("status") or "ACTIVE",
                asset_id,
            ),
        )
        _rebuild_schedule(cur, asset_id, calc["purchase_date"], calc["value_crc"], calc["useful_life_months"])
        db.commit()
        return {"ok": True, "id": asset_id}


@router.put("/{asset_id}/disable")
def disable_fixed_asset(asset_id: int, payload: dict | None = None, db=Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("UPDATE fixed_assets SET status='INACTIVE', updated_at=NOW() WHERE id=%s RETURNING id", (asset_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Activo no encontrado")
        db.commit()
        return {"ok": True, "id": asset_id}


@router.get("/inventory/items")
def list_inventory_items(
    search: str | None = None,
    status: str | None = "ACTIVE",
    db=Depends(get_db),
):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_inventory_schema(cur)
        filters = []
        params = []
        if status and status != "TODOS":
            filters.append("status=%s")
            params.append(status)
        if search:
            filters.append("(item_code ILIKE %s OR description ILIKE %s OR category ILIKE %s OR location ILIKE %s)")
            like = f"%{search}%"
            params.extend([like, like, like, like])
        where = "WHERE " + " AND ".join(filters) if filters else ""
        cur.execute(
            f"""
            SELECT *
            FROM accounting_inventory_items
            {where}
            ORDER BY category NULLS LAST, item_code
            LIMIT 2000
            """,
            params,
        )
        rows = cur.fetchall()
        cur.execute(
            f"""
            SELECT COUNT(*) AS items, COALESCE(SUM(total_cost_crc),0) AS total_cost_crc
            FROM accounting_inventory_items
            {where}
            """,
            params,
        )
        return {"summary": dict(cur.fetchone() or {}), "data": rows}


@router.post("/inventory/items")
def create_inventory_item(payload: dict, db=Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_inventory_schema(cur)
        code = payload.get("item_code") or _next_inventory_code(cur)
        description = str(payload.get("description") or "").strip()
        if not description:
            raise HTTPException(400, "Descripcion requerida")
        qty = _money(payload.get("quantity"))
        unit_cost = _money(payload.get("unit_cost"))
        total = (qty * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cur.execute(
            """
            INSERT INTO accounting_inventory_items (
                item_code, description, category, location, responsible, unit,
                quantity, minimum_quantity, currency_code, unit_cost, total_cost_crc,
                status, notes
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'ACTIVE',%s)
            RETURNING id, item_code
            """,
            (
                code,
                description,
                payload.get("category"),
                payload.get("location"),
                payload.get("responsible"),
                payload.get("unit") or "unidad",
                qty,
                _money(payload.get("minimum_quantity")),
                payload.get("currency_code") or "CRC",
                unit_cost,
                total,
                payload.get("notes"),
            ),
        )
        row = cur.fetchone()
        db.commit()
        return {"ok": True, "id": row["id"], "item_code": row["item_code"]}


@router.put("/inventory/items/{item_id}")
def update_inventory_item(item_id: int, payload: dict, db=Depends(get_db)):
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        _ensure_inventory_schema(cur)
        cur.execute("SELECT * FROM accounting_inventory_items WHERE id=%s", (item_id,))
        existing = cur.fetchone()
        if not existing:
            raise HTTPException(404, "Inventario no encontrado")
        merged = dict(existing)
        merged.update({k: v for k, v in payload.items() if v is not None})
        qty = _money(merged.get("quantity"))
        unit_cost = _money(merged.get("unit_cost"))
        total = (qty * unit_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cur.execute(
            """
            UPDATE accounting_inventory_items
            SET description=%s, category=%s, location=%s, responsible=%s,
                unit=%s, quantity=%s, minimum_quantity=%s, currency_code=%s,
                unit_cost=%s, total_cost_crc=%s, status=%s, notes=%s, updated_at=NOW()
            WHERE id=%s
            """,
            (
                merged.get("description"),
                merged.get("category"),
                merged.get("location"),
                merged.get("responsible"),
                merged.get("unit") or "unidad",
                qty,
                _money(merged.get("minimum_quantity")),
                merged.get("currency_code") or "CRC",
                unit_cost,
                total,
                merged.get("status") or "ACTIVE",
                merged.get("notes"),
                item_id,
            ),
        )
        db.commit()
        return {"ok": True, "id": item_id}
