from datetime import datetime
import base64

import bcrypt
import requests

from backend_api.database import get_conn
from totp_service import (
    start_totp_enrollment,
    confirm_totp_enrollment,
    validate_totp,
)


AUTH_BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"
AUTH_TIMEOUT = 20


def _api_error(response):
    try:
        payload = response.json()
    except Exception:
        return response.text or "Error de autenticacion"
    return payload.get("detail") or payload.get("error") or "Error de autenticacion"


def _post_auth(path, payload):
    response = requests.post(
        f"{AUTH_BASE_URL}{path}",
        json=payload,
        timeout=AUTH_TIMEOUT,
    )
    if response.status_code >= 400:
        return False, {"error": _api_error(response)}
    return True, response.json()


def login_usuario(usuario: str, password: str):
    """
    Paso 1 de login.

    En produccion usa la API HTTPS para evitar depender del proxy publico
    directo a PostgreSQL desde Windows. El acceso local a DB queda como
    fallback de desarrollo.
    """

    try:
        ok, data = _post_auth(
            "/auth/mobile/login",
            {"usuario": usuario, "password": password},
        )
        if not ok:
            return False, data

        if data.get("action") == "ENROLL_TOTP" and data.get("qr_base64"):
            data["qr"] = base64.b64decode(data["qr_base64"])

        return True, data
    except Exception:
        pass

    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT pass_hash, rol, activo, totp_enabled
            FROM usuarios
            WHERE usuario=%s
            """,
            (usuario,),
        )
        row = cur.fetchone()

        if not row:
            return False, {"error": "Usuario no existe"}

        pass_hash, rol, activo, totp_enabled = row

        if not activo:
            return False, {"error": "Usuario inactivo"}

        if not bcrypt.checkpw(password.encode(), pass_hash.encode()):
            return False, {"error": "Credenciales invalidas"}

        if not totp_enabled:
            qr_bytes = start_totp_enrollment(usuario)
            if not qr_bytes:
                return False, {"error": "No se pudo iniciar TOTP"}
            return True, {
                "action": "ENROLL_TOTP",
                "usuario": usuario,
                "rol": rol,
                "qr": qr_bytes,
            }

        return True, {
            "action": "VERIFY_TOTP",
            "usuario": usuario,
            "rol": rol,
        }

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def confirmar_registro_totp(usuario: str, codigo: str):
    if not codigo or not codigo.strip():
        return False, {"error": "Codigo requerido"}

    try:
        return _post_auth(
            "/auth/mobile/totp/confirm",
            {"usuario": usuario, "codigo": codigo.strip()},
        )
    except Exception:
        pass

    ok = confirm_totp_enrollment(usuario, codigo.strip())
    if not ok:
        return False, {"error": "Codigo invalido"}

    return True, {"usuario": usuario}


def validar_totp_login(usuario: str, codigo: str):
    if not codigo or not codigo.strip():
        return False, {"error": "Codigo requerido"}

    try:
        return _post_auth(
            "/auth/mobile/totp/verify",
            {"usuario": usuario, "codigo": codigo.strip()},
        )
    except Exception:
        pass

    ok = validate_totp(usuario, codigo.strip())
    if not ok:
        return False, {"error": "Codigo invalido"}

    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT rol
            FROM usuarios
            WHERE usuario=%s
            """,
            (usuario,),
        )
        row = cur.fetchone()

        if not row:
            return False, {"error": "Usuario no encontrado"}

        rol = row[0]

        cur.execute(
            """
            UPDATE usuarios
            SET last_login=%s
            WHERE usuario=%s
            """,
            (datetime.now(), usuario),
        )
        conn.commit()

        return True, {
            "usuario": usuario,
            "rol": rol,
            "token": "LOCAL_SESSION",
        }

    finally:
        if cur:
            cur.close()
        conn.close()
