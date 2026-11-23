"""Add only absent desktop-contract columns; never change existing values/types.

Run without --apply to inspect. --apply captures a local backup and checks the
entire original projection before committing. Keep lock acquisition bounded.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import runpy
import sys
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend_api'))
from services.bunker_web_fields import SPEC,NUMERIC


def run(apply=False):
    config=runpy.run_path(str(root/'backend_api/hr.py'))
    conn=psycopg2.connect(config['DATABASE_URL'],host='tramway.proxy.rlwy.net',port=15258,connect_timeout=15,sslmode='require')
    conn.set_session(readonly=not apply)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SET LOCAL lock_timeout='5s'")
            cur.execute("SET LOCAL statement_timeout='20s'")
            cur.execute("SELECT column_name,data_type FROM information_schema.columns WHERE table_schema='public' AND table_name='vessel_bunker_reports' ORDER BY ordinal_position")
            schema=[dict(r) for r in cur.fetchall()]
            if not schema:raise RuntimeError('Bunker table missing; aborting')
            columns=[r['column_name'] for r in schema]
            missing=sorted(set(SPEC['fields'])-set(columns))
            print('Missing columns:',len(missing),flush=True)
            if not apply:return
            if not missing:return
            cur.execute('LOCK TABLE vessel_bunker_reports IN ACCESS EXCLUSIVE MODE')
            projection=sql.SQL('SELECT {} FROM vessel_bunker_reports ORDER BY id').format(sql.SQL(',').join(map(sql.Identifier,columns)))
            cur.execute(projection);before=[dict(r) for r in cur.fetchall()]
            backup=root/'tmp/bunker-qa'/('schema-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
            backup.parent.mkdir(parents=True,exist_ok=True)
            backup.write_text(json.dumps(dict(schema=schema,rows=before),default=str,ensure_ascii=False,indent=2),encoding='utf8')
            additions=[]
            for key in missing:
                typ='NUMERIC' if key in NUMERIC else 'DATE' if SPEC['fields'][key]['type']=='date' else 'TEXT'
                additions.append(sql.SQL('ADD COLUMN IF NOT EXISTS {} {}').format(sql.Identifier(key),sql.SQL(typ)))
            cur.execute(sql.SQL('ALTER TABLE vessel_bunker_reports {}').format(sql.SQL(',').join(additions)))
            cur.execute(projection);after=[dict(r) for r in cur.fetchall()]
            if before!=after:raise RuntimeError('Original values changed; refusing commit')
            conn.commit()
            print(f'Added {len(missing)} nullable columns; all {len(before)} original rows verified unchanged.',flush=True)
    finally:
        conn.rollback();conn.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true')
    run(parser.parse_args().apply)
