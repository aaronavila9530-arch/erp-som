from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
import bcrypt

from database import get_db
from .totp_service import validate_totp


router = APIRouter(
    prefix="/auth/reset",
    tags=["Password Reset"]
)


# ============================================================
# PASO 1 — VERIFICAR IDENTIDAD
# ============================================================
@router.post("/verify-identity")
def verify_identity(payload: dict, conn=Depends(get_db)):

    usuario = payload.get("usuario")
    nombre = payload.get("nombre")
    apellido = payload.get("apellido")
    email = payload.get("email")

    if not all([usuario, nombre, apellido, email]):
        raise HTTPException(400, "Datos incompletos")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT id
        FROM usuarios
        WHERE LOWER(usuario)  = LOWER(TRIM(%s))
          AND LOWER(nombre)   = LOWER(TRIM(%s))
          AND LOWER(apellido) = LOWER(TRIM(%s))
          AND LOWER(email)    = LOWER(TRIM(%s))
          AND activo = TRUE
    """, (usuario, nombre, apellido, email))

    if not cur.fetchone():
        raise HTTPException(401, "Datos no coinciden")

    cur.execute("""
        UPDATE usuarios
        SET reset_step='IDENTITY_OK'
        WHERE LOWER(usuario)=LOWER(TRIM(%s))
    """, (usuario,))

    conn.commit()

    return {
        "ok": True,
        "step": "TOTP_REQUIRED"
    }


# ============================================================
# PASO 2 — VERIFICAR TOTP
# ============================================================
@router.post("/verify-totp")
def verify_totp(payload: dict, conn=Depends(get_db)):

    usuario = payload.get("usuario")
    codigo = payload.get("codigo")

    if not usuario or not codigo:
        raise HTTPException(400, "Datos incompletos")

    if not validate_totp(usuario.strip(), codigo.strip()):
        raise HTTPException(401, "Código inválido")

    cur = conn.cursor()

    cur.execute("""
        SELECT reset_step
        FROM usuarios
        WHERE LOWER(usuario)=LOWER(TRIM(%s))
    """, (usuario,))

    row = cur.fetchone()
    if not row or row[0] != "IDENTITY_OK":
        raise HTTPException(403, "Flujo inválido")

    cur.execute("""
        UPDATE usuarios
        SET reset_step='TOTP_OK'
        WHERE LOWER(usuario)=LOWER(TRIM(%s))
    """, (usuario,))

    conn.commit()

    return {
        "ok": True,
        "step": "RESET_ALLOWED"
    }


# ============================================================
# PASO 3 — CAMBIAR CONTRASEÑA
# ============================================================
@router.post("/set-password")
def set_password(payload: dict, conn=Depends(get_db)):

    usuario = payload.get("usuario")
    password = payload.get("password")

    if not usuario or not password or len(password) < 8:
        raise HTTPException(400, "Contraseña inválida")

    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    cur = conn.cursor()

    cur.execute("""
        SELECT reset_step
        FROM usuarios
        WHERE LOWER(usuario)=LOWER(TRIM(%s))
    """, (usuario,))

    row = cur.fetchone()
    if not row or row[0] != "TOTP_OK":
        raise HTTPException(403, "No autorizado")

    cur.execute("""
        UPDATE usuarios
        SET pass_hash=%s,
            pass_temp=FALSE,
            reset_step=NULL
        WHERE LOWER(usuario)=LOWER(TRIM(%s))
    """, (hashed, usuario))

    conn.commit()

    return {
        "ok": True,
        "message": "Contraseña actualizada"
    }
