from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel
from datetime import datetime
import re
import database

from rbac_service import has_permission
from services.tenanting import company_code, ensure_company_column, set_payload_company

router = APIRouter(prefix="/servicios", tags=["Servicios"])


def _ensure_tenant_schema():
    ensure_company_column("servicios")

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


# ============================================
# MODELO PARA DEMORAS
# ============================================
class DemoraUpdate(BaseModel):
    total: str


def _num_informe_con_fecha(num_informe: str | None, fecha_inicio: str | None) -> str | None:
    """Conserva el prefijo del informe y recalcula DDMM-YYYY desde fecha_inicio."""
    if not num_informe or not fecha_inicio:
        return num_informe

    parts = str(num_informe).strip().split("-")
    if len(parts) != 3 or not parts[0]:
        return num_informe

    try:
        fecha_dt = _parse_service_date(fecha_inicio)
    except Exception:
        return num_informe

    return f"{parts[0]}-{fecha_dt.strftime('%d%m')}-{fecha_dt.strftime('%Y')}"


def _parse_service_date(value):
    text = str(value or "").strip()
    if not text:
        raise ValueError("Fecha vacia")

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
            return datetime.strptime(normalized, fmt)
        except Exception:
            continue

    return datetime.fromisoformat(text[:10])


def _normalize_service_date(value):
    if value in (None, ""):
        return value
    return _parse_service_date(value).strftime("%Y-%m-%d")


def _normalize_service_time(value):
    text = str(value or "").strip()
    if not text:
        return ""

    normalized = text.upper().replace(".", "").replace(" ", "")
    suffix = None
    if normalized.endswith("AM") or normalized.endswith("PM"):
        suffix = normalized[-2:]
        normalized = normalized[:-2]

    match = re.match(r"^(\d{1,2})(?::(\d{1,2}))?$", normalized)
    if not match:
        raise ValueError("Hora inicio invalida")

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)

    if suffix == "PM" and hour < 12:
        hour += 12
    elif suffix == "AM" and hour == 12:
        hour = 0

    if hour > 23 or minute > 59:
        raise ValueError("Hora inicio invalida")

    return f"{hour:02d}:{minute:02d}"


def _validate_required_service_payload(payload: dict) -> None:
    required = {
        "tipo": "Tipo",
        "buque_contenedor": "Buque / Contenedor",
        "cliente": "Cliente",
        "continente": "Continente",
        "pais": "Pais",
        "puerto": "Puerto",
        "operacion": "Operacion",
        "surveyor": "Surveyor",
        "fecha_inicio": "Fecha inicio",
        "hora_inicio": "Hora inicio",
    }
    missing = [
        label
        for key, label in required.items()
        if not str(payload.get(key) or "").strip()
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Campos obligatorios faltantes: " + ", ".join(missing),
        )


def _validate_location_combo(payload: dict) -> None:
    continente = str(payload.get("continente") or "").strip()
    pais = str(payload.get("pais") or "").strip()
    puerto = str(payload.get("puerto") or "").strip()
    if not continente or not pais or not puerto:
        return

    rows = database.sql(
        """
        SELECT continente, pais, puerto
        FROM continentes_paises_puertos
        WHERE LOWER(translate(TRIM(continente), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) =
              LOWER(translate(TRIM(%s), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'))
          AND LOWER(translate(TRIM(pais), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) =
              LOWER(translate(TRIM(%s), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'))
          AND LOWER(translate(TRIM(puerto), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou')) =
              LOWER(translate(TRIM(%s), 'ÁÉÍÓÚáéíóú', 'AEIOUaeiou'))
        LIMIT 1
        """,
        (continente, pais, puerto),
        fetch=True,
    )
    if not rows:
        raise HTTPException(
            status_code=400,
            detail=(
                "Ubicacion invalida: el puerto no pertenece al pais y "
                "continente seleccionados."
            ),
        )
    payload["continente"] = rows[0][0]
    payload["pais"] = rows[0][1]
    payload["puerto"] = rows[0][2]


REPORT_CONSECUTIVE_BASE = 2141
REPORT_CONSECUTIVE_LOCK_KEY = 2141001


