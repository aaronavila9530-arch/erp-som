import os
import threading
import time
from pathlib import Path
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from security.auth import get_current_user
from routers.mobile_auth import _has_visual_permission
from services.service_voice import extract

router = APIRouter(prefix='/servicios/voice', tags=['Service voice drafts'])
_slots = threading.BoundedSemaphore(2)
_rate_lock = threading.Lock()
_recent = {}
MAX_AUDIO = 12 * 1024 * 1024
MIMES = {'audio/webm': 'webm', 'audio/mp4': 'mp4', 'audio/ogg': 'ogg',
         'audio/mpeg': 'mp3', 'audio/wav': 'wav', 'audio/x-wav': 'wav', 'audio/x-m4a': 'm4a'}


def access(x_user: str | None = Header(default=None), x_role: str | None = Header(default=None)):
    from database import get_conn, release_conn
    conn = get_conn()
    try:
        user = get_current_user(x_user=x_user, x_role=x_role, conn=conn)
    finally:
        release_conn(conn)
    if not (_has_visual_permission(user['usuario'], user['rol'], 'servicios', 'edit')
            or _has_visual_permission(user['usuario'], user['rol'], 'servicios', 'create')):
        raise HTTPException(403, 'Sin permiso para editar Servicios.')
    return user


def rate_limit(user):
    now = time.monotonic()
    with _rate_lock:
        for key in list(_recent):
            _recent[key] = [t for t in _recent[key] if now-t < 60]
            if not _recent[key]: del _recent[key]
        times = _recent.setdefault(user['usuario'], [])
        if len(times) >= 8:
            raise HTTPException(429, 'Demasiados dictados. Espere un minuto antes de reintentar.')
        times.append(now)


def bounded_call(fn):
    if not os.getenv('OPENAI_API_KEY'):
        raise HTTPException(503, 'El dictado no esta configurado. Puede completar el formulario manualmente.')
    if not _slots.acquire(blocking=False):
        raise HTTPException(429, 'Dictado ocupado. Intente nuevamente en unos segundos.')
    try:
        return fn()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, 'No se pudo procesar el dictado. Revise el texto o intente otra vez.') from None
    finally:
        _slots.release()


@router.get('/assets/{name}', include_in_schema=False)
def asset(name: str):
    if name not in {'voice.js', 'voice.css', 'mic.svg'}:
        raise HTTPException(404)
    return FileResponse(Path(__file__).resolve().parents[1] / 'assets' / 'service_voice' / name)


class TextDraft(BaseModel):
    text: str = Field(min_length=3, max_length=6000)


@router.post('/draft')
def draft(payload: TextDraft, user=Depends(access)):
    rate_limit(user)
    return bounded_call(lambda: extract(payload.text))


@router.post('/transcribe')
async def transcribe(request: Request, user=Depends(access)):
    rate_limit(user)
    mime = request.headers.get('content-type', '').split(';')[0].lower()
    if mime not in MIMES:
        raise HTTPException(415, 'Formato no compatible. Use WebM, MP4, M4A, MP3, OGG o WAV.')
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > MAX_AUDIO:
            raise HTTPException(413, 'Audio demasiado grande. Maximo 12 MB.')
    if len(audio) < 100:
        raise HTTPException(422, 'No se recibio audio suficiente.')
    def process():
        from ai.maritime_ai import _get_openai_client
        with _get_openai_client().with_options(timeout=60, max_retries=0) as client:
            result = client.audio.transcriptions.create(
                model=os.getenv('SERVICE_VOICE_TRANSCRIBE_MODEL', 'gpt-4o-mini-transcribe'),
                file=('dictado.' + MIMES[mime], bytes(audio), mime))
        return {'text': result.text[:6000]}
    # No database lease or audio file is retained while the provider processes audio.
    return await run_in_threadpool(bounded_call, process)


@router.get('/locations')
def locations(pais: str = '', puerto: str = '', user=Depends(access)):
    from database import sql
    import re
    puerto = re.sub(r'^puerto\s+', '', puerto.strip(), flags=re.IGNORECASE)
    if not pais.strip() and not puerto.strip():
        return {'data': []}
    rows = sql('''SELECT DISTINCT continente, pais, puerto FROM continentes_paises_puertos
        WHERE (%s = '' OR lower(pais) = lower(%s))
          AND (%s = '' OR lower(puerto) LIKE lower(%s)) LIMIT 100''',
        (pais[:100], pais[:100], puerto[:200], '%' + puerto[:200] + '%'), fetch=True)
    return {'data': [dict(zip(('continente', 'pais', 'puerto'), r)) for r in rows]}
