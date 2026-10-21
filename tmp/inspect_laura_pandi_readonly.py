"""Locate the reported service without altering business data."""
import json
import runpy
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

root = Path(__file__).resolve().parents[1]
config = runpy.run_path(str(root / "backend_api/hr.py"))
conn = psycopg2.connect(
    config["DATABASE_URL"], host="tramway.proxy.rlwy.net", port=15258,
    sslmode="require", connect_timeout=15,
)
conn.set_session(readonly=True)
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET LOCAL statement_timeout='15s'")
        cur.execute("""
            SELECT to_jsonb(s) AS record FROM servicios s
            WHERE buque_contenedor ILIKE %s
            AND company_code IN ('MCI-CR','MSL-CR')
            ORDER BY consec DESC
        """, ("%LAURA%",))
        keys = (
            "consec", "company_code", "buque_contenedor", "cliente",
            "operacion", "estado", "num_informe", "fecha_inicio",
            "hora_inicio", "created_at", "updated_at", "created_by",
        )
        for item in cur.fetchall():
            row = item["record"]
            print(json.dumps({k: row[k] for k in keys if k in row}, ensure_ascii=False))
finally:
    conn.rollback()
    conn.close()
