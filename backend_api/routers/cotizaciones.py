# ============================================================
# ROUTER — COTIZACIONES (ERP-SOM)
# Archivo: backend_api/routers/cotizaciones.py
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from fastapi.responses import FileResponse
from typing import Optional
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
import os
import tempfile

from database import get_db
from rbac_service import has_permission
from services.cotizacion_export_service import export_cotizacion_pdf, export_cotizacion_word

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
# HELPERS
# ============================================================

def _clean_str(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def _normalize_payload_dict(data: dict) -> dict:
    clean = {}
    for k, v in (data or {}).items():
        if isinstance(v, str):
            clean[k] = _clean_str(v)
        else:
            clean[k] = v
    return clean


def _build_cotizaciones_filters(
    cliente: str | None = None,
    servicio: str | None = None,
    continente: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    status: str | None = None,
    year: int | None = None,
):
    filters = []
    params = {}

    cliente = _clean_str(cliente)
    servicio = _clean_str(servicio)
    continente = _clean_str(continente)
    pais = _clean_str(pais)
    puerto = _clean_str(puerto)
    status = _clean_str(status)

    if year:
        filters.append("EXTRACT(YEAR FROM COALESCE(updated_at, created_at)) = %(year)s")
        params["year"] = year

    if cliente:
        filters.append("TRIM(cliente) = %(cliente)s")
        params["cliente"] = cliente

    if servicio:
        filters.append("TRIM(servicio) = %(servicio)s")
        params["servicio"] = servicio

    if continente:
        filters.append("TRIM(continente) = %(continente)s")
        params["continente"] = continente

    if pais:
        filters.append("TRIM(pais) = %(pais)s")
        params["pais"] = pais

    if puerto:
        filters.append("TRIM(puerto) = %(puerto)s")
        params["puerto"] = puerto

    if status:
        filters.append("TRIM(status) = %(status)s")
        params["status"] = status

    return filters, params


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


def _safe_export_name(value: str) -> str:
    clean = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in str(value or "quotation"))
    return clean[:80] or "quotation"


# ============================================================
# GET — META PARA POPUP (PRECIOS + CATÁLOGOS)
# ============================================================

