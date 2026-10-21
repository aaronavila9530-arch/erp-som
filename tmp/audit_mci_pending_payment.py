from pathlib import Path
import sys,runpy,json
import psycopg2
from psycopg2.extras import RealDictCursor
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"backend_api"))
config=runpy.run_path(str(root/"backend_api/hr.py"))
conn=psycopg2.connect(config["DATABASE_URL"],host="tramway.proxy.rlwy.net",port=15258,sslmode="require",connect_timeout=15)
conn.set_session(readonly=True)
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id,payee_name,reference,issue_date,currency,total,balance,status,active,origin FROM payment_obligations WHERE company_code='MCI-CR' AND balance>0 ORDER BY payee_name,id")
        rows=[dict(r) for r in cur.fetchall()]
        (root/"tmp/mci_pending_before.json").write_text(json.dumps(rows,default=str,indent=2),encoding="utf-8")
        print(json.dumps(rows,default=str))
        cur.execute("SELECT * FROM accounting_accounts WHERE account_name ILIKE '%BAC%' OR account_name ILIKE '%HAZEL%'")
        print("ACCOUNTS",json.dumps([dict(r) for r in cur.fetchall()],default=str))
finally:
    conn.rollback();conn.close()
