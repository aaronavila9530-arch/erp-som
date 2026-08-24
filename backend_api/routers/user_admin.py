from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import bcrypt
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor, Json

from database import connect


router = APIRouter(prefix="/admin/users", tags=["Admin - Usuarios"])


MODULES = [
    {"code": "dashboard", "label": "Dashboard"},
    {"code": "master_data", "label": "Master Data"},
    {"code": "servicios", "label": "Servicios"},
    {"code": "finanzas", "label": "Finanzas"},
    {"code": "hhrre", "label": "HHRR"},
    {"code": "comercial", "label": "Comercial"},
    {"code": "informes", "label": "Informes"},
    {"code": "portia", "label": "PORTIA"},
    {"code": "qa_som", "label": "Q&A SOM"},
    {"code": "admin_users", "label": "Usuarios y permisos"},
]

MODULE_ACTIONS = [
    {"code": "view", "label": "Ver"},
    {"code": "create", "label": "Crear"},
    {"code": "edit", "label": "Editar"},
    {"code": "download", "label": "Descargar"},
    {"code": "approve", "label": "Aprobar/Rechazar"},
    {"code": "delete", "label": "Eliminar"},
    {"code": "admin", "label": "Administrar todo"},
]

PASSWORD_RULES = [
    "Minimo 12 caracteres",
    "Al menos una mayuscula",
    "Al menos una minuscula",
    "Al menos un numero",
    "Al menos un simbolo",
]


class UserCreatePayload(BaseModel):
    usuario: str
    password: str
    rol: str = "user"
    source_type: str | None = None
    source_id: str | None = None
    nombre: str | None = None
    apellido: str | None = None
    email: str | None = None
    activo: bool = True
    permissions: dict[str, list[str]] | None = None


class PermissionPayload(BaseModel):
    permissions: dict[str, list[str]]


def _actor_is_admin(actor: str | None, role: str | None) -> bool:
    actor = (actor or "").strip().lower()
    role = (role or "").strip().lower()
    return role in {"admin", "master"} or actor in {"admin", "aaron01", "gerencia1"}


def _require_admin(actor: str | None, role: str | None) -> None:
    if not _actor_is_admin(actor, role):
        raise HTTPException(status_code=403, detail="Solo admin/master puede administrar usuarios")


