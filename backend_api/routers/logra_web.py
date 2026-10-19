"""LOGRA web adapter. No DDL or changes to the desktop endpoints."""
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from psycopg2.extras import Json, RealDictCursor

from database import get_db
from security.auth import get_current_user
from routers.mobile_auth import _has_visual_permission
from routers.logra_reports_router import _save_revision, STORAGE_ROOT

router = APIRouter(prefix='/informes/logra', tags=['LOGRA Web'])
ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / 'services/logra_web_catalog.json').read_text(encoding='utf-8'))
FORMS = {form['slug']: form for form in CATALOG}
QUESTIONS = {(f['slug'], section, str(q.get('id') or q.get('number'))): q
             for f in CATALOG for section in ('critical_questions', 'detailed_questions') for q in f[section]}
log = logging.getLogger(__name__)


def access(user=Depends(get_current_user)):
    permissions = {key: _has_visual_permission(user['usuario'], user['rol'], 'informes', key)
                   for key in ('view', 'create', 'edit')}
    if not permissions['view']:
        raise HTTPException(403, 'Sin permiso para Informes')
    return {'user': user['usuario'], 'permissions': permissions}


def require(ctx, action):
    if not ctx['permissions'].get(action):
        raise HTTPException(403, 'Sin permiso para esta accion')


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def read(cur, rid, lock=False):
    cur.execute('SELECT * FROM logra_reports WHERE id=%s' + (' FOR UPDATE' if lock else ''), (rid,))
    report = cur.fetchone()
    if not report:
        raise HTTPException(404, 'Reporte LOGRA no encontrado')
    cur.execute('SELECT form_slug,form_title,section,item_key,question_text,bullets,updated_at FROM logra_answers WHERE report_id=%s ORDER BY form_slug,section,item_key', (rid,))
    answers = cur.fetchall()
    cur.execute('SELECT id,form_slug,section,item_key,bullet_index,original_filename,content_type,file_size,created_at FROM logra_attachments WHERE report_id=%s ORDER BY id', (rid,))
    attachments = cur.fetchall()
    result = {'report': report, 'answers': answers, 'attachments': attachments}
    result['revision'] = digest(result)
    return result


def check_revision(payload, revision):
    if payload['revision'] != revision:
        raise HTTPException(409, 'El reporte cambio en otro dispositivo. Tu borrador se conserva; descarga una copia y recarga antes de combinar los cambios.')


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class NewReport(StrictModel):
    form_slug: str = Field(default='', max_length=150)
    kind: Literal['questionnaire', 'agenda'] = 'questionnaire'


class Answer(StrictModel):
    form_slug: str
    section: Literal['critical_questions', 'detailed_questions']
    item_key: str = Field(max_length=80)
    bullets: list[str] = Field(max_length=20)


class Save(StrictModel):
    revision: str
    answers: list[Answer] = Field(default_factory=list, max_length=390)
    agenda_items: list[dict] | None = Field(default=None, max_length=150)
    agenda_notes: str | None = Field(default=None, max_length=30000)


def clean_answers(body, current):
    existing = {(a['form_slug'], a['section'], a['item_key']): a for a in current['answers']}
    slug = current['report'].get('form_slug')
    allowed_slugs = {a['form_slug'] for a in current['answers']} if not slug else {slug}
    seen = set()
    result = []
    for answer in body.answers:
        key = (answer.form_slug, answer.section, answer.item_key)
        if key in seen or answer.form_slug not in allowed_slugs:
            raise HTTPException(422, 'Pregunta duplicada o de otro cuestionario')
        seen.add(key)
        question = QUESTIONS.get(key)
        if not question and key not in existing:
            raise HTTPException(422, 'Pregunta desconocida')
        if any(len(v) > 12000 or '\x00' in v for v in answer.bullets):
            raise HTTPException(422, 'Respuesta demasiado larga o invalida')
        old = existing.get(key, {})
        result.append({**answer.model_dump(), 'form_title': old.get('form_title') or FORMS.get(answer.form_slug, {}).get('title', answer.form_slug),
                       'question_text': old.get('question_text') or question['question'],
                       'bullets': [v.strip() for v in answer.bullets if v.strip()]})
    return result


