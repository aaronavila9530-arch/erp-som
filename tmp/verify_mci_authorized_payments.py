from pathlib import Path
import sys,runpy,json
import psycopg2
from psycopg2.extras import RealDictCursor
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"backend_api"))
config=runpy.run_path(str(root/"backend_api/hr.py"))
ids=[r["id"] for r in json.loads((root/"tmp/mci_payments_verified.json").read_text(encoding="utf-8"))]
conn=psycopg2.connect(config["DATABASE_URL"],host="tramway.proxy.rlwy.net",port=15258,sslmode="require",connect_timeout=15)
conn.set_session(readonly=True)
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT payee_name,COUNT(*) AS obligations,currency,SUM(balance) AS balance
            FROM payment_obligations WHERE company_code='MCI-CR' AND COALESCE(active,TRUE)
            AND balance>0 GROUP BY payee_name,currency ORDER BY payee_name""")
        pending=[dict(r) for r in cur.fetchall()]
        print("PENDING",json.dumps(pending,default=str))
        assert len(pending)==4 and sum(r["obligations"] for r in pending)==8
        cur.execute("""SELECT p.id,p.currency,p.total,e.id AS entry_id,e.entry_date,p.last_payment_date,
            SUM(l.debit)-SUM(l.credit) AS difference
            FROM payment_obligations p JOIN accounting_entries e ON e.company_code=p.company_code
            AND e.origin='ITP_PAYMENT' AND e.origin_id=p.id
            JOIN accounting_lines l ON l.entry_id=e.id
            WHERE p.id=ANY(%s) AND p.status='PAID' AND p.balance=0 AND p.last_payment_date=p.issue_date
            GROUP BY p.id,e.id""",(ids,))
        rows=cur.fetchall()
        assert len(rows)==43 and all(r["difference"]==0 and r["entry_date"]==r["last_payment_date"] for r in rows)
        print("VERIFIED 43 PAID, 43 balanced payment entries, invoice dates, 8 protected pending.")
finally:conn.rollback();conn.close()
