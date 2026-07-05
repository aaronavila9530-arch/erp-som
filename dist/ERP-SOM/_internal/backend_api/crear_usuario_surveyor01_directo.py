from datetime import datetime
import secrets

import bcrypt
import psycopg2
from psycopg2 import sql as psql


DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

USERNAME = "surveyor01"
DISPLAY_NAME = "Surveyor 1"
ROLE = "user"


def secure_password():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%*-_"
    return "".join(secrets.choice(alphabet) for _ in range(20))


def get_columns(cur):
    cur.execute(
        """
        SELECT column_name, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'usuarios'
        ORDER BY ordinal_position
        """
    )
    return {
        row[0]: {
            "is_nullable": row[1],
            "default": row[2],
        }
        for row in cur.fetchall()
    }


def main():
    password = secure_password()
    pass_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now()

    print("Conectando a PostgreSQL Railway...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        cur = conn.cursor()
        columns = get_columns(cur)

        if not columns:
            raise Exception("No existe la tabla public.usuarios")

        values = {
            "usuario": USERNAME,
            "pass_hash": pass_hash,
            "rol": ROLE,
            "activo": True,
            "totp_enabled": False,
            "totp_secret": None,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "nombre": "Surveyor",
            "apellido": "1",
            "name": DISPLAY_NAME,
            "display_name": DISPLAY_NAME,
            "email": "surveyor01@som.local",
        }

        missing_required = [
            col
            for col, meta in columns.items()
            if col not in values
            and meta["is_nullable"] == "NO"
            and meta["default"] is None
        ]
        if missing_required:
            raise Exception(
                "Columnas requeridas sin valor/default en usuarios: "
                + ", ".join(missing_required)
            )

        cur.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (USERNAME,),
        )
        exists = cur.fetchone() is not None

        if exists:
            update_values = {
                key: value
                for key, value in values.items()
                if key in columns and key not in ("usuario", "created_at")
            }
            query = psql.SQL(
                "UPDATE usuarios SET {} WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(%s))"
            ).format(
                psql.SQL(", ").join(
                    psql.SQL("{} = %s").format(psql.Identifier(key))
                    for key in update_values
                )
            )
            cur.execute(query, list(update_values.values()) + [USERNAME])
            print("Usuario existente actualizado.")
        else:
            insert_values = {
                key: value
                for key, value in values.items()
                if key in columns
            }
            query = psql.SQL("INSERT INTO usuarios ({}) VALUES ({})").format(
                psql.SQL(", ").join(psql.Identifier(key) for key in insert_values),
                psql.SQL(", ").join(psql.Placeholder() for _ in insert_values),
            )
            cur.execute(query, list(insert_values.values()))
            print("Usuario creado.")

        conn.commit()
        print(f"USUARIO={USERNAME}")
        print(f"ROL={ROLE}")
        print(f"PASSWORD={password}")
        print("TOTP=se enrola al primer login")

    except Exception as e:
        conn.rollback()
        print("ERROR creando usuario:")
        print(e)
        raise

    finally:
        conn.close()
        print("Conexion cerrada.")


if __name__ == "__main__":
    main()
