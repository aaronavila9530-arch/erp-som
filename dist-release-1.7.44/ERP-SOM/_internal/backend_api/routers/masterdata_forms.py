from __future__ import annotations

import io
import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse


router = APIRouter(prefix="/master-data/forms", tags=["Master Data - Forms"])


@dataclass(frozen=True)
class FormSpec:
    key: str
    label: str
    fields: tuple[str, ...]


SPECS = {
    "clientes": FormSpec("clientes", "Cliente", ("NombreJuridico", "NombreComercial", "Pais", "Correo", "Telefono", "CedulaJuridicaVAT", "Comentarios", "Provincia", "Canton", "Distrito", "DireccionExacta", "FechaDePago", "Prefijo", "ContactoPrincipal", "ContactoSecundario")),
    "proveedores": FormSpec("proveedores", "Proveedor", ("Nombre", "Apellidos", "NombreComercial", "Cedula", "Pais", "Provincia", "Canton", "Distrito", "DireccionExacta", "Prefijo", "Telefono", "Correo", "TerminosPago", "Banco", "CuentaIBAN", "SwiftCode", "UID", "DireccionBanco", "TipoProveeduria", "Comentarios", "Activo")),
    "empleados": FormSpec("empleados", "Empleado", ("nombre", "apellidos", "estado_civil", "genero", "nacionalidad", "prefijo", "telefono", "provincia", "canton", "distrito", "direccion", "jornada", "salario", "fecha_ingreso", "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo", "tarifa_hora_extra", "pago_minimo_garantizado", "pago", "banco", "cuenta_iban", "moneda", "enfermedades", "contacto_emergencia", "telefono_emergencia", "activo1", "marca1", "serial1", "activo2", "marca2", "serial2", "activo3", "marca3", "serial3", "activo")),
    "surveyores": FormSpec("surveyores", "Surveyor", ("nombre", "apellidos", "email", "estado_civil", "genero", "nacionalidad", "prefijo", "telefono", "provincia", "canton", "distrito", "direccion", "jornada", "operacion", "honorario", "pago", "banco", "direccion_banco", "cuenta_iban", "moneda", "swift", "uid", "enfermedades", "contacto_emergencia", "telefono_emergencia", "puerto", "activo")),
    "servicios-md": FormSpec("servicios-md", "Servicio", ("codigo_prod", "nombre", "costo")),
}

ALIASES = {
    "cliente": "clientes",
    "clientes": "clientes",
    "proveedor": "proveedores",
    "proveedores": "proveedores",
    "empleado": "empleados",
    "empleados": "empleados",
    "surveyor": "surveyores",
    "surveyores": "surveyores",
    "servicio": "servicios-md",
    "servicios": "servicios-md",
    "servicios_md": "servicios-md",
    "servicios-md": "servicios-md",
}


