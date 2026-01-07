import bcrypt
from backend_api.database import get_conn
from totp_service import validate_totp


# =====================================================
# PASO 1 — VERIFICAR IDENTIDAD (usuario + nombre + apellido)
# =====================================================
def verify_identity(usuario: str, nombre: str, apellido: str):
    """
    Verifica que el usuario exista y que nombre / apellido hagan match.
    Si es correcto, habilita el paso TOTP.
    """

    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT id
            FROM usuarios
            WHERE usuario=%s
              AND LOWER(first_name)=LOWER(%s)
              AND LOWER(last_name)=LOWER(%s)
              AND activo=TRUE
        """, (usuario, nombre.strip(), apellido.strip()))

        if not cur.fetchone():
            return False, {"error": "Datos no coinciden"}

        cur.execute("""
            UPDATE usuarios
            SET reset_step='IDENTITY_OK'
            WHERE usuario=%s
        """, (usuario,))
        conn.commit()

        return True, {"step": "TOTP_REQUIRED"}

    finally:
        cur.close()
        conn.close()


# =====================================================
# PASO 2 — VERIFICAR TOTP
# =====================================================
def verify_reset_totp(usuario: str, codigo: str):
    """
    Verifica el código de Microsoft Authenticator
    """

    if not validate_totp(usuario, codigo.strip()):
        return False, {"error": "Código inválido"}

    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT reset_step
            FROM usuarios
            WHERE usuario=%s
        """, (usuario,))
        row = cur.fetchone()

        if not row or row[0] != "IDENTITY_OK":
            return False, {"error": "Flujo inválido"}

        cur.execute("""
            UPDATE usuarios
            SET reset_step='TOTP_OK'
            WHERE usuario=%s
        """, (usuario,))
        conn.commit()

        return True, {"step": "RESET_ALLOWED"}

    finally:
        cur.close()
        conn.close()


# =====================================================
# PASO 3 — CAMBIAR CONTRASEÑA
# =====================================================
def reset_password_final(usuario: str, new_password: str):
    """
    Cambia la contraseña definitivamente
    """

    if len(new_password) < 8:
        return False, {"error": "La contraseña debe tener al menos 8 caracteres"}

    hashed = bcrypt.hashpw(
        new_password.encode(),
        bcrypt.gensalt()
    ).decode()

    conn = get_conn()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT reset_step
            FROM usuarios
            WHERE usuario=%s
        """, (usuario,))
        row = cur.fetchone()

        if not row or row[0] != "TOTP_OK":
            return False, {"error": "No autorizado"}

        cur.execute("""
            UPDATE usuarios
            SET pass_hash=%s,
                pass_temp=FALSE,
                reset_step=NULL
            WHERE usuario=%s
        """, (hashed, usuario))
        conn.commit()

        return True, {"message": "Contraseña actualizada"}

    finally:
        cur.close()
        conn.close()
