from fastapi import APIRouter, HTTPException, Depends, Header, Query
import database

from rbac_service import has_permission
from services.tenanting import company_code, ensure_company_column

router = APIRouter(prefix="/servicios_md", tags=["ServiciosMD"])


def _ensure_tenant_schema():
    ensure_company_column("ServiciosMD")

# ============================================================
# RBAC GUARD
# ============================================================
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
# INSERTAR NUEVO SERVICIO EN ServiciosMD
# ============================================================
@router.post("/add")
def add_servicio(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    data = dict(data or {})
    data["company_code"] = company_code(data.get("company_code"), x_company_code)
    sql = """
        INSERT INTO ServiciosMD (
            company_code, Codigo, CodigoProd, Nombre, Costo
        )
        VALUES (
            %(company_code)s, %(codigo)s, %(codigo_prod)s, %(nombre)s, %(costo)s
        )
    """
    database.sql(sql, data)
    return {"status": "OK", "msg": "Servicio registrado 💾✔"}


# ============================================================
# OBTENER ÚLTIMO CÓDIGO CORRELATIVO
# ============================================================
@router.get("/ultimo")
def get_ultimo_codigo(
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    data = database.sql("""
        SELECT MAX(CAST(SUBSTRING(codigo FROM 5 FOR 4) AS INTEGER)) 
        FROM ServiciosMD
        WHERE company_code = %s;
    """, (company,), fetch=True)

    ultimo = data[0][0] if data and data[0][0] else 0
    return {"ultimo": ultimo}

# ============================================================
# LISTAR SERVICIOS — PAGINADO
# ============================================================
@router.get("/")
def get_servicios(
    page: int = 1,
    page_size: int = 50,
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    offset = (page - 1) * page_size

    rows = database.sql("""
        SELECT Codigo, CodigoProd, Nombre, Costo
        FROM ServiciosMD
        WHERE company_code = %s
        ORDER BY Codigo ASC
        LIMIT %s OFFSET %s
    """, (company, page_size, offset), fetch=True)

    # total para paginación
    total = database.sql("""
        SELECT COUNT(*) FROM ServiciosMD
        WHERE company_code = %s
    """, (company,), fetch=True)[0][0]

    data = [
        {
            "codigo": r[0],
            "codigo_prod": r[1],
            "nombre": r[2],
            "costo": r[3],
        }
        for r in rows
    ]

    return {"data": data, "total": total}


# ============================================================
# OBTENER UN SERVICIO POR CÓDIGO
# ============================================================
@router.get("/{codigo}")
def get_servicio(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(header_value=x_company_code)
    row = database.sql("""
        SELECT Codigo, CodigoProd, Nombre, Costo
        FROM ServiciosMD
        WHERE Codigo = %s
          AND company_code = %s
    """, (codigo, company), fetch=True)

    if not row:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    r = row[0]
    return {
        "codigo": r[0],
        "codigo_prod": r[1],
        "nombre": r[2],
        "costo": r[3],
    }

# ============================================================
# ACTUALIZAR SERVICIO
# ============================================================
@router.put("/update")
def update_servicio(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code((data or {}).get("company_code"), x_company_code)
    sql = """
        UPDATE ServiciosMD SET
            CodigoProd = %(codigo_prod)s,
            Nombre = %(nombre)s,
            Costo = %(costo)s
        WHERE Codigo = %(codigo)s
          AND company_code = %(company_code)s
    """
    data = dict(data or {})
    data["company_code"] = company
    database.sql(sql, data)
    return {"status": "OK", "msg": "Servicio actualizado ✔"}


# ============================================================
# ELIMINAR SERVICIO
# ============================================================
@router.delete("/{codigo}")
def delete_servicio(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(header_value=x_company_code)
    database.sql("""
        DELETE FROM ServiciosMD
        WHERE Codigo = %s
          AND company_code = %s
    """, (codigo, company))
    return {"status": "OK", "msg": "Servicio eliminado 🗑️"}