LABELS = {
    "nombre": "Nombre / First name",
    "apellidos": "Apellidos / Last name",
    "Nombre": "Nombre / First name",
    "Apellidos": "Apellidos / Last name",
    "NombreJuridico": "Nombre juridico / Legal name",
    "NombreComercial": "Nombre comercial / Trade name",
    "Pais": "Pais / Country",
    "Correo": "Correo electronico / Email",
    "Telefono": "Telefono / Phone",
    "CedulaJuridicaVAT": "Cedula juridica o VAT / Tax ID or VAT",
    "Comentarios": "Comentarios / Notes",
    "Provincia": "Provincia / Province",
    "Canton": "Canton / County",
    "Distrito": "Distrito / District",
    "DireccionExacta": "Direccion exacta / Full address",
    "FechaDePago": "Fecha de pago / Payment date",
    "Prefijo": "Prefijo telefonico / Phone prefix",
    "ContactoPrincipal": "Contacto principal / Main contact",
    "ContactoSecundario": "Contacto secundario / Secondary contact",
    "Cedula": "Cedula / ID",
    "TerminosPago": "Terminos de pago / Payment terms",
    "Banco": "Banco / Bank",
    "CuentaIBAN": "Cuenta IBAN / IBAN account",
    "SwiftCode": "Swift Code / Swift code",
    "UID": "UID",
    "DireccionBanco": "Direccion banco / Bank address",
    "TipoProveeduria": "Tipo de proveeduria / Supplier type",
    "Activo": "Activo / Active",
    "email": "Correo electronico / Email",
    "estado_civil": "Estado civil / Marital status",
    "genero": "Genero / Gender",
    "nacionalidad": "Nacionalidad / Nationality",
    "prefijo": "Prefijo telefonico / Phone prefix",
    "telefono": "Telefono / Phone",
    "provincia": "Provincia / Province",
    "canton": "Canton / County",
    "distrito": "Distrito / District",
    "direccion": "Direccion / Address",
    "jornada": "Jornada / Work schedule",
    "salario": "Salario / Salary",
    "fecha_ingreso": "Fecha ingreso / Start date",
    "horas_contratadas": "Horas pactadas / Contracted hours",
    "horas_tope_ordinario": "Primer aviso / Regular hours cap",
    "horas_tope_maximo": "Segundo aviso / Maximum hours cap",
    "tarifa_hora_extra": "Tarifa hora extra / Overtime rate",
    "pago_minimo_garantizado": "Pago minimo garantizado / Guaranteed minimum pay",
    "pago": "Forma de pago / Payment method",
    "banco": "Banco / Bank",
    "cuenta_iban": "Cuenta IBAN / IBAN account",
    "moneda": "Moneda / Currency",
    "enfermedades": "Enfermedades / Medical conditions",
    "contacto_emergencia": "Contacto emergencia / Emergency contact",
    "telefono_emergencia": "Telefono emergencia / Emergency phone",
    "activo1": "Activo asignado 1 / Assigned asset 1",
    "marca1": "Marca 1 / Brand 1",
    "serial1": "Serial 1",
    "activo2": "Activo asignado 2 / Assigned asset 2",
    "marca2": "Marca 2 / Brand 2",
    "serial2": "Serial 2",
    "activo3": "Activo asignado 3 / Assigned asset 3",
    "marca3": "Marca 3 / Brand 3",
    "serial3": "Serial 3",
    "activo": "Activo / Active",
    "operacion": "Operacion / Operation",
    "honorario": "Honorario / Fee",
    "direccion_banco": "Direccion banco / Bank address",
    "swift": "Swift Code / Swift code",
    "uid": "UID",
    "puerto": "Puerto / Port",
    "codigo_prod": "Codigo producto / Product code",
    "costo": "Costo / Cost",
}

LABEL_TO_FIELD = {label.strip().lower(): field for field, label in LABELS.items()}

UPLOAD_SPECS = {
    "cliente": {
        "label": "Cliente",
        "code_field": "Codigo",
        "fields": SPECS["clientes"].fields,
        "required": ("NombreJuridico", "Pais"),
    },
    "proveedor": {
        "label": "Proveedor",
        "code_field": "Codigo",
        "fields": SPECS["proveedores"].fields,
        "required": ("Nombre", "Pais"),
    },
    "empleado": {
        "label": "Empleado",
        "code_field": "codigo",
        "fields": SPECS["empleados"].fields,
        "required": ("nombre", "apellidos"),
    },
    "surveyor": {
        "label": "Surveyor",
        "code_field": "codigo",
        "fields": SPECS["surveyores"].fields,
        "required": ("nombre", "apellidos", "pais_o_nacionalidad"),
    },
    "servicio": {
        "label": "Servicio",
        "code_field": "codigo",
        "fields": SPECS["servicios-md"].fields,
        "required": ("nombre",),
    },
}


def _spec(entity_key: str) -> FormSpec:
    spec = SPECS.get(ALIASES.get(str(entity_key or "").strip().lower(), entity_key))
    if not spec:
        raise HTTPException(status_code=400, detail="Tipo de formulario no soportado")
    return spec


