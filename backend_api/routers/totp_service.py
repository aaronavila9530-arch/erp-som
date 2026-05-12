# ============================================================
# TOTP SERVICE — Microsoft / Google Authenticator
# ERP-SOM
# ============================================================

import io
import pyotp
import qrcode
from database import get_conn, release_conn


# ============================================================
# GENERAR SECRET BASE32
# ============================================================
def generate_totp_secret() -> str:
    """
    Genera un secret Base32 compatible con Microsoft / Google Authenticator
    """
    return pyotp.random_base32()


# ============================================================
# GENERAR URI OTPAUTH (QR CONTENT)
# ============================================================
def generate_totp_uri(usuario: str, secret: str) -> str:
    """
    Genera la URI estándar otpauth:// para Authenticator
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=usuario,
        issuer_name="ERP-SOM"
    )


# ============================================================
# GENERAR QR (BYTES PNG)
# ============================================================
def generate_totp_qr_bytes(uri: str) -> bytes:
    """
    Genera el QR como imagen PNG en memoria (bytes)
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=8,
        border=4
    )
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return buffer.read()


# ============================================================
# INICIAR REGISTRO TOTP (PASO 1)
# ============================================================
def start_totp_enrollment(usuario: str) -> bytes:
    """
    1️⃣ Genera secret
    2️⃣ Guarda secret (pendiente)
    3️⃣ Devuelve QR (PNG bytes)
    """

    secret = generate_totp_secret()
    uri = generate_totp_uri(usuario, secret)

    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT id
            FROM usuarios
            WHERE usuario=%s AND activo=TRUE
        """, (usuario,))
        if not cur.fetchone():
            return None

        cur.execute("""
            UPDATE usuarios
            SET totp_secret=%s,
                totp_enabled=FALSE
            WHERE usuario=%s
        """, (secret, usuario))

        conn.commit()
        return generate_totp_qr_bytes(uri)

    finally:
        if cur:
            cur.close()
        release_conn(conn)


# ============================================================
# CONFIRMAR REGISTRO TOTP (PASO 2)
# ============================================================
def confirm_totp_enrollment(usuario: str, codigo: str) -> bool:
    """
    Verifica el código ingresado desde Authenticator
    Si es correcto, activa TOTP definitivamente
    """

    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT totp_secret
            FROM usuarios
            WHERE usuario=%s AND activo=TRUE
        """, (usuario,))
        row = cur.fetchone()

        if not row or not row[0]:
            return False

        secret = row[0]
        totp = pyotp.TOTP(secret)

        if not totp.verify(codigo, valid_window=1):
            return False

        cur.execute("""
            UPDATE usuarios
            SET totp_enabled=TRUE
            WHERE usuario=%s
        """, (usuario,))

        conn.commit()
        return True

    finally:
        if cur:
            cur.close()
        release_conn(conn)


# ============================================================
# VALIDAR TOTP (LOGIN / RESET)
# ============================================================
def validate_totp(usuario: str, codigo: str) -> bool:
    """
    Valida código TOTP durante login o reset de contraseña
    """

    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT totp_secret, totp_enabled
            FROM usuarios
            WHERE usuario=%s AND activo=TRUE
        """, (usuario,))
        row = cur.fetchone()

        if not row:
            return False

        secret, enabled = row

        if not enabled or not secret:
            return False

        totp = pyotp.TOTP(secret)
        return totp.verify(codigo, valid_window=1)

    finally:
        if cur:
            cur.close()
        release_conn(conn)
