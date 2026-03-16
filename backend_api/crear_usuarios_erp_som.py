import psycopg2
import bcrypt
from datetime import datetime

# ==========================================================
# DATABASE CONNECTION
# ==========================================================
DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


# ==========================================================
# USERS TO CREATE
# ==========================================================
USERS = [

    {
        "usuario": "contador01",
        "password": "M$LUser01",
        "rol": "user",
        "email": "contabilidad@mslogisticsgroup.com",
        "nombre": "Maritza",
        "apellido": "Pendiente"
    },

    {
        "usuario": "surveyor01",
        "password": "M$LUser02",
        "rol": "user",
        "email": "administrativo@mslogisticsgroup.com",
        "nombre": "Manfred",
        "apellido": "Bolaños"
    },

    {
        "usuario": "surveyor02",
        "password": "M$LUser03",
        "rol": "user",
        "email": "administrativo@mslogisticsgroup.com",
        "nombre": "Patricia",
        "apellido": "Omier"
    }

]


# ==========================================================
# HASH PASSWORD
# ==========================================================
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    return hashed.decode()


# ==========================================================
# MAIN
# ==========================================================
def main():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🔐 Creando usuarios ERP-SOM...\n")

    for u in USERS:

        username = u["usuario"].lower().strip()

        # -------------------------------------------
        # CHECK IF USER EXISTS
        # -------------------------------------------
        cur.execute(
            "SELECT id FROM usuarios WHERE usuario = %s",
            (username,)
        )

        if cur.fetchone():
            print(f"⚠️ Usuario ya existe: {username}")
            continue

        password_hash = hash_password(u["password"])

        cur.execute(
            """
            INSERT INTO usuarios
            (
                usuario,
                pass_hash,
                rol,
                activo,
                email,
                creado,
                intentos,
                bloqueado,
                totp_enabled,
                nombre,
                apellido
            )
            VALUES
            (
                %s,
                %s,
                %s,
                TRUE,
                %s,
                %s,
                0,
                FALSE,
                FALSE,
                %s,
                %s
            )
            """,
            (
                username,
                password_hash,
                u["rol"],
                u["email"],
                datetime.now(),
                u["nombre"],
                u["apellido"]
            )
        )

        print(f"✅ Usuario creado: {username}")

    conn.commit()

    cur.close()
    conn.close()

    print("\n🎉 Proceso finalizado.")


# ==========================================================
# EXECUTE
# ==========================================================
if __name__ == "__main__":
    main()