def _next_code(entity: str, company: str) -> str | None:
    import database
    from services.tenanting import company_prefix

    table_suffix = {
        "cliente": ("cliente", "C"),
        "proveedor": ("proveedor", "P"),
        "surveyor": ("surveyor", "S"),
    }.get(entity)
    if not table_suffix:
        return None
    table, suffix = table_suffix
    prefix = company_prefix(company)
    rows = database.sql(
        f"""
        SELECT MAX(CAST(SUBSTRING(codigo FROM 5 FOR 4) AS INTEGER))
        FROM {table}
        WHERE company_code = %s
          AND codigo LIKE %s
        """,
        (company, f"{prefix}-%-{suffix}"),
        fetch=True,
    )
    ultimo = rows[0][0] if rows and rows[0][0] is not None else 0
    return f"{prefix}-{int(ultimo) + 1:04d}-{suffix}"


def _normalize_upload_entity(entity: str) -> str:
    value = str(entity or "").strip().lower()
    if value in {"clientes", "cliente"}:
        return "cliente"
    if value in {"proveedores", "proveedor"}:
        return "proveedor"
    if value in {"empleados", "empleado"}:
        return "empleado"
    if value in {"surveyores", "surveyor"}:
        return "surveyor"
    if value in {"servicio", "servicios", "servicios-md", "servicios_md"}:
        return "servicio"
    return value


def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _clean_number(value: Any) -> str:
    return _clean_value(value).replace(",", "")


def _format_date(value: Any) -> str:
    text = _clean_value(value)
    if not text:
        return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except Exception:
            continue
    return text


def _normalize_import_key(value: Any) -> str:
    text = _clean_value(value)
    match = re.search(r"\(([^()]+)\)\s*$", text)
    if match:
        text = match.group(1)
    return text.strip()


def _field_from_header(value: Any, spec: dict | None = None) -> str:
    text = _normalize_import_key(value)
    fields = set(spec["fields"]) if spec else None
    if fields and text in fields:
        return text
    candidates = fields or set(LABELS)
    exact = [field for field in candidates if LABELS.get(field, field).casefold() == text.casefold()]
    if len(exact) == 1:
        return exact[0]
    # A bilingual heading may have an edited half; accept only an unambiguous match.
    parts = {part.strip().casefold() for part in text.split("/") if part.strip()}
    matches = [field for field in candidates if parts.intersection(
        part.strip().casefold() for part in LABELS.get(field, field).split("/"))]
    if len(matches) == 1:
        return matches[0]
    return text


def _infer_upload_spec(text: str, fields: list[str]) -> tuple[str, dict] | tuple[None, None]:
    haystack = f"{text} {' '.join(fields)}".lower()
    for key, spec in UPLOAD_SPECS.items():
        if key in haystack or spec["label"].lower() in haystack:
            return key, spec
    for key, spec in UPLOAD_SPECS.items():
        if sum(1 for field in fields if field in spec["fields"]) >= 3:
            return key, spec
    return None, None


def _clean_record(entity: str, data: dict[str, Any]) -> dict[str, Any]:
    spec = UPLOAD_SPECS[entity]
    cleaned = {field: _clean_value(data.get(field)) for field in spec["fields"]}
    if entity == "cliente":
        cleaned["FechaDePago"] = _format_date(cleaned.get("FechaDePago"))
    elif entity in {"surveyor", "empleado"}:
        for field in ("honorario", "salario", "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo", "tarifa_hora_extra"):
            if cleaned.get(field):
                cleaned[field] = _clean_number(cleaned[field])
    return cleaned


