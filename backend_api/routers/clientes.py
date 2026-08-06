# backend_api/routers/clientes.py
from fastapi import APIRouter, HTTPException
import database
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from rbac_service import has_permission
from datetime import date, datetime
from services.tenanting import company_code, company_prefix, ensure_company_column, set_payload_company

router = APIRouter(prefix="/clientes", tags=["Clientes"])


def _ensure_tenant_schema():
    ensure_company_column("cliente")


def _normalize_fecha_pago(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    normalized = " ".join(text.replace(",", " ").split())
    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%b %d %Y",
        "%B %d %Y",
    ):
        try:
            return datetime.strptime(normalized, fmt).date()
        except Exception:
            continue

    try:
        return datetime.fromisoformat(text[:10]).date()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"FechaDePago invalida: {value}"
        )

def require_permission(module: str, action: str):
    def checker(
        x_user_role: str = Header(..., alias="X-User-Role")
    ):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(
                status_code=403,
                detail="No autorizado"
            )
    return checker



@router.post("/add")
def add_cliente(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(data.get("company_code"), x_company_code)
    data = set_payload_company(data, company)
    data["FechaDePago"] = _normalize_fecha_pago(data.get("FechaDePago"))
    sql = """
        INSERT INTO cliente (
            company_code,
            codigo,
            nombrejuridico,
            nombrecomercial,
            pais,
            correo,
            telefono,
            cedulajuridicavat,
            actividad_economica,
            comentarios,
            provincia,
            canton,
            distrito,
            direccionexacta,
            fecha_pago,
            prefijo,
            contacto_principal,
            contacto_secundario
        )
        VALUES (
            %(company_code)s,
            %(Codigo)s,
            %(NombreJuridico)s,
            %(NombreComercial)s,
            %(Pais)s,
            %(Correo)s,
            %(Telefono)s,
            %(CedulaJuridicaVAT)s,
            '' , -- valor temporal
            %(Comentarios)s,
            %(Provincia)s,
            %(Canton)s,
            %(Distrito)s,
            %(DireccionExacta)s,
            %(FechaDePago)s,
            %(Prefijo)s,
            %(ContactoPrincipal)s,
            %(ContactoSecundario)s
        )
    """
    try:
        database.sql(sql, data)
        return {"status": "OK", "msg": "Cliente registrado 💾✔"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# OBTENER ÚLTIMO CÓDIGO CORRELATIVO  ✅ MOVER ARRIBA
# ============================================================
@router.get("/ultimo")
def get_ultimo_cliente(
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    prefix = company_prefix(company)
    sql = """
        SELECT MAX(CAST(SUBSTRING(codigo FROM 5 FOR 4) AS INTEGER))
        FROM cliente
        WHERE company_code = %s
          AND codigo LIKE %s;
    """
    result = database.sql(sql, (company, f"{prefix}-%-C"), fetch=True)
    ultimo = result[0][0] if result and result[0][0] is not None else 0
    return {"ultimo": ultimo}



# ============================================================
# LISTAR CLIENTES — PAGINADO
# ============================================================
@router.get("")
def get_clientes(
    page: int = 1,
    page_size: int = 50,
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    offset = (page - 1) * page_size

    rows = database.sql("""
        SELECT
            codigo,
            nombrejuridico,
            nombrecomercial,
            pais,
            correo,
            telefono,
            cedulajuridicavat,
            actividad_economica,
            comentarios,
            provincia,
            canton,
            distrito,
            direccionexacta,
            fecha_pago,
            prefijo,
            contacto_principal,
            contacto_secundario
        FROM cliente
        WHERE company_code = %s
        ORDER BY codigo ASC
        LIMIT %s OFFSET %s
    """, (company, page_size, offset), fetch=True)

    total = database.sql("SELECT COUNT(*) FROM cliente WHERE company_code = %s", (company,), fetch=True)[0][0]

    data = [
        {
            "codigo": r[0],
            "nombrejuridico": r[1],
            "nombrecomercial": r[2],
            "pais": r[3],
            "correo": r[4],
            "telefono": r[5],
            "cedulajuridicavat": r[6],
            "actividad_economica": r[7],
            "comentarios": r[8],
            "provincia": r[9],
            "canton": r[10],
            "distrito": r[11],
            "direccionexacta": r[12],
            "fecha_pago": r[13],
            "prefijo": r[14],
            "contacto_principal": r[15],
            "contacto_secundario": r[16],
        }
        for r in rows
    ]

    return {"total": total, "data": data}


# ============================================================
# OBTENER UN CLIENTE POR CÓDIGO
# ============================================================
@router.get("/{codigo}")
def get_cliente(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    row = database.sql("""
        SELECT
            codigo,
            nombrejuridico,
            nombrecomercial,
            pais,
            correo,
            telefono,
            cedulajuridicavat,
            actividad_economica,
            comentarios,
            provincia,
            canton,
            distrito,
            direccionexacta,
            fecha_pago,
            prefijo,
            contacto_principal,
            contacto_secundario
        FROM cliente
        WHERE codigo = %s
          AND company_code = %s
    """, (codigo, company), fetch=True)

    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    r = row[0]
    return {
        "codigo": r[0],
        "nombrejuridico": r[1],
        "nombrecomercial": r[2],
        "pais": r[3],
        "correo": r[4],
        "telefono": r[5],
        "cedulajuridicavat": r[6],
        "actividad_economica": r[7],
        "comentarios": r[8],
        "provincia": r[9],
        "canton": r[10],
        "distrito": r[11],
        "direccionexacta": r[12],
        "fecha_pago": r[13],
        "prefijo": r[14],
        "contacto_principal": r[15],
        "contacto_secundario": r[16],
    }


@router.put("/update")
def update_cliente(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(data.get("company_code"), x_company_code)
    data = set_payload_company(data, company)
    data["FechaDePago"] = _normalize_fecha_pago(data.get("FechaDePago"))
    sql = """
        UPDATE cliente SET
            nombrejuridico = %(NombreJuridico)s,
            nombrecomercial = %(NombreComercial)s,
            pais = %(Pais)s,
            correo = %(Correo)s,
            telefono = %(Telefono)s,
            cedulajuridicavat = %(CedulaJuridicaVAT)s,
            comentarios = %(Comentarios)s,
            provincia = %(Provincia)s,
            canton = %(Canton)s,
            distrito = %(Distrito)s,
            direccionexacta = %(DireccionExacta)s,
            fecha_pago = %(FechaDePago)s,
            prefijo = %(Prefijo)s,
            contacto_principal = %(ContactoPrincipal)s,
            contacto_secundario = %(ContactoSecundario)s
        WHERE codigo = %(Codigo)s
          AND company_code = %(company_code)s
    """
    try:
        database.sql(sql, data)
        return {"status": "OK", "msg": "Cliente actualizado ✔"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ELIMINAR CLIENTE
# ============================================================
@router.delete("/{codigo}")
def delete_cliente(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    database.sql("DELETE FROM cliente WHERE codigo = %s AND company_code = %s", (codigo, company))
    return {"status": "OK", "msg": "Cliente eliminado 🗑️"}

