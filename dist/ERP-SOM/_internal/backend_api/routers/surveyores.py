from fastapi import APIRouter, HTTPException
import database
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from rbac_service import has_permission
from services.tenanting import company_code, company_prefix, ensure_company_column, set_payload_company

router = APIRouter(prefix="/surveyores", tags=["Surveyores"])
_tarifas_table_checked = False


def _ensure_tenant_schema():
    ensure_company_column("surveyor")


def _ensure_tarifas_table():
    global _tarifas_table_checked
    if _tarifas_table_checked:
        return
    database.sql("""
        CREATE TABLE IF NOT EXISTS surveyor_tarifas (
            id SERIAL PRIMARY KEY,
            surveyor_codigo TEXT NOT NULL,
            puerto TEXT NOT NULL,
            servicio TEXT NOT NULL,
            honorario NUMERIC(14, 2),
            moneda TEXT DEFAULT 'USD',
            activo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (surveyor_codigo, puerto, servicio)
        )
    """)
    _tarifas_table_checked = True


def _clean_tarifas(data: dict) -> list[dict]:
    tarifas = data.get("tarifas")
    if not isinstance(tarifas, list):
        return []

    cleaned = []
    for item in tarifas:
        if not isinstance(item, dict):
            continue
        puerto = str(item.get("puerto") or "").strip()
        servicio = str(item.get("servicio") or item.get("operacion") or "").strip()
        honorario_raw = str(item.get("honorario") or "").strip().replace(",", "")
        moneda = str(item.get("moneda") or data.get("moneda") or "USD").strip() or "USD"
        if not puerto and not servicio and not honorario_raw:
            continue
        honorario = None
        if honorario_raw:
            try:
                honorario = float(honorario_raw)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Honorario invalido: {honorario_raw}")
        cleaned.append({
            "puerto": puerto,
            "servicio": servicio,
            "honorario": honorario,
            "moneda": moneda,
        })
    return cleaned


def _sync_legacy_fields(data: dict) -> dict:
    tarifas = _clean_tarifas(data)
    if tarifas:
        first = tarifas[0]
        data["puerto"] = data.get("puerto") or first["puerto"]
        data["operacion"] = data.get("operacion") or first["servicio"]
        data["honorario"] = data.get("honorario") or ("" if first["honorario"] is None else first["honorario"])
    data.setdefault("puerto", "")
    data.setdefault("operacion", "")
    data.setdefault("honorario", None)
    data.setdefault("email", "")
    data.setdefault("direccion_banco", "")
    if str(data.get("honorario") or "").strip() == "":
        data["honorario"] = None
    data["_tarifas_clean"] = tarifas
    return data


def _save_tarifas(codigo: str, tarifas: list[dict]):
    _ensure_tarifas_table()
    database.sql("DELETE FROM surveyor_tarifas WHERE surveyor_codigo = %s", (codigo,))
    for item in tarifas:
        if not item["puerto"] and not item["servicio"]:
            continue
        database.sql("""
            INSERT INTO surveyor_tarifas (
                surveyor_codigo, puerto, servicio, honorario, moneda, activo, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
            ON CONFLICT (surveyor_codigo, puerto, servicio)
            DO UPDATE SET
                honorario = EXCLUDED.honorario,
                moneda = EXCLUDED.moneda,
                activo = TRUE,
                updated_at = NOW()
        """, (
            codigo,
            item["puerto"],
            item["servicio"],
            item["honorario"],
            item["moneda"],
        ))


def _get_tarifas(codigo: str) -> list[dict]:
    try:
        _ensure_tarifas_table()
        rows = database.sql("""
            SELECT puerto, servicio, honorario, moneda
            FROM surveyor_tarifas
            WHERE surveyor_codigo = %s AND COALESCE(activo, TRUE) = TRUE
            ORDER BY puerto ASC, servicio ASC
        """, (codigo,), fetch=True)
    except Exception:
        rows = []
    return [
        {
            "puerto": r[0],
            "servicio": r[1],
            "honorario": float(r[2]) if r[2] is not None else None,
            "moneda": r[3] or "USD",
        }
        for r in rows
    ]

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