def _assign_new_global_report_number(
    consec: int,
    company: str,
    fecha_inicio: str,
    hora_inicio: str,
) -> str:
    fecha_dt = _parse_service_date(fecha_inicio)
    date_suffix = f"-{fecha_dt.strftime('%d%m')}-{fecha_dt.strftime('%Y')}"
    rows = database.sql(
        """
        WITH lock_row AS (
            SELECT pg_advisory_xact_lock(%s)
        ),
        next_num AS (
            SELECT COALESCE(
                MAX(split_part(s.num_informe, '-', 1)::int),
                %s
            ) + 1 AS prefix
            FROM servicios s, lock_row
            WHERE s.num_informe IS NOT NULL
              AND TRIM(s.num_informe) <> ''
              AND split_part(s.num_informe, '-', 1) ~ '^[0-9]+$'
        ),
        updated AS (
            UPDATE servicios s
            SET
                fecha_inicio = %s,
                hora_inicio  = %s,
                num_informe  = next_num.prefix::text || %s,
                estado       = 'En Operación'
            FROM next_num
            WHERE s.consec = %s
              AND s.company_code = %s
            RETURNING s.num_informe
        )
        SELECT num_informe FROM updated
        """,
        (
            REPORT_CONSECUTIVE_LOCK_KEY,
            REPORT_CONSECUTIVE_BASE,
            fecha_inicio,
            hora_inicio,
            date_suffix,
            consec,
            company,
        ),
        fetch=True,
    )

    if not rows:
        raise HTTPException(404, "Servicio no encontrado")

    return rows[0][0]



# ============================================================
# MODELO DE INSERCIÓN DESDE POPUP
# ============================================================
class ServicioCreate(BaseModel):
    tipo: str
    buque_contenedor: str
    cliente: str
    contacto: str | None = None
    detalle: str | None = None
    continente: str
    pais: str
    puerto: str
    operacion: str
    surveyor: str
    honorarios: float | None = None
    costo_operativo: float | None = None
    costo_tarjetas: float | None = None   # 👈 AGREGAR
    fecha_inicio: str    # "YYYY-MM-DD"
    hora_inicio: str     # "HH:MM"


