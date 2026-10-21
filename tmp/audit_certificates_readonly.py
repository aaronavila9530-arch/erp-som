"""Read-only schema and company-link audit. No business content is printed."""
import json
from pathlib import Path
import runpy
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend_api"))
config = runpy.run_path(str(root / "backend_api/hr.py"))
conn = psycopg2.connect(config["DATABASE_URL"], host="tramway.proxy.rlwy.net", port=15258,
                        connect_timeout=15, sslmode="require")
conn.set_session(readonly=True)
tables = {"weight_certificates":"report_number", "vessel_holds_inspection_certificates":"report_number",
          "sampling_certificates":"report_no", "sealing_certificates":"report_no", "lashing_certificates":"report_no"}
result = {}
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET LOCAL statement_timeout='20s'")
        for table, key in tables.items():
            cur.execute("""SELECT column_name,data_type,character_maximum_length,is_nullable,column_default
                FROM information_schema.columns WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position""", (table,))
            cols = [dict(r) for r in cur.fetchall()]
            cur.execute(f"""SELECT COALESCE(s.company,'UNLINKED') AS company,s.companies,COUNT(*) AS records
                FROM {table} c LEFT JOIN LATERAL (
                  SELECT MIN(company_code) AS company,COUNT(DISTINCT company_code) AS companies
                  FROM servicios WHERE num_informe=c.{key}) s ON TRUE
                GROUP BY s.company,s.companies""")
            counts = [dict(r) for r in cur.fetchall()]
            cur.execute(f"SELECT status,COUNT(*) AS records FROM {table} GROUP BY status")
            result[table] = dict(columns=cols, links=counts, statuses=[dict(r) for r in cur.fetchall()])
    target = root / "tmp/certificates-qa"
    target.mkdir(exist_ok=True)
    (target / "schema.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    for table, item in result.items():
        print(table, json.dumps(item, default=str))
finally:
    conn.rollback()
    conn.close()
