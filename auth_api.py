from datetime import datetime
import bcrypt

from backend_api.database import get_conn
from totp_service import (
    start_totp_enrollment,
    confirm_totp_enrollment,
    validate_totp
)


# =====================================================
# LOGIN USUARIO — PASO 1 (usuario + contraseña)
# =====================================================
def login_usuario(usuario: str, password: str):
    """
    Verifica credenciales básicas y decide el siguiente paso:
    - ENROLL_TOTP → mostrar QR
    - VERIFY_TOTP → pedir código Authenticator
    """

    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT pass_hash, rol, activo, totp_enabled
            FROM usuarios
            WHERE usuario=%s
        """, (usuario,))
        row = cur.fetchone()

        if not row:
            return False, {"error": "Usuario no existe"}

        pass_hash, rol, activo, totp_enabled = row

        if not activo:
            return False, {"error": "Usuario inactivo"}

        if not bcrypt.checkpw(password.encode(), pass_hash.encode()):
            return False, {"error": "Credenciales inválidas"}

        # 🔐 Usuario válido → decidir flujo
        if not totp_enabled:
            # Primer login → registrar Authenticator (QR)
            qr_bytes = start_totp_enrollment(usuario)

            if not qr_bytes:
                return False, {"error": "No se pudo iniciar TOTP"}

            return True, {
                "action": "ENROLL_TOTP",
                "usuario": usuario,
                "rol": rol,
                "qr": qr_bytes
            }

        # Login normal → pedir código TOTP
        return True, {
            "action": "VERIFY_TOTP",
            "usuario": usuario,
            "rol": rol
        }

    finally:
        cur.close()
        conn.close()


# =====================================================
# CONFIRMAR REGISTRO TOTP — PASO 2 (QR)
# =====================================================
def confirmar_registro_totp(usuario: str, codigo: str):
    """
    Confirma el código ingresado tras escanear el QR
    """

    if not codigo or not codigo.strip():
        return False, {"error": "Código requerido"}

    ok = confirm_totp_enrollment(usuario, codigo.strip())

    if not ok:
        return False, {"error": "Código inválido"}

    # Registro TOTP completado → acceso permitido
    return True, {
        "usuario": usuario
    }


# =====================================================
# VALIDAR TOTP — LOGIN / RESET PASSWORD
# =====================================================
def validar_totp_login(usuario: str, codigo: str):

    if not codigo or not codigo.strip():
        return False, {"error": "Código requerido"}

    ok = validate_totp(usuario, codigo.strip())

    if not ok:
        return False, {"error": "Código inválido"}

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT rol
            FROM usuarios
            WHERE usuario=%s
        """, (usuario,))
        row = cur.fetchone()

        if not row:
            return False, {"error": "Usuario no encontrado"}

        rol = row[0]

        cur.execute("""
            UPDATE usuarios
            SET last_login=%s
            WHERE usuario=%s
        """, (datetime.now(), usuario))
        conn.commit()

        return True, {
            "usuario": usuario,
            "rol": rol,
            "token": "LOCAL_SESSION"
        }

    finally:
        cur.close()
        conn.close()
