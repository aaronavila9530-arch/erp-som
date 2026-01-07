from datetime import datetime, timedelta
from backend_api.database import get_conn
import random
import string


def generar_otp():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def enviar_otp(usuario):
    otp = generar_otp()
    expira = datetime.now() + timedelta(minutes=5)

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE usuarios
            SET otp_code=%s, otp_expira=%s
            WHERE usuario=%s
        """, (otp, expira, usuario))

    # ===============================
    # DEBUG OTP (DESARROLLO)
    # ===============================
    print("\n==============================")
    print(f"🔐 OTP DEBUG | Usuario: {usuario}")
    print(f"🔑 Código OTP: {otp}")
    print("⏱ Válido por 5 minutos")
    print("==============================\n")
