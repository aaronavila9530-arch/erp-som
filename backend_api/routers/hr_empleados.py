from fastapi import APIRouter, Depends, Query, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from security.auth import get_current_user   # ✅ MISMO IMPORT QUE hr_events.py


router = APIRouter(
    prefix="/hr/employees",
    tags=["HHRR - Employees"]
)


# =========================================================
# UTIL — RBAC (MISMO CRITERIO QUE OTROS HHRR)
# =========================================================
def _check_admin_role(current_user):
    rol = (current_user.get("rol") or "").lower()
    if rol not in ("admin", "master"):
        raise HTTPException(403, "Acceso denegado")


# =========================================================
# GET — LISTAR EMPLEADOS (LAZY + FILTROS)
# =========================================================
@router.get("")
def listar_empleados(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    nombre: str | None = None,
    codigo: str | None = None,
    estado: str | None = None,
    usuario: str | None = None,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _check_admin_role(current_user)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    where = []
    params = {}

    if nombre:
        where.append("(nombre ILIKE %(nombre)s OR apellidos ILIKE %(nombre)s)")
        params["nombre"] = f"%{nombre}%"

    if codigo:
        where.append("codigo ILIKE %(codigo)s")
        params["codigo"] = f"%{codigo}%"

    if estado:
        where.append("estado = %(estado)s")
        params["estado"] = estado

    if usuario:
        where.append("usuario ILIKE %(usuario)s")
        params["usuario"] = f"%{usuario}%"

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    # TOTAL
    cur.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM empleados
        {where_sql}
        """,
        params
    )
    total = cur.fetchone()["total"]

    offset = (page - 1) * page_size

    # DATA (COLUMNAS USADAS POR LA UI)
    cur.execute(
        f"""
        SELECT
            id,
            codigo,
            nombre,
            apellidos,
            cedula_id,
            usuario,
            estado,
            jornada,
            salario,
            pago,
            banco,
            moneda,
            fecha_ingreso,
            horas_contratadas,
            activo1,
            activo2,
            activo3
        FROM empleados
        {where_sql}
        ORDER BY id
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {
            **params,
            "limit": page_size,
            "offset": offset
        }
    )

    data = cur.fetchall()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": data
    }


