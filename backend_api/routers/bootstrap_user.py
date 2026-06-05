import os
import secrets
from datetime import datetime

import bcrypt
from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg2 import sql as psql

from database import get_db


router = APIRouter(prefix="/bootstrap", tags=["Bootstrap"])


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


def _require_bootstrap_token(token):
    expected = os.getenv("SOM_BOOTSTRAP_TOKEN")
    if not expected:
        raise HTTPException(status_code=404, detail="Not found")
    if not token or not secrets.compare_digest(str(token), expected):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/surveyor01")
def create_surveyor01(
    x_bootstrap_token: str | None = Header(default=None, alias="X-Bootstrap-Token"),
    conn=Depends(get_db),
):
    _require_bootstrap_token(x_bootstrap_token)

    username = "surveyor01"
    role = "user"
    password = _secure_password()
    pass_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    now = datetime.now()

    cur = conn.cursor()
    try:
        columns = _columns(cur)
        if not columns:
            raise HTTPException(status_code=500, detail="No existe la tabla public.usuarios")

        values = {
            "usuario": username,
            "pass_hash": pass_hash,
            "rol": role,
            "activo": True,
            "totp_enabled": False,
            "totp_secret": None,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "nombre": "Surveyor",
            "apellido": "1",
            "name": "Surveyor 1",
            "display_name": "Surveyor 1",
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
            raise HTTPException(
                status_code=500,
                detail="Columnas requeridas sin valor/default: " + ", ".join(missing_required),
            )

        cur.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE LOWER(TRIM(usuario)) = LOWER(TRIM(%s))
            LIMIT 1
            """,
            (username,),
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
            cur.execute(query, list(update_values.values()) + [username])
            action = "updated"
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
            action = "created"

        conn.commit()
        return {
            "success": True,
            "action": action,
            "usuario": username,
            "rol": role,
            "password": password,
            "totp": "enroll_on_first_login",
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cur.close()
