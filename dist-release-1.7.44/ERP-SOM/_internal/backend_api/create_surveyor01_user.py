from datetime import datetime
import os
import secrets

import bcrypt
import psycopg2
from psycopg2 import sql as psql

database_url = os.getenv("DATABASE_URL", "")
database_public_url = os.getenv("DATABASE_PUBLIC_URL", "")
if database_public_url and "railway.internal" in database_url:
    os.environ["DATABASE_URL"] = database_public_url


USERNAME = "surveyor01"
DISPLAY_NAME = "Surveyor 1"
ROLE = "user"


def _secure_password():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%*-_"
    return "".join(secrets.choice(alphabet) for _ in range(20))


def _columns(cur):
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


def _get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL no definido")

    last_error = None
    for sslmode in ("require", "prefer", "disable"):
        try:
            return psycopg2.connect(
                dsn,
                connect_timeout=15,
                sslmode=sslmode,
            )
        except Exception as exc:
            last_error = exc

    raise last_error


def main():
    password = _secure_password()
    pass_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now()

    conn = _get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cols = _columns(cur)
        if not cols:
            raise RuntimeError("No existe la tabla public.usuarios")

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
            "nombre": DISPLAY_NAME,
            "name": DISPLAY_NAME,
            "display_name": DISPLAY_NAME,
            "email": "surveyor01@som.local",
        }

        missing_required = [
            col
            for col, meta in cols.items()
            if col not in values
            and meta["is_nullable"] == "NO"
            and meta["default"] is None
        ]
        if missing_required:
            raise RuntimeError(
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
                if key in cols and key not in ("usuario", "created_at")
            }
            assignments = [
                psql.SQL("{} = %s").format(psql.Identifier(key))
                for key in update_values
            ]
            query = psql.SQL("UPDATE usuarios SET {} WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(%s))").format(
                psql.SQL(", ").join(assignments)
            )
            cur.execute(query, list(update_values.values()) + [USERNAME])
        else:
            insert_values = {
                key: value
                for key, value in values.items()
                if key in cols
            }
            query = psql.SQL("INSERT INTO usuarios ({}) VALUES ({})").format(
                psql.SQL(", ").join(psql.Identifier(key) for key in insert_values),
                psql.SQL(", ").join(psql.Placeholder() for _ in insert_values),
            )
            cur.execute(query, list(insert_values.values()))

        conn.commit()
        print(f"USUARIO={USERNAME}")
        print(f"ROL={ROLE}")
        print(f"PASSWORD={password}")
        print("TOTP=se enrola al primer login")
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()


if __name__ == "__main__":
    main()