# =========================================================
# POST — CREAR EMPLEADO
# =========================================================
@router.post("")
def crear_empleado(
    payload: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _check_admin_role(current_user)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # HELPERS DE NORMALIZACIÓN
    # =====================================================
    def _to_int(v):
        try:
            return int(v)
        except Exception:
            return None

    def _to_float(v):
        try:
            return float(v)
        except Exception:
            return None

    def _to_date(v):
        if not v:
            return None
        try:
            return v  # YYYY-MM-DD válido
        except Exception:
            return None

    def _clean(v):
        if v in ("", "None", None):
            return None
        return v

    # =====================================================
    # 1️⃣ GENERAR CÓDIGO EMPLEADO (MSL-000X-E)
    # =====================================================
    cur.execute("""
        SELECT codigo
        FROM empleados
        WHERE codigo LIKE 'MSL-%-E'
        ORDER BY id DESC
        LIMIT 1
        FOR UPDATE
    """)

    row = cur.fetchone()

    if row and row.get("codigo"):
        try:
            ultimo = int(row["codigo"].split("-")[1])
        except Exception:
            ultimo = 0
    else:
        ultimo = 0

    codigo_generado = f"MSL-{str(ultimo + 1).zfill(4)}-E"

    # =====================================================
    # 2️⃣ PARAMS 1:1 CON TABLA (TIPOS CORRECTOS)
    # =====================================================
    params = {
        "codigo": codigo_generado,

        "nombre": _clean(payload.get("nombre")),
        "apellidos": _clean(payload.get("apellidos")),
        "estado_civil": _clean(payload.get("estado_civil")),
        "genero": _clean(payload.get("genero")),
        "nacionalidad": _clean(payload.get("nacionalidad")),

        "prefijo": _clean(payload.get("prefijo")),
        "telefono": _clean(payload.get("telefono")),
        "provincia": _clean(payload.get("provincia")),
        "canton": _clean(payload.get("canton")),
        "distrito": _clean(payload.get("distrito")),
        "direccion": _clean(payload.get("direccion")),

        "jornada": payload.get("jornada") or "Completa",
        "salario": _to_float(payload.get("salario")),
        "pago": payload.get("pago") or "Mensual",
        "banco": payload.get("banco") or "Sin definir",
        "cuenta_iban": _clean(payload.get("cuenta_iban")),
        "moneda": payload.get("moneda") or "CRC",

        "enfermedades": _clean(payload.get("enfermedades")),
        "contacto_emergencia": _clean(payload.get("contacto_emergencia")),
        "telefono_emergencia": _clean(payload.get("telefono_emergencia")),

        "activo1": _clean(payload.get("activo1")),
        "marca1": _clean(payload.get("marca1")),
        "serial1": _clean(payload.get("serial1")),

        "activo2": _clean(payload.get("activo2")),
        "marca2": _clean(payload.get("marca2")),
        "serial2": _clean(payload.get("serial2")),

        "activo3": _clean(payload.get("activo3")),
        "marca3": _clean(payload.get("marca3")),
        "serial3": _clean(payload.get("serial3")),

        "fecha_ingreso": _to_date(payload.get("fecha_ingreso")),
        "vacaciones": _to_float(payload.get("vacaciones")) or 0,
        "estado": payload.get("estado") or "Activo",

        "horas_contratadas": _to_float(payload.get("horas_contratadas")),
        "usuario": _clean(payload.get("usuario")),
        "cedula_id": _clean(payload.get("cedula_id")),

        "fecha_nacimiento": _to_date(payload.get("fecha_nacimiento")),
        "edad": _to_int(payload.get("edad")),
    }

    # =====================================================
    # 3️⃣ INSERT
    # =====================================================
    sql = """
    INSERT INTO empleados (
        codigo,
        nombre, apellidos, estado_civil, genero, nacionalidad,
        prefijo, telefono, provincia, canton, distrito, direccion,
        jornada, salario, pago, banco, cuenta_iban, moneda,
        enfermedades, contacto_emergencia, telefono_emergencia,
        activo1, marca1, serial1,
        activo2, marca2, serial2,
        activo3, marca3, serial3,
        fecharegistro, fecha_ingreso, vacaciones, estado,
        horas_contratadas, usuario, cedula_id,
        fecha_nacimiento, edad
    )
    VALUES (
        %(codigo)s,
        %(nombre)s, %(apellidos)s, %(estado_civil)s, %(genero)s, %(nacionalidad)s,
        %(prefijo)s, %(telefono)s, %(provincia)s, %(canton)s, %(distrito)s, %(direccion)s,
        %(jornada)s, %(salario)s, %(pago)s, %(banco)s, %(cuenta_iban)s, %(moneda)s,
        %(enfermedades)s, %(contacto_emergencia)s, %(telefono_emergencia)s,
        %(activo1)s, %(marca1)s, %(serial1)s,
        %(activo2)s, %(marca2)s, %(serial2)s,
        %(activo3)s, %(marca3)s, %(serial3)s,
        NOW(), %(fecha_ingreso)s, %(vacaciones)s, %(estado)s,
        %(horas_contratadas)s, %(usuario)s, %(cedula_id)s,
        %(fecha_nacimiento)s, %(edad)s
    )
    """

    try:
        cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error creando empleado: {str(e)}"
        )

    return {
        "status": "ok",
        "codigo_generado": codigo_generado
    }


# =========================================================
# PUT — ACTUALIZAR EMPLEADO
# =========================================================
@router.put("/{empleado_id}")
def actualizar_empleado(
    empleado_id: int,
    payload: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _check_admin_role(current_user)

    if not payload:
        raise HTTPException(400, "No hay datos para actualizar")

    allowed_fields = {
        "codigo", "nombre", "apellidos", "estado_civil", "genero", "nacionalidad",
        "prefijo", "telefono", "provincia", "canton", "distrito", "direccion",
        "jornada", "salario", "pago", "banco", "cuenta_iban", "moneda",
        "enfermedades", "contacto_emergencia", "telefono_emergencia",
        "activo1", "marca1", "serial1",
        "activo2", "marca2", "serial2",
        "activo3", "marca3", "serial3",
        "fecha_ingreso", "vacaciones", "estado",
        "horas_contratadas", "usuario", "cedula_id",
        "fecha_nacimiento", "edad"
    }

    sets = []
    params = {"id": empleado_id}

    for k, v in payload.items():
        if k in allowed_fields:
            sets.append(f"{k} = %({k})s")
            params[k] = v

    if not sets:
        raise HTTPException(400, "No hay campos válidos para actualizar")

    sql = f"""
    UPDATE empleados
    SET {", ".join(sets)}
    WHERE id = %(id)s
    """

    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(400, f"Error actualizando empleado: {str(e)}")

    return {"status": "ok"}
