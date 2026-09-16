# ============================================================
# ROUTER — SERVICIOS PRECIOS (ERP-SOM)
# Archivo: backend_api/routers/servicios_precios.py
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from rbac_service import has_permission
from services.tenanting import company_code

# ============================================================
# RBAC — MISMA LÓGICA QUE ROUTERS FUNCIONALES
# ============================================================

def require_permission(module: str, action: str):
    def checker(
        x_user_role: str = Header(..., alias="X-User-Role")
    ):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(status_code=403, detail="No autorizado")
    return checker


router = APIRouter(
    prefix="/comercial/precios",
    tags=["Comercial — Precios"]
)

# ============================================================
# SCHEMAS
# ============================================================

class PrecioCreate(BaseModel):
    servicio: str
    cliente: str
    continente: Optional[str] = None
    pais: Optional[str] = None
    puerto: Optional[str] = None
    precio: float


class PrecioUpdate(BaseModel):
    servicio: Optional[str] = None
    cliente: Optional[str] = None
    continente: Optional[str] = None
    pais: Optional[str] = None
    puerto: Optional[str] = None
    precio: Optional[float] = None
    activo: Optional[bool] = None


def _ensure_precios_company(cur):
    cur.execute("""
        ALTER TABLE servicios_precios
        ADD COLUMN IF NOT EXISTS company_code VARCHAR(30) NOT NULL DEFAULT 'MSL-CR';
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_servicios_precios_company
        ON servicios_precios(company_code, activo, cliente, servicio);
    """)
    cur.execute("""
        WITH client_keys AS (
            SELECT UPPER(TRIM(nombrejuridico::text)) AS client_key,
                   COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') AS company_code
            FROM cliente
            WHERE nombrejuridico IS NOT NULL AND TRIM(nombrejuridico::text) <> ''
            UNION ALL
            SELECT UPPER(TRIM(nombrecomercial::text)) AS client_key,
                   COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') AS company_code
            FROM cliente
            WHERE nombrecomercial IS NOT NULL AND TRIM(nombrecomercial::text) <> ''
            UNION ALL
            SELECT UPPER(TRIM(codigo::text)) AS client_key,
                   COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') AS company_code
            FROM cliente
            WHERE codigo IS NOT NULL AND TRIM(codigo::text) <> ''
        ),
        unique_client_company AS (
            SELECT client_key, MAX(company_code) AS company_code
            FROM client_keys
            GROUP BY client_key
            HAVING COUNT(DISTINCT company_code) = 1
        )
        UPDATE servicios_precios sp
        SET company_code = u.company_code
        FROM unique_client_company u
        WHERE UPPER(TRIM(sp.cliente::text)) = u.client_key
          AND COALESCE(NULLIF(TRIM(sp.company_code::text), ''), 'MSL-CR') <> u.company_code;
    """)


# ============================================================
# GET — DATA PARA POPUP (DESPLEGABLES)
# ============================================================

@router.get(
    "/meta",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def get_precios_meta(
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _ensure_precios_company(cur)
    conn.commit()
    company = company_code(header_value=x_company_code)

    # Servicios (Catálogo)
    cur.execute("""
        SELECT
            codigo,
            codigoprod,
            TRIM(nombre) AS nombre
        FROM serviciosmd
        ORDER BY nombre;
    """)
    servicios = cur.fetchall()

    # Clientes
    cur.execute("""
        SELECT
            codigo,
            TRIM(nombrejuridico) AS nombrejuridico
        FROM cliente
        WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %(company_code)s
        ORDER BY nombrejuridico;
    """, {"company_code": company})
    clientes = cur.fetchall()

    # Ubicaciones
    cur.execute("""
        SELECT DISTINCT
            TRIM(continente) AS continente,
            TRIM(pais) AS pais,
            TRIM(puerto) AS puerto
        FROM continentes_paises_puertos
        WHERE continente IS NOT NULL
          AND pais IS NOT NULL
          AND puerto IS NOT NULL
        ORDER BY continente, pais, puerto;
    """)
    ubicaciones = cur.fetchall()

    cur.close()

    return {
        "servicios": servicios,
        "clientes": clientes,
        "ubicaciones": ubicaciones
    }


# ============================================================
# GET — LISTAR PRECIOS
# ============================================================

@router.get(
    "",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def listar_precios(
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    _ensure_precios_company(cur)
    conn.commit()
    company = company_code(header_value=x_company_code)

    cur.execute("""
        SELECT
            id,
            company_code,
            servicio,
            cliente,
            continente,
            pais,
            puerto,
            precio,
            activo,
            created_at,
            updated_at
        FROM servicios_precios
        WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %(company_code)s
        ORDER BY cliente, servicio;
    """, {"company_code": company})

    data = cur.fetchall()
    cur.close()

    return {
        "total": len(data),
        "data": data
    }


# ============================================================
# POST — CREAR PRECIO
# ============================================================

@router.post(
    "",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def crear_precio(
    payload: PrecioCreate,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    cur = conn.cursor()
    _ensure_precios_company(cur)
    company = company_code(header_value=x_company_code)

    sql = """
        INSERT INTO servicios_precios (
            company_code,
            servicio,
            cliente,
            continente,
            pais,
            puerto,
            precio,
            activo,
            created_at,
            updated_at
        )
        VALUES (
            %(company_code)s,
            %(servicio)s,
            %(cliente)s,
            %(continente)s,
            %(pais)s,
            %(puerto)s,
            %(precio)s,
            TRUE,
            NOW(),
            NOW()
        )
        RETURNING id;
    """

    data = payload.dict()
    data["company_code"] = company
    cur.execute(sql, data)
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()

    return {
        "status": "OK",
        "id": new_id
    }


# ============================================================
# PUT — ACTUALIZAR PRECIO
# ============================================================

@router.put(
    "/{precio_id}",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def actualizar_precio(
    precio_id: int,
    payload: PrecioUpdate,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db)
):
    cur = conn.cursor()
    _ensure_precios_company(cur)
    company = company_code(header_value=x_company_code)

    fields = []
    params = {"id": precio_id}

    for k, v in payload.dict(exclude_unset=True).items():
        fields.append(f"{k} = %({k})s")
        params[k] = v

    if not fields:
        conn.rollback()
        cur.close()
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    fields.append("updated_at = NOW()")

    sql = f"""
        UPDATE servicios_precios
        SET {", ".join(fields)}
        WHERE id = %(id)s
          AND COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %(company_code)s;
    """

    params["company_code"] = company
    cur.execute(sql, params)
    if cur.rowcount == 0:
        conn.rollback()
        cur.close()
        raise HTTPException(status_code=404, detail="Precio no encontrado para esta empresa")
    conn.commit()
    cur.close()

    return {"status": "OK"}


# ============================================================
# DELETE — ELIMINAR PRECIO
# ============================================================

@router.delete(
    "/{precio_id}",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def eliminar_precio(
    precio_id: int,
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
    conn=Depends(get_db),
):
    cur = conn.cursor()
    _ensure_precios_company(cur)
    company = company_code(header_value=x_company_code)

    cur.execute("""
        DELETE FROM servicios_precios
        WHERE id = %s
          AND COALESCE(NULLIF(TRIM(company_code::text), ''), 'MSL-CR') = %s;
    """, (precio_id, company))
    if cur.rowcount == 0:
        conn.rollback()
        cur.close()
        raise HTTPException(status_code=404, detail="Precio no encontrado para esta empresa")

    conn.commit()
    cur.close()

    return {"status": "OK"}
