from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from datetime import datetime
import database

from rbac_service import has_permission

router = APIRouter(prefix="/servicios", tags=["Servicios"])

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
def add_servicio(data: ServicioCreate):
    payload = data.dict()
    payload["fecha_inicio"] = _normalize_service_date(payload.get("fecha_inicio"))

    sql = """
        INSERT INTO servicios (
            tipo, estado, num_informe,
            buque_contenedor, cliente, contacto, detalle,
            continente, pais, puerto,
            operacion, surveyor, honorarios, costo_operativo, costo_tarjetas,
            fecha_inicio, hora_inicio
        )
        VALUES (
            %(tipo)s, 'Confirmado', '',
            %(buque_contenedor)s, %(cliente)s, %(contacto)s, %(detalle)s,
            %(continente)s, %(pais)s, %(puerto)s,
            %(operacion)s, %(surveyor)s, %(honorarios)s, %(costo_operativo)s, %(costo_tarjetas)s,
            %(fecha_inicio)s, %(hora_inicio)s
        )
        RETURNING consec;
    """

    try:
        result = database.sql(sql, payload, fetch=True)
        new_id = result[0][0]
        return {"status": "OK", "msg": "Servicio creado", "consec": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================
# META — FILTROS DINÁMICOS (A PRUEBA DE COLISIONES)
# GET /servicios/_meta/filtros
# ============================================================
@router.get("/_meta/filtros")
def listar_filtros_servicios():

    rows = database.sql(
        """
        SELECT
            estado,
            surveyor,
            RIGHT(num_informe, 4) AS anio
        FROM servicios
        WHERE num_informe IS NOT NULL
          AND LENGTH(num_informe) >= 4
        """,
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
    surveyor: str | None = None
):
    offset = (page - 1) * page_size

    # --------------------------------------------------------
    # NORMALIZAR INPUTS (blindaje contra strings vacíos)
    # --------------------------------------------------------
    if isinstance(status, str) and status.strip() == "":
        status = None

    if isinstance(surveyor, str) and surveyor.strip() == "":
        surveyor = None

    conditions = []
    params = {}

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
def get_servicio(consec: int):
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
    """, (consec,), fetch=True)

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
def eliminar_servicio(consec: int):
    try:
        sql = "DELETE FROM servicios WHERE consec = %s"
        database.sql(sql, (consec,))

        return {"status": "ok", "msg": f"Servicio {consec} eliminado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





@router.put("/cancelar/{consec}")
def cancelar_servicio(consec: int, data: dict):
    try:
        sql = """
            UPDATE servicios
            SET estado = %(estado)s,
                razon_cancelacion = %(razon_cancelacion)s,
                comentario_cancelacion = %(comentario_cancelacion)s
            WHERE consec = %(consec)s
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
def confirmar_servicio(consec: int, data: dict):

    try:
        # --------------------------------------------------
        # 1. Lock para evitar doble ejecución
        # --------------------------------------------------
        database.sql(
            "SELECT pg_advisory_lock(%s)",
            (consec,),
            fetch=False
        )

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
            """,
            (consec,),
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
                """,
                (fecha_inicio, hora_inicio, num_actualizado, consec)
            )

            return {
                "status": "ok",
                "num_informe": num_actualizado,
                "generated_now": False
            }

        # --------------------------------------------------
        # 4. Buscar siguiente consecutivo libre
        # --------------------------------------------------
        base = 2141
        candidato = base + 1

        while True:
            existe = database.sql(
                """
                SELECT 1
                FROM servicios
                WHERE
                    num_informe IS NOT NULL
                    AND num_informe <> ''
                    AND split_part(num_informe, '-', 1) ~ '^[0-9]+$'
                    AND split_part(num_informe, '-', 1)::int = %s
                """,
                (candidato,),
                fetch=True
            )

            if not existe:
                break

            candidato += 1

        # --------------------------------------------------
        # 5. Construir num_informe usando fecha_inicio
        # --------------------------------------------------
        fecha_dt = _parse_service_date(fecha_inicio)

        num_informe = f"{candidato}-{fecha_dt.strftime('%d%m')}-{fecha_dt.strftime('%Y')}"

        # --------------------------------------------------
        # 6. Guardar todo
        # --------------------------------------------------
        database.sql(
            """
            UPDATE servicios
            SET
                fecha_inicio = %s,
                hora_inicio  = %s,
                num_informe  = %s,
                estado       = 'En Operación'
            WHERE consec = %s
            """,
            (fecha_inicio, hora_inicio, num_informe, consec)
        )

        return {
            "status": "ok",
            "num_informe": num_informe,
            "generated_now": True
        }

    finally:
        database.sql(
            "SELECT pg_advisory_unlock(%s)",
            (consec,),
            fetch=False
        )




