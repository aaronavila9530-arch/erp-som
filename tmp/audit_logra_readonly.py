"""Read-only LOGRA schema and compatibility inventory."""
from pathlib import Path
import runpy
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

root = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend_api'))
from routers import logra_web as web
config = runpy.run_path(str(root / 'backend_api/hr.py'))
conn = psycopg2.connect(config['DATABASE_URL'], host='tramway.proxy.rlwy.net', port=15258,
                        connect_timeout=15, sslmode='require')
conn.set_session(readonly=True)
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET LOCAL statement_timeout='15s'")
        cur.execute("SELECT table_name,column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name LIKE 'logra_%' ORDER BY table_name,ordinal_position")
        for row in cur.fetchall(): print(dict(row))
        cur.execute("SELECT form_slug,status,COUNT(*) AS total FROM logra_reports GROUP BY form_slug,status")
        print('Report groups', [dict(r) for r in cur.fetchall()])
        cur.execute("SELECT COUNT(*) AS answers,COUNT(DISTINCT report_id) AS reports FROM logra_answers")
        print('Answers',dict(cur.fetchone()))
        cur.execute("SELECT COUNT(*) AS attachments,COALESCE(SUM(file_size),0) AS bytes FROM logra_attachments")
        print('Attachments',dict(cur.fetchone()))
        cur.execute("SELECT column_name,is_nullable,column_default,character_maximum_length FROM information_schema.columns WHERE table_name='logra_reports' AND is_nullable='NO'")
        print('Required columns',[dict(r) for r in cur.fetchall()])
    ctx={'user':'admin','permissions':dict(view=True,create=True,edit=True)}
    listing=web.listing(q='',kind='all',offset=0,ctx=ctx,conn=conn)
    print('Web listing',listing['total'])
    for row in listing['data']:
        detail=web.detail(row['id'],ctx,conn)
        print('Read-compatible',row['id'],len(detail['answers']),len(detail['attachments']),len(detail['revision']))
finally:
    conn.rollback()
    conn.close()
