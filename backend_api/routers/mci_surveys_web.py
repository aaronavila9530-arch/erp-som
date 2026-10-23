"""Separate MCI generic survey storage. Does not change desktop report tables."""
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
import tempfile
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from psycopg2.extras import RealDictCursor, Json
from database import get_db
from routers.container_web import access, require, version
from routers.certificates_web import StatusInput
from services.mci_survey_schema import SurveySave, SurveyContent, SECTION_TITLES

router = APIRouter(prefix='/informes/mci-surveys', tags=['MCI Surveys Web'])


def mci_access(ctx=Depends(access)):
    if ctx['company'] != 'MCI-CR':
        raise HTTPException(404, 'Informe disponible solo para MCI')
    return ctx


def record(cur, rid, lock=False):
    cur.execute("SELECT * FROM mci_generic_surveys WHERE id=%s AND company_code='MCI-CR'" + (' FOR UPDATE' if lock else ''), (rid,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, 'Informe no encontrado')
    return row


@router.get('/editor.js')
def asset():
    return FileResponse(Path(__file__).resolve().parents[1] / 'assets/mci_surveys/editor.js', media_type='text/javascript')


@router.get('/bootstrap')
def bootstrap(ctx=Depends(mci_access), conn=Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.mci_generic_surveys') IS NOT NULL")
        ready = cur.fetchone()[0]
    return dict(ready=ready, permissions=ctx['permissions'], sections=SECTION_TITLES)


@router.get('')
def listing(kind: str, q: str = Query('', max_length=150), offset: int = Query(0, ge=0),
            ctx=Depends(mci_access), conn=Depends(get_db)):
    if kind not in ('vessel','condition','cargo'):
        raise HTTPException(422, 'Tipo invalido')
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT id,report_number,vessel,requested_by,status,updated_at FROM mci_generic_surveys
            WHERE company_code='MCI-CR' AND kind=%s
            AND CONCAT_WS(' ',report_number,vessel,requested_by) ILIKE %s ORDER BY id DESC LIMIT 51 OFFSET %s""",
                    (kind, '%' + q + '%', offset))
        rows = cur.fetchall()
    return dict(data=rows[:50], more=len(rows)>50)


@router.get('/{rid}')
def detail(rid: int, ctx=Depends(mci_access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        row = record(cur, rid)
    return dict(data=row, version=version(row))


def persist(body, ctx, conn, rid=None):
    require(ctx, 'edit' if rid else 'create')
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if rid:
                old = record(cur, rid, True)
                if version(old) != body.version:
                    raise HTTPException(409, 'El informe cambio en otra sesion. Conserve su texto y vuelva a abrirlo.')
                if old['status'] == 'Approved':
                    raise HTTPException(409, 'Rechace el informe aprobado antes de editarlo.')
                if old['service_id'] != body.service_id or old['kind'] != body.kind:
                    raise HTTPException(422, 'No se puede cambiar el servicio ni el tipo de informe.')
            cur.execute("""SELECT consec,num_informe,buque_contenedor,cliente FROM servicios
                WHERE consec=%s AND company_code='MCI-CR' AND NULLIF(TRIM(num_informe),'') IS NOT NULL""", (body.service_id,))
            service = cur.fetchone()
            if not service:
                raise HTTPException(404, 'Servicio MCI no encontrado o sin numero de informe.')
            status = 'Pending for review' if body.submit else 'Draft'
            content = Json(body.content.model_dump(mode='json'))
            if rid:
                cur.execute("""UPDATE mci_generic_surveys SET content=%s,status=%s,updated_at=%s
                    WHERE id=%s RETURNING *""", (content,status,datetime.now(timezone.utc),rid))
            else:
                cur.execute("""INSERT INTO mci_generic_surveys
                    (company_code,kind,service_id,report_number,vessel,requested_by,content,status)
                    VALUES ('MCI-CR',%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
                    (body.kind,body.service_id,service['num_informe'],service['buque_contenedor'] or '',
                     service['cliente'] or '',content,status))
            row = cur.fetchone()
        conn.commit()
        return dict(data=row, version=version(row))
    except Exception:
        conn.rollback()
        raise


@router.post('')
def create(body: SurveySave, ctx=Depends(mci_access), conn=Depends(get_db)):
    return persist(body,ctx,conn)


@router.patch('/{rid}')
def update(rid: int, body: SurveySave, ctx=Depends(mci_access), conn=Depends(get_db)):
    return persist(body,ctx,conn,rid)


@router.post('/{rid}/status')
def review(rid: int, body: StatusInput, ctx=Depends(mci_access), conn=Depends(get_db)):
    require(ctx,'approve')
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row=record(cur,rid,True)
            if version(row)!=body.version:
                raise HTTPException(409,'El informe cambio. Vuelva a abrirlo.')
            if body.status=='Approved' and row['status']!='Pending for review':
                raise HTTPException(409,'Envie el informe a revision antes de aprobarlo.')
            cur.execute('UPDATE mci_generic_surveys SET status=%s,updated_at=%s WHERE id=%s RETURNING *',
                        (body.status,datetime.now(timezone.utc),rid))
            row=cur.fetchone()
        conn.commit()
        return dict(data=row,version=version(row))
    except Exception:
        conn.rollback()
        raise


@router.get('/{rid}/export/{format}')
def export(rid: int, format: Literal['word','pdf'], ctx=Depends(mci_access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        row=dict(record(cur,rid))
    try:
        from services.mci_survey_export import build_word
        content=build_word(row)
        if format=='pdf':
            from services.container_web_export import convert
            with tempfile.TemporaryDirectory(prefix='mci_survey_') as folder:
                source=Path(folder)/'survey.docx';source.write_bytes(content)
                content=convert(source,Path(folder)).read_bytes()
        return Response(content,media_type='application/pdf' if format=='pdf' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        headers={'Content-Disposition':f'attachment; filename="Survey_{rid}.{"pdf" if format=="pdf" else "docx"}"'})
    except Exception:
        logging.getLogger(__name__).exception('MCI survey export failed: %s',rid)
        raise HTTPException(503,'No se pudo generar el documento; los datos guardados no han cambiado.')
