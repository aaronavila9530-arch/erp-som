from fastapi import APIRouter, Depends, HTTPException
from psycopg2.extras import RealDictCursor
import bcrypt

from database import get_db
from .totp_service import validate_totp


router = APIRouter(
    prefix="/auth/reset",
    tags=["Password Reset"]
)


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
        WHERE usuario=%s
          AND LOWER(nombre)=LOWER(%s)
          AND LOWER(apellido)=LOWER(%s)
          AND LOWER(email)=LOWER(%s)
          AND activo=TRUE
    """, (usuario, nombre, apellido, email))

    if not cur.fetchone():
        raise HTTPException(401, "Datos no coinciden")

    cur.execute("""
        UPDATE usuarios
        SET reset_step='IDENTITY_OK'
        WHERE usuario=%s
    """, (usuario,))

    conn.commit()
    return {"step": "TOTP_REQUIRED"}



@router.post("/verify-totp")
def verify_totp(payload: dict, conn=Depends(get_db)):

    usuario = payload.get("usuario")
    codigo = payload.get("codigo")

    if not validate_totp(usuario, codigo):
        raise HTTPException(401, "Código inválido")

    cur = conn.cursor()

    cur.execute("""
        SELECT reset_step
        FROM usuarios
        WHERE usuario=%s
    """, (usuario,))

    row = cur.fetchone()
    if not row or row[0] != "IDENTITY_OK":
        raise HTTPException(403, "Flujo inválido")

    cur.execute("""
        UPDATE usuarios
        SET reset_step='TOTP_OK'
        WHERE usuario=%s
    """, (usuario,))

    conn.commit()
    return {"step": "RESET_ALLOWED"}


@router.post("/set-password")
def set_password(payload: dict, conn=Depends(get_db)):

    usuario = payload.get("usuario")
    password = payload.get("password")

    if not password or len(password) < 8:
        raise HTTPException(400, "Contraseña inválida")

    hashed = bcrypt.hashpw(
        password.encode(),
        bcrypt.gensalt()
    ).decode()

    cur = conn.cursor()

    cur.execute("""
        SELECT reset_step
        FROM usuarios
        WHERE usuario=%s
    """, (usuario,))

    row = cur.fetchone()
    if not row or row[0] != "TOTP_OK":
        raise HTTPException(403, "No autorizado")

    cur.execute("""
        UPDATE usuarios
        SET pass_hash=%s,
            pass_temp=FALSE,
            reset_step=NULL
        WHERE usuario=%s
    """, (hashed, usuario))

    conn.commit()
    return {"message": "Contraseña actualizada"}
