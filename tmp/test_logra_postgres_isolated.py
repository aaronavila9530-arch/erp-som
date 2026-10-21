"""Exercise real SQL exclusively in connection-local temporary tables."""
from pathlib import Path
import io
import runpy
import sys
import tempfile
from unittest.mock import patch
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException, UploadFile

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend_api'))
from routers import logra_web as web
config=runpy.run_path(str(root/'backend_api/hr.py'))
conn=psycopg2.connect(config['DATABASE_URL'],host='tramway.proxy.rlwy.net',port=15258,connect_timeout=15,sslmode='require')
tables=('logra_reports','logra_answers','logra_attachments','logra_report_revisions')
try:
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout='15s'")
        for table in tables:
            cur.execute(sql.SQL('CREATE TEMP TABLE {} (LIKE public.{} INCLUDING ALL)').format(sql.Identifier(table),sql.Identifier(table)))
            # LIKE copies serial defaults; replace them before any insertion.
            sequence=table+'_qa_seq'
            cur.execute(sql.SQL('CREATE TEMP SEQUENCE {}').format(sql.Identifier(sequence)))
            cur.execute(sql.SQL('ALTER TABLE pg_temp.{} ALTER COLUMN id SET DEFAULT nextval(%s)').format(sql.Identifier(table)),('pg_temp.'+sequence,))
            cur.execute('SELECT to_regclass(%s)::oid<>to_regclass(%s)::oid',(table,'public.'+table))
            assert cur.fetchone()[0], 'Temporary table is not shadowing public data'
    conn.commit()
    ctx={'user':'qa-isolated','permissions':dict(view=True,create=True,edit=True)}
    slug=web.CATALOG[0]['slug']
    created=web.create(web.NewReport(form_slug=slug),ctx,conn)
    rid=created['report']['id']
    answer={'form_slug':slug,'section':'critical_questions','item_key':'1','bullets':['Temporary SQL validation']}
    saved=web.update(rid,web.Save(revision=created['revision'],answers=[answer]),ctx,conn)
    assert saved['answers'][0]['bullets']==answer['bullets']
    assert saved['report']['created_by']=='qa-isolated'
    try:
        web.update(rid,web.Save(revision=created['revision'],answers=[answer]),ctx,conn)
        raise AssertionError('Stale write accepted')
    except HTTPException as error: assert error.status_code==409
    with tempfile.TemporaryDirectory(prefix='logra_sql_qa_') as directory,patch.object(web,'STORAGE_ROOT',Path(directory)):
        uploaded=web.upload(rid,saved['revision'],slug,'critical_questions','1',UploadFile(io.BytesIO(b'QA attachment only'),filename='qa.txt'),ctx,conn)
        aid=uploaded['attachments'][0]['id']
        assert web.download(aid,ctx,conn).filename=='qa.txt'
        removed=web.remove_attachment(rid,aid,web.AttachmentRemoval(revision=uploaded['revision']),ctx,conn)
        assert removed['attachments']==[]
        assert list(Path(directory).rglob('*.txt')), 'Audit recovery file unexpectedly removed'
        history=web.history(rid,ctx,conn)
        snapshot=web.history_detail(rid,history['data'][0]['id'],ctx,conn)
        assert 'stored_path' not in snapshot['removed_attachment']
    agenda=web.create(web.NewReport(kind='agenda'),ctx,conn)
    item={'date_iso':'2026-10-19','start_time':'09:01','end_time':'10:00','topic':'Temporary meeting','legacy':'Preserved'}
    agenda=web.update(agenda['report']['id'],web.Save(revision=agenda['revision'],agenda_items=[item],agenda_notes='Temporary notes'),ctx,conn)
    assert agenda['report']['agenda_items'][0]['legacy']=='Preserved'
    for kind in ('pdf','docx','xlsx'):
        assert len(web.export(rid,kind,ctx,conn).body)>1000
    print('PASS PostgreSQL temporary tables: create, save, conflict, attachments, recovery audit, agenda, exports. No public table writes.')
finally:
    conn.rollback()
    conn.close()