@router.post("/add")
def add_surveyor(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    try:
        _ensure_tenant_schema()
        data = set_payload_company(data, company_code(data.get("company_code"), x_company_code))
        sql = """
        INSERT INTO surveyor (
            company_code,
            codigo,
            nombre,
            apellidos,
            email,
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
            operacion,
            honorario,
            pago,
            banco,
            direccion_banco,
            cuenta_iban,
            moneda,
            swift,
            uid,
            enfermedades,
            contacto_emergencia,
            telefono_emergencia,
            puerto
        )
        VALUES (
            %(company_code)s,
            %(codigo)s,
            %(nombre)s,
            %(apellidos)s,
            %(email)s,
            %(estado_civil)s,
            %(genero)s,
            %(nacionalidad)s,
            %(prefijo)s,
            %(telefono)s,
            %(provincia)s,
            %(canton)s,
            %(distrito)s,
            %(direccion)s,
            %(jornada)s,
            %(operacion)s,
            %(honorario)s,
            %(pago)s,
            %(banco)s,
            %(direccion_banco)s,
            %(cuenta_iban)s,
            %(moneda)s,
            %(swift)s,
            %(uid)s,
            %(enfermedades)s,
            %(contacto_emergencia)s,
            %(telefono_emergencia)s,
            %(puerto)s
        );
        """
        data = _sync_legacy_fields(data)
        database.sql(sql, data)
        _save_tarifas(data["codigo"], data.get("_tarifas_clean", []))
        return {"status": "OK", "msg": "Surveyor registrado 💾✔"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# OBTENER ÚLTIMO CÓDIGO CORRELATIVO
# ============================================================
@router.get("/ultimo")
def get_ultimo_surveyor(company_code_param: str | None = Query(None, alias="company_code"), x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    prefix = company_prefix(company)
    sql = """
        SELECT MAX(CAST(SUBSTRING(codigo FROM 5 FOR 4) AS INTEGER))
        FROM surveyor
        WHERE company_code = %s
          AND codigo LIKE %s;
    """
    result = database.sql(sql, (company, f"{prefix}-%-S"), fetch=True)
    ultimo = result[0][0] if result and result[0][0] is not None else 0
    return {"ultimo": ultimo}


# ============================================================
# LISTAR SURVEYORS — PAGINADO
# ============================================================
@router.get("/")
def get_surveyores(
    page: int = 1,
    page_size: int = 50,
    company_code_param: str | None = Query(None, alias="company_code"),
    x_company_code: str | None = Header(None, alias="X-Company-Code"),
):
    _ensure_tenant_schema()
    company = company_code(company_code_param, x_company_code)
    offset = (page - 1) * page_size

    rows = database.sql(f"""
        SELECT
            codigo,nombre,apellidos,estado_civil,genero,nacionalidad,
            prefijo,telefono,provincia,canton,distrito,direccion,
            jornada,operacion,honorario,pago,banco,cuenta_iban,
            moneda,swift,uid,enfermedades,contacto_emergencia,
            telefono_emergencia,puerto,email,direccion_banco
        FROM surveyor
        WHERE company_code = %(company_code)s
        ORDER BY codigo ASC
        LIMIT {page_size} OFFSET {offset}
    """, {"company_code": company}, fetch=True)

    total = database.sql("SELECT COUNT(*) FROM surveyor WHERE company_code = %s", (company,), fetch=True)[0][0]

    data = [
        {
            "codigo": r[0],
            "nombre": r[1],
            "apellidos": r[2],
            "estado_civil": r[3],
            "genero": r[4],
            "nacionalidad": r[5],
            "prefijo": r[6],
            "telefono": r[7],
            "provincia": r[8],
            "canton": r[9],
            "distrito": r[10],
            "direccion": r[11],
            "jornada": r[12],
            "operacion": r[13],
            "honorario": r[14],
            "pago": r[15],
            "banco": r[16],
            "cuenta_iban": r[17],
            "moneda": r[18],
            "swift": r[19],
            "uid": r[20],
            "enfermedades": r[21],
            "contacto_emergencia": r[22],
            "telefono_emergencia": r[23],
            "puerto": r[24],
            "email": r[25],
            "direccion_banco": r[26],
            "tarifas": _get_tarifas(r[0]),
        }
        for r in rows
    ]

    return {"total": total, "data": data}


# ============================================================
# OBTENER UN SURVEYOR POR CÓDIGO
# ============================================================
@router.get("/{codigo}")
def get_surveyor(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    company = company_code(None, x_company_code)
    row = database.sql("""
        SELECT
            codigo,nombre,apellidos,estado_civil,genero,nacionalidad,
            prefijo,telefono,provincia,canton,distrito,direccion,
            jornada,operacion,honorario,pago,banco,cuenta_iban,
            moneda,swift,uid,enfermedades,contacto_emergencia,
            telefono_emergencia,puerto,email,direccion_banco
        FROM surveyor
        WHERE codigo = %s
          AND company_code = %s
    """, (codigo, company), fetch=True)

    if not row:
        raise HTTPException(status_code=404, detail="Surveyor no encontrado")

    r = row[0]
    return {
        "codigo": r[0],
        "nombre": r[1],
        "apellidos": r[2],
        "estado_civil": r[3],
        "genero": r[4],
        "nacionalidad": r[5],
        "prefijo": r[6],
        "telefono": r[7],
        "provincia": r[8],
        "canton": r[9],
        "distrito": r[10],
        "direccion": r[11],
        "jornada": r[12],
        "operacion": r[13],
        "honorario": r[14],
        "pago": r[15],
        "banco": r[16],
        "cuenta_iban": r[17],
        "moneda": r[18],
        "swift": r[19],
        "uid": r[20],
        "enfermedades": r[21],
        "contacto_emergencia": r[22],
        "telefono_emergencia": r[23],
        "puerto": r[24],
        "email": r[25],
        "direccion_banco": r[26],
        "tarifas": _get_tarifas(codigo),
    }


@router.get("/{codigo}/tarifas")
def get_surveyor_tarifas(codigo: str):
    return {"data": _get_tarifas(codigo)}


@router.put("/{codigo}/tarifas")
def update_surveyor_tarifas(codigo: str, data: dict):
    tarifas = _clean_tarifas(data)
    _save_tarifas(codigo, tarifas)
    return {"status": "OK", "data": _get_tarifas(codigo)}


# ============================================================
# ACTUALIZAR SURVEYOR
# ============================================================
@router.put("/update")
def update_surveyor(data: dict, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    _ensure_tenant_schema()
    data = set_payload_company(data, company_code(data.get("company_code"), x_company_code))
    sql = """
        UPDATE surveyor SET
            nombre = %(nombre)s,
            apellidos = %(apellidos)s,
            email = %(email)s,
            estado_civil = %(estado_civil)s,
            genero = %(genero)s,
            nacionalidad = %(nacionalidad)s,
            prefijo = %(prefijo)s,
            telefono = %(telefono)s,
            provincia = %(provincia)s,
            canton = %(canton)s,
            distrito = %(distrito)s,
            direccion = %(direccion)s,
            jornada = %(jornada)s,
            operacion = %(operacion)s,
            honorario = %(honorario)s,
            pago = %(pago)s,
            banco = %(banco)s,
            direccion_banco = %(direccion_banco)s,
            cuenta_iban = %(cuenta_iban)s,
            moneda = %(moneda)s,
            swift = %(swift)s,
            uid = %(uid)s,
            enfermedades = %(enfermedades)s,
            contacto_emergencia = %(contacto_emergencia)s,
            telefono_emergencia = %(telefono_emergencia)s,
            puerto = %(puerto)s
        WHERE codigo = %(codigo)s
          AND company_code = %(company_code)s
    """
    try:
        data = _sync_legacy_fields(data)
        database.sql(sql, data)
        _save_tarifas(data["codigo"], data.get("_tarifas_clean", []))
        return {"status": "OK", "msg": "Surveyor actualizado ✔"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ELIMINAR SURVEYOR
# ============================================================
@router.delete("/{codigo}")
def delete_surveyor(codigo: str, x_company_code: str | None = Header(None, alias="X-Company-Code")):
    try:
        _ensure_tenant_schema()
        company = company_code(None, x_company_code)
        database.sql("DELETE FROM surveyor WHERE codigo = %s AND company_code = %s", (codigo, company))
        return {"status": "OK", "msg": "Surveyor eliminado 🗑️"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
