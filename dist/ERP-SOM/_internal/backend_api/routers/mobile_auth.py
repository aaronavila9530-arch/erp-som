import base64
from datetime import datetime

import bcrypt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from database import get_conn, release_conn
from routers.totp_service import (
    confirm_totp_enrollment,
    start_totp_enrollment,
    validate_totp,
)


router = APIRouter(prefix="/auth/mobile", tags=["Auth Mobile"])


class LoginRequest(BaseModel):
    usuario: str
    password: str


class TotpRequest(BaseModel):
    usuario: str
    codigo: str


MODULES_CONFIG = [
    ("Dashboard", "dashboard"),
    ("Master Data", "master_data"),
    ("Servicios", "servicios"),
    ("Finanzas", "finanzas"),
    ("HHRR", "hhrre"),
    ("Comercial", "comercial"),
    ("Informes", "informes"),
    ("PORTIA", "portia"),
    ("Q&A SOM", "qa_som"),
    ("Admin", "admin_users"),
]


def _fetch_user(usuario: str):
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT usuario, pass_hash, rol, activo, totp_enabled
            FROM usuarios
            WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (usuario,),
        )
        return cur.fetchone()
    finally:
        if cur:
            cur.close()
        release_conn(conn)


def _fetch_role(usuario: str) -> str:
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rol
            FROM usuarios
            WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (usuario,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Usuario no encontrado")
        return row[0]
    finally:
        if cur:
            cur.close()
        release_conn(conn)


def _touch_last_login(usuario: str):
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE usuarios
            SET last_login=%s
            WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(%s))
            """,
            (datetime.now(), usuario),
        )
        conn.commit()
    finally:
        if cur:
            cur.close()
        release_conn(conn)


def _has_visual_permission(usuario: str, rol: str, module_code: str, action: str) -> bool:
    usuario = (usuario or "").strip().lower()
    rol = (rol or "").strip().lower()
    module_code = (module_code or "").strip().lower()
    action = (action or "").strip().lower()

    if usuario in ("gerencia1", "captain", "aaron01", "admin"):
        return True

    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM user_module_permissions
            WHERE lower(usuario)=lower(%s)
              AND allowed=TRUE
            """,
            (usuario,),
        )
        has_rows = (cur.fetchone() or [0])[0] > 0
        if has_rows:
            cur.execute(
                """
                SELECT 1
                FROM user_module_permissions
                WHERE lower(usuario)=lower(%s)
                  AND lower(module_code)=lower(%s)
                  AND lower(action_code) IN (lower(%s), 'admin')
                  AND allowed=TRUE
                LIMIT 1
                """,
                (usuario, module_code, action),
            )
            return cur.fetchone() is not None
    except Exception:
        pass
    finally:
        if cur:
            cur.close()
        if conn:
            release_conn(conn)

    if usuario in ("surveyor01", "surveyor02", "surveyor03"):
        return module_code in {"comercial", "hhrre", "informes", "qa_som"} and action == "view"

    if usuario == "contador01":
        return module_code in {"finanzas", "hhrre"} and action == "view"

    if rol in ("master", "admin"):
        return True

    role_permissions = {
        "accounting": {
            "finanzas": ["view"],
            "qa_som": ["view"],
        },
        "user": {
            "dashboard": ["view"],
            "servicios": ["view"],
            "informes": ["view"],
        },
        "finance": {
            "dashboard": ["view"],
            "finanzas": ["view"],
        },
        "hr": {
            "dashboard": ["view"],
            "hhrre": ["view"],
        },
    }

    return action in role_permissions.get(rol, {}).get(module_code, [])


def _allowed_modules(usuario: str, rol: str):
    return [
        {"label": label, "code": code}
        for label, code in MODULES_CONFIG
        if _has_visual_permission(usuario, rol, code, "view")
    ]


def _permissions_for(usuario: str) -> dict[str, list[str]]:
    conn = None
    cur = None
    permissions: dict[str, list[str]] = {}
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT module_code, action_code
            FROM user_module_permissions
            WHERE lower(usuario)=lower(%s) AND allowed=TRUE
            ORDER BY module_code, action_code
            """,
            (usuario,),
        )
        for module_code, action_code in cur.fetchall() or []:
            permissions.setdefault(str(module_code), []).append(str(action_code))
    except Exception:
        return {}
    finally:
        if cur:
            cur.close()
        if conn:
            release_conn(conn)
    return permissions


def _session_payload(usuario: str, rol: str):
    return {
        "usuario": str(usuario).strip().lower(),
        "rol": str(rol).strip().lower(),
        "token": "LOCAL_SESSION",
        "modules": _allowed_modules(usuario, rol),
        "permissions": _permissions_for(usuario),
    }


@router.post("/login")
def mobile_login(payload: LoginRequest):
    usuario = (payload.usuario or "").strip()
    password = payload.password or ""

    if not usuario or not password:
        raise HTTPException(status_code=400, detail="Usuario y contraseña requeridos")

    row = _fetch_user(usuario)
    if not row:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    username, pass_hash, rol, activo, totp_enabled = row

    if not activo:
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    try:
        password_ok = bcrypt.checkpw(password.encode(), str(pass_hash).encode())
    except ValueError:
        password_ok = False

    if not password_ok:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not totp_enabled:
        qr_bytes = start_totp_enrollment(username)
        if not qr_bytes:
            raise HTTPException(status_code=500, detail="No se pudo iniciar TOTP")
        return {
            "action": "ENROLL_TOTP",
            "usuario": username,
            "rol": rol,
            "qr_base64": base64.b64encode(qr_bytes).decode("ascii"),
        }

    return {
        "action": "VERIFY_TOTP",
        "usuario": username,
        "rol": rol,
    }


@router.post("/totp/confirm")
def mobile_confirm_totp(payload: TotpRequest):
    usuario = (payload.usuario or "").strip()
    codigo = (payload.codigo or "").strip()

    if not usuario or not codigo:
        raise HTTPException(status_code=400, detail="Usuario y código requeridos")

    if not confirm_totp_enrollment(usuario, codigo):
        raise HTTPException(status_code=401, detail="Código inválido")

    rol = _fetch_role(usuario)
    _touch_last_login(usuario)
    return _session_payload(usuario, rol)


@router.post("/totp/verify")
def mobile_verify_totp(payload: TotpRequest):
    usuario = (payload.usuario or "").strip()
    codigo = (payload.codigo or "").strip()

    if not usuario or not codigo:
        raise HTTPException(status_code=400, detail="Usuario y código requeridos")

    if not validate_totp(usuario, codigo):
        raise HTTPException(status_code=401, detail="Código inválido")

    rol = _fetch_role(usuario)
    _touch_last_login(usuario)
    return _session_payload(usuario, rol)
