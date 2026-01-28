# ============================================================
# ROUTER — COTIZACIONES (ERP-SOM)
# Archivo: backend_api/routers/cotizaciones.py
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
from datetime import date

from database import get_db
from rbac_service import has_permission

# ============================================================
# RBAC — MISMA LÓGICA ERP-SOM
# ============================================================

def require_permission(module: str, action: str):
    def checker(
        x_user_role: str = Header(..., alias="X-User-Role")
    ):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(status_code=403, detail="No autorizado")
    return checker


router = APIRouter(
    prefix="/comercial/cotizaciones",
    tags=["Comercial — Cotizaciones"]
)

# ============================================================
# SCHEMAS
# ============================================================

class CotizacionCreate(BaseModel):
    cliente: str
    servicio: str
    continente: Optional[str] = None
    pais: Optional[str] = None
    puerto: Optional[str] = None
    precio: float
    moneda: Optional[str] = "USD"
    fecha_servicio: Optional[date] = None
    validez_dias: Optional[int] = 15
    terminos_pago: Optional[str] = "15 días"
    idioma: str  # ES | EN
    texto_cotizacion: str


class CotizacionUpdate(BaseModel):
    cliente: Optional[str] = None
    servicio: Optional[str] = None
    continente: Optional[str] = None
    pais: Optional[str] = None
    puerto: Optional[str] = None
    precio: Optional[float] = None
    moneda: Optional[str] = None
    fecha_servicio: Optional[date] = None
    validez_dias: Optional[int] = None
    terminos_pago: Optional[str] = None
    idioma: Optional[str] = None
    texto_cotizacion: Optional[str] = None
    estado: Optional[str] = None


# ============================================================
# GET — META PARA POPUP (PRECIOS + CATÁLOGOS)
# ============================================================

@router.get(
    "/meta",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def get_cotizaciones_meta(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Clientes
    cur.execute("""
        SELECT
            codigo,
            TRIM(nombrejuridico) AS nombre
        FROM cliente
        ORDER BY nombre;
    """)
    clientes = cur.fetchall()

    # Servicios
    cur.execute("""
        SELECT
            codigo,
            codigoprod,
            TRIM(nombre) AS nombre
        FROM serviciosmd
        ORDER BY nombre;
    """)
    servicios = cur.fetchall()

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

    # Precios activos
    cur.execute("""
        SELECT
            servicio,
            cliente,
            continente,
            pais,
            puerto,
            precio,
            moneda
        FROM servicios_precios
        WHERE activo = TRUE;
    """)
    precios = cur.fetchall()

    cur.close()

    return {
        "clientes": clientes,
        "servicios": servicios,
        "ubicaciones": ubicaciones,
        "precios": precios
    }


# ============================================================
# GET — LISTAR COTIZACIONES
# ============================================================

@router.get(
    "",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def listar_cotizaciones(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            id,
            codigo_cotizacion,
            cliente,
            servicio,
            continente,
            pais,
            puerto,
            precio,
            moneda,
            fecha_servicio,
            validez_dias,
            terminos_pago,
            idioma,
            estado,
            created_at
        FROM comercial.cotizaciones
        ORDER BY created_at DESC;
    """)

    data = cur.fetchall()
    cur.close()

    return {
        "total": len(data),
        "data": data
    }


# ============================================================
# POST — CREAR COTIZACIÓN
# ============================================================

@router.post(
    "",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def crear_cotizacion(payload: CotizacionCreate, conn=Depends(get_db)):
    cur = conn.cursor()

    sql = """
        INSERT INTO comercial.cotizaciones (
            cliente,
            servicio,
            continente,
            pais,
            puerto,
            precio,
            moneda,
            fecha_servicio,
            validez_dias,
            terminos_pago,
            idioma,
            texto_cotizacion
        )
        VALUES (
            %(cliente)s,
            %(servicio)s,
            %(continente)s,
            %(pais)s,
            %(puerto)s,
            %(precio)s,
            %(moneda)s,
            %(fecha_servicio)s,
            %(validez_dias)s,
            %(terminos_pago)s,
            %(idioma)s,
            %(texto_cotizacion)s
        )
        RETURNING id, codigo_cotizacion;
    """

    cur.execute(sql, payload.dict())
    row = cur.fetchone()
    conn.commit()
    cur.close()

    return {
        "status": "OK",
        "id": row[0],
        "codigo": row[1]
    }


# ============================================================
# PUT — ACTUALIZAR COTIZACIÓN
# ============================================================

@router.put(
    "/{cotizacion_id}",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def actualizar_cotizacion(
    cotizacion_id: int,
    payload: CotizacionUpdate,
    conn=Depends(get_db)
):
    cur = conn.cursor()

    fields = []
    params = {"id": cotizacion_id}

    for k, v in payload.dict(exclude_unset=True).items():
        fields.append(f"{k} = %({k})s")
        params[k] = v

    if not fields:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")

    fields.append("updated_at = NOW()")

    sql = f"""
        UPDATE comercial.cotizaciones
        SET {", ".join(fields)}
        WHERE id = %(id)s;
    """

    cur.execute(sql, params)
    conn.commit()
    cur.close()

    return {"status": "OK"}


# ============================================================
# DELETE — ELIMINAR COTIZACIÓN
# ============================================================

@router.delete(
    "/{cotizacion_id}",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def eliminar_cotizacion(cotizacion_id: int, conn=Depends(get_db)):
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM comercial.cotizaciones
        WHERE id = %s;
    """, (cotizacion_id,))

    conn.commit()
    cur.close()

    return {"status": "OK"}
