"""Web-only certificate API. Desktop routes, payloads and templates are unchanged."""
from datetime import datetime
import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict
from psycopg2 import DataError, IntegrityError
from psycopg2.extras import RealDictCursor

from database import get_db
from routers.container_web import access, require, version, linked_service
from services.certificate_web_fields import TYPES

router = APIRouter(prefix="/informes/certificates", tags=["Certificates Web"])
ASSETS = Path(__file__).resolve().parents[1] / "assets" / "certificates"
log = logging.getLogger(__name__)


def specification(kind):
    if kind not in TYPES:
        raise HTTPException(404, "Tipo de certificado no encontrado")
    return TYPES[kind]


def source(spec):
    # No company exists on the legacy tables. A unique company through Services
    # is required; orphaned or cross-company ambiguous certificates fail closed.
    return f"""FROM {spec['table']} c JOIN LATERAL (
        SELECT MIN(COALESCE(NULLIF(TRIM(company_code),''),'MSL-CR')) AS company,
        COUNT(DISTINCT COALESCE(NULLIF(TRIM(company_code),''),'MSL-CR')) AS companies,
        MIN(cliente) AS customer
        FROM servicios WHERE num_informe=c.{spec['number']}
    ) s ON s.companies=1 WHERE s.company=%s"""


def read_record(cur, spec, rid, ctx, lock=False):
    cur.execute("SELECT c.* " + source(spec) + " AND c.id=%s" + (" FOR UPDATE OF c" if lock else ""),
                (ctx["company"], rid))
    row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Certificado no encontrado en esta empresa")
    return row


def clean_fields(spec, values):
    if set(values) - spec["fields"].keys():
        raise HTTPException(422, "El certificado contiene campos no permitidos")
    result = {}
    for key, value in values.items():
        field = spec["fields"][key]
        if value is not None:
            if not isinstance(value, str) or "\x00" in value or len(value) > (30000 if field["type"] == "textarea" else 2000):
                raise HTTPException(422, f"{field['label']}: valor invalido o demasiado largo")
            value = value.strip() or None
        if value and field["type"] in ("date", "time"):
            formats = ("%d/%m/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d, %Y") if field["type"] == "date" else ("%H:%M", "%H:%M:%S")
            parsed = None
            for fmt in formats:
                try:
                    parsed = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    pass
            if parsed is None:
                raise HTTPException(422, f"{field['label']}: use DD/MM/YYYY" if field["type"] == "date" else f"{field['label']}: use HH:MM")
            # Desktop holds form splits times into exactly two components.
            value = parsed.strftime("%Y-%m-%d" if field["type"] == "date" else "%H:%M")
        result[key] = value
    return result


class SaveInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fields: dict
    version: str | None = None
    submit: bool = False


class StatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str
    status: Literal["Approved", "Rejected"]


@router.get("/assets/{name}")
def asset(name: Literal["certificates.js", "certificates.css"]):
    return FileResponse(ASSETS / name, media_type="text/javascript" if name.endswith(".js") else "text/css")


@router.get("/bootstrap")
def bootstrap(ctx=Depends(access)):
    return {"types": {key: {k: spec[k] for k in ("title", "label", "number", "document", "sections")}
                      for key, spec in TYPES.items()}, "permissions": ctx["permissions"], "company": ctx["company"]}