def clean_agenda(items):
    from datetime import date, time
    for item in items:
        if len(json.dumps(item, default=str)) > 40000:
            raise HTTPException(422, 'Linea de agenda demasiado larga')
        try:
            if item.get('date_iso'): date.fromisoformat(item['date_iso'])
            for key in ('start_time', 'end_time'):
                if item.get(key): time.fromisoformat(item[key])
            if item.get('start_time') and item.get('end_time') and time.fromisoformat(item['end_time']) <= time.fromisoformat(item['start_time']):
                raise ValueError()
        except (TypeError, ValueError):
            raise HTTPException(422, 'Revise fecha y horas de la agenda; la hora final debe ser posterior a la inicial')
    return items


@router.get('/assets/{name}')
def asset(name: Literal['logra.js', 'logra.css']):
    return FileResponse(ROOT / 'assets/logra' / name, media_type='text/javascript' if name.endswith('.js') else 'text/css')


@router.get('/bootstrap')
def bootstrap(ctx=Depends(access)):
    return {'forms': CATALOG, 'permissions': ctx['permissions'], 'scope': 'shared'}


@router.get('')
def listing(q: str = Query('', max_length=200), kind: Literal['all', 'questionnaire', 'agenda'] = 'all',
            offset: int = Query(0, ge=0), ctx=Depends(access), conn=Depends(get_db)):
    where, params = ['TRUE'], []
    if q:
        where.append('(title ILIKE %s OR created_by ILIKE %s)')
        params.extend(['%' + q + '%'] * 2)
    if kind != 'all':
        where.append("LOWER(TRIM(COALESCE(title,''))) " + ('=' if kind == 'agenda' else '<>') + " 'ong - agenda'")
    clause = ' WHERE ' + ' AND '.join(where)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT COUNT(*) AS total FROM logra_reports' + clause, params)
        total = cur.fetchone()['total']
        cur.execute('''SELECT id,title,status,form_slug,version,updated_at,created_by,
            jsonb_array_length(COALESCE(agenda_items,'[]'::jsonb)) AS agenda_count,
            (SELECT COUNT(*) FROM logra_answers a WHERE a.report_id=logra_reports.id AND a.bullets<>'[]'::jsonb) AS answer_count,
            (SELECT COUNT(*) FROM logra_attachments a WHERE a.report_id=logra_reports.id) AS attachment_count
            FROM logra_reports''' + clause + ' ORDER BY updated_at DESC,id DESC LIMIT 50 OFFSET %s', params + [offset])
        return {'data': cur.fetchall(), 'total': total}


