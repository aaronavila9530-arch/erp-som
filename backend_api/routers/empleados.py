from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel
import database
import psycopg2
import os

from rbac_service import has_permission
from services.tenanting import company_code, company_prefix, ensure_company_column
from services.employee_hours_policy_schema import ensure_employee_hours_policy_columns

DB_URL = os.getenv("DATABASE_URL") or database.DATABASE_URL

router = APIRouter(prefix="/empleados", tags=["Empleados"])


def _ensure_tenant_schema():
    ensure_company_column("empleados")
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()
        ensure_employee_hours_policy_columns(cursor)
        conn.commit()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# RBAC — GUARD (UNA SOLA VEZ POR ROUTER)
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



class Empleado(BaseModel):
    codigo: str
    nombre: str
    apellidos: str
    estado_civil: str | None = None
    genero: str | None = None
    nacionalidad: str | None = None
    prefijo: str | None = None
    telefono: str | None = None
    provincia: str | None = None
    canton: str | None = None
    distrito: str | None = None
    direccion: str | None = None
    jornada: str | None = None
    salario: str | None = None
    horas_contratadas: str | None = None
    horas_tope_ordinario: str | None = None
    horas_tope_maximo: str | None = None
    tarifa_hora_extra: str | None = None
    pago_minimo_garantizado: bool | None = False
    pago: str | None = None
    banco: str | None = None
    cuenta_iban: str | None = None
    moneda: str | None = None
    enfermedades: str | None = None
    contacto_emergencia: str | None = None
    telefono_emergencia: str | None = None
    activo1: str | None = None
    marca1: str | None = None
    serial1: str | None = None
    activo2: str | None = None
    marca2: str | None = None
    serial2: str | None = None
    activo3: str | None = None
    marca3: str | None = None
    serial3: str | None = None
    company_code: str | None = None


