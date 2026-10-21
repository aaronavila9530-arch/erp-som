import ast
import json
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
tree = ast.parse((ROOT / 'backend_api/hr.py').read_text(encoding='utf-8-sig'))
node = next(n.value for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'DATABASE_URL' for t in n.targets))
dsn = ast.literal_eval(node.args[1] if isinstance(node, ast.Call) else node)
conn = psycopg2.connect(dsn, host='tramway.proxy.rlwy.net', port=15258,
                        connect_timeout=15, sslmode='require')
conn.set_session(readonly=True)
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET LOCAL statement_timeout='20s'")
        cur.execute("SELECT table_schema,table_name,column_name,data_type FROM information_schema.columns WHERE table_name IN ('fixed_assets','fixed_asset_depreciation_schedule') ORDER BY table_schema,table_name,ordinal_position")
        print(json.dumps([dict(r) for r in cur.fetchall()], default=str))
        cur.execute('SELECT * FROM public.fixed_assets ORDER BY id')
        assets = [dict(r) for r in cur.fetchall()]
        cur.execute('SELECT * FROM public.fixed_asset_depreciation_schedule ORDER BY asset_id,period')
        schedule = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT e.id, to_jsonb(e)->>'company_code' AS company_code, to_jsonb(e)->>'status' AS status, to_jsonb(e)->>'entry_date' AS entry_date FROM accounting_entries e JOIN fixed_asset_depreciation_schedule s ON s.accounting_entry_id=e.id")
        entries = [dict(r) for r in cur.fetchall()]
        out = ROOT / 'tmp/fixed-assets-report'
        out.mkdir(exist_ok=True)
        (out / 'source.json').write_text(json.dumps({'assets':assets, 'schedule':schedule, 'entries':entries},default=str,ensure_ascii=False),encoding='utf-8')
        print('Assets',len(assets),'Schedule',len(schedule))
        print('Entry scope', sorted({(r['company_code'] or 'Unspecified',r['status'] or 'Unspecified') for r in entries}))
finally:
    conn.rollback()
    conn.close()