def _ensure_tables(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_module_permissions (
            id SERIAL PRIMARY KEY,
            usuario TEXT NOT NULL REFERENCES usuarios(usuario) ON DELETE CASCADE,
            module_code TEXT NOT NULL,
            action_code TEXT NOT NULL,
            allowed BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now(),
            updated_by TEXT,
            UNIQUE (usuario, module_code, action_code)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_admin_audit (
            id SERIAL PRIMARY KEY,
            actor_usuario TEXT,
            target_usuario TEXT,
            action TEXT NOT NULL,
            detail JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT now()
        )
        """
    )


def _validate_password(password: str) -> list[str]:
    errors: list[str] = []
    if len(password or "") < 12:
        errors.append(PASSWORD_RULES[0])
    if not re.search(r"[A-Z]", password or ""):
        errors.append(PASSWORD_RULES[1])
    if not re.search(r"[a-z]", password or ""):
        errors.append(PASSWORD_RULES[2])
    if not re.search(r"\d", password or ""):
        errors.append(PASSWORD_RULES[3])
    if not re.search(r"[^A-Za-z0-9]", password or ""):
        errors.append(PASSWORD_RULES[4])
    return errors


def _normalize_permissions(permissions: dict[str, list[str]] | None) -> list[tuple[str, str]]:
    valid_modules = {m["code"] for m in MODULES}
    valid_actions = {a["code"] for a in MODULE_ACTIONS}
    rows: list[tuple[str, str]] = []
    for module_code, actions in (permissions or {}).items():
        module_code = str(module_code or "").strip().lower()
        if module_code not in valid_modules:
            continue
        for action in actions or []:
            action_code = str(action or "").strip().lower()
            if action_code in valid_actions:
                rows.append((module_code, action_code))
    return rows


def _upsert_permissions(cur, usuario: str, permissions: dict[str, list[str]] | None, actor: str | None) -> None:
    rows = _normalize_permissions(permissions)
    cur.execute("DELETE FROM user_module_permissions WHERE lower(usuario)=lower(%s)", (usuario,))
    for module_code, action_code in rows:
        cur.execute(
            """
            INSERT INTO user_module_permissions (usuario, module_code, action_code, allowed, updated_by)
            VALUES (%s, %s, %s, TRUE, %s)
            ON CONFLICT (usuario, module_code, action_code)
            DO UPDATE SET allowed=TRUE, updated_at=now(), updated_by=EXCLUDED.updated_by
            """,
            (usuario, module_code, action_code, actor),
        )


def _permissions_for(cur, usuario: str) -> dict[str, list[str]]:
    cur.execute(
        """
        SELECT module_code, action_code
        FROM user_module_permissions
        WHERE lower(usuario)=lower(%s) AND allowed=TRUE
        ORDER BY module_code, action_code
        """,
        (usuario,),
    )
    permissions: dict[str, list[str]] = {}
    for row in cur.fetchall():
        module_code = row["module_code"] if isinstance(row, dict) else row[0]
        action_code = row["action_code"] if isinstance(row, dict) else row[1]
        permissions.setdefault(module_code, []).append(action_code)
    return permissions


def _audit(cur, actor: str | None, target: str | None, action: str, detail: dict[str, Any]) -> None:
    cur.execute(
        """
        INSERT INTO user_admin_audit (actor_usuario, target_usuario, action, detail)
        VALUES (%s, %s, %s, %s)
        """,
        (actor, target, action, Json(detail)),
    )


@router.get("/meta")
def meta(x_user: str | None = Header(default=None, alias="X-User"),
         x_role: str | None = Header(default=None, alias="X-User-Role")):
    _require_admin(x_user, x_role)
    return {
        "modules": MODULES,
        "actions": MODULE_ACTIONS,
        "password_rules": PASSWORD_RULES,
        "roles": ["user", "hr", "finance", "accounting", "admin", "master"],
    }


@router.get("/people")
def people(x_user: str | None = Header(default=None, alias="X-User"),
           x_role: str | None = Header(default=None, alias="X-User-Role")):
    _require_admin(x_user, x_role)
    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        rows: list[dict[str, Any]] = []
        cur.execute(
            """
            SELECT id, codigo, nombre, apellidos, usuario
            FROM empleados
            ORDER BY nombre, apellidos
            """
        )
        for r in cur.fetchall():
            full_name = " ".join([str(r.get("nombre") or "").strip(), str(r.get("apellidos") or "").strip()]).strip()
            rows.append({
                "source_type": "empleado",
                "source_id": str(r.get("id") or r.get("codigo") or ""),
                "label": full_name or str(r.get("codigo") or ""),
                "nombre": r.get("nombre") or "",
                "apellido": r.get("apellidos") or "",
                "email": "",
                "usuario": r.get("usuario") or "",
            })
        return {"people": rows}
    finally:
        cur.close()
        conn.close()


@router.get("")
def list_users(x_user: str | None = Header(default=None, alias="X-User"),
               x_role: str | None = Header(default=None, alias="X-User-Role")):
    _require_admin(x_user, x_role)
    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        _ensure_tables(cur)
        cur.execute(
            """
            SELECT usuario, nombre, apellido, email, rol, activo
            FROM usuarios
            ORDER BY usuario
            """
        )
        users = []
        for row in cur.fetchall():
            user = dict(row)
            user["permissions"] = _permissions_for(cur, row["usuario"])
            users.append(user)
        conn.commit()
        return {"users": users}
    finally:
        cur.close()
        conn.close()


@router.get("/{usuario}/permissions")
def get_permissions(usuario: str):
    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        _ensure_tables(cur)
        permissions = _permissions_for(cur, usuario)
        conn.commit()
        return {"usuario": usuario, "permissions": permissions}
    finally:
        cur.close()
        conn.close()


@router.post("")
def create_user(payload: UserCreatePayload,
                x_user: str | None = Header(default=None, alias="X-User"),
                x_role: str | None = Header(default=None, alias="X-User-Role")):
    _require_admin(x_user, x_role)
    usuario = (payload.usuario or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{4,40}", usuario):
        raise HTTPException(status_code=400, detail="Usuario invalido. Usa 4-40 caracteres: letras, numeros, punto, guion o guion bajo.")
    errors = _validate_password(payload.password)
    if errors:
        raise HTTPException(status_code=400, detail="La contraseña no cumple: " + "; ".join(errors))

    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        _ensure_tables(cur)
        cur.execute("SELECT 1 FROM usuarios WHERE lower(usuario)=lower(%s)", (usuario,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Ese usuario ya existe")

        pass_hash = bcrypt.hashpw(payload.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        cur.execute(
            """
            INSERT INTO usuarios (
                usuario, pass_hash, rol, activo, email, pass_temp, intentos,
                bloqueado, totp_secret, totp_enabled, reset_step, last_login,
                nombre, apellido, fecha_ingreso
            )
            VALUES (%s, %s, %s, %s, %s, TRUE, 0, FALSE, NULL, FALSE, NULL, NULL, %s, %s, %s)
            """,
            (
                usuario,
                pass_hash,
                (payload.rol or "user").strip().lower(),
                payload.activo,
                payload.email,
                payload.nombre,
                payload.apellido,
                datetime.now().date(),
            ),
        )
        _upsert_permissions(cur, usuario, payload.permissions, x_user)
        _audit(cur, x_user, usuario, "CREATE_USER", payload.model_dump(exclude={"password"}))
        conn.commit()
        return {"status": "OK", "usuario": usuario}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cur.close()
        conn.close()


@router.put("/{usuario}/permissions")
def save_permissions(usuario: str, payload: PermissionPayload,
                     x_user: str | None = Header(default=None, alias="X-User"),
                     x_role: str | None = Header(default=None, alias="X-User-Role")):
    _require_admin(x_user, x_role)
    conn = connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        _ensure_tables(cur)
        cur.execute("SELECT 1 FROM usuarios WHERE lower(usuario)=lower(%s)", (usuario,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        _upsert_permissions(cur, usuario, payload.permissions, x_user)
        _audit(cur, x_user, usuario, "UPDATE_PERMISSIONS", {"permissions": payload.permissions})
        conn.commit()
        return {"status": "OK", "usuario": usuario}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cur.close()
        conn.close()
