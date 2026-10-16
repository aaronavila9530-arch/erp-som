"""Revocable bearer capabilities limited to existing MCI tally sheets."""
import hashlib
import secrets
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse
from psycopg2.extras import RealDictCursor
from database import get_db
from security.gmail_access import require_gmail_admin
from routers import tally

router = APIRouter(tags=['Tally access'])


def schema(conn):
    with conn.cursor() as cur:
        cur.execute('''CREATE TABLE IF NOT EXISTS tally_access_links (
            id BIGSERIAL PRIMARY KEY, token_hash TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL, company_code TEXT NOT NULL,
            created_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL, revoked_at TIMESTAMPTZ)''')
    conn.commit()


def access(x_tally_token: str = Header(default=''), conn=Depends(get_db)):
    if not 40 <= len(x_tally_token) <= 100:
        raise HTTPException(401, 'Enlace invalido o vencido')
    schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''SELECT a.id,a.username,a.company_code FROM tally_access_links a
            JOIN usuarios u ON lower(trim(u.usuario))=a.username
            WHERE a.token_hash=%s AND a.revoked_at IS NULL AND a.expires_at>NOW()
            AND a.company_code='MCI-CR' AND u.activo IS TRUE''',
            (hashlib.sha256(x_tally_token.encode()).hexdigest(),))
        row = cur.fetchone()
    if not row:
        raise HTTPException(401, 'Enlace invalido, vencido o revocado')
    return dict(company='MCI-CR', user=f"{row['username']} (enlace tally {row['id']})", editable=True)


@router.post('/tally/access-links')
def issue(principal=Depends(require_gmail_admin), conn=Depends(get_db)):
    if principal['company'] != 'MCI-CR':
        raise HTTPException(403, 'Seleccione MCI')
    schema(conn)
    token = secrets.token_urlsafe(32)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT usuario FROM usuarios WHERE lower(trim(usuario))='patricia.omier' AND activo IS TRUE")
        if not cur.fetchone():
            raise HTTPException(409, 'Patricia Omier no tiene un registro activo')
        cur.execute('''INSERT INTO tally_access_links(token_hash,username,company_code,created_by,expires_at)
            VALUES(%s,'patricia.omier','MCI-CR',%s,NOW()+INTERVAL '90 days') RETURNING id,expires_at''',
            (hashlib.sha256(token.encode()).hexdigest(), principal['user']))
        result = dict(cur.fetchone())
    conn.commit()
    return {**result, 'path': '/tally-access#' + token}


@router.get('/tally/access-links')
def links(principal=Depends(require_gmail_admin), conn=Depends(get_db)):
    if principal['company'] != 'MCI-CR':
        raise HTTPException(403, 'Seleccione MCI')
    schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id,username,expires_at,revoked_at FROM tally_access_links WHERE company_code='MCI-CR' ORDER BY id DESC")
        return cur.fetchall()


@router.delete('/tally/access-links/{link_id}')
def revoke(link_id: int, principal=Depends(require_gmail_admin), conn=Depends(get_db)):
    if principal['company'] != 'MCI-CR':
        raise HTTPException(403, 'Seleccione MCI')
    schema(conn)
    with conn.cursor() as cur:
        cur.execute("UPDATE tally_access_links SET revoked_at=NOW() WHERE id=%s AND company_code='MCI-CR'", (link_id,))
    conn.commit()
    return {'ok': True}


@router.get('/tally-access', include_in_schema=False)
def page():
    return FileResponse(tally.ASSETS / 'access.html', headers={
        'Cache-Control':'no-store', 'Referrer-Policy':'no-referrer',
        'X-Frame-Options':'DENY', 'X-Robots-Tag':'noindex, nofollow',
        'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' blob: data:; frame-ancestors 'none'; base-uri 'none'"})


@router.get('/tally-access/api/bootstrap')
def bootstrap(ctx=Depends(access), conn=Depends(get_db)):
    tally.schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT id,name,holds,revision FROM tally_projects WHERE company_code=%s ORDER BY id DESC', (ctx['company'],))
        projects = cur.fetchall()
        cur.execute('SELECT name FROM tally_companies WHERE company_code=%s ORDER BY name', (ctx['company'],))
        companies = [r['name'] for r in cur.fetchall()]
    return dict(projects=projects, companies=companies, services=[], drivers=[], editable=True, restricted=True)


@router.get('/tally-access/api/projects/{pid}/sheets/{hold}')
def sheet(pid: int, hold: int, ctx=Depends(access), conn=Depends(get_db)):
    return tally.get_sheet(pid, hold, ctx, conn)


@router.put('/tally-access/api/projects/{pid}/sheets/{hold}')
def save(pid: int, hold: int, body: tally.SheetInput, ctx=Depends(access), conn=Depends(get_db)):
    return tally.save_sheet(pid, hold, body, ctx, conn)


@router.get('/tally-access/api/projects/{pid}/excel')
def excel(pid: int, ctx=Depends(access), conn=Depends(get_db)):
    return tally.excel(pid, ctx, conn)