@router.post('')
def create(body: NewReport, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, 'create')
    if body.kind == 'questionnaire' and body.form_slug not in FORMS:
        raise HTTPException(422, 'Seleccione un cuestionario')
    title = 'ONG - Agenda' if body.kind == 'agenda' else 'ONG - ' + FORMS[body.form_slug]['title']
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''INSERT INTO logra_reports (title,category,status,form_slug,created_by,version,created_at,updated_at,agenda_items,agenda_notes)
                VALUES (%s,'ONG','Pending',%s,%s,1,NOW(),NOW(),'[]'::jsonb,'') RETURNING id''',
                (title, body.form_slug if body.kind == 'questionnaire' else None, ctx['user']))
            rid = cur.fetchone()['id']
            _save_revision(cur, rid, 1, body.form_slug, ctx['user'])
            result = read(cur, rid)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise


@router.get('/{rid:int}')
def detail(rid: int, ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        return read(cur, rid)


@router.patch('/{rid:int}')
def update(rid: int, body: Save, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, 'edit')
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            current = read(cur, rid, True)
            check_revision(current, body.revision)
            answers = clean_answers(body, current)
            for a in answers:
                cur.execute('''INSERT INTO logra_answers (report_id,form_slug,form_title,section,item_key,question_text,bullets,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,NOW()) ON CONFLICT (report_id,form_slug,section,item_key)
                    DO UPDATE SET bullets=EXCLUDED.bullets,updated_at=NOW()''',
                    (rid, a['form_slug'], a['form_title'], a['section'], a['item_key'], a['question_text'], Json(a['bullets'])))
            if body.agenda_items is not None:
                items = clean_agenda(body.agenda_items)
                cur.execute('UPDATE logra_reports SET agenda_items=%s WHERE id=%s', (Json(items), rid))
                first = items[0] if items else {}
                if first.get('date_iso'):
                    cur.execute('''UPDATE logra_reports SET meeting_date=%s,meeting_time=%s,
                        meeting_start_time=%s,meeting_end_time=%s,meeting_location=%s,meeting_person=%s WHERE id=%s''',
                        (first['date_iso'], first.get('start_time') or '00:00', first.get('start_time') or '',
                         first.get('end_time') or '', first.get('place') or '', first.get('person') or '', rid))
            if body.agenda_notes is not None:
                cur.execute('UPDATE logra_reports SET agenda_notes=%s WHERE id=%s', (body.agenda_notes, rid))
            cur.execute('UPDATE logra_reports SET updated_at=NOW(),version=COALESCE(version,1)+1 WHERE id=%s RETURNING version', (rid,))
            version = cur.fetchone()['version']
            _save_revision(cur, rid, version, current['report'].get('form_slug'), ctx['user'])
            result = read(cur, rid)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise


@router.get('/{rid:int}/history')
def history(rid: int, ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT id,version,saved_by,created_at FROM logra_report_revisions WHERE report_id=%s ORDER BY id DESC LIMIT 100', (rid,))
        return {'data': cur.fetchall()}


@router.get('/{rid:int}/history/{revision_id:int}')
def history_detail(rid: int, revision_id: int, ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT snapshot FROM logra_report_revisions WHERE report_id=%s AND id=%s', (rid, revision_id))
        row = cur.fetchone()
        if not row: raise HTTPException(404, 'Version no encontrada')
        snapshot = dict(row['snapshot'])
        if snapshot.get('removed_attachment'):
            snapshot['removed_attachment'] = {k:v for k,v in snapshot['removed_attachment'].items() if k != 'stored_path'}
        return snapshot


@router.post('/{rid:int}/attachments')
def upload(rid: int, revision: str = Form(...), form_slug: str = Form(...), section: str = Form(...),
           item_key: str = Form(...), file: UploadFile = File(...), ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, 'edit')
    name = Path((file.filename or 'adjunto').replace('\\', '/')).name
    if Path(name).suffix.lower() not in {'.pdf', '.docx', '.xlsx', '.xls', '.doc', '.jpg', '.jpeg', '.png', '.webp', '.txt', '.csv'}:
        raise HTTPException(422, 'Formato de adjunto no permitido')
    path = None
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            current = read(cur, rid, True)
            check_revision(current, revision)
            key = (form_slug, section, item_key)
            valid = key in QUESTIONS and form_slug == current['report'].get('form_slug')
            valid = valid or any((a['form_slug'], a['section'], a['item_key']) == key for a in current['answers'])
            if not valid: raise HTTPException(422, 'Pregunta no pertenece al reporte')
            if sum((a['form_slug'], a['section'], a['item_key']) == key for a in current['attachments']) >= 10:
                raise HTTPException(422, 'Maximo 10 adjuntos por pregunta')
            folder = STORAGE_ROOT / str(rid) / 'web'
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / (uuid4().hex + Path(name).suffix.lower())
            size = 0
            with path.open('wb') as output:
                while chunk := file.file.read(65536):
                    size += len(chunk)
                    if size > 20 * 1024 * 1024: raise HTTPException(413, 'Maximo 20 MB por archivo')
                    output.write(chunk)
            if not size: raise HTTPException(422, 'El archivo esta vacio')
            cur.execute('''INSERT INTO logra_attachments (report_id,form_slug,section,item_key,original_filename,stored_path,content_type,file_size,created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,NOW())''', (rid, form_slug, section, item_key, name, str(path), file.content_type, size))
            cur.execute('UPDATE logra_reports SET version=COALESCE(version,1)+1,updated_at=NOW() WHERE id=%s RETURNING version', (rid,))
            _save_revision(cur, rid, cur.fetchone()['version'], current['report'].get('form_slug'), ctx['user'])
            result = read(cur, rid)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        if path: path.unlink(missing_ok=True)
        raise
    finally:
        file.file.close()


@router.get('/attachments/{aid:int}')
def download(aid: int, ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT original_filename,stored_path FROM logra_attachments WHERE id=%s', (aid,))
        row = cur.fetchone()
    if not row: raise HTTPException(404, 'Adjunto no encontrado')
    path = Path(row['stored_path']).resolve()
    if not path.is_relative_to(STORAGE_ROOT.resolve()) or not path.is_file():
        raise HTTPException(404, 'Archivo no disponible en el servidor')
    return FileResponse(path, filename=row['original_filename'], media_type='application/octet-stream', headers={'X-Content-Type-Options':'nosniff'})


class Improve(StrictModel):
    form_slug: str
    section: str
    item_key: str
    text: str = Field(min_length=1, max_length=12000)
    language: Literal['ES', 'EN'] = 'ES'


@router.post('/improve')
def improve(body: Improve, ctx=Depends(access)):
    require(ctx, 'edit')
    question = QUESTIONS.get((body.form_slug, body.section, body.item_key))
    if not question: raise HTTPException(422, 'Pregunta desconocida')
    from ai.maritime_ai import improve_logra_questionnaire_text
    try:
        text = improve_logra_questionnaire_text(body.text, body.section, question['question'], FORMS[body.form_slug]['title'], body.language)
        return {'text': text}
    except Exception:
        log.exception('LOGRA web AI improvement failed')
        raise HTTPException(503, 'PORTIA no esta disponible; tu texto original se conserva')


class Executive(StrictModel):
    ids: list[int] = Field(min_length=1, max_length=100)
    language: Literal['ES', 'EN'] = 'ES'


@router.post('/executive')
def executive(body: Executive, ctx=Depends(access), conn=Depends(get_db)):
    from ai.maritime_ai import generate_logra_questionnaire_report
    from routers.logra_reports_router import _valid_ai_bullets
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''SELECT a.form_title,a.section,a.question_text,a.bullets FROM logra_answers a
            JOIN logra_reports r ON r.id=a.report_id WHERE r.id=ANY(%s) ORDER BY r.id,a.form_slug,a.section,a.item_key''', (list(set(body.ids)),))
        answers = [{**a, 'bullets': _valid_ai_bullets(a['bullets'])} for a in cur.fetchall()]
    answers = [a for a in answers if a['bullets']]
    if not answers: raise HTTPException(422, 'No hay respuestas validas en los reportes seleccionados')
    if len(json.dumps(answers)) > 200000: raise HTTPException(422, 'Seleccione menos reportes para esta consulta')
    try:
        return {'text': generate_logra_questionnaire_report('LOGRA', answers, body.language), 'answer_count': len(answers)}
    except Exception:
        log.exception('LOGRA web executive generation failed')
        raise HTTPException(503, 'No se pudo generar el reporte ejecutivo. Los cuestionarios no se han modificado')