@router.put("/demoras/{consec}")
def actualizar_demoras(consec: int, payload: DemoraUpdate):

    try:
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
              AND fecha_fin IS NOT NULL
              AND hora_fin IS NOT NULL
            """,
            {
                "d": payload.total,
                "c": consec
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
def editar_servicio(consec: int, data: dict):
    try:
        data = dict(data)
        data["fecha_inicio"] = _normalize_service_date(data.get("fecha_inicio"))

        row = database.sql(
            """
            SELECT
                num_informe,
                buque_contenedor,
                cliente,
                contacto,
                detalle,
                continente,
                pais,
                puerto,
                operacion
            FROM servicios
            WHERE consec = %s
            """,
            (consec,),
            fetch=True
        )

        if not row:
            raise HTTPException(404, "Servicio no encontrado")

        num_actualizado = _num_informe_con_fecha(row[0][0], data.get("fecha_inicio"))
        current = {
            "buque_contenedor": row[0][1],
            "cliente": row[0][2],
            "contacto": row[0][3],
            "detalle": row[0][4],
            "continente": row[0][5],
            "pais": row[0][6],
            "puerto": row[0][7],
            "operacion": row[0][8],
        }

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
                num_informe = %(num_informe)s
            WHERE consec = %(consec)s
        """

        params = {
            "buque_contenedor": data["buque_contenedor"] if "buque_contenedor" in data else current["buque_contenedor"],
            "cliente": data["cliente"] if "cliente" in data else current["cliente"],
            "contacto": data["contacto"] if "contacto" in data else current["contacto"],
            "detalle": data["detalle"] if "detalle" in data else current["detalle"],
            "continente": data["continente"] if "continente" in data else current["continente"],
            "pais": data["pais"] if "pais" in data else current["pais"],
            "puerto": data["puerto"] if "puerto" in data else current["puerto"],
            "operacion": data["operacion"] if "operacion" in data else current["operacion"],
            "surveyor": data.get("surveyor"),
            "honorarios": data.get("honorarios"),
            "costo_operativo": data.get("costo_operativo"),
            "costo_tarjetas": data.get("costo_tarjetas"),
            "fecha_inicio": data.get("fecha_inicio"),
            "hora_inicio": data.get("hora_inicio"),
            "num_informe": num_actualizado,
            "consec": consec
        }

        database.sql(sql, params)
        return {"status": "ok", "msg": "Servicio actualizado"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# ============================================================
# CERRAR OPERACIÓN (FECHA Y HORA DE FINALIZACIÓN)
# ============================================================
@router.put("/cerrar/{consec}")
def cerrar_operacion(consec: int, data: dict):

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
            """,
            {
                "f": fecha_fin,
                "h": hora_fin,
                "c": consec
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
def generar_informe(consec: int):

    try:
        row = database.sql(
            """
            SELECT num_informe
            FROM servicios
            WHERE consec = %s
            """,
            (consec,),
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
            """,
            (consec,)
        )

        return {
            "status": "ok",
            "num_informe": num_informe,
            "msg": "Servicio finalizado correctamente"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
