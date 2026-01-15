from fastapi import APIRouter, Depends, Query, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from auth.dependencies import get_current_user


router = APIRouter(
    prefix="/hr/employees",
    tags=["HHRR - Employees"]
)


# =========================================================
# UTIL — RBAC
# =========================================================
def _check_admin_role(current_user):
    rol = (current_user.get("rol") or "").lower()
    if rol not in ("admin", "master"):
        raise HTTPException(status_code=403, detail="Acceso denegado")


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

    # DATA
    cur.execute(
        f"""
        SELECT
            id,
            codigo,
            nombre,
            apellidos,
            estado_civil,
            genero,
            nacionalidad,
            prefijo,
            telefono,
            provincia,
            canton,
            distrito,
            direccion,
            jornada,
            salario,
            pago,
            banco,
            cuenta_iban,
            moneda,
            enfermedades,
            contacto_emergencia,
            telefono_emergencia,
            activo1,
            marca1,
            serial1,
            activo2,
            marca2,
            serial2,
            activo3,
            marca3,
            serial3,
            fecharegistro,
            fecha_ingreso,
            vacaciones,
            estado,
            horas_contratadas,
            usuario,
            cedula_id,
            fecha_nacimiento,
            edad
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

    cur = conn.cursor()

    sql = """
    INSERT INTO empleados (
        codigo, nombre, apellidos, estado_civil, genero, nacionalidad,
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
        %(codigo)s, %(nombre)s, %(apellidos)s, %(estado_civil)s, %(genero)s, %(nacionalidad)s,
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

    cur.execute(sql, payload)
    conn.commit()

    return {"status": "ok", "message": "Empleado creado correctamente"}


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

    sets = []
    params = payload.copy()
    params["id"] = empleado_id

    for campo in payload.keys():
        sets.append(f"{campo} = %({campo})s")

    if not sets:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")

    sql = f"""
    UPDATE empleados
    SET {", ".join(sets)}
    WHERE id = %(id)s
    """

    cur = conn.cursor()
    cur.execute(sql, params)
    conn.commit()

    return {"status": "ok", "message": "Empleado actualizado correctamente"}
