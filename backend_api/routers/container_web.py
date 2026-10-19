"""Isolated Containers web API; legacy desktop routes are intentionally untouched."""
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from psycopg2 import DataError, IntegrityError
from psycopg2.extras import RealDictCursor

from database import get_db
from security.auth import get_current_user
from routers.mobile_auth import _has_visual_permission
from services.tenanting import company_code
from services.container_web_fields import SECTIONS, FIELDS, BOOLEAN_FIELDS, DATE_FIELDS

router = APIRouter(prefix="/informes/containers", tags=["Containers Web"])
ASSETS = Path(__file__).resolve().parents[1] / "assets" / "containers"
log = logging.getLogger(__name__)
# Legacy records may carry the default company despite being linked to another
# company. Resolve through Services only when that link is unambiguous.
REPORT_SOURCE = """FROM container_reports cr LEFT JOIN LATERAL (
    SELECT MIN(NULLIF(TRIM(company_code),'')) AS company,
           COUNT(DISTINCT NULLIF(TRIM(company_code),'')) AS companies,
           MIN(cliente) AS customer
    FROM servicios WHERE num_informe=cr.linked_report_number
) s ON TRUE WHERE s.companies <= 1
AND COALESCE(s.company,NULLIF(TRIM(to_jsonb(cr)->>'company_code'),''),'MSL-CR')=%s"""


def access(user=Depends(get_current_user), x_company_code: str = Header(default="MSL-CR")):
    permissions = {a: _has_visual_permission(user["usuario"], user["rol"], "informes", a)
                   for a in ("view", "create", "edit")}
    if not permissions["view"]:
        raise HTTPException(403, "Sin permiso para Informes")
    permissions["approve"] = user["rol"] in ("admin", "master") and permissions["edit"]
    return {"company": company_code(x_company_code), "user": user["usuario"], "permissions": permissions}


def require(ctx, action):
    if not ctx["permissions"].get(action):
        raise HTTPException(403, "Sin permiso para esta accion")


def version(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest()


def read_report(cur, rid, ctx, lock=False):
    cur.execute("SELECT cr.* " + REPORT_SOURCE + " AND cr.id=%s" + (" FOR UPDATE OF cr" if lock else ""),
                (ctx["company"], rid))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Informe no encontrado en esta empresa")
    return row


def clean_fields(values):
    if set(values) - FIELDS.keys():
        raise HTTPException(422, "El informe contiene campos no permitidos")
    result = {}
    for key, value in values.items():
        if key in BOOLEAN_FIELDS:
            if type(value) is not bool:
                raise HTTPException(422, f"{key}: seleccione si o no")
        elif value is not None:
            if not isinstance(value, str) or len(value) > (30000 if FIELDS[key]["type"] == "textarea" else 2000):
                raise HTTPException(422, f"{key}: valor invalido o demasiado largo")
            if "\x00" in value:
                raise HTTPException(422, f"{key}: caracter no permitido")
            if key in DATE_FIELDS:
                try:
                    parsed = datetime.fromisoformat(value) if value else None
                    if parsed and parsed.tzinfo:
                        raise ValueError("Business dates must not include an implicit timezone conversion")
                    value = parsed.isoformat(sep=" ", timespec="minutes" if parsed.second == 0 else "seconds") if parsed else None
                except ValueError:
                    raise HTTPException(422, f"{key}: fecha y hora invalidas")
        result[key] = value
    return result


def linked_service(cur, number, ctx):
    if not number or not str(number).strip():
        raise HTTPException(422, "Seleccione un servicio con numero de informe")
    cur.execute("SELECT company_code FROM servicios WHERE num_informe=%s FOR SHARE", (number,))
    rows = cur.fetchall()
    if len(rows) != 1 or company_code(rows[0]["company_code"]) != ctx["company"]:
        raise HTTPException(422, "El servicio no existe en esta empresa o su numero es ambiguo")


class SaveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fields: dict
    version: str | None = None
    submit: bool = False


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    status: Literal["Approved", "Rejected"]


class AIInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=30000)
    container_no: str = Field(default="", max_length=2000)
    cargo: str = Field(default="", max_length=30000)
    location: str = Field(default="", max_length=2000)
    condition: str = Field(default="", max_length=30000)


@router.get("/assets/{name}")
def asset(name: Literal["containers.js", "containers.css"]):
    return FileResponse(ASSETS / name, media_type="text/javascript" if name.endswith("js") else "text/css")


@router.get("/bootstrap")
def bootstrap(ctx=Depends(access)):
    return {"sections": SECTIONS, "permissions": ctx["permissions"], "company": ctx["company"]}


