# ============================================================
# ROUTER — SERVICIOS PRECIOS (ERP-SOM)
# Archivo: backend_api/routers/servicios_precios.py
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from datetime import datetime

from database import get_db
from security import require_permission

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


# ============================================================
# GET — DATA PARA POPUP (DESPLEGABLES)
# ============================================================

@router.get(
    "/meta",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def get_precios_meta(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

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
        ORDER BY nombrejuridico;
    """)
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
def listar_precios(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            id,
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
        ORDER BY cliente, servicio;
    """)

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
def crear_precio(payload: PrecioCreate, conn=Depends(get_db)):
    cur = conn.cursor()

    sql = """
        INSERT INTO servicios_precios (
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

    cur.execute(sql, payload.dict())
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
    conn=Depends(get_db)
):
    cur = conn.cursor()

    fields = []
    params = {"id": precio_id}

    for k, v in payload.dict(exclude_unset=True).items():
        fields.append(f"{k} = %({k})s")
        params[k] = v

    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    fields.append("updated_at = NOW()")

    sql = f"""
        UPDATE servicios_precios
        SET {", ".join(fields)}
        WHERE id = %(id)s;
    """

    cur.execute(sql, params)
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
def eliminar_precio(precio_id: int, conn=Depends(get_db)):
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM servicios_precios
        WHERE id = %s;
    """, (precio_id,))

    conn.commit()
    cur.close()

    return {"status": "OK"}
