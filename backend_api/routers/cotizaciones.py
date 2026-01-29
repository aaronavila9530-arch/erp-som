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
    servicio: Optional[str] = None
    continente: Optional[str] = None
    pais: Optional[str] = None
    puerto: Optional[str] = None
    precio: Optional[float] = None
    idioma: Optional[str] = "ES"
    validez: Optional[int] = 15
    status: Optional[str] = "PENDIENTE"

    servicio_1: Optional[str] = None
    precio_1: Optional[float] = None
    servicio_2: Optional[str] = None
    precio_2: Optional[float] = None
    servicio_3: Optional[str] = None
    precio_3: Optional[float] = None
    servicio_4: Optional[str] = None
    precio_4: Optional[float] = None


class CotizacionUpdate(BaseModel):
    cliente: Optional[str] = None
    servicio: Optional[str] = None
    continente: Optional[str] = None
    pais: Optional[str] = None
    puerto: Optional[str] = None
    precio: Optional[float] = None
    idioma: Optional[str] = None
    validez: Optional[int] = None
    status: Optional[str] = None

    servicio_1: Optional[str] = None
    precio_1: Optional[float] = None
    servicio_2: Optional[str] = None
    precio_2: Optional[float] = None
    servicio_3: Optional[str] = None
    precio_3: Optional[float] = None
    servicio_4: Optional[str] = None
    precio_4: Optional[float] = None

    razon_cancelacion: Optional[str] = None


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
            quotation_number,
            cliente,
            servicio,
            continente,
            pais,
            puerto,
            precio,
            idioma,
            validez,
            status,
            created_at
        FROM public.cotizaciones
        ORDER BY created_at DESC;
    """)

    data = cur.fetchall()
    cur.close()

    return {
        "total": len(data),
        "data": data
    }

# ============================================================
# Consecutivo Cotización
# ============================================================

@router.get(
    "/next-quotation-number",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def get_next_quotation_number(conn=Depends(get_db)):
    cur = conn.cursor()

    cur.execute("""
        SELECT quotation_number
        FROM public.cotizaciones
        ORDER BY id DESC
        LIMIT 1
        FOR UPDATE;
    """)

    row = cur.fetchone()

    if row and row[0]:
        last_num = int(row[0].replace("Quotation", "").strip())
        next_num = last_num + 1
    else:
        next_num = 1

    cur.close()

    return {
        "quotation_number": f"Quotation {next_num:05d}"
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

    cur.execute("""
        SELECT quotation_number
        FROM public.cotizaciones
        ORDER BY id DESC
        LIMIT 1
        FOR UPDATE;
    """)

    row = cur.fetchone()
    next_num = int(row[0].replace("Quotation", "").strip()) + 1 if row else 1
    quotation_number = f"Quotation {next_num:05d}"

    sql = """
        INSERT INTO public.cotizaciones (
            cliente, servicio, continente, pais, puerto,
            precio, idioma, validez, status,
            servicio_1, precio_1, servicio_2, precio_2,
            servicio_3, precio_3, servicio_4, precio_4,
            quotation_number
        )
        VALUES (
            %(cliente)s, %(servicio)s, %(continente)s, %(pais)s, %(puerto)s,
            %(precio)s, %(idioma)s, %(validez)s, %(status)s,
            %(servicio_1)s, %(precio_1)s, %(servicio_2)s, %(precio_2)s,
            %(servicio_3)s, %(precio_3)s, %(servicio_4)s, %(precio_4)s,
            %(quotation_number)s
        )
        RETURNING id, quotation_number;
    """

    params = payload.dict()
    params["quotation_number"] = quotation_number

    cur.execute(sql, params)
    row = cur.fetchone()
    conn.commit()
    cur.close()

    return {"status": "OK", "id": row[0], "quotation_number": row[1]}


# ============================================================
# PUT — ACTUALIZAR COTIZACIÓN (STATUS / RAZÓN)
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
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # Validar existencia de la cotización
    # --------------------------------------------------------
    cur.execute("""
        SELECT id, status
        FROM public.cotizaciones
        WHERE id = %s;
    """, (cotizacion_id,))

    current = cur.fetchone()
    if not current:
        cur.close()
        raise HTTPException(status_code=404, detail="Cotización no encontrada")

    status_actual = current["status"]
    data = payload.dict(exclude_unset=True)

    if not data:
        cur.close()
        raise HTTPException(
            status_code=400,
            detail="No hay campos para actualizar"
        )

    # --------------------------------------------------------
    # Validaciones de negocio sobre STATUS
    # --------------------------------------------------------
    nuevo_status = data.get("status")

    if nuevo_status:
        if nuevo_status not in ("PENDIENTE", "APROBADO", "CANCELADO"):
            cur.close()
            raise HTTPException(
                status_code=400,
                detail="Estado inválido"
            )

        # No permitir volver atrás
        if status_actual == "APROBADO":
            cur.close()
            raise HTTPException(
                status_code=400,
                detail="Una cotización APROBADA no puede modificarse"
            )

        if status_actual == "CANCELADO":
            cur.close()
            raise HTTPException(
                status_code=400,
                detail="Una cotización CANCELADA no puede modificarse"
            )

        # Si se cancela → razón obligatoria
        if nuevo_status == "CANCELADO" and not data.get("razon_cancelacion"):
            cur.close()
            raise HTTPException(
                status_code=400,
                detail="Debe indicar la razón de cancelación"
            )

    # --------------------------------------------------------
    # Construcción segura del UPDATE
    # --------------------------------------------------------
    fields = []
    params = {"id": cotizacion_id}

    for k, v in data.items():
        fields.append(f"{k} = %({k})s")
        params[k] = v

    fields.append("updated_at = NOW()")

    sql = f"""
        UPDATE public.cotizaciones
        SET {", ".join(fields)}
        WHERE id = %(id)s;
    """

    cur.execute(sql, params)
    conn.commit()
    cur.close()

    return {
        "status": "OK",
        "id": cotizacion_id
    }




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
        DELETE FROM public.cotizaciones
        WHERE id = %s;
    """, (cotizacion_id,))

    conn.commit()
    cur.close()

    return {"status": "OK"}
