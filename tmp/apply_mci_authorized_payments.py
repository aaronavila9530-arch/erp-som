"""Authorized bookkeeping only; no bank transfer. Atomic batch with verification."""
from pathlib import Path
from datetime import date
from decimal import Decimal
import sys,runpy,json,unicodedata,re
from unittest.mock import patch
import psycopg2
from psycopg2.extras import RealDictCursor
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"backend_api"))
from routers.invoice_to_pay import apply_payment
from services.accounting_auto import sync_itp_to_accounting
config=runpy.run_path(str(root/"backend_api/hr.py"))
conn=psycopg2.connect(config["DATABASE_URL"],host="tramway.proxy.rlwy.net",port=15258,sslmode="require",connect_timeout=15)
def key(s):
    return " ".join("".join(c for c in unicodedata.normalize("NFKD",s.upper()) if not unicodedata.combining(c)).split())
keep={key(s) for s in ["AARON JOSE AVILA VARGAS","SHARON STACEY BARQUERO SANCHEZ","FABIAN JOSE ZAMORA MADRIGAL","Luis Mendez"]}
before=json.loads((root/"tmp/mci_pending_before.json").read_text(encoding="utf-8"))
targets=[r for r in before if r["active"] and key(r["payee_name"]) not in keep]
ids=[r["id"] for r in targets]
with conn.cursor() as schema_cursor:
    schema_cursor.execute("SELECT table_name,column_name FROM information_schema.columns WHERE table_schema='public'")
    existing_columns=set(schema_cursor.fetchall())
conn.rollback()
class ExistingSchemaCursor:
    def __init__(self,inner):self.inner=inner
    def __getattr__(self,name):return getattr(self.inner,name)
    def __enter__(self):return self
    def __exit__(self,*args):self.inner.close()
    def execute(self,query,params=None):
        # The application repeats additive DDL per payment. Verified existing
        # columns need no ALTER and no table-wide DDL lock for this batch.
        match=re.fullmatch(r"\s*ALTER TABLE (\w+)\s+ADD COLUMN IF NOT EXISTS (\w+)\s+[^;]+;?\s*",query,re.I) if isinstance(query,str) else None
        if match and (match[1],match[2]) in existing_columns:return
        return self.inner.execute(query,params)
class BatchConnection:
    def __getattr__(self,name):return getattr(conn,name)
    def cursor(self,*args,**kwargs):return ExistingSchemaCursor(conn.cursor(*args,**kwargs))
    def commit(self):pass
    def rollback(self):raise RuntimeError("Operation requested rollback; abort entire batch")
