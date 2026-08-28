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

MODULE_ACTIONS_BY_MODULE = {
    "dashboard": [
        {"code": "view", "label": "Ver dashboard"},
    ],
    "master_data": [
        {"code": "view", "label": "Ver Master Data"},
        {"code": "company_profile", "label": "Ver/editar datos de empresa"},
        {"code": "clients_view", "label": "Ver clientes"},
        {"code": "clients_edit", "label": "Crear/editar clientes"},
        {"code": "providers_view", "label": "Ver proveedores"},
        {"code": "providers_edit", "label": "Crear/editar proveedores"},
        {"code": "employees_view", "label": "Ver empleados"},
        {"code": "employees_edit", "label": "Crear/editar empleados"},
        {"code": "surveyors_view", "label": "Ver surveyors"},
        {"code": "surveyors_edit", "label": "Crear/editar surveyors"},
        {"code": "ports_view", "label": "Ver puertos"},
        {"code": "ports_edit", "label": "Crear/editar puertos"},
        {"code": "operations_view", "label": "Ver operaciones"},
        {"code": "operations_edit", "label": "Crear/editar operaciones"},
        {"code": "bulk_import", "label": "Importaciones masivas"},
        {"code": "export", "label": "Exportar Master Data"},
        {"code": "delete", "label": "Eliminar registros"},
    ],
    "servicios": [
        {"code": "view", "label": "Ver servicios"},
        {"code": "view_detail", "label": "Ver detalle de servicio"},
        {"code": "create", "label": "Crear servicio"},
        {"code": "edit", "label": "Editar servicio"},
        {"code": "edit_client", "label": "Editar cliente/contacto"},
        {"code": "edit_vessel", "label": "Editar buque/contenedor"},
        {"code": "edit_operation", "label": "Editar operacion/puerto/pais"},
        {"code": "assign_surveyor", "label": "Asignar surveyor"},
        {"code": "close_service", "label": "Cerrar servicio"},
        {"code": "cancel_service", "label": "Cancelar servicio"},
        {"code": "delays", "label": "Gestionar demoras"},
        {"code": "generate_report", "label": "Generar informe de servicio"},
        {"code": "billing_ready", "label": "Enviar a facturacion"},
        {"code": "download", "label": "Exportar/descargar"},
    ],
    "finanzas": [
        {"code": "view", "label": "Ver Finanzas"},
        {"code": "billing_view", "label": "Ver Billing"},
        {"code": "billing_manual_invoice", "label": "Crear factura manual"},
        {"code": "billing_xml_invoice", "label": "Crear factura XML"},
        {"code": "billing_advance_invoice", "label": "Factura anticipada"},
        {"code": "billing_credit_note", "label": "Crear nota de credito"},
        {"code": "collections_view", "label": "Ver Collections"},
        {"code": "collections_edit", "label": "Editar Collections"},
        {"code": "collections_apply_payment", "label": "Aplicar pagos CxC"},
        {"code": "collections_post_accounting", "label": "Contabilizar Collections"},
        {"code": "collections_bank_select", "label": "Seleccionar banco en Collections"},
        {"code": "itp_view", "label": "Ver ITP"},
        {"code": "itp_edit", "label": "Editar ITP"},
        {"code": "itp_apply_payment", "label": "Aplicar pagos ITP"},
        {"code": "itp_upload_xml", "label": "Cargar XML compras"},
        {"code": "itp_post_accounting", "label": "Contabilizar ITP"},
        {"code": "itp_quincenal", "label": "Obligaciones quincenales"},
        {"code": "bank_reconciliation_view", "label": "Ver bancos/conciliacion"},
        {"code": "bank_reconciliation_import", "label": "Importar extractos"},
        {"code": "bank_reconciliation_match", "label": "Matching bancario"},
        {"code": "bank_reconciliation_close", "label": "Cerrar conciliacion"},
        {"code": "accounting_view", "label": "Ver Accounting"},
        {"code": "accounting_post", "label": "Postear asientos"},
        {"code": "accounting_adjust", "label": "Ajustar/reversar asientos"},
        {"code": "accounting_catalog", "label": "Catalogo de cuentas"},
        {"code": "accounting_engine", "label": "Motor de contabilizacion"},
        {"code": "accounting_auxiliaries", "label": "Auxiliares contables"},
        {"code": "accounting_audit", "label": "Auditoria financiera"},
        {"code": "accounting_alerts", "label": "Alertas y validaciones"},
        {"code": "accounting_monthly_close", "label": "Cierre mensual"},
        {"code": "accounting_portia", "label": "PORTIA contable"},
        {"code": "tax_center", "label": "Centro fiscal"},
        {"code": "tax_declarations", "label": "Declaraciones D150/D102"},
        {"code": "legal_library", "label": "Biblioteca legal"},
        {"code": "fixed_assets", "label": "Activos fijos"},
        {"code": "inventory", "label": "Inventarios"},
        {"code": "executive_reports", "label": "Reportes ejecutivos"},
        {"code": "reports_download", "label": "Reportes/descargas"},
        {"code": "admin", "label": "Administrar Finanzas"},
    ],
    "hhrre": [
        {"code": "view", "label": "Ver HHRR"},
        {"code": "payslips_view", "label": "Ver colillas"},
        {"code": "payslips_download", "label": "Descargar colillas"},
        {"code": "payroll_view", "label": "Ver Payroll"},
        {"code": "payroll_generate", "label": "Generar Payroll"},
        {"code": "requests_view", "label": "Ver solicitudes"},
        {"code": "requests_create", "label": "Crear solicitudes"},
        {"code": "requests_approve", "label": "Aprobar/rechazar solicitudes"},
        {"code": "hours_view", "label": "Ver horas"},
        {"code": "hours_register", "label": "Registrar horas"},
        {"code": "hours_approve", "label": "Aprobar horas"},
        {"code": "employees_view", "label": "Ver empleados HHRR"},
        {"code": "employees_edit", "label": "Editar empleados HHRR"},
        {"code": "salary_calculator", "label": "Calculadora salarial"},
        {"code": "medical_network", "label": "Red medica"},
        {"code": "policies_view", "label": "Ver politicas"},
        {"code": "policies_edit", "label": "Crear/editar politicas"},
        {"code": "news_publish", "label": "Publicar noticias"},
    ],
    "comercial": [
        {"code": "view", "label": "Ver Comercial"},
        {"code": "quotes_view", "label": "Ver cotizaciones"},
        {"code": "quotes_edit", "label": "Crear/editar cotizaciones"},
        {"code": "prices_view", "label": "Ver precios"},
        {"code": "prices_edit", "label": "Editar precios"},
        {"code": "analytics_view", "label": "Analitica comercial"},
        {"code": "download", "label": "Exportar/descargar"},
    ],
    "informes": [
        {"code": "view", "label": "Ver Informes"},
        {"code": "generate", "label": "Generar informes"},
        {"code": "review", "label": "Revisar informes"},
        {"code": "edit", "label": "Editar informes"},
        {"code": "submit", "label": "Enviar a revision"},
        {"code": "approve", "label": "Aprobar/rechazar"},
        {"code": "download", "label": "Exportar/descargar"},
        {"code": "attachments", "label": "Adjuntos"},
        {"code": "draft_survey", "label": "Draft Survey"},
        {"code": "draft_survey_edit", "label": "Editar Draft Survey"},
        {"code": "draft_survey_export", "label": "Exportar Draft Survey"},
        {"code": "vessel_reports", "label": "Informes de buque"},
        {"code": "container_reports", "label": "Informes de contenedor"},
        {"code": "certificates", "label": "Certificados"},
        {"code": "ong_generate", "label": "Generar ONG"},
        {"code": "ong_review", "label": "Revisar ONG"},
        {"code": "ong_agenda", "label": "Agenda ONG"},
        {"code": "ong_agenda_edit", "label": "Editar agenda ONG"},
        {"code": "ong_agenda_export", "label": "Exportar agenda ONG"},
        {"code": "portia", "label": "PORTIA en informes"},
    ],
    "portia": [
        {"code": "view", "label": "Usar PORTIA"},
        {"code": "finance", "label": "PORTIA contable"},
        {"code": "reports", "label": "PORTIA informes"},
    ],
    "qa_som": [
        {"code": "view", "label": "Ver Q&A SOM"},
        {"code": "ask", "label": "Preguntar"},
    ],
    "admin_users": [
        {"code": "view", "label": "Ver Admin"},
        {"code": "users_create", "label": "Crear usuarios"},
        {"code": "users_permissions", "label": "Asignar permisos"},
        {"code": "users_disable", "label": "Inactivar usuarios"},
        {"code": "company_switch", "label": "Cambiar empresa"},
        {"code": "audit", "label": "Auditar cambios de usuarios"},
        {"code": "admin", "label": "Administrar usuarios"},
    ],
}

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
    rows: list[tuple[str, str]] = []
    for module_code, actions in (permissions or {}).items():
        module_code = str(module_code or "").strip().lower()
        if module_code not in valid_modules:
            continue
        valid_actions = {a["code"] for a in MODULE_ACTIONS_BY_MODULE.get(module_code, MODULE_ACTIONS)}
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
        "module_actions": MODULE_ACTIONS_BY_MODULE,
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
        cur.execute(
            """
            SELECT id, codigo, nombre, apellidos, nombrecomercial, correo
            FROM proveedor
            ORDER BY nombrecomercial NULLS LAST, nombre, apellidos
            """
        )
        for r in cur.fetchall():
            full_name = " ".join([str(r.get("nombre") or "").strip(), str(r.get("apellidos") or "").strip()]).strip()
            label = str(r.get("nombrecomercial") or "").strip() or full_name or str(r.get("codigo") or "")
            rows.append({
                "source_type": "proveedor",
                "source_id": str(r.get("id") or r.get("codigo") or ""),
                "label": label,
                "nombre": r.get("nombre") or r.get("nombrecomercial") or "",
                "apellido": r.get("apellidos") or "",
                "email": r.get("correo") or "",
                "usuario": "",
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
