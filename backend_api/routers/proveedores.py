from fastapi import APIRouter, HTTPException
import database
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from rbac_service import has_permission
from services.tenanting import company_code, company_prefix, ensure_company_column, set_payload_company



router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


def _ensure_tenant_schema():
    ensure_company_column("proveedor")


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

# ============================================================
# INSERTAR NUEVO PROVEEDOR EN BD
# ============================================================
@router.post("/add")
def add_proveedor(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    try:
        _ensure_tenant_schema()
        data = set_payload_company(data, company_code(data.get("company_code"), x_company_code))
        sql = """
        INSERT INTO proveedor (
            company_code,
            codigo,
            nombre,
            apellidos,
            nombrecomercial,
            cedula_vat,
            pais,
            provincia,
            canton,
            distrito,
            direccionexacta,
            prefijo,
            telefono,
            correo,
            terminospago,
            banco,
            cuenta_iban,
            swiftcode,
            uid,
            direccionbanco,
            tipoproveeduria,
            comentarios
        )
        VALUES (
            %(company_code)s,
            %(Codigo)s,
            %(Nombre)s,
            %(Apellidos)s,
            %(NombreComercial)s,
            %(Cedula)s,
            %(Pais)s,
            %(Provincia)s,
            %(Canton)s,
            %(Distrito)s,
            %(DireccionExacta)s,
            %(Prefijo)s,
            %(Telefono)s,
            %(Correo)s,
            %(TerminosPago)s,
            %(Banco)s,
            %(CuentaIBAN)s,
            %(SwiftCode)s,
            %(UID)s,
            %(DireccionBanco)s,
            %(TipoProveeduria)s,
            %(Comentarios)s
        )
        """
        database.sql(sql, data)
        return {"status": "OK", "msg": "Proveedor registrado 💾✔"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# OBTENER ÚLTIMO CÓDIGO CORRELATIVO
# ============================================================
@router.get("/ultimo")
def get_ultimo_proveedor(company_code_param: str | None = Query(None, alias="company_code"), x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    prefix = company_prefix(company)
    sql_query = """
        SELECT MAX(CAST(SUBSTRING(codigo FROM 5 FOR 4) AS INTEGER))
        FROM proveedor
        WHERE company_code = %s
          AND codigo LIKE %s;
    """
    result = database.sql(sql_query, (company, f"{prefix}-%-P"), fetch=True)

    ultimo = result[0][0] if result and result[0][0] is not None else 0
    return {"ultimo": ultimo}

# ============================================================
# LISTAR PROVEEDORES — PAGINADO
# ============================================================
@router.get("/")
def get_proveedores(
    page: int = 1,
    page_size: int = 50,
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    offset = (page - 1) * page_size

    rows = database.sql(f"""
        SELECT codigo, nombre, apellidos, nombrecomercial,
               cedula_vat, pais, provincia, canton, distrito,
               direccionexacta, prefijo, telefono, correo,
               terminospago, banco, cuenta_iban, swiftcode,
               uid, direccionbanco, tipoproveeduria, comentarios
        FROM proveedor
        WHERE company_code = %(company_code)s
        ORDER BY codigo ASC
        LIMIT {page_size} OFFSET {offset}
    """, {"company_code": company}, fetch=True)

    total = database.sql("SELECT COUNT(*) FROM proveedor WHERE company_code = %s", (company,), fetch=True)[0][0]

    data = [
        {
            "Codigo": r[0],
            "Nombre": r[1],
            "Apellidos": r[2],
            "NombreComercial": r[3],
            "Cedula": r[4],
            "Pais": r[5],
            "Provincia": r[6],
            "Canton": r[7],
            "Distrito": r[8],
            "DireccionExacta": r[9],
            "Prefijo": r[10],
            "Telefono": r[11],
            "Correo": r[12],
            "TerminosPago": r[13],
            "Banco": r[14],
            "CuentaIBAN": r[15],
            "SwiftCode": r[16],
            "UID": r[17],
            "DireccionBanco": r[18],
            "TipoProveeduria": r[19],
            "Comentarios": r[20]
        }
        for r in rows
    ]

    return {"data": data, "total": total}

# ============================================================
# OBTENER UN PROVEEDOR POR CÓDIGO
# ============================================================
@router.get("/{codigo}")
def get_proveedor(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    row = database.sql("""
        SELECT codigo, nombre, apellidos, nombrecomercial,
               cedula_vat, pais, provincia, canton, distrito,
               direccionexacta, prefijo, telefono, correo,
               terminospago, banco, cuenta_iban, swiftcode,
               uid, direccionbanco, tipoproveeduria, comentarios
        FROM proveedor
        WHERE codigo = %s
          AND company_code = %s
    """, (codigo, company), fetch=True)

    if not row:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")

    r = row[0]
    return {
        "Codigo": r[0],
        "Nombre": r[1],
        "Apellidos": r[2],
        "NombreComercial": r[3],
        "Cedula": r[4],
        "Pais": r[5],
        "Provincia": r[6],
        "Canton": r[7],
        "Distrito": r[8],
        "DireccionExacta": r[9],
        "Prefijo": r[10],
        "Telefono": r[11],
        "Correo": r[12],
        "TerminosPago": r[13],
        "Banco": r[14],
        "CuentaIBAN": r[15],
        "SwiftCode": r[16],
        "UID": r[17],
        "DireccionBanco": r[18],
        "TipoProveeduria": r[19],
        "Comentarios": r[20]
    }


# ============================================================
# ACTUALIZAR PROVEEDOR
# ============================================================
@router.put("/update")
def update_proveedor(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    data = set_payload_company(data, company_code(data.get("company_code"), x_company_code))
    sql = """
        UPDATE proveedor SET
            nombre = %(Nombre)s,
            apellidos = %(Apellidos)s,
            nombrecomercial = %(NombreComercial)s,
            cedula_vat = %(Cedula)s,
            pais = %(Pais)s,
            provincia = %(Provincia)s,
            canton = %(Canton)s,
            distrito = %(Distrito)s,
            direccionexacta = %(DireccionExacta)s,
            prefijo = %(Prefijo)s,
            telefono = %(Telefono)s,
            correo = %(Correo)s,
            terminospago = %(TerminosPago)s,
            banco = %(Banco)s,
            cuenta_iban = %(CuentaIBAN)s,
            swiftcode = %(SwiftCode)s,
            uid = %(UID)s,
            direccionbanco = %(DireccionBanco)s,
            tipoproveeduria = %(TipoProveeduria)s,
            comentarios = %(Comentarios)s
        WHERE codigo = %(Codigo)s
          AND company_code = %(company_code)s
    """
    database.sql(sql, data)
    return {"status": "OK", "msg": "Proveedor actualizado ✔"}


# ============================================================
# ELIMINAR PROVEEDOR
# ============================================================
@router.delete("/{codigo}")
def delete_proveedor(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    database.sql("DELETE FROM proveedor WHERE codigo = %s AND company_code = %s", (codigo, company))
    return {"status": "OK", "msg": "Proveedor eliminado 🗑️"}

