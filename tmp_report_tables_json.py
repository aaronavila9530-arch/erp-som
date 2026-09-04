import json
import os
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

DSN = os.getenv("DATABASE_URL") or (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@tramway.proxy.rlwy.net:15258/"
    "railway?sslmode=require"
)

conn = psycopg2.connect(DSN)
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute(
    """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema='public'
      AND (
        table_name ILIKE '%report%'
        OR table_name ILIKE '%survey%'
        OR table_name ILIKE '%certificate%'
        OR table_name ILIKE '%sampling%'
        OR table_name ILIKE '%sealing%'
        OR table_name ILIKE '%lashing%'
        OR table_name ILIKE '%draft%'
        OR table_name ILIKE '%bunker%'
        OR table_name ILIKE '%captancy%'
        OR table_name ILIKE '%weight%'
        OR table_name ILIKE '%logra%'
      )
    ORDER BY table_name
    """
)
tables = [r["table_name"] for r in cur.fetchall()]
payload = {}
for table in tables:
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    payload[table] = [dict(r) for r in cur.fetchall()]

out = Path("tmp") / "report_tables_columns.json"
out.write_text(json.dumps(payload, default=str, indent=2), encoding="utf-8")
print(out.resolve())
print("tables", len(payload))
for table, cols in payload.items():
    print(table, len(cols))
cur.close()
conn.close()
