import os
import re
import sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import openpyxl
from psycopg2.extras import Json, RealDictCursor, execute_values

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend_api"))

from backend_api.database import connect  # noqa: E402
from backend_api.routers.exchange_rate import _fetch_tc_venta_from_bccr  # noqa: E402
from routers.accounting_auxiliaries import _ensure_schema as ensure_aux_schema  # noqa: E402


SOURCE_FILE = r"C:\Users\aaron\Desktop\Activos e Inventario MSL FY2025.xlsx"
SOURCE_TABLE = "fixed_assets_import_2025"
PURCHASE_DATE = date(2024, 12, 31)
CREATED_BY = "SYSTEM_IMPORT_ACTIVOS_2025"


CLASS_MAP = {
    "muebles y enseres": {
        "asset_account": "120-001-000-001",
        "depr_account": "120-002-000-001",
        "expense_account": "500-001-001-041",
        "life_months": 120,
    },
    "equipos de oficina": {
        "asset_account": "120-001-000-001",
        "depr_account": "120-002-000-001",
        "expense_account": "500-001-001-041",
        "life_months": 120,
    },
    "equipos de comunicacion": {
        "asset_account": "120-005-000-001",
        "depr_account": "120-006-000-001",
        "expense_account": "500-001-001-041",
        "life_months": 60,
    },
    "equipos de comunicación": {
        "asset_account": "120-005-000-001",
        "depr_account": "120-006-000-001",
        "expense_account": "500-001-001-041",
        "life_months": 60,
    },
    "maquinaria y equipo": {
        "asset_account": "120-001-000-001",
        "depr_account": "120-002-000-001",
        "expense_account": "500-001-001-041",
        "life_months": 120,
    },
    "equipos de cocina": {
        "asset_account": "120-001-000-001",
        "depr_account": "120-002-000-001",
        "expense_account": "500-001-001-041",
        "life_months": 120,
    },
    "equipos de transporte": {
        "asset_account": "1.2.01.05",
        "depr_account": "1.2.01.06",
        "expense_account": "5.1.11",
        "life_months": 120,
    },
}


