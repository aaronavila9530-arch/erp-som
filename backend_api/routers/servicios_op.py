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
    fecha_inicio: str    # "YYYY-MM-DD"
    hora_inicio: str     # "HH:MM"


# ============================================================
# INSERTAR SERVICIO
# ============================================================
@router.post("/add")
def add_servicio(data: ServicioCreate):

    sql = """
        INSERT INTO servicios (
            tipo, estado, num_informe,
            buque_contenedor, cliente, contacto, detalle,
            continente, pais, puerto,
            operacion, surveyor, honorarios, costo_operativo,
            fecha_inicio, hora_inicio
        )
        VALUES (
            %(tipo)s, 'Buque por confirmar', '',
            %(buque_contenedor)s, %(cliente)s, %(contacto)s, %(detalle)s,
            %(continente)s, %(pais)s, %(puerto)s,
            %(operacion)s, %(surveyor)s, %(honorarios)s, %(costo_operativo)s,
            %(fecha_inicio)s, %(hora_inicio)s
        )
        RETURNING consec;
    """

    try:
        result = database.sql(sql, data.dict(), fetch=True)
        new_id = result[0][0]
        return {"status": "OK", "msg": "Servicio creado", "consec": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from datetime import datetime

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

    # --------------------------------------------------------
    # DEFAULT: si NO hay filtros → año en curso
    # --------------------------------------------------------
    if year is None and status is None and surveyor is None:
        year = datetime.now().year

    conditions = []
    params = {}

    # -------------------------
    # AÑO (desde num_informe)
    # -------------------------
    if year is not None:
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
            operacion, surveyor, honorarios, costo_operativo,
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
        "operacion", "surveyor", "honorarios", "costo_operativo",
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
            operacion, surveyor, honorarios, costo_operativo,
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
        "operacion", "surveyor", "honorarios", "costo_operativo",
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




@router.put("/por_confirmar/{consec}")
def marcar_por_confirmar(consec: int):
    try:
        sql = """
            UPDATE servicios
            SET estado = 'Por confirmar'
            WHERE consec = %s
        """
        database.sql(sql, (consec,))
        return {"status": "ok", "msg": f"Servicio {consec} marcado como 'Por confirmar'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/confirmar/{consec}")
def confirmar_servicio(consec: int, data: dict):
    try:
        sql = """
            UPDATE servicios
            SET fecha_inicio = %(fecha_inicio)s,
                hora_inicio = %(hora_inicio)s,
                estado = 'Confirmado'
            WHERE consec = %(consec)s
        """
        params = {
            "fecha_inicio": data.get("fecha_inicio"),
            "hora_inicio": data.get("hora_inicio"),
            "consec": consec
        }

        database.sql(sql, params)
        return {"status": "ok", "msg": f"Servicio {consec} confirmado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




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
        sql = """
            UPDATE servicios SET
                surveyor = %(surveyor)s,
                honorarios = %(honorarios)s,
                costo_operativo = %(costo_operativo)s,
                fecha_inicio = %(fecha_inicio)s,
                hora_inicio = %(hora_inicio)s
            WHERE consec = %(consec)s
        """

        params = {
            "surveyor": data.get("surveyor"),
            "honorarios": data.get("honorarios"),
            "costo_operativo": data.get("costo_operativo"),
            "fecha_inicio": data.get("fecha_inicio"),
            "hora_inicio": data.get("hora_inicio"),
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

    fecha_fin = data.get("fecha_fin")
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
# GENERAR INFORME (NUM_INFORME + FINALIZAR)
# ============================================================
@router.put("/generar_informe/{consec}")
def generar_informe(consec: int):
    try:
        # --------------------------------------------------
        # 1. Obtener fecha de inicio
        # --------------------------------------------------
        row = database.sql(
            "SELECT fecha_inicio FROM servicios WHERE consec = %s",
            (consec,),
            fetch=True
        )

        if not row or not row[0][0]:
            raise HTTPException(
                status_code=400,
                detail="Servicio sin fecha de inicio"
            )

        fecha_inicio = row[0][0]

        if isinstance(fecha_inicio, str):
            fecha_dt = datetime.strptime(fecha_inicio[:10], "%Y-%m-%d")
        else:
            fecha_dt = fecha_inicio

        ddmm = fecha_dt.strftime("%d%m")
        year = fecha_dt.strftime("%Y")

        # --------------------------------------------------
        # 2. Obtener último consecutivo
        #    BASE = 2139 si no hay informes aún
        # --------------------------------------------------
        max_row = database.sql(
            """
            SELECT COALESCE(
                MAX(
                    NULLIF(split_part(num_informe, '-', 1), '')::int
                ),
                2139
            )
            FROM servicios
            WHERE num_informe IS NOT NULL
              AND num_informe <> ''
            """,
            fetch=True
        )

        ultimo = int(max_row[0][0])
        nuevo = ultimo + 1

        num_informe = f"{nuevo}-{ddmm}-{year}"

        # --------------------------------------------------
        # 3. Actualizar servicio
        # --------------------------------------------------
        database.sql(
            """
            UPDATE servicios
            SET num_informe = %s,
                estado = 'Finalizado'
            WHERE consec = %s
            """,
            (num_informe, consec)
        )

        return {
            "status": "ok",
            "num_informe": num_informe
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

