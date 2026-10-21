"""Explicit additive migration; no certificate data updates."""
from pathlib import Path
import runpy
import sys
import psycopg2

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"backend_api"))
config=runpy.run_path(str(root/"backend_api/hr.py"))
conn=psycopg2.connect(config["DATABASE_URL"],host="tramway.proxy.rlwy.net",port=15258,connect_timeout=15,sslmode="require")
try:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM sampling_certificates")
        before=cur.fetchone()[0]
        conn.rollback()
        if "--apply" not in sys.argv:
            print("Dry run: add 5 optional text columns. Existing sampling records:",before)
        else:
            cur.execute((root/"backend_api/migrations/20261020_sampling_certificate_compat.sql").read_text())
            cur.execute("SELECT COUNT(*) FROM sampling_certificates")
            assert cur.fetchone()[0]==before
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='sampling_certificates' AND column_name IN ('holds_inspected','observations','closing_date','closing_time','master')")
            assert len(cur.fetchall())==5
            print("Verified: five nullable columns present; record count unchanged:",before)
finally:
    conn.rollback();conn.close()