def export_response(payload, kind, text=None):
    from services.logra_web_export import build
    media = {'pdf':'application/pdf', 'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
             'xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}
    return Response(build(payload, kind, text), media_type=media[kind],
                    headers={'Content-Disposition': f'attachment; filename="LOGRA_{payload["report"].get("id") or "Ejecutivo"}.{kind}"'})


@router.get('/{rid:int}/export/{kind}')
def export(rid: int, kind: Literal['pdf', 'docx', 'xlsx'], ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        payload = read(cur, rid)
    return export_response(payload, kind)


class ExportAI(StrictModel):
    text: str = Field(min_length=1, max_length=100000)
    kind: Literal['pdf', 'docx']


@router.post('/executive/export')
def executive_export(body: ExportAI, ctx=Depends(access)):
    return export_response({'report': {'title': 'LOGRA Informe ejecutivo IA'}, 'answers': [], 'attachments': []}, body.kind, body.text)


class AttachmentRemoval(StrictModel):
    revision: str


@router.delete('/{rid:int}/attachments/{aid:int}')
def remove_attachment(rid: int, aid: int, body: AttachmentRemoval, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, 'edit')
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            current = read(cur, rid, True)
            check_revision(current, body.revision)
            if not any(a['id'] == aid for a in current['attachments']):
                raise HTTPException(404, 'Adjunto no pertenece al reporte')
            # Retain the file and a full audit snapshot for administrative recovery.
            cur.execute('SELECT * FROM logra_attachments WHERE id=%s AND report_id=%s', (aid, rid))
            removed = cur.fetchone()
            cur.execute('DELETE FROM logra_attachments WHERE id=%s AND report_id=%s', (aid, rid))
            cur.execute('UPDATE logra_reports SET version=COALESCE(version,1)+1,updated_at=NOW() WHERE id=%s RETURNING version', (rid,))
            version = cur.fetchone()['version']
            snapshot = {**current, 'removed_attachment': removed}
            cur.execute('''INSERT INTO logra_report_revisions (report_id,version,form_slug,snapshot,saved_by,created_at)
                VALUES (%s,%s,%s,%s,%s,NOW())''',
                (rid, version, current['report'].get('form_slug'), Json(snapshot,dumps=lambda v:json.dumps(v,default=str)), ctx['user']))
            result = read(cur, rid)
        conn.commit()
        return result
    except Exception:
        conn.rollback()
        raise