@router.get(
    "/meta",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def get_cotizaciones_meta(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Clientes
        cur.execute("""
            SELECT
                codigo,
                TRIM(nombrejuridico) AS nombre
            FROM cliente
            WHERE nombrejuridico IS NOT NULL
              AND TRIM(nombrejuridico) <> ''
            ORDER BY nombre;
        """)
        clientes = cur.fetchall() or []

        # Servicios
        cur.execute("""
            SELECT
                codigo,
                codigoprod,
                TRIM(nombre) AS nombre
            FROM serviciosmd
            WHERE nombre IS NOT NULL
              AND TRIM(nombre) <> ''
            ORDER BY nombre;
        """)
        servicios = cur.fetchall() or []

        # Ubicaciones
        cur.execute("""
            SELECT DISTINCT
                TRIM(continente) AS continente,
                TRIM(pais) AS pais,
                TRIM(puerto) AS puerto
            FROM continentes_paises_puertos
            WHERE continente IS NOT NULL
              AND TRIM(continente) <> ''
              AND pais IS NOT NULL
              AND TRIM(pais) <> ''
              AND puerto IS NOT NULL
              AND TRIM(puerto) <> ''
            ORDER BY continente, pais, puerto;
        """)
        ubicaciones = cur.fetchall() or []

        # Precios activos y limpios para cascada
        cur.execute("""
            SELECT
                TRIM(servicio)   AS servicio,
                TRIM(cliente)    AS cliente,
                TRIM(continente) AS continente,
                TRIM(pais)       AS pais,
                TRIM(puerto)     AS puerto,
                precio,
                moneda,
                activo
            FROM servicios_precios
            WHERE activo = TRUE
              AND cliente IS NOT NULL
              AND TRIM(cliente) <> ''
              AND servicio IS NOT NULL
              AND TRIM(servicio) <> ''
            ORDER BY cliente, servicio, continente, pais, puerto;
        """)
        precios = cur.fetchall() or []

        return {
            "clientes": clientes,
            "servicios": servicios,
            "ubicaciones": ubicaciones,
            "precios": precios
        }

    finally:
        cur.close()


# ============================================================
# GET — LISTAR COTIZACIONES
# ============================================================

@router.get(
    "",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def listar_cotizaciones(
    cliente: str | None = Query(None),
    servicio: str | None = Query(None),
    continente: str | None = Query(None),
    pais: str | None = Query(None),
    puerto: str | None = Query(None),
    status: str | None = Query(None),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        filters, params = _build_cotizaciones_filters(
            cliente=cliente,
            servicio=servicio,
            continente=continente,
            pais=pais,
            puerto=puerto,
            status=status,
        )

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        cur.execute(f"""
            SELECT
                id,
                quotation_number,
                TRIM(cliente)    AS cliente,
                TRIM(servicio)   AS servicio,
                TRIM(continente) AS continente,
                TRIM(pais)       AS pais,
                TRIM(puerto)     AS puerto,
                precio,
                idioma,
                validez,
                TRIM(status)     AS status,
                created_at
            FROM public.cotizaciones
            {where_clause}
            ORDER BY created_at DESC;
        """, params)

        data = cur.fetchall() or []

        return {
            "total": len(data),
            "data": data
        }

    finally:
        cur.close()


# ============================================================
# Consecutivo Cotización
# ============================================================

@router.get(
    "/next-quotation-number",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def get_next_quotation_number(conn=Depends(get_db)):
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT quotation_number
            FROM public.cotizaciones
            ORDER BY id DESC
            LIMIT 1
            FOR UPDATE;
        """)

        row = cur.fetchone()

        if row and row[0]:
            last_num = int(str(row[0]).replace("Quotation", "").strip())
            next_num = last_num + 1
        else:
            next_num = 1

        return {
            "quotation_number": f"Quotation {next_num:05d}"
        }

    finally:
        cur.close()


# ============================================================
# GET - EXPORTAR COTIZACION MOBILE (WORD / PDF)
# ============================================================

@router.get("/export/{formato}")
def exportar_cotizacion_mobile(
    formato: str,
    quotation_number: str = Query(""),
    cliente: str = Query(""),
    servicio: str = Query(""),
    idioma: str = Query("ES"),
    texto: str = Query(""),
    request_user: str = Query(""),
    request_role: str = Query("")
):
    if not request_user or not has_permission((request_role or "").lower(), "comercial", "view"):
        raise HTTPException(status_code=403, detail="Usuario no autenticado")

    formato = (formato or "").strip().lower()
    if formato not in {"word", "pdf"}:
        raise HTTPException(status_code=400, detail="Formato invalido")

    suffix = ".docx" if formato == "word" else ".pdf"
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    data = {
        "quotation_number": quotation_number,
        "cliente": cliente,
        "servicio": servicio,
        "idioma": idioma or "ES",
        "texto": texto
    }

    try:
        if formato == "word":
            export_cotizacion_word(data, path)
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            export_cotizacion_pdf(data, path)
            media_type = "application/pdf"

        filename = f"{_safe_export_name(quotation_number or cliente)}{suffix}"
        return FileResponse(path, filename=filename, media_type=media_type)
    except Exception as exc:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(exc))


# ============================================================
# POST — CREAR COTIZACIÓN
# ============================================================

@router.post(
    "",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def crear_cotizacion(payload: CotizacionCreate, conn=Depends(get_db)):
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT quotation_number
            FROM public.cotizaciones
            ORDER BY id DESC
            LIMIT 1
            FOR UPDATE;
        """)

        row = cur.fetchone()
        next_num = int(str(row[0]).replace("Quotation", "").strip()) + 1 if row and row[0] else 1
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

        params = _normalize_payload_dict(payload.dict())
        params["quotation_number"] = quotation_number

        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()

        return {
            "status": "OK",
            "id": row[0],
            "quotation_number": row[1]
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()


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

    try:
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
            raise HTTPException(status_code=404, detail="Cotización no encontrada")

        status_actual = _clean_str(current["status"])
        data = _normalize_payload_dict(payload.dict(exclude_unset=True))

        if not data:
            raise HTTPException(
                status_code=400,
                detail="No hay campos para actualizar"
            )

        # --------------------------------------------------------
        # Validaciones de negocio sobre STATUS
        # --------------------------------------------------------
        nuevo_status = _clean_str(data.get("status"))

        if nuevo_status:
            if nuevo_status not in ("PENDIENTE", "APROBADO", "CANCELADO"):
                raise HTTPException(
                    status_code=400,
                    detail="Estado inválido"
                )

            if status_actual == "APROBADO":
                raise HTTPException(
                    status_code=400,
                    detail="Una cotización APROBADA no puede modificarse"
                )

            if status_actual == "CANCELADO":
                raise HTTPException(
                    status_code=400,
                    detail="Una cotización CANCELADA no puede modificarse"
                )

            if nuevo_status == "CANCELADO" and not _clean_str(data.get("razon_cancelacion")):
                raise HTTPException(
                    status_code=400,
                    detail="Debe indicar la razón de cancelación"
                )

        # --------------------------------------------------------
        # Construcción segura del UPDATE
        # --------------------------------------------------------
        allowed_fields = {
            "cliente", "servicio", "continente", "pais", "puerto",
            "precio", "idioma", "validez", "status",
            "servicio_1", "precio_1", "servicio_2", "precio_2",
            "servicio_3", "precio_3", "servicio_4", "precio_4",
            "razon_cancelacion"
        }

        fields = []
        params = {"id": cotizacion_id}

        for k, v in data.items():
            if k not in allowed_fields:
                continue
            fields.append(f"{k} = %({k})s")
            params[k] = v

        if not fields:
            raise HTTPException(
                status_code=400,
                detail="No hay campos válidos para actualizar"
            )

        fields.append("updated_at = NOW()")

        sql = f"""
            UPDATE public.cotizaciones
            SET {", ".join(fields)}
            WHERE id = %(id)s;
        """

        cur.execute(sql, params)
        conn.commit()

        return {
            "status": "OK",
            "id": cotizacion_id
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()


# ============================================================
# DELETE — ELIMINAR COTIZACIÓN
# ============================================================

@router.delete(
    "/{cotizacion_id}",
    dependencies=[Depends(require_permission("comercial", "edit"))]
)
def eliminar_cotizacion(cotizacion_id: int, conn=Depends(get_db)):
    cur = conn.cursor()

    try:
        cur.execute("""
            DELETE FROM public.cotizaciones
            WHERE id = %s;
        """, (cotizacion_id,))

        conn.commit()

        return {"status": "OK"}

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()


# ============================================================
# GET — KPIs COTIZACIONES COMERCIALES
# ============================================================

@router.get(
    "/kpis",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def get_cotizaciones_kpis(
    year: int | None = None,
    cliente: str | None = None,
    servicio: str | None = None,
    continente: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    status: str | None = None,
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        filters, params = _build_cotizaciones_filters(
            year=year,
            cliente=cliente,
            servicio=servicio,
            continente=continente,
            pais=pais,
            puerto=puerto,
            status=status
        )

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        sql = f"""
            SELECT
                COUNT(DISTINCT TRIM(cliente))                        AS clientes,
                COUNT(DISTINCT TRIM(servicio))                       AS servicios,
                COUNT(DISTINCT TRIM(pais))                           AS paises,
                COUNT(DISTINCT TRIM(puerto))                         AS puertos,
                COUNT(*) FILTER (WHERE TRIM(status) = 'PENDIENTE')   AS pendientes,
                COUNT(*) FILTER (WHERE TRIM(status) = 'APROBADO')    AS aprobadas,
                COUNT(*) FILTER (WHERE TRIM(status) = 'CANCELADO')   AS canceladas
            FROM public.cotizaciones
            {where_clause};
        """

        cur.execute(sql, params)
        result = cur.fetchone()

        return {
            "year": year,
            "kpis": result
        }

    finally:
        cur.close()
