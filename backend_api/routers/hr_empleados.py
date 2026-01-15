from fastapi import APIRouter, Depends, Query, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db


# =========================================================
# BLINDAJE — IMPORT get_current_user
# Evita crash si el módulo/ruta no existe en tu proyecto.
# =========================================================
def _get_current_user_fallback():
    """
    Fallback seguro: si no se encuentra get_current_user real,
    el backend NO debe crashear. Responde 503 indicando configuración.
    """
    raise HTTPException(
        status_code=503,
        detail="Auth no configurado: get_current_user no disponible."
    )


try:
    # Opción 1: la que yo propuse (si existiera)
    from auth.dependencies import get_current_user  # type: ignore
except Exception:
    try:
        # Opción 2: patrón muy común en tu proyecto (ajustable si existe)
        from dependencies import get_current_user  # type: ignore
    except Exception:
        # Opción 3: fallback que NO crashea
        get_current_user = _get_current_user_fallback  # type: ignore


router = APIRouter(
    prefix="/hr/employees",
    tags=["HHRR - Employees"]
)


# =========================================================
# UTIL — RBAC
# =========================================================
def _check_admin_role(current_user):
    if not isinstance(current_user, dict):
        raise HTTPException(status_code=401, detail="No autenticado")

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
    row_total = cur.fetchone()
    total = int(row_total["total"]) if row_total and row_total.get("total") is not None else 0

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

    # Normalización segura (evita KeyError por campos faltantes)
    params = {
        "codigo": payload.get("codigo"),
        "nombre": payload.get("nombre"),
        "apellidos": payload.get("apellidos"),
        "estado_civil": payload.get("estado_civil"),
        "genero": payload.get("genero"),
        "nacionalidad": payload.get("nacionalidad"),
        "prefijo": payload.get("prefijo"),
        "telefono": payload.get("telefono"),
        "provincia": payload.get("provincia"),
        "canton": payload.get("canton"),
        "distrito": payload.get("distrito"),
        "direccion": payload.get("direccion"),
        "jornada": payload.get("jornada"),
        "salario": payload.get("salario"),
        "pago": payload.get("pago"),
        "banco": payload.get("banco"),
        "cuenta_iban": payload.get("cuenta_iban"),
        "moneda": payload.get("moneda"),
        "enfermedades": payload.get("enfermedades"),
        "contacto_emergencia": payload.get("contacto_emergencia"),
        "telefono_emergencia": payload.get("telefono_emergencia"),
        "activo1": payload.get("activo1"),
        "marca1": payload.get("marca1"),
        "serial1": payload.get("serial1"),
        "activo2": payload.get("activo2"),
        "marca2": payload.get("marca2"),
        "serial2": payload.get("serial2"),
        "activo3": payload.get("activo3"),
        "marca3": payload.get("marca3"),
        "serial3": payload.get("serial3"),
        "fecha_ingreso": payload.get("fecha_ingreso"),
        "vacaciones": payload.get("vacaciones"),
        "estado": payload.get("estado"),
        "horas_contratadas": payload.get("horas_contratadas"),
        "usuario": payload.get("usuario"),
        "cedula_id": payload.get("cedula_id"),
        "fecha_nacimiento": payload.get("fecha_nacimiento"),
        "edad": payload.get("edad"),
    }

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

    try:
        cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error creando empleado: {str(e)}")

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

    if not isinstance(payload, dict) or not payload:
        raise HTTPException(status_code=400, detail="No hay datos para actualizar")

    # Whitelist de campos permitidos para evitar updates peligrosos
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

    for campo, valor in payload.items():
        if campo not in allowed_fields:
            continue
        sets.append(f"{campo} = %({campo})s")
        params[campo] = valor

    if not sets:
        raise HTTPException(status_code=400, detail="No hay campos válidos para actualizar")

    sql = f"""
    UPDATE empleados
    SET {", ".join(sets)}
    WHERE id = %(id)s
    """

    cur = conn.cursor()

    try:
        cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Error actualizando empleado: {str(e)}")

    return {"status": "ok", "message": "Empleado actualizado correctamente"}