def _validate_upload_record(entity: str, data: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in UPLOAD_SPECS[entity]["required"]:
        if field == "pais_o_nacionalidad":
            if not (data.get("nacionalidad") or data.get("Pais") or data.get("pais")):
                missing.append("nacionalidad/pais")
            continue
        if not data.get(field):
            missing.append(field)
    return missing


def _read_xlsx_upload(path: Path) -> list[dict[str, Any]]:
    from openpyxl import load_workbook

    wb = load_workbook(path, data_only=True)
    records: list[dict[str, Any]] = []
    for ws in wb.worksheets:
        entity, spec = _infer_upload_spec(ws.title, [])
        header_row = None
        headers: list[str] = []
        for row_idx in range(1, min(ws.max_row, 20) + 1):
            row_values = [_field_from_header(ws.cell(row_idx, col).value, spec) for col in range(1, ws.max_column + 1)]
            row_keys = [value for value in row_values if value]
            inferred_entity, inferred_spec = _infer_upload_spec(ws.title, row_keys)
            if inferred_entity and inferred_spec:
                entity, spec = inferred_entity, inferred_spec
            if spec and sum(1 for header in row_values if header in spec["fields"]) >= 2:
                header_row = row_idx
                headers = row_values
                break
        if not entity or not spec or not header_row:
            records.append({"file": str(path), "entity": ws.title, "data": {}, "error": "No se pudo identificar el formulario"})
            continue
        for row_idx in range(header_row + 1, ws.max_row + 1):
            data = {}
            has_value = False
            for col_idx, field in enumerate(headers, start=1):
                if field not in spec["fields"]:
                    continue
                value = ws.cell(row_idx, col_idx).value
                if _clean_value(value):
                    has_value = True
                data[field] = value
            if all(_clean_value(data.get(field)) == LABELS.get(field, field) for field in data):
                continue
            if has_value:
                records.append({"file": str(path), "entity": entity, "data": _clean_record(entity, data), "error": ""})
    return records


def _read_docx_upload(path: Path) -> list[dict[str, Any]]:
    from docx import Document

    doc = Document(str(path))
    title_text = "\n".join(p.text for p in doc.paragraphs[:8])
    table_fields: dict[str, Any] = {}
    for table in doc.tables:
        for row in table.rows[1:]:
            cells = row.cells
            if len(cells) >= 3:
                field = _normalize_import_key(cells[2].text)
                value = cells[1].text
            elif len(cells) >= 2:
                field = cells[0].text
                value = cells[1].text
            else:
                continue
            if field:
                table_fields[field] = value
    entity, spec = _infer_upload_spec(title_text, list(table_fields))
    if not entity or not spec:
        return [{"file": str(path), "entity": "", "data": {}, "error": "No se pudo identificar el formulario"}]
    table_fields = {_field_from_header(field, spec): value for field, value in table_fields.items()}
    return [{"file": str(path), "entity": entity, "data": _clean_record(entity, table_fields), "error": ""}]


def _import_masterdata_files(paths: list[Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in paths:
        suffix = path.suffix.lower()
        try:
            if suffix == ".xlsx":
                records.extend(_read_xlsx_upload(path))
            elif suffix == ".docx":
                records.extend(_read_docx_upload(path))
            else:
                raise ValueError("Formato no soportado")
        except Exception:
            records.append({"file": str(path), "entity": "", "data": {}, "error":
                "No se pudo leer el archivo. Compruebe que sea un Excel o Word valido, "
                "sin contrasena y descargado completamente de OneDrive."})
    return records


def _save_masterdata_record(entity: str, data: dict, company: str) -> str:
    from routers.clientes import add_cliente, update_cliente
    from routers.empleados import Empleado, agregar_empleado, update_empleado
    from routers.proveedores import add_proveedor, update_proveedor
    from routers.servicios_md import add_servicio, update_servicio
    from routers.surveyores import add_surveyor, update_surveyor

    entity = _normalize_upload_entity(entity)
    spec = UPLOAD_SPECS.get(entity)
    if not spec:
        raise ValueError(f"Tipo de formulario no soportado: {entity}")
    payload = dict(data or {})
    payload["company_code"] = company

    code_field = spec["code_field"]
    if not str(payload.get(code_field) or "").strip():
        if entity == "empleado":
            payload.pop("codigo", None)
        else:
            code = _next_code(entity, company)
            if code:
                payload[code_field] = code

    missing = _validate_upload_record(entity, payload)
    if missing:
        raise ValueError("Faltan campos requeridos: " + ", ".join(missing))

    adders = {
        "cliente": lambda p: add_cliente(p, x_company_code=company),
        "proveedor": lambda p: add_proveedor(p, x_company_code=company),
        "empleado": lambda p: agregar_empleado(Empleado(**p), x_company_code=company),
        "surveyor": lambda p: add_surveyor(p, x_company_code=company),
        "servicio": lambda p: add_servicio(p, x_company_code=company),
    }
    updaters = {
        "cliente": lambda p: update_cliente(p, x_company_code=company),
        "proveedor": lambda p: update_proveedor(p, x_company_code=company),
        "empleado": lambda p: update_empleado(p, x_company_code=company),
        "surveyor": lambda p: update_surveyor(p, x_company_code=company),
        "servicio": lambda p: update_servicio(p, x_company_code=company),
    }
    try:
        adders[entity](payload)
        return "created"
    except Exception:
        if not str(payload.get(code_field) or "").strip():
            raise
        updaters[entity](payload)
        return "updated"


def _filename(spec: FormSpec, suffix: str) -> str:
    return f"Formulario_MasterData_{spec.label}.{suffix}"


def _excel(spec: FormSpec) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = spec.label
    ws["A1"] = "Formulario Master Data / Master Data Form"
    ws["A2"] = spec.label
    ws.append([])
    ws.append(list(spec.fields))
    ws.append([LABELS.get(field, field) for field in spec.fields])
    for row in (4, 5):
        for cell in ws[row]:
            cell.font = Font(bold=row == 4)
            if row == 4:
                cell.fill = PatternFill("solid", fgColor="D9EAF7")
    for column_cells in ws.columns:
        ws.column_dimensions[column_cells[0].column_letter].width = min(max(len(str(cell.value or "")) for cell in column_cells) + 2, 38)
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


def _word(spec: FormSpec) -> bytes:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    doc.add_heading("Formulario Master Data / Master Data Form", level=1)
    doc.add_paragraph(spec.label)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    header = table.rows[0].cells
    header[0].text = "Campo / Field"
    header[1].text = "Valor / Value"
    for cell in header:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(10)
    for field in spec.fields:
        cells = table.add_row().cells
        cells[0].text = LABELS.get(field, field)
        cells[1].text = ""
    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()


@router.get("/{entity_key}/{fmt}")
def download_masterdata_form(entity_key: str, fmt: str):
    spec = _spec(entity_key)
    fmt = fmt.lower().strip()
    if fmt in {"excel", "xlsx"}:
        content = _excel(spec)
        suffix = "xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif fmt in {"word", "docx"}:
        content = _word(spec)
        suffix = "docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise HTTPException(status_code=400, detail="Formato no soportado. Use word o excel.")
    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{_filename(spec, suffix)}"'},
    )


@router.post("/upload")
async def upload_masterdata_forms(
    files: list[UploadFile] = File(...),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    from services.tenanting import company_code

    company = company_code(header_value=x_company_code)
    created = 0
    updated = 0
    failed: list[dict] = []
    imported: list[dict] = []
    temp_paths: list[Path] = []
    filenames: dict[str, str] = {}
    try:
        for upload in files:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in {".xlsx", ".docx"}:
                failed.append({"file": upload.filename, "error": "Formato no soportado"})
                continue
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(await upload.read())
                temp_paths.append(Path(tmp.name))
                filenames[tmp.name] = upload.filename or "Formulario"
        if temp_paths:
            imported = _import_masterdata_files(temp_paths)
        for idx, record in enumerate(imported, start=1):
            record["file"] = filenames.get(record.get("file"), "Formulario")
            if record.get("error"):
                failed.append({"index": idx, "file": record.get("file"), "error": record.get("error")})
                continue
            try:
                status = _save_masterdata_record(record.get("entity"), record.get("data") or {}, company)
                if status == "updated":
                    updated += 1
                else:
                    created += 1
            except Exception as exc:
                failed.append({"index": idx, "file": record.get("file"), "entity": record.get("entity"), "error": str(exc)})
    finally:
        for path in temp_paths:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
    return {
        "created": created,
        "updated": updated,
        "failed": failed,
        "total": created + updated + len(failed),
    }