@router.post("/add")
def agregar_empleado(emp: Empleado, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    conn = None
    cursor = None

    try:
        _ensure_tenant_schema()
        company = company_code(emp.company_code, x_company_code)
        prefix = company_prefix(company)
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        # ============================================================
        # OBTENER ÚLTIMO CÓDIGO DE EMPLEADO
        # FORMATO: MSL-0001-E
        # ============================================================
        cursor.execute("""
            SELECT codigo
            FROM empleados
            WHERE company_code = %s
              AND codigo LIKE %s
            ORDER BY
                CAST(SUBSTRING(codigo FROM 5 FOR 4) AS INTEGER) DESC
            LIMIT 1
        """, (company, f"{prefix}-%-E"))
        row = cursor.fetchone()

        if row:
            last_code = row[0]          # ej: MSL-0007-E
            last_number = int(last_code[4:8])
            next_number = last_number + 1
        else:
            next_number = 1

        nuevo_codigo = f"{prefix}-{next_number:04d}-E"

        # ============================================================
        # PREPARAR DATA (SOBRESCRIBE CÓDIGO)
        # ============================================================
        data = emp.dict()
        data["codigo"] = nuevo_codigo
        data["company_code"] = company

        # Blindaje numericos laborales
        for numeric_key in ("salario", "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo", "tarifa_hora_extra"):
            if data.get(numeric_key):
                try:
                    data[numeric_key] = float(str(data[numeric_key]).replace(",", ""))
                except ValueError:
                    data[numeric_key] = None
            else:
                data[numeric_key] = None

        if not data.get("horas_tope_ordinario"):
            data["horas_tope_ordinario"] = data.get("horas_contratadas")

        if data.get("pago_minimo_garantizado") is None:
            data["pago_minimo_garantizado"] = False

        # Compatibilidad con payloads viejos
        if data.get("salario"):
            try:
                data["salario"] = float(data["salario"])
            except ValueError:
                data["salario"] = None
        else:
            data["salario"] = None

        # ============================================================
        # INSERT
        # ============================================================
        cursor.execute("""
            INSERT INTO empleados (
                company_code, codigo, nombre, apellidos, estado_civil, genero, nacionalidad,
                prefijo, telefono, provincia, canton, distrito, direccion,
                jornada, salario, horas_contratadas, horas_tope_ordinario, horas_tope_maximo,
                tarifa_hora_extra, pago_minimo_garantizado, pago, banco, cuenta_iban, moneda,
                enfermedades, contacto_emergencia, telefono_emergencia,
                activo1, marca1, serial1,
                activo2, marca2, serial2,
                activo3, marca3, serial3
            )
            VALUES (
                %(company_code)s, %(codigo)s, %(nombre)s, %(apellidos)s, %(estado_civil)s, %(genero)s, %(nacionalidad)s,
                %(prefijo)s, %(telefono)s, %(provincia)s, %(canton)s, %(distrito)s, %(direccion)s,
                %(jornada)s, %(salario)s, %(horas_contratadas)s, %(horas_tope_ordinario)s, %(horas_tope_maximo)s,
                %(tarifa_hora_extra)s, %(pago_minimo_garantizado)s, %(pago)s, %(banco)s, %(cuenta_iban)s, %(moneda)s,
                %(enfermedades)s, %(contacto_emergencia)s, %(telefono_emergencia)s,
                %(activo1)s, %(marca1)s, %(serial1)s,
                %(activo2)s, %(marca2)s, %(serial2)s,
                %(activo3)s, %(marca3)s, %(serial3)s
            );
        """, data)

        conn.commit()

        return {
            "status": "OK",
            "msg": "Empleado registrado 💾✔",
            "codigo": nuevo_codigo
        }

    except Exception as e:
        print("❌ Error API empleados:", str(e))
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# ============================================================
# LISTAR empleados — paginado
# ============================================================
@router.get("/")
def get_empleados(
    page: int = 1,
    page_size: int = 50,
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    offset = (page - 1) * page_size

    rows = database.sql("""
        SELECT
            codigo, nombre, apellidos, estado_civil, genero, nacionalidad,
            prefijo, telefono, provincia, canton, distrito, direccion,
            jornada, salario, horas_contratadas, horas_tope_ordinario, horas_tope_maximo,
            tarifa_hora_extra, pago_minimo_garantizado, pago, banco, cuenta_iban, moneda,
            enfermedades, contacto_emergencia, telefono_emergencia,
            activo1, marca1, serial1,
            activo2, marca2, serial2,
            activo3, marca3, serial3,
            fecharegistro
        FROM empleados
        WHERE company_code = %s
        ORDER BY codigo ASC
        LIMIT %s OFFSET %s
    """, (company, page_size, offset), fetch=True)

    total = database.sql("SELECT COUNT(*) FROM empleados WHERE company_code = %s", (company,), fetch=True)[0][0]

    columnas = [
        "codigo", "nombre", "apellidos", "estado_civil", "genero", "nacionalidad",
        "prefijo", "telefono", "provincia", "canton", "distrito", "direccion",
        "jornada", "salario", "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo",
        "tarifa_hora_extra", "pago_minimo_garantizado", "pago", "banco", "cuenta_iban", "moneda",
        "enfermedades", "contacto_emergencia", "telefono_emergencia",
        "activo1", "marca1", "serial1",
        "activo2", "marca2", "serial2",
        "activo3", "marca3", "serial3",
        "fecharegistro"
    ]

    data = []
    for r in rows:
        item = {}
        for i, c in enumerate(columnas):
            v = r[i]
            item[c] = "" if v is None else str(v)
        data.append(item)

    return {"data": data, "total": total}


# ============================================================
# GET por código
# ============================================================
@router.get("/{codigo}")
def get_empleado(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    row = database.sql("""
        SELECT
            codigo, nombre, apellidos, estado_civil, genero, nacionalidad,
            prefijo, telefono, provincia, canton, distrito, direccion,
            jornada, salario, horas_contratadas, horas_tope_ordinario, horas_tope_maximo,
            tarifa_hora_extra, pago_minimo_garantizado, pago, banco, cuenta_iban, moneda,
            enfermedades, contacto_emergencia, telefono_emergencia,
            activo1, marca1, serial1,
            activo2, marca2, serial2,
            activo3, marca3, serial3,
            fecharegistro
        FROM empleados
        WHERE codigo = %s
          AND company_code = %s
    """, (codigo, company), fetch=True)

    if not row:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    r = row[0]
    columnas = [
        "codigo", "nombre", "apellidos", "estado_civil", "genero", "nacionalidad",
        "prefijo", "telefono", "provincia", "canton", "distrito", "direccion",
        "jornada", "salario", "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo",
        "tarifa_hora_extra", "pago_minimo_garantizado", "pago", "banco", "cuenta_iban", "moneda",
        "enfermedades", "contacto_emergencia", "telefono_emergencia",
        "activo1", "marca1", "serial1",
        "activo2", "marca2", "serial2",
        "activo3", "marca3", "serial3",
        "fecharegistro"
    ]

    return {c: ("" if r[i] is None else str(r[i])) for i, c in enumerate(columnas)}


# ============================================================
# UPDATE — alineado con front
# ============================================================
@router.put("/update")
def update_empleado(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    data = dict(data or {})
    data["company_code"] = company_code(data.get("company_code"), x_company_code)
    for key in (
        "nombre", "apellidos", "estado_civil", "genero", "prefijo", "telefono",
        "provincia", "canton", "distrito", "direccion", "jornada", "salario",
        "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo",
        "tarifa_hora_extra", "pago_minimo_garantizado", "pago", "banco",
        "cuenta_iban", "moneda", "enfermedades", "contacto_emergencia",
        "telefono_emergencia", "activo1", "marca1", "serial1", "activo2",
        "marca2", "serial2", "activo3", "marca3", "serial3",
    ):
        data.setdefault(key, None)
    for key in ("salario", "horas_contratadas", "horas_tope_ordinario", "horas_tope_maximo", "tarifa_hora_extra"):
        value = data.get(key)
        if value in ("", None, "None"):
            data[key] = None
            continue
        try:
            data[key] = float(str(value).replace(",", ""))
        except Exception:
            data[key] = None
    if not data.get("horas_tope_ordinario"):
        data["horas_tope_ordinario"] = data.get("horas_contratadas")
    data["pago_minimo_garantizado"] = bool(data.get("pago_minimo_garantizado"))
    sql = """
        UPDATE empleados SET
            nombre = %(nombre)s,
            apellidos = %(apellidos)s,
            estado_civil = %(estado_civil)s,
            genero = %(genero)s,
            prefijo = %(prefijo)s,
            telefono = %(telefono)s,
            provincia = %(provincia)s,
            canton = %(canton)s,
            distrito = %(distrito)s,
            direccion = %(direccion)s,
            jornada = %(jornada)s,
            salario = %(salario)s,
            horas_contratadas = %(horas_contratadas)s,
            horas_tope_ordinario = %(horas_tope_ordinario)s,
            horas_tope_maximo = %(horas_tope_maximo)s,
            tarifa_hora_extra = %(tarifa_hora_extra)s,
            pago_minimo_garantizado = %(pago_minimo_garantizado)s,
            pago = %(pago)s,
            banco = %(banco)s,
            cuenta_iban = %(cuenta_iban)s,
            moneda = %(moneda)s,
            enfermedades = %(enfermedades)s,
            contacto_emergencia = %(contacto_emergencia)s,
            telefono_emergencia = %(telefono_emergencia)s,
            activo1 = %(activo1)s,
            marca1 = %(marca1)s,
            serial1 = %(serial1)s,
            activo2 = %(activo2)s,
            marca2 = %(marca2)s,
            serial2 = %(serial2)s,
            activo3 = %(activo3)s,
            marca3 = %(marca3)s,
            serial3 = %(serial3)s
        WHERE codigo = %(codigo)s
          AND company_code = %(company_code)s
    """
    database.sql(sql, data)
    return {"status": "OK", "msg": "Empleado actualizado ✔"}


# ============================================================
# DELETE
# ============================================================
@router.delete("/{codigo}")
def delete_empleado(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    database.sql("DELETE FROM empleados WHERE codigo = %s AND company_code = %s", (codigo, company))
    return {"status": "OK", "msg": "Empleado eliminado 🗑️"}