@router.get("/services")
def services(q: str = Query("", max_length=150), offset: int = Query(0, ge=0),
             ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT num_informe,cliente,buque_contenedor,continente,pais,puerto,operacion,fecha_inicio
            FROM servicios WHERE COALESCE(NULLIF(TRIM(company_code),''),'MSL-CR')=%s
            AND NULLIF(TRIM(num_informe),'') IS NOT NULL
            AND (%s='' OR CONCAT_WS(' ',num_informe,cliente,buque_contenedor) ILIKE %s)
            ORDER BY fecha_inicio DESC NULLS LAST,num_informe LIMIT 51 OFFSET %s""",
            (ctx["company"], q, "%" + q + "%", offset))
        rows = cur.fetchall()
    return {"data": rows[:50], "more": len(rows) > 50}


@router.get("/{kind}")
def listing(kind: str, q: str = Query("", max_length=150), status: str = Query("", max_length=50),
            offset: int = Query(0, ge=0), ctx=Depends(access), conn=Depends(get_db)):
    spec = specification(kind)
    vessel = "flat_rack_container" if kind == "lashing" else "vessel"
    where = source(spec) + f""" AND (%s='' OR CONCAT_WS(' ',c.{spec['number']},c.{vessel},s.customer) ILIKE %s)
        AND (%s='' OR LOWER(c.status)=LOWER(%s))"""
    params = (ctx["company"], q, "%" + q + "%", status, status)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS total " + where, params)
        total = cur.fetchone()["total"]
        cur.execute(f"SELECT c.id,c.{spec['number']} AS report_number,c.{vessel} AS vessel,c.status,c.date,s.customer "
                    + where + " ORDER BY c.id DESC LIMIT 50 OFFSET %s", (*params, offset))
        rows = cur.fetchall()
    return {"data": rows, "total": total}


@router.get("/{kind}/{rid}")
def detail(kind: str, rid: int, ctx=Depends(access), conn=Depends(get_db)):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        row = read_record(cur, specification(kind), rid, ctx)
    return {"data": row, "version": version(row)}


@router.post("/{kind}")
def create(kind: str, body: SaveInput, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, "create")
    spec = specification(kind)
    values = clean_fields(spec, body.fields)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            linked_service(cur, values.get(spec["number"]), ctx)
            values.update(status="Pending for review" if body.submit else "Draft",
                          created_at=datetime.utcnow(), updated_at=datetime.utcnow())
            cur.execute(f"INSERT INTO {spec['table']} (" + ",".join('"' + k + '"' for k in values)
                        + ") VALUES (" + ",".join(["%s"] * len(values)) + ") RETURNING *", tuple(values.values()))
            row = cur.fetchone()
        conn.commit()
        return {"data": row, "version": version(row)}
    except (DataError, IntegrityError):
        conn.rollback()
        raise HTTPException(422, "Revise el formato de los datos del certificado")
    except Exception:
        conn.rollback()
        raise


@router.patch("/{kind}/{rid}")
def update(kind: str, rid: int, body: SaveInput, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, "edit")
    spec = specification(kind)
    values = clean_fields(spec, body.fields)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = read_record(cur, spec, rid, ctx, True)
            if body.version != version(row):
                raise HTTPException(409, "El certificado cambio en otra sesion. Conserve su borrador y vuelva a abrirlo.")
            if row.get("status") == "Approved":
                raise HTTPException(409, "Un administrador debe rechazar el certificado aprobado antes de editarlo")
            if spec["number"] in values and values[spec["number"]] != row.get(spec["number"]):
                raise HTTPException(422, "No se puede cambiar el servicio del certificado")
            # Editing a submitted/rejected record requires a fresh review.
            values.update(updated_at=datetime.utcnow(), status="Pending for review" if body.submit else "Draft")
            cur.execute(f"UPDATE {spec['table']} SET " + ",".join('"' + k + '"=%s' for k in values)
                        + " WHERE id=%s RETURNING *", (*values.values(), rid))
            result = cur.fetchone()
        conn.commit()
        return {"data": result, "version": version(result)}
    except (DataError, IntegrityError):
        conn.rollback()
        raise HTTPException(422, "Revise el formato de los datos del certificado")
    except Exception:
        conn.rollback()
        raise


@router.post("/{kind}/{rid}/status")
def change_status(kind: str, rid: int, body: StatusInput, ctx=Depends(access), conn=Depends(get_db)):
    require(ctx, "approve")
    spec = specification(kind)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            row = read_record(cur, spec, rid, ctx, True)
            if body.version != version(row):
                raise HTTPException(409, "El certificado cambio. Vuelva a abrirlo antes de revisar.")
            if body.status == "Approved" and row.get("status") not in ("Pending for review", "Pending review", "Draft"):
                raise HTTPException(409, "Envie el certificado a revision antes de aprobar")
            cur.execute(f"UPDATE {spec['table']} SET status=%s,updated_at=%s WHERE id=%s RETURNING *",
                        (body.status, datetime.utcnow(), rid))
            row = cur.fetchone()
        conn.commit()
        return {"data": row, "version": version(row)}
    except Exception:
        conn.rollback()
        raise


@router.get("/{kind}/{rid}/export/{format}")
def export(kind: str, rid: int, format: Literal["word", "excel", "pdf"], ctx=Depends(access), conn=Depends(get_db)):
    spec = specification(kind)
    if format not in (spec["document"], "pdf"):
        raise HTTPException(422, "Formato no disponible para este certificado")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        row = dict(read_record(cur, spec, rid, ctx))
    try:
        from services.certificate_web_export import build
        row["company_code"] = ctx["company"]
        content = build(kind, row, format)
        ext, mime = {"word": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                     "excel": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                     "pdf": ("pdf", "application/pdf")}[format]
        return Response(content, media_type=mime,
                        headers={"Content-Disposition": f'attachment; filename="Certificate_{kind}_{rid}.{ext}"'})
    except Exception:
        log.exception("Certificate export failed: %s / %s / %s", kind, rid, format)
        raise HTTPException(503, "No se pudo generar el documento. El certificado guardado no ha cambiado.")