def money(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    if isinstance(value, str):
        value = value.strip().replace("$", "").replace("USD", "").replace("CRC", "")
        if "," in value and "." in value:
            value = value.replace(",", "")
        elif "," in value:
            value = value.replace(",", ".")
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def clean(value) -> str:
    return str(value or "").strip()


def normalize(value) -> str:
    text = clean(value).lower()
    text = text.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    return re.sub(r"\s+", " ", text)


def create_schema(cur):
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fixed_assets (
            id BIGSERIAL PRIMARY KEY,
            asset_code TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL,
            serial TEXT,
            location TEXT,
            responsible TEXT,
            role TEXT,
            area TEXT,
            plate TEXT,
            condition TEXT,
            classification TEXT,
            notes TEXT,
            purchase_date DATE NOT NULL,
            purchase_year INTEGER NOT NULL,
            currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
            original_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
            exchange_rate NUMERIC(18,6) NOT NULL DEFAULT 1,
            exchange_rate_date DATE,
            value_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            salvage_value_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            depreciable_base_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            useful_life_months INTEGER NOT NULL DEFAULT 120,
            monthly_depreciation_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            accumulated_depreciation_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            book_value_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            asset_account_code TEXT,
            accumulated_depreciation_account_code TEXT,
            depreciation_expense_account_code TEXT,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            source_file TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_by TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS fixed_asset_depreciation_schedule (
            id BIGSERIAL PRIMARY KEY,
            asset_id BIGINT NOT NULL REFERENCES fixed_assets(id) ON DELETE CASCADE,
            period VARCHAR(7) NOT NULL,
            depreciation_date DATE NOT NULL,
            depreciation_amount_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            accumulated_depreciation_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            book_value_crc NUMERIC(18,2) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'SCHEDULED',
            accounting_entry_id INTEGER,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(asset_id, period)
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fixed_assets_class ON fixed_assets(classification, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fixed_asset_schedule_period ON fixed_asset_depreciation_schedule(period, status)")


def get_tc(conn) -> tuple[Decimal, date]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT rate, rate_date
            FROM exchange_rate
            WHERE rate_date = %s
            LIMIT 1
            """,
            (PURCHASE_DATE,),
        )
        row = cur.fetchone()
        if row:
            return money(row["rate"]), row["rate_date"]

    rate, rate_date = _fetch_tc_venta_from_bccr(PURCHASE_DATE)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO exchange_rate(rate, rate_date, source)
            VALUES (%s, %s, 'BCCR_ASSETS')
            ON CONFLICT DO NOTHING
            """,
            (rate, rate_date),
        )
    conn.commit()
    return money(rate), rate_date


def read_assets():
    wb = openpyxl.load_workbook(SOURCE_FILE, data_only=True)
    ws = wb["Activos"]
    rows = []
    seen_codes = {}
    for row in ws.iter_rows(min_row=6, values_only=True):
        codigo, desc, serie, ubicacion, responsable, cargo, area, placa, estado, clasificacion, obs, monto = row[:12]
        if not desc and not placa and not monto:
            continue
        amount = money(monto)
        if amount <= 0:
            continue
        base_code = clean(placa) or f"MSL-AUTO-{clean(codigo)}"
        seen_codes[base_code] = seen_codes.get(base_code, 0) + 1
        asset_code = base_code if seen_codes[base_code] == 1 else f"{base_code}-DUP{seen_codes[base_code]}"
        rows.append(
            {
                "codigo_excel": clean(codigo),
                "description": clean(desc),
                "serial": clean(serie),
                "location": clean(ubicacion),
                "responsible": clean(responsable),
                "role": clean(cargo),
                "area": clean(area),
                "asset_code": asset_code,
                "original_plate": base_code,
                "condition": clean(estado),
                "classification": clean(clasificacion),
                "notes": clean(obs),
                "amount_usd": amount,
            }
        )
    return rows


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = (year * 12 + (month - 1)) + delta
    return month_index // 12, month_index % 12 + 1


def last_day(year: int, month: int) -> date:
    next_year, next_month = add_months(year, month, 1)
    return date(next_year, next_month, 1).replace(day=1) - __import__("datetime").timedelta(days=1)


def upsert_aux_asset(cur, asset, value_crc):
    cur.execute(
        """
        INSERT INTO accounting_auxiliary_entities (
            entity_type, entity_code, entity_name, identification, currency_code,
            control_account_code, source_table, source_id, metadata, created_by
        ) VALUES ('ASSET', %s, %s, %s, 'CRC', %s, %s, %s, %s, %s)
        ON CONFLICT(entity_type, entity_code) DO UPDATE SET
            entity_name = EXCLUDED.entity_name,
            control_account_code = EXCLUDED.control_account_code,
            metadata = accounting_auxiliary_entities.metadata || EXCLUDED.metadata,
            active = TRUE,
            updated_at = NOW()
        RETURNING id
        """,
        (
            asset["asset_code"],
            asset["description"],
            asset["serial"] or asset["asset_code"],
            asset["asset_account"],
            SOURCE_TABLE,
            asset["asset_code"],
            Json({"fixed_asset": True, "classification": asset["classification"]}),
            CREATED_BY,
        ),
    )
    entity_id = cur.fetchone()["id"]
    cur.execute(
        """
        INSERT INTO accounting_auxiliary_documents (
            entity_id, document_type, document_number, issue_date, due_date,
            currency_code, original_amount, open_amount, status, reference,
            source_table, source_id, metadata, created_by
        ) VALUES (%s, 'FIXED_ASSET', %s, %s, NULL, 'CRC', %s, %s, 'OPEN', %s, %s, %s, %s, %s)
        ON CONFLICT(source_table, source_id, document_type) DO UPDATE SET
            entity_id = EXCLUDED.entity_id,
            issue_date = EXCLUDED.issue_date,
            original_amount = EXCLUDED.original_amount,
            open_amount = EXCLUDED.open_amount,
            status = 'OPEN',
            reference = EXCLUDED.reference,
            metadata = accounting_auxiliary_documents.metadata || EXCLUDED.metadata,
            updated_at = NOW()
        """,
        (
            entity_id,
            asset["asset_code"],
            PURCHASE_DATE,
            value_crc,
            value_crc,
            asset["description"],
            SOURCE_TABLE,
            asset["asset_code"],
            Json({"source_file": os.path.basename(SOURCE_FILE)}),
            CREATED_BY,
        ),
    )


def main():
    assets = read_assets()
    conn = connect()
    try:
        ensure_aux_schema(conn)
        tc, tc_date = get_tc(conn)
        inserted = 0
        updated = 0
        total_usd = Decimal("0.00")
        total_crc = Decimal("0.00")
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            create_schema(cur)
            for asset in assets:
                rule = CLASS_MAP.get(normalize(asset["classification"]), CLASS_MAP["muebles y enseres"])
                value_crc = (asset["amount_usd"] * tc).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                monthly_dep = (value_crc / Decimal(rule["life_months"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                months_elapsed = max(0, (date.today().year - PURCHASE_DATE.year) * 12 + (date.today().month - PURCHASE_DATE.month))
                months_elapsed = min(months_elapsed, rule["life_months"])
                accum_dep = (monthly_dep * Decimal(months_elapsed)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if accum_dep > value_crc:
                    accum_dep = value_crc
                book_value = value_crc - accum_dep
                asset.update(
                    {
                        "asset_account": rule["asset_account"],
                        "depr_account": rule["depr_account"],
                        "expense_account": rule["expense_account"],
                    }
                )
                cur.execute("SELECT id FROM fixed_assets WHERE asset_code=%s", (asset["asset_code"],))
                existed = cur.fetchone() is not None
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
                        'USD',%s,%s,%s,%s,0,%s,%s,%s,%s,%s,
                        %s,%s,%s,'ACTIVE',%s,%s,%s
                    )
                    ON CONFLICT(asset_code) DO UPDATE SET
                        description=EXCLUDED.description,
                        serial=EXCLUDED.serial,
                        location=EXCLUDED.location,
                        responsible=EXCLUDED.responsible,
                        role=EXCLUDED.role,
                        area=EXCLUDED.area,
                        plate=EXCLUDED.plate,
                        condition=EXCLUDED.condition,
                        classification=EXCLUDED.classification,
                        notes=EXCLUDED.notes,
                        purchase_date=EXCLUDED.purchase_date,
                        purchase_year=EXCLUDED.purchase_year,
                        currency_code=EXCLUDED.currency_code,
                        original_amount=EXCLUDED.original_amount,
                        exchange_rate=EXCLUDED.exchange_rate,
                        exchange_rate_date=EXCLUDED.exchange_rate_date,
                        value_crc=EXCLUDED.value_crc,
                        depreciable_base_crc=EXCLUDED.depreciable_base_crc,
                        useful_life_months=EXCLUDED.useful_life_months,
                        monthly_depreciation_crc=EXCLUDED.monthly_depreciation_crc,
                        accumulated_depreciation_crc=EXCLUDED.accumulated_depreciation_crc,
                        book_value_crc=EXCLUDED.book_value_crc,
                        asset_account_code=EXCLUDED.asset_account_code,
                        accumulated_depreciation_account_code=EXCLUDED.accumulated_depreciation_account_code,
                        depreciation_expense_account_code=EXCLUDED.depreciation_expense_account_code,
                        status='ACTIVE',
                        source_file=EXCLUDED.source_file,
                        metadata=fixed_assets.metadata || EXCLUDED.metadata,
                        updated_at=NOW()
                    RETURNING id
                    """,
                    (
                        asset["asset_code"],
                        asset["description"],
                        asset["serial"],
                        asset["location"],
                        asset["responsible"],
                        asset["role"],
                        asset["area"],
                        asset["original_plate"],
                        asset["condition"],
                        asset["classification"],
                        asset["notes"],
                        PURCHASE_DATE,
                        PURCHASE_DATE.year,
                        asset["amount_usd"],
                        tc,
                        tc_date,
                        value_crc,
                        value_crc,
                        rule["life_months"],
                        monthly_dep,
                        accum_dep,
                        book_value,
                        rule["asset_account"],
                        rule["depr_account"],
                        rule["expense_account"],
                        os.path.basename(SOURCE_FILE),
                        Json(
                            {
                                "excel_codigo": asset["codigo_excel"],
                                "source_sheet": "Activos",
                                "original_plate": asset["original_plate"],
                            }
                        ),
                        CREATED_BY,
                    ),
                )
                asset_id = cur.fetchone()["id"]
                cur.execute("DELETE FROM fixed_asset_depreciation_schedule WHERE asset_id=%s", (asset_id,))
                accum = Decimal("0.00")
                schedule_rows = []
                for i in range(rule["life_months"]):
                    y, m = add_months(PURCHASE_DATE.year, PURCHASE_DATE.month, i)
                    if i == rule["life_months"] - 1:
                        dep = value_crc - accum
                    else:
                        dep = monthly_dep
                    accum = (accum + dep).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    if accum > value_crc:
                        accum = value_crc
                    period = f"{y:04d}-{m:02d}"
                    schedule_rows.append(
                        (
                            asset_id,
                            period,
                            last_day(y, m),
                            dep,
                            accum,
                            value_crc - accum,
                            "POSTED_BASE" if period < date.today().strftime("%Y-%m") else "SCHEDULED",
                        )
                    )
                execute_values(
                    cur,
                    """
                    INSERT INTO fixed_asset_depreciation_schedule (
                        asset_id, period, depreciation_date, depreciation_amount_crc,
                        accumulated_depreciation_crc, book_value_crc, status
                    ) VALUES %s
                    ON CONFLICT(asset_id, period) DO UPDATE SET
                        depreciation_amount_crc=EXCLUDED.depreciation_amount_crc,
                        accumulated_depreciation_crc=EXCLUDED.accumulated_depreciation_crc,
                        book_value_crc=EXCLUDED.book_value_crc,
                        status=EXCLUDED.status
                    """,
                    schedule_rows,
                    page_size=500,
                )
                upsert_aux_asset(cur, asset, value_crc)
                inserted += 0 if existed else 1
                updated += 1 if existed else 0
                total_usd += asset["amount_usd"]
                total_crc += value_crc
        conn.commit()
        print(
            {
                "source_rows": len(assets),
                "inserted": inserted,
                "updated": updated,
                "tc": str(tc),
                "tc_date": str(tc_date),
                "total_usd": str(total_usd.quantize(Decimal("0.01"))),
                "total_crc": str(total_crc.quantize(Decimal("0.01"))),
            }
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