def fingerprint(cur):
    result=[]
    for query in [
        "SELECT md5(COALESCE(string_agg(to_jsonb(p)::text,'' ORDER BY p.id),'')) AS hash FROM payment_obligations p WHERE NOT(id=ANY(%s))",
        "SELECT md5(COALESCE(string_agg(to_jsonb(e)::text,'' ORDER BY e.id),'')) AS hash FROM accounting_entries e WHERE NOT(company_code='MCI-CR' AND origin IN ('ITP','ITP_PAYMENT') AND origin_id=ANY(%s))",
        "SELECT md5(COALESCE(string_agg(to_jsonb(l)::text,'' ORDER BY l.id),'')) AS hash FROM accounting_lines l JOIN accounting_entries e ON e.id=l.entry_id WHERE NOT(e.company_code='MCI-CR' AND e.origin IN ('ITP','ITP_PAYMENT') AND e.origin_id=ANY(%s))",
    ]:
        cur.execute(query,(ids,));result.append(cur.fetchone()["hash"])
    return result
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET LOCAL lock_timeout='5s'")
        cur.execute("SET LOCAL statement_timeout='45s'")
        cur.execute("SELECT * FROM payment_obligations WHERE id=ANY(%s) ORDER BY id FOR UPDATE",(ids,))
        rows={r["id"]:dict(r) for r in cur.fetchall()}
        for expected in targets:
            actual=rows[expected["id"]]
            assert actual["company_code"]=="MCI-CR" and actual["active"]
            assert key(actual["payee_name"]) not in keep
            for field in ("payee_name","currency","balance","status","issue_date"):
                assert str(actual[field])==str(expected[field]),f"Changed {expected['id']} {field}"
            assert actual["status"] in ("PENDING","PARTIAL")
            assert actual["issue_date"] and actual["issue_date"]<=date(2026,10,20)
            assert not actual.get("historical_closed")
        untouched=fingerprint(cur)
        cur.execute("SELECT account_code,account_name,currency_code FROM accounting_accounts WHERE account_code=ANY(%s) AND active",(["1.1.02.02.01","1.1.02.02.02"],))
        banks={r["currency_code"]:dict(r) for r in cur.fetchall()}
        assert set(banks)=={"CRC","USD"}
    proxy=BatchConnection()
    # Each normal payment is audited, but the commit and automatic broad sync
    # are deferred until the complete, scoped accounting batch is verified.
    with patch("services.accounting_auto.sync_itp_to_accounting",return_value=None):
        for expected in targets:
            row=rows[expected["id"]];bank=banks[row["currency"]]
            result=apply_payment(
                obligation_id=row["id"],amount=float(row["balance"]),payment_date=row["issue_date"],
                bank_account_code=bank["account_code"],bank_account_name=bank["account_name"],
                bank_name="BAC SAN JOSE",
                payment_reference=f"REGULARIZACION AUTORIZADA 2026-10-20 / ITP {row['id']} (sin comprobante aportado)",
                payment_method="BANK",payment_card_last4="",conn=proxy,
                x_user="Codex-autorizado-Aaron",x_role="admin",x_user_role="admin")
            assert not result.get("accounting_warning")
            print("Validated payment",row["id"],flush=True)
    sync_itp_to_accounting(proxy,company_code_filter="MCI-CR",obligation_ids=ids)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        assert fingerprint(cur)==untouched,"Unrelated records changed; refusing commit"
        cur.execute("""SELECT p.id,p.payee_name,p.currency,p.total,p.balance,p.status,p.issue_date,p.last_payment_date,
            p.payment_bank_account_code,e.id AS entry_id,e.entry_date,
            SUM(l.debit) AS debit,SUM(l.credit) AS credit,
            SUM(CASE WHEN l.account_code=p.payment_bank_account_code THEN l.credit ELSE 0 END) AS bank_credit
            FROM payment_obligations p LEFT JOIN accounting_entries e ON e.origin='ITP_PAYMENT' AND e.origin_id=p.id AND e.company_code=p.company_code
            LEFT JOIN accounting_lines l ON l.entry_id=e.id
            WHERE p.id=ANY(%s) GROUP BY p.id,e.id ORDER BY p.id""",(ids,))
        verified=[dict(r) for r in cur.fetchall()]
        assert len(verified)==len(ids)
        for row in verified:
            assert row["status"]=="PAID" and row["balance"]==0
            assert row["entry_id"],f"No accounting entry for {row['id']}"
            assert row["issue_date"]==row["last_payment_date"]==row["entry_date"]
            assert abs(row["debit"]-row["credit"])<=Decimal("0.01"),row
            assert row["bank_credit"]>0,row
    if "--apply" in sys.argv:
        conn.commit()
        (root/"tmp/mci_payments_verified.json").write_text(json.dumps(verified,default=str,indent=2),encoding="utf-8")
        print("COMMITTED",len(verified),"payments and balanced BAC entries; other obligations and entries unchanged.")
    else:
        conn.rollback()
        print("DRY RUN ROLLED BACK",len(verified),"payments and balanced BAC entries; other obligations and entries unchanged.")
    print(json.dumps(verified,default=str))
except:
    conn.rollback()
    raise
finally:conn.close()