# ============================================================
# INSERTAR SERVICIO
# ============================================================
@router.post("/add")
def add_servicio(data: ServicioCreate, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    try:
        _ensure_tenant_schema()
        payload = set_payload_company(data.dict(), company_code(None, x_company_code))
        for key, value in list(payload.items()):
            if isinstance(value, str):
                payload[key] = value.strip()
        _validate_required_service_payload(payload)
        try:
            payload["fecha_inicio"] = _normalize_service_date(payload.get("fecha_inicio"))
            payload["hora_inicio"] = _normalize_service_time(payload.get("hora_inicio"))
        except Exception:
            raise HTTPException(status_code=400, detail="Fecha u hora de inicio invalida")
        _validate_required_service_payload(payload)
        _validate_location_combo(payload)

        sql = """
            INSERT INTO servicios (
                company_code,
                tipo, estado, num_informe,
                buque_contenedor, cliente, contacto, detalle,
                continente, pais, puerto,
                operacion, surveyor, honorarios, costo_operativo, costo_tarjetas,
                fecha_inicio, hora_inicio
            )
            VALUES (
                %(company_code)s,
                %(tipo)s, 'Confirmado', '',
                %(buque_contenedor)s, %(cliente)s, %(contacto)s, %(detalle)s,
                %(continente)s, %(pais)s, %(puerto)s,
                %(operacion)s, %(surveyor)s, %(honorarios)s, %(costo_operativo)s, %(costo_tarjetas)s,
                %(fecha_inicio)s, %(hora_inicio)s
            )
            RETURNING consec;
        """
        result = database.sql(sql, payload, fetch=True)
        new_id = result[0][0]
        return {"status": "OK", "msg": "Servicio creado", "consec": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================
# META — FILTROS DINÁMICOS (A PRUEBA DE COLISIONES)
# GET /servicios/_meta/filtros
# ============================================================
@router.get("/_meta/filtros")
def listar_filtros_servicios(x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)

    rows = database.sql(
        """
        SELECT
            estado,
            surveyor,
            RIGHT(num_informe, 4) AS anio
        FROM servicios
        WHERE num_informe IS NOT NULL
          AND LENGTH(num_informe) >= 4
          AND company_code = %s
        """,
        (company,),
        fetch=True
    )

    statuses = set()
    surveyores = set()
    anios = set()

    for estado, surveyor, anio in rows:
        if estado:
            statuses.add(estado)
        if surveyor:
            surveyores.add(surveyor)
        if anio and anio.isdigit():
            anios.add(int(anio))

    return {
        "status": sorted(statuses),
        "surveyor": sorted(surveyores),
        "year": sorted(anios)
    }


from datetime import datetime

# ============================================================
# LISTAR — PAGINADO (CON FILTROS AÑO / STATUS / SURVEYOR)
# GET /servicios
# ============================================================
@router.get("/")
def listar_servicios(
    page: int = 1,
    page_size: int = 50,
    year: int | None = None,
    status: str | None = None,
    surveyor: str | None = None,
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    offset = (page - 1) * page_size

    # --------------------------------------------------------
    # NORMALIZAR INPUTS (blindaje contra strings vacíos)
    # --------------------------------------------------------
    if isinstance(status, str) and status.strip() == "":
        status = None

    if isinstance(surveyor, str) and surveyor.strip() == "":
        surveyor = None

    conditions = ["company_code = %(company_code)s"]
    params = {"company_code": company}

    # --------------------------------------------------------
    # AÑO — LÓGICA ERP-SOM (CORREGIDA Y BLINDADA)
    # --------------------------------------------------------
    if year is None and status is None and surveyor is None:
        year_actual = datetime.now().year

        conditions.append("""
            (
                (
                    num_informe IS NOT NULL
                    AND num_informe <> ''
                    AND RIGHT(num_informe, 4) = %(year)s
                )
                OR
                (
                    (num_informe IS NULL OR num_informe = '')
                    AND EXTRACT(YEAR FROM fecha_inicio) = %(year)s
                )
            )
        """)
        params["year"] = str(year_actual)

    elif year is not None:
        conditions.append(
            "RIGHT(COALESCE(num_informe, ''), 4) = %(year)s"
        )
        params["year"] = str(year)

    # -------------------------
    # STATUS
    # -------------------------
    if status:
        status_clean = status.strip()
        if status_clean.upper() != "TODOS":
            conditions.append("estado = %(estado)s")
            params["estado"] = status_clean

    # -------------------------
    # SURVEYOR
    # -------------------------
    if surveyor:
        surveyor_clean = surveyor.strip()
        if surveyor_clean:
            conditions.append("surveyor = %(surveyor)s")
            params["surveyor"] = surveyor_clean

    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    rows = database.sql(
        f"""
        SELECT
            consec, tipo, estado, num_informe,
            buque_contenedor, cliente, contacto, detalle,
            continente, pais, puerto,
            operacion, surveyor, honorarios, costo_operativo, costo_tarjetas,
            fecha_inicio, hora_inicio,
            fecha_fin, hora_fin, demoras, duracion,
            factura, valor_factura, fecha_factura,
            terminos_pago, fecha_vencimiento, dias_vencido,
            razon_cancelacion, comentario_cancelacion
        FROM servicios
        {where_sql}
        ORDER BY consec DESC
        LIMIT {page_size} OFFSET {offset}
        """,
        params,
        fetch=True
    )

    total = database.sql(
        f"""
        SELECT COUNT(*)
        FROM servicios
        {where_sql}
        """,
        params,
        fetch=True
    )[0][0]

    columnas = [
        "consec", "tipo", "estado", "num_informe",
        "buque_contenedor", "cliente", "contacto", "detalle",
        "continente", "pais", "puerto",
        "operacion", "surveyor", "honorarios", "costo_operativo", "costo_tarjetas",
        "fecha_inicio", "hora_inicio",
        "fecha_fin", "hora_fin", "demoras", "duracion",
        "factura", "valor_factura", "fecha_factura",
        "terminos_pago", "fecha_vencimiento", "dias_vencido",
        "razon_cancelacion", "comentario_cancelacion"
    ]

    data = []
    for r in rows:
        item = {
            col: ("" if r[idx] is None else str(r[idx]))
            for idx, col in enumerate(columnas)
        }
        data.append(item)

    return {
        "total": total,
        "data": data
    }

# ============================================================
# GET POR CONSEC
# ============================================================
@router.get("/{consec}")
def get_servicio(consec: int, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    row = database.sql("""
        SELECT
            consec, tipo, estado, num_informe,
            buque_contenedor, cliente, contacto, detalle,
            continente, pais, puerto,
            operacion, surveyor, honorarios, costo_operativo, costo_tarjetas,
            fecha_inicio, hora_inicio,
            fecha_fin, hora_fin, demoras, duracion,
            factura, valor_factura, fecha_factura,
            terminos_pago, fecha_vencimiento, dias_vencido,
            razon_cancelacion, comentario_cancelacion
        FROM servicios
        WHERE consec = %s
          AND company_code = %s
    """, (consec, company), fetch=True)

    if not row:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    r = row[0]
    columnas = [
        "consec", "tipo", "estado", "num_informe",
        "buque_contenedor", "cliente", "contacto", "detalle",
        "continente", "pais", "puerto",
        "operacion", "surveyor", "honorarios", "costo_operativo", "costo_tarjetas",
        "fecha_inicio", "hora_inicio",
        "fecha_fin", "hora_fin", "demoras", "duracion",
        "factura", "valor_factura", "fecha_factura",
        "terminos_pago", "fecha_vencimiento", "dias_vencido",
        "razon_cancelacion", "comentario_cancelacion"
    ]

    return {c: ("" if r[i] is None else str(r[i])) for i, c in enumerate(columnas)}


@router.delete("/{consec}")
def eliminar_servicio(consec: int, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    try:
        _ensure_tenant_schema()
        company = company_code(None, x_company_code)
        sql = "DELETE FROM servicios WHERE consec = %s AND company_code = %s"
        database.sql(sql, (consec, company))

        return {"status": "ok", "msg": f"Servicio {consec} eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.put("/cancelar/{consec}")
def cancelar_servicio(consec: int, data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    try:
        _ensure_tenant_schema()
        company = company_code(None, x_company_code)
        sql = """
            UPDATE servicios
            SET estado = %(estado)s,
                razon_cancelacion = %(razon_cancelacion)s,
                comentario_cancelacion = %(comentario_cancelacion)s
            WHERE consec = %(consec)s
              AND company_code = %(company_code)s
        """

        params = {
            "estado": data.get("estado", "Cancelado"),
            "razon_cancelacion": data.get("razon_cancelacion", ""),
            "comentario_cancelacion": data.get("comentario_cancelacion", ""),
            "consec": consec
        }

        database.sql(sql, params)
        return {"status": "ok", "msg": f"Servicio {consec} cancelado"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# CONFIRMAR SERVICIO + GENERAR CONSECUTIVO
# ============================================================
@router.put("/confirmar/{consec}")
def confirmar_servicio(consec: int, data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):

    try:
        _ensure_tenant_schema()
        company = company_code(None, x_company_code)

        fecha_inicio = _normalize_service_date(data.get("fecha_inicio"))
        hora_inicio  = data.get("hora_inicio")

        if not fecha_inicio or not hora_inicio:
            raise HTTPException(
                status_code=400,
                detail="Fecha y hora de inicio requeridas"
            )

        # --------------------------------------------------
        # 2. Obtener servicio
        # --------------------------------------------------
        row = database.sql(
            """
            SELECT num_informe
            FROM servicios
            WHERE consec = %s
              AND company_code = %s
            """,
            (consec, company),
            fetch=True
        )

        if not row:
            raise HTTPException(404, "Servicio no encontrado")

        num_existente = row[0][0]

        # --------------------------------------------------
        # 3. Si ya tiene consecutivo → solo actualizar estado
        # --------------------------------------------------
        if num_existente:
            num_actualizado = _num_informe_con_fecha(num_existente, fecha_inicio)
            database.sql(
                """
                UPDATE servicios
                SET
                    fecha_inicio = %s,
                    hora_inicio  = %s,
                    num_informe  = %s,
                    estado       = 'En Operación'
                WHERE consec = %s
                  AND company_code = %s
                """,
                (fecha_inicio, hora_inicio, num_actualizado, consec, company)
            )

            return {
                "status": "ok",
                "num_informe": num_actualizado,
                "generated_now": False
            }

        # --------------------------------------------------
        # 4. Asignar siguiente consecutivo global MSL/MCI
        # --------------------------------------------------
        num_informe = _assign_new_global_report_number(
            consec=consec,
            company=company,
            fecha_inicio=fecha_inicio,
            hora_inicio=hora_inicio,
        )

        return {
            "status": "ok",
            "num_informe": num_informe,
            "generated_now": True
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




@router.put("/demoras/{consec}")
def actualizar_demoras(consec: int, payload: DemoraUpdate, x_company_code: str | None = Header(None, alias="X-Company-Code")):

    try:
        _ensure_tenant_schema()
        company = company_code(None, x_company_code)
        database.sql(
            """
            UPDATE servicios
            SET
                demoras = %(d)s,
                duracion = (
                    EXTRACT(EPOCH FROM (
                        (fecha_fin::date + hora_fin::time)
                        -
                        (fecha_inicio::date + hora_inicio::time)
                    )) / 60
                    - COALESCE(%(d)s, 0)
                )
            WHERE consec = %(c)s
              AND company_code = %(company_code)s
              AND fecha_fin IS NOT NULL
              AND hora_fin IS NOT NULL
            """,
            {
                "d": payload.total,
                "c": consec,
                "company_code": company
            }
        )

        return {
            "status": "ok",
            "msg": "Demoras y duración actualizadas"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# EDITAR SERVICIO (SIN CAMBIAR ESTADO)
# ============================================================
@router.put("/editar/{consec}")
def editar_servicio(consec: int, data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    try:
        _ensure_tenant_schema()
        company = company_code(None, x_company_code)
        data = dict(data)
        for date_key in ("fecha_inicio", "fecha_fin", "fecha_factura", "fecha_vencimiento"):
            if date_key in data:
                data[date_key] = _normalize_service_date(data.get(date_key))
        for time_key in ("hora_inicio", "hora_fin"):
            if time_key in data:
                data[time_key] = _normalize_service_time(data.get(time_key))
        if "fecha_inicio" in data:
            data["fecha_inicio"] = _normalize_service_date(data.get("fecha_inicio"))
        if "hora_inicio" in data:
            data["hora_inicio"] = _normalize_service_time(data.get("hora_inicio"))

        row = database.sql(
            """
            SELECT
                num_informe,
                tipo,
                buque_contenedor,
                cliente,
                contacto,
                detalle,
                continente,
                pais,
                puerto,
                operacion,
                surveyor,
                honorarios,
                costo_operativo,
                costo_tarjetas,
                fecha_inicio,
                hora_inicio,
                fecha_fin,
                hora_fin,
                fecha_factura,
                fecha_vencimiento
            FROM servicios
            WHERE consec = %s
              AND company_code = %s
            """,
            (consec, company),
            fetch=True
        )

        if not row:
            raise HTTPException(404, "Servicio no encontrado")

        current = {
            "tipo": row[0][1],
            "buque_contenedor": row[0][2],
            "cliente": row[0][3],
            "contacto": row[0][4],
            "detalle": row[0][5],
            "continente": row[0][6],
            "pais": row[0][7],
            "puerto": row[0][8],
            "operacion": row[0][9],
            "surveyor": row[0][10],
            "honorarios": row[0][11],
            "costo_operativo": row[0][12],
            "costo_tarjetas": row[0][13],
            "fecha_inicio": row[0][14],
            "hora_inicio": row[0][15],
            "fecha_fin": row[0][16],
            "hora_fin": row[0][17],
            "fecha_factura": row[0][18],
            "fecha_vencimiento": row[0][19],
        }
        effective_fecha_inicio = data["fecha_inicio"] if "fecha_inicio" in data else current["fecha_inicio"]
        num_actualizado = _num_informe_con_fecha(row[0][0], effective_fecha_inicio)

        sql = """
            UPDATE servicios SET
                buque_contenedor = %(buque_contenedor)s,
                cliente = %(cliente)s,
                contacto = %(contacto)s,
                detalle = %(detalle)s,
                continente = %(continente)s,
                pais = %(pais)s,
                puerto = %(puerto)s,
                operacion = %(operacion)s,
                surveyor = %(surveyor)s,
                honorarios = %(honorarios)s,
                costo_operativo = %(costo_operativo)s,
                costo_tarjetas = %(costo_tarjetas)s,
                fecha_inicio = %(fecha_inicio)s,
                hora_inicio = %(hora_inicio)s,
                fecha_fin = %(fecha_fin)s,
                hora_fin = %(hora_fin)s,
                fecha_factura = %(fecha_factura)s,
                fecha_vencimiento = %(fecha_vencimiento)s,
                duracion = CASE
                    WHEN %(fecha_fin)s IS NOT NULL
                     AND NULLIF(%(hora_fin)s, '') IS NOT NULL
                     AND %(fecha_inicio)s IS NOT NULL
                     AND NULLIF(%(hora_inicio)s, '') IS NOT NULL
                    THEN (
                        EXTRACT(EPOCH FROM (
                            (%(fecha_fin)s::date + %(hora_fin)s::time)
                            -
                            (%(fecha_inicio)s::date + %(hora_inicio)s::time)
                        )) / 60
                        - COALESCE(demoras, 0)
                    )
                    ELSE duracion
                END,
                num_informe = %(num_informe)s
            WHERE consec = %(consec)s
              AND company_code = %(company_code)s
        """

        params = {
            "tipo": data["tipo"] if "tipo" in data else current["tipo"],
            "buque_contenedor": data["buque_contenedor"] if "buque_contenedor" in data else current["buque_contenedor"],
            "cliente": data["cliente"] if "cliente" in data else current["cliente"],
            "contacto": data["contacto"] if "contacto" in data else current["contacto"],
            "detalle": data["detalle"] if "detalle" in data else current["detalle"],
            "continente": data["continente"] if "continente" in data else current["continente"],
            "pais": data["pais"] if "pais" in data else current["pais"],
            "puerto": data["puerto"] if "puerto" in data else current["puerto"],
            "operacion": data["operacion"] if "operacion" in data else current["operacion"],
            "surveyor": data["surveyor"] if "surveyor" in data else current["surveyor"],
            "honorarios": data["honorarios"] if "honorarios" in data else current["honorarios"],
            "costo_operativo": data["costo_operativo"] if "costo_operativo" in data else current["costo_operativo"],
            "costo_tarjetas": data["costo_tarjetas"] if "costo_tarjetas" in data else current["costo_tarjetas"],
            "fecha_inicio": data["fecha_inicio"] if "fecha_inicio" in data else current["fecha_inicio"],
            "hora_inicio": data["hora_inicio"] if "hora_inicio" in data else current["hora_inicio"],
            "fecha_fin": data["fecha_fin"] if "fecha_fin" in data else current["fecha_fin"],
            "hora_fin": data["hora_fin"] if "hora_fin" in data else current["hora_fin"],
            "fecha_factura": data["fecha_factura"] if "fecha_factura" in data else current["fecha_factura"],
            "fecha_vencimiento": data["fecha_vencimiento"] if "fecha_vencimiento" in data else current["fecha_vencimiento"],
            "num_informe": num_actualizado,
            "consec": consec,
            "company_code": company
        }
        _validate_required_service_payload(params)
        _validate_location_combo(params)

        database.sql(sql, params)
        return {"status": "ok", "msg": "Servicio actualizado"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================
# CERRAR OPERACIÓN (FECHA Y HORA DE FINALIZACIÓN)
# ============================================================
@router.put("/cerrar/{consec}")
def cerrar_operacion(consec: int, data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)

    fecha_fin = _normalize_service_date(data.get("fecha_fin"))
    hora_fin = data.get("hora_fin")

    if not fecha_fin or not hora_fin:
        raise HTTPException(
            status_code=400,
            detail="Fecha y hora de finalización requeridas"
        )

    try:
        database.sql(
            """
            UPDATE servicios
            SET
                fecha_fin = %(f)s,
                hora_fin  = %(h)s,
                duracion = (
                    EXTRACT(EPOCH FROM (
                        (%(f)s::date + %(h)s::time)
                        -
                        (fecha_inicio::date + hora_inicio::time)
                    )) / 60
                    - COALESCE(demoras, 0)
                )
            WHERE consec = %(c)s
              AND company_code = %(company_code)s
            """,
            {
                "f": fecha_fin,
                "h": hora_fin,
                "c": consec,
                "company_code": company
            }
        )

        return {
            "status": "ok",
            "fecha_fin": fecha_fin,
            "hora_fin": hora_fin,
            "msg": "Operación cerrada y duración calculada"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# FINALIZAR SERVICIO (NO GENERA CONSECUTIVO)
# ============================================================
@router.put("/generar_informe/{consec}")
def generar_informe(consec: int, x_company_code: str | None = Header(None, alias="X-Company-Code")):

    try:
        _ensure_tenant_schema()
        company = company_code(None, x_company_code)
        row = database.sql(
            """
            SELECT num_informe
            FROM servicios
            WHERE consec = %s
              AND company_code = %s
            """,
            (consec, company),
            fetch=True
        )

        if not row:
            raise HTTPException(404, "Servicio no encontrado")

        num_informe = row[0][0]

        if not num_informe:
            raise HTTPException(
                status_code=400,
                detail="El servicio aún no tiene consecutivo generado"
            )

        database.sql(
            """
            UPDATE servicios
            SET estado = 'Finalizado'
            WHERE consec = %s
              AND company_code = %s
            """,
            (consec, company)
        )

        return {
            "status": "ok",
            "num_informe": num_informe,
            "msg": "Servicio finalizado correctamente"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
