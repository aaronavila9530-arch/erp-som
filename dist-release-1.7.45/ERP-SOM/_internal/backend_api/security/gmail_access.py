"""Independent, short-lived step-up authentication for mailbox administration."""
import base64
import hashlib
import hmac
import json
import os
import time

import bcrypt
import pyotp
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, Header, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db

SESSION_TTL = 900


def _cipher():
    key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Seguridad Gmail no configurada")
    # Separate session signing material from the mailbox credential key.
    derived = hmac.new(key.encode(), b"som-gmail-admin-session-v1", hashlib.sha256).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def _stamp(user):
    return hashlib.sha256((str(user["pass_hash"]) + ":" + str(user["totp_secret"])).encode()).hexdigest()


def _user(conn, username):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT usuario,rol,activo,pass_hash,totp_enabled,totp_secret
            FROM usuarios WHERE lower(trim(usuario))=%s LIMIT 1""", (username,))
        return cur.fetchone()


def _allowed(user):
    return bool(user and user["activo"] and user["totp_enabled"]
                and str(user["rol"]).strip().lower() in {"admin", "master"})


def validate_oauth_actor(conn, username):
    if not username or not _allowed(_user(conn, str(username).strip().lower())):
        raise ValueError("El administrador ya no tiene acceso")


def ensure_security_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS gmail_security_attempts (
            bucket_key TEXT NOT NULL, window_id BIGINT NOT NULL, attempts INTEGER NOT NULL,
            PRIMARY KEY(bucket_key,window_id))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS gmail_security_totp (
            username TEXT PRIMARY KEY, last_step BIGINT NOT NULL)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS gmail_security_audit (
            id BIGSERIAL PRIMARY KEY, username TEXT NOT NULL, company_code TEXT NOT NULL,
            action TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
    conn.commit()


def issue_session(conn, username, password, code, company, client_ip):
    ensure_security_schema(conn)
    username = username.strip().lower()
    window = int(time.time()) // SESSION_TTL
    # Shared database counters work across workers; headers cannot reset them.
    blocked = False
    with conn.cursor() as cur:
        cur.execute("DELETE FROM gmail_security_attempts WHERE window_id < %s", (window - 2,))
        for key, limit in (("user:" + username, 5), ("ip:" + client_ip, 60)):
            digest = hashlib.sha256(key.encode()).hexdigest()
            cur.execute("""INSERT INTO gmail_security_attempts VALUES (%s,%s,1)
                ON CONFLICT(bucket_key,window_id) DO UPDATE
                SET attempts=gmail_security_attempts.attempts+1 RETURNING attempts""", (digest, window))
            blocked = cur.fetchone()[0] > limit or blocked
    conn.commit()
    if blocked:
        raise HTTPException(429, "Demasiados intentos. Espere 15 minutos.")
    user = _user(conn, username)
    valid = False
    if _allowed(user):
        try:
            valid = bcrypt.checkpw(password.encode(), str(user["pass_hash"]).encode())
        except (ValueError, TypeError):
            pass
    if not valid:
        raise HTTPException(401, "Credenciales o permisos no validos")
    now = int(time.time())
    totp = pyotp.TOTP(user["totp_secret"])
    step = next((s for s in (now // 30, now // 30 - 1, now // 30 + 1)
                 if hmac.compare_digest(totp.at(s * 30), code)), None)
    if step is None:
        raise HTTPException(401, "Credenciales o permisos no validos")
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO gmail_security_totp(username,last_step) VALUES(%s,%s)
            ON CONFLICT(username) DO UPDATE SET last_step=EXCLUDED.last_step
            WHERE gmail_security_totp.last_step < EXCLUDED.last_step RETURNING last_step""", (username, step))
        accepted = cur.fetchone()
    conn.commit()
    if not accepted:
        raise HTTPException(401, "Espere un nuevo codigo Authenticator")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO gmail_security_audit(username,company_code,action) VALUES(%s,%s,'STEP_UP_AUTHORIZED')",
                    (username, company))
    conn.commit()
    claims = {"purpose": "gmail-admin", "user": username, "company": company, "stamp": _stamp(user)}
    return {"access_token": _cipher().encrypt(json.dumps(claims).encode()).decode(),
            "token_type": "Bearer", "expires_in": SESSION_TTL}


def require_gmail_admin(authorization: str | None = Header(default=None),
                       x_company_code: str = Header(default="MSL-CR"), conn=Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer ") or len(authorization) > 4096:
        raise HTTPException(401, "Autorice la administracion de Gmail con contrasena y Authenticator")
    try:
        claims = json.loads(_cipher().decrypt(authorization[7:].encode(), ttl=SESSION_TTL))
        if not isinstance(claims, dict) or claims.get("purpose") != "gmail-admin":
            raise ValueError()
        user = _user(conn, claims["user"])
        if not _allowed(user) or not hmac.compare_digest(claims["stamp"], _stamp(user)):
            raise ValueError()
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Sesion de administracion Gmail invalida o vencida")
    if claims.get("company") != x_company_code.strip().upper():
        raise HTTPException(403, "La sesion Gmail pertenece a otra empresa")
    return claims