@router.get("/services")
def services(q: str = Query(default="", max_length=150), offset: int = Query(default=0, ge=0),
             ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT num_informe,cliente,buque_contenedor,puerto,contacto,detalle,fecha_inicio
            FROM servicios WHERE COALESCE(NULLIF(TRIM(company_code),''),'MSL-CR')=%s
            AND NULLIF(TRIM(num_informe),'') IS NOT NULL
            AND (%s='' OR CONCAT_WS(' ',num_informe,cliente,buque_contenedor) ILIKE %s)
            ORDER BY fecha_inicio DESC NULLS LAST, num_informe LIMIT 51 OFFSET %s""",
            (ctx["company"], q, "%" + q + "%", offset))
        rows = cur.fetchall()
    return {"data": rows[:50], "more": len(rows) > 50}


@router.get("")
def listing(q: str = Query(default="", max_length=150), status: str = Query(default="", max_length=50),
            offset: int = Query(default=0, ge=0), ctx=Depends(access), conn=Depends(get_db)):
    where = REPORT_SOURCE + """ AND (%s='' OR CONCAT_WS(' ',cr.linked_report_number,cr.report_no,
        cr.vessel,cr.\"user\",s.customer) ILIKE %s)
        AND (%s='' OR cr.status=%s OR (%s='Pending for review' AND cr.status='Pending review'))"""
    params = (ctx["company"], q, "%" + q + "%", status, status, status)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS total " + where, params)
        total = cur.fetchone()["total"]
        cur.execute('SELECT cr.id,cr.linked_report_number,cr.report_no,cr.vessel,cr."user",cr.status,cr.created_at,s.customer '
                    + where + " ORDER BY cr.id DESC LIMIT 50 OFFSET %s", (*params, offset))
        rows = cur.fetchall()
    return {"data": rows, "total": total}


@router.post("/improve")
def improve(body: AIInput, ctx=Depends(access)):
    if not (ctx["permissions"]["edit"] or ctx["permissions"]["create"]):
        raise HTTPException(403, "Sin permiso para editar Informes")
    try:
        from ai.maritime_ai import improve_container_text
        return {"text": improve_container_text(user_text=body.text, container_no=body.container_no,
                    cargo=body.cargo, location=body.location, condition=body.condition)}
    except Exception:
        log.exception("Containers AI unavailable")
        raise HTTPException(503, "PORTIA no esta disponible. El texto original se conserva.")


@router.get("/{rid}")
def detail(rid: int, ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        row = read_report(cur, rid, ctx)
    return {"data": row, "version": version(row)}


@router.post("")
def create(body: SaveInput, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, "create")
    values = clean_fields(body.fields)
    for key in BOOLEAN_FIELDS:
        values.setdefault(key, False)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            linked_service(cur, values.get("linked_report_number"), ctx)
            cur.execute("""SELECT EXISTS(SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='container_reports'
                AND column_name='company_code') AS present""")
            if cur.fetchone()["present"]:
                values["company_code"] = ctx["company"]
            values.update(user=ctx["user"],
                          status="Pending for review" if body.submit else "draft",
                          created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            columns = ','.join('"' + k + '"' for k in values)
            cur.execute(f"INSERT INTO container_reports ({columns}) VALUES ({','.join(['%s'] * len(values))}) RETURNING *",
                        tuple(values.values()))
            row = cur.fetchone()
            cur.execute("""UPDATE servicios SET status_informe='Generated' WHERE num_informe=%s
                AND COALESCE(NULLIF(TRIM(company_code),''),'MSL-CR')=%s AND status_informe='Pending'""",
                (values["linked_report_number"], ctx["company"]))
        conn.commit()
        return {"data": row, "version": version(row)}
    except (DataError, IntegrityError):
        conn.rollback()
        raise HTTPException(422, "Revise los datos: un campo supera el formato o limite permitido")
    except Exception:
        conn.rollback()
        raise


@router.patch("/{rid}")
def update(rid: int, body: SaveInput, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, "edit")
    values = clean_fields(body.fields)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = read_report(cur, rid, ctx, lock=True)
            if body.version != version(row):
                raise HTTPException(409, "El informe cambio en otra sesion. Conserve su borrador y vuelva a abrirlo.")
            if row.get("status") == "Approved":
                raise HTTPException(409, "Informe aprobado: un administrador debe rechazarlo antes de editar")
            if "linked_report_number" in values and values["linked_report_number"] != row.get("linked_report_number"):
                raise HTTPException(422, "No se puede cambiar el servicio de un informe existente")
            if body.submit:
                values["status"] = "Pending for review"
            values["updated_at"] = datetime.utcnow()
            cur.execute("UPDATE container_reports SET " + ','.join('"' + k + '"=%s' for k in values)
                        + " WHERE id=%s RETURNING *", (*values.values(), rid))
            result = cur.fetchone()
        conn.commit()
        return {"data": result, "version": version(result)}
    except (DataError, IntegrityError):
        conn.rollback()
        raise HTTPException(422, "Revise los datos: un campo supera el formato o limite permitido")
    except Exception:
        conn.rollback()
        raise


@router.post("/{rid}/status")
def change_status(rid: int, body: StatusInput, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, "approve")
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = read_report(cur, rid, ctx, lock=True)
            if body.version != version(row):
                raise HTTPException(409, "El informe cambio. Vuelva a abrirlo antes de revisar.")
            if body.status == "Approved" and row.get("status") not in ("Pending for review", "Pending review"):
                raise HTTPException(409, "Solo se aprueban informes enviados a revision")
            cur.execute("UPDATE container_reports SET status=%s,updated_at=%s WHERE id=%s RETURNING *",
                        (body.status, datetime.utcnow(), rid))
            result = cur.fetchone()
        conn.commit()
        return {"data": result, "version": version(result)}
    except Exception:
        conn.rollback()
        raise


@router.get("/{rid}/export/{kind}")
def export(rid: int, kind: Literal["excel", "pdf", "presentation", "unified"],
           ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        row = dict(read_report(cur, rid, ctx))
        cur.execute("""SELECT MIN(cliente) AS customer FROM servicios WHERE num_informe=%s
            AND COALESCE(NULLIF(TRIM(company_code),''),'MSL-CR')=%s""",
            (row.get("linked_report_number"), ctx["company"]))
        customer = cur.fetchone()["customer"]
    try:
        from services.container_web_export import build
        row["company_code"] = ctx["company"]
        content = build(row, customer, kind)
        filename = f"Container_{rid}_{kind}." + ("xlsx" if kind == "excel" else "pdf")
        return Response(content, headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if kind == "excel" else "application/pdf")
    except Exception:
        log.exception("Container export failed: %s / %s", rid, kind)
        raise HTTPException(503, "No se pudo generar el documento. El informe guardado no ha cambiado.")
