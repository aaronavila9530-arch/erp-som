import requests
from typing import Optional, Any
from datetime import datetime
from session_context import get_user, get_rol
import os
import tempfile
from email.message import Message
from urllib.parse import unquote

BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"
TIMEOUT = 30


# ============================================================
# PORTIA SOM — CONSULTAS ERP
# ============================================================
def _portia_safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _portia_num(value: Any) -> float:
    parsed = _portia_safe_float(value)
    return parsed if parsed is not None else 0.0


def _portia_safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _portia_rows(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("data", "rows", "items", "results"):
            rows = payload.get(key)
            if isinstance(rows, list):
                return [x for x in rows if isinstance(x, dict)]
    return []


def _portia_total(payload: Any) -> int:
    if isinstance(payload, dict):
        for key in ("total", "count", "total_count"):
            if key in payload:
                return _portia_safe_int(payload.get(key))
        return len(_portia_rows(payload))
    if isinstance(payload, list):
        return len(payload)
    return 0


def _portia_call(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def _portia_has_financial_data(context: dict) -> bool:
    if not isinstance(context, dict):
        return False
    fin = context.get("finanzas", {})
    if not isinstance(fin, dict):
        return False
    keys = (
        "facturado_total",
        "cuentas_por_cobrar",
        "pagos_recibidos",
        "cuentas_por_pagar_pendientes",
    )
    return any(_portia_num(fin.get(key)) != 0 for key in keys)


def _portia_weak_answer(answer: str) -> bool:
    normalized = (answer or "").lower()
    weak_markers = (
        "portia no devolvio respuesta",
        "facturado total: 0.00",
        "cuentas por cobrar: 0.00",
        "pagos recibidos: 0.00",
        "contexto vivo del backend no esta disponible",
    )
    return any(marker in normalized for marker in weak_markers)


def _build_portia_context_from_existing_apis() -> dict:
    year = datetime.now().year
    context = {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "year": year,
        "source": "desktop_existing_apis",
        "servicios": {},
        "finanzas": {},
        "comercial": {},
        "master_data": {},
        "informes": {},
        "top_clientes_ar": [],
        "actividad_puertos": [],
    }

    fin_dash = _portia_call(lambda: get_dashboard_finanzas_resumen_api(anio=year), {}) or {}
    fin_kpis = fin_dash.get("kpis", {}) if isinstance(fin_dash, dict) else {}
    context["finanzas"] = {
        "facturado_total": _portia_num(fin_kpis.get("revenue_total")),
        "cuentas_por_cobrar": _portia_num(fin_kpis.get("ar_total")),
        "pagos_recibidos": _portia_num(fin_kpis.get("payments_total")),
        "cuentas_por_pagar_pendientes": _portia_num(fin_kpis.get("ap_total")),
    }

    top_clientes = fin_dash.get("top_clientes_deuda", []) if isinstance(fin_dash, dict) else []
    context["top_clientes_ar"] = [
        {
            "cliente": row.get("nombre_cliente") or row.get("cliente") or "N/D",
            "saldo": _portia_num(row.get("deuda") or row.get("saldo")),
        }
        for row in top_clientes
        if isinstance(row, dict)
    ][:8]

    svc_rows = _portia_call(lambda: get_servicios_api(page=1, page_size=500, year=year), {}) or {}
    rows = _portia_rows(svc_rows)
    finalizados = [
        r for r in rows
        if str(r.get("estado") or r.get("status") or "").strip().upper() == "FINALIZADO"
    ]
    pendientes_factura = [
        r for r in finalizados
        if not str(r.get("factura") or r.get("numero_factura") or "").strip()
    ]
    context["servicios"] = {
        "total": _portia_total(svc_rows),
        "actual_year": len(rows),
        "finalizados": len(finalizados),
        "pendientes_factura": len(pendientes_factura),
        "valor_factura_total": sum(
            _portia_num(r.get("valor_factura") or r.get("monto") or r.get("precio"))
            for r in rows
        ),
    }

    puerto_count: dict[tuple[str, str], int] = {}
    for row in rows:
        pais = str(row.get("pais") or "").strip()
        puerto = str(row.get("puerto") or "").strip()
        if puerto:
            key = (pais, puerto)
            puerto_count[key] = puerto_count.get(key, 0) + 1
    context["actividad_puertos"] = [
        {"pais": pais, "puerto": puerto, "servicios": total}
        for (pais, puerto), total in sorted(puerto_count.items(), key=lambda item: item[1], reverse=True)[:10]
    ]

    com_dash = _portia_call(lambda: get_dashboard_comercial_resumen_api(anio=year), {}) or {}
    com_kpis = com_dash.get("kpis", {}) if isinstance(com_dash, dict) else {}
    cotizaciones = _portia_call(get_comercial_cotizaciones_api, []) or []
    cot_rows = _portia_rows(cotizaciones)
    approved_statuses = {"APROBADO", "APROBADA", "APPROVED"}
    context["comercial"] = {
        "cotizaciones": len(cot_rows) or _portia_safe_int(com_kpis.get("cotizaciones")),
        "cotizaciones_aprobadas": sum(
            1 for row in cot_rows
            if str(row.get("status") or row.get("estado") or "").strip().upper() in approved_statuses
        ),
        "precios_activos": _portia_safe_int(com_kpis.get("precios_activos")),
        "revenue_total": _portia_num(com_kpis.get("revenue_total")),
        "margen_neto_usd": _portia_num(com_kpis.get("margen_neto_usd")),
        "margen_neto_pct": _portia_num(com_kpis.get("margen_neto_pct")),
        "clientes_activos": _portia_safe_int(com_kpis.get("clientes_activos")),
        "paises_activos": _portia_safe_int(com_kpis.get("paises_activos")),
    }

    clientes = _portia_call(
        lambda: api_request("GET", f"{BASE_URL}/clientes", params={"page": 1, "page_size": 1}, timeout=15).json(),
        {},
    ) or {}
    proveedores = _portia_call(
        lambda: api_request("GET", f"{BASE_URL}/proveedores", params={"page": 1, "page_size": 1}, timeout=15).json(),
        {},
    ) or {}
    empleados = _portia_call(
        lambda: api_request("GET", f"{BASE_URL}/empleados", params={"page": 1, "page_size": 1}, timeout=15).json(),
        {},
    ) or {}
    surveyors = _portia_call(get_surveyores_api, []) or []
    puertos = _portia_call(lambda: api_request("GET", f"{BASE_URL}/puertos", timeout=15).json(), []) or []
    context["master_data"] = {
        "clientes": _portia_total(clientes),
        "proveedores": _portia_total(proveedores),
        "empleados": _portia_total(empleados),
        "surveyors": _portia_total(surveyors),
        "puertos": _portia_total(puertos),
    }

    informes = _portia_call(lambda: get_dashboard_informes_resumen_api(anio=year), {}) or {}
    inf_kpis = informes.get("kpis", {}) if isinstance(informes, dict) else {}
    context["informes"] = {
        "total": _portia_safe_int(inf_kpis.get("total_informes") or inf_kpis.get("total")),
        "pendientes": _portia_safe_int(inf_kpis.get("pendientes")),
        "aprobados": _portia_safe_int(inf_kpis.get("aprobados")),
        "rechazados": _portia_safe_int(inf_kpis.get("rechazados")),
    }

    return context


def get_portia_qa_api():
    url = f"{BASE_URL}/portia/qa"
    try:
        return api_request("GET", url, timeout=20).json()
    except Exception:
        from backend_api.ai.som_portia_knowledge import SOM_QA
        return {"data": SOM_QA}


def get_portia_suggestions_api():
    url = f"{BASE_URL}/portia/suggestions"
    try:
        return api_request("GET", url, timeout=20).json()
    except Exception:
        from backend_api.ai.som_portia_knowledge import PORTIA_SUGGESTED_QUESTIONS
        return {"data": PORTIA_SUGGESTED_QUESTIONS}


def get_portia_context_api():
    url = f"{BASE_URL}/portia/context"
    try:
        payload = api_request("GET", url, timeout=30).json()
        if isinstance(payload, dict) and payload.get("data"):
            return payload
    except Exception:
        pass
    return {"data": _build_portia_context_from_existing_apis()}


def ask_portia_api(question: str, scope: str = "erp"):
    url = f"{BASE_URL}/portia/ask"
    payload = {
        "question": question,
        "scope": scope,
    }
    try:
        response = api_request("POST", url, json=payload, timeout=60).json()
        if isinstance(response, dict) and response.get("answer"):
            if _portia_weak_answer(response.get("answer", "")):
                context = get_portia_context_api().get("data", {})
                if _portia_has_financial_data(context):
                    from backend_api.ai.som_portia import answer_som_portia
                    result = answer_som_portia(question, context, [], scope=scope)
                    result["context"] = context
                    return result
            return response
    except Exception:
        pass

    from backend_api.ai.som_portia import answer_som_portia
    context = get_portia_context_api().get("data", {})
    result = answer_som_portia(question, context, [], scope=scope)
    result["context"] = context
    return result

# ============================================================
# USER ROLE (RBAC)
# ============================================================

_current_user_role: Optional[str] = None


def set_user_role(role: str):
    global _current_user_role
    _current_user_role = role


def get_user_role() -> Optional[str]:
    return _current_user_role

def _get_hhrr_headers(usuario, rol):
    if not usuario or not rol:
        raise Exception("HHRR requiere usuario y rol")
    return {
        "X-User": str(usuario).strip().lower(),
        "X-Role": str(rol).strip().lower()
    }


# ============================================================
# CLIENTES
# ============================================================
def get_clientes_api():
    url = f"{BASE_URL}/clientes?page=1&page_size=500"
    resp = api_request("GET", url).json()
    return [c["nombrecomercial"] for c in resp.get("data", [])]

# ============================================================
# CONTINENTES / PAISES / PUERTOS
# ============================================================
def get_continentes_api():
    url = f"{BASE_URL}/continentes"
    return api_request("GET", url).json()

def get_paises_api(continente):
    url = f"{BASE_URL}/paises?continente={continente}"
    return api_request("GET", url).json()

def get_puertos_api(pais):
    url = f"{BASE_URL}/puertos?pais={pais}"
    return api_request("GET", url).json()

# ============================================================
# SERVICIOS MD (OPERACIONES)
# ============================================================
def get_serviciosmd_api():
    url = f"{BASE_URL}/servicios_md?page=1&page_size=500"
    resp = api_request("GET", url).json()
    return [s["nombre"] for s in resp.get("data", [])]



# ============================================================
# AGREGAR SERVICIO
# ============================================================
def post_servicio(data):
    url = f"{BASE_URL}/servicios/add"
    r = api_request("POST", url, json=data, timeout=15)
    r.raise_for_status()
    return r.json()


# ============================================================
# CONTINENTES (CPP) — NUEVO ENDPOINT
# ============================================================
def get_continentes_cpp_api():
    url = f"{BASE_URL}/cpp/continentes"
    try:
        resp = api_request("GET", url).json()
        return resp
    except Exception as e:
        print("❌ Error API continentes CPP:", e)
        return []

# ============================================================
# Paises (CPP) — NUEVO ENDPOINT
# ============================================================
def get_paises_cpp_api(continente):
    url = f"{BASE_URL}/cpp/paises?continente={continente}"
    try:
        resp = api_request("GET", url).json()
        return resp
    except Exception as e:
        print("❌ Error API países CPP:", e)
        return []

# ------------------------------------------------------------
# LISTAR SERVICIOS (CON FILTROS AÑO / STATUS / SURVEYOR)
# GET /servicios
# ------------------------------------------------------------
def get_servicios_api(
    page: int = 1,
    page_size: int = 50,
    year: int | None = None,
    status: str | None = None,
    surveyor: str | None = None
):
    """
    Lista servicios con filtros opcionales.

    - year: int (ej: 2025) → últimos 4 dígitos de num_informe
    - status: str (ej: 'Confirmado', 'Finalizado', 'Cancelado')
    - surveyor: str (ej: 'Juan Pérez')
    - Ningún filtro se aplica si no viene explícito
    """

    params = {
        "page": page,
        "page_size": page_size
    }

    # ----------------------------
    # AÑO
    # ----------------------------
    if year is not None:
        params["year"] = year

    # ----------------------------
    # STATUS
    # ----------------------------
    if status:
        status_clean = status.strip()
        if status_clean.upper() != "TODOS":
            params["status"] = status_clean

    # ----------------------------
    # SURVEYOR
    # ----------------------------
    if surveyor:
        surveyor_clean = surveyor.strip()
        if surveyor_clean:
            params["surveyor"] = surveyor_clean

    resp = api_request(
        "GET",
        f"{BASE_URL}/servicios",
        params=params,
        timeout=20
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# FILTROS DINÁMICOS — SERVICIOS
# GET /servicios/_meta/filtros
# ============================================================
def get_filtros_servicios_api():
    resp = api_request(
        "GET",
        f"{BASE_URL}/servicios/_meta/filtros",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# SURVEYORS (CATÁLOGO MAESTRO – USADO EN POPUP SERVICIO)
# ============================================================
def get_surveyores_api():
    """
    Retorna SOLO surveyores únicos (por nombre)
    para poblar el ComboBox de +Servicio.
    """
    resp = api_request(
        "GET",
        f"{BASE_URL}/surveyores?page=1&page_size=500",
        timeout=15
    )
    resp.raise_for_status()

    rows = resp.json().get("data", [])

    # --------------------------------------------
    # DEDUPLICAR POR NOMBRE (CATÁLOGO MAESTRO)
    # --------------------------------------------
    surveyores_unicos = sorted(
        {r["nombre"].strip() for r in rows if r.get("nombre")}
    )

    return surveyores_unicos

# ============================================================
# SURVEYORS (FULL ROWS PARA VLOOKUP HONORARIOS)
# ============================================================
def get_surveyores_full_api():
    """
    Retorna la data COMPLETA de surveyores (lista de dicts),
    necesaria para hacer VLOOKUP (operacion + honorario + moneda).
    """
    resp = api_request(
        "GET",
        f"{BASE_URL}/surveyores?page=1&page_size=500",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_surveyores_display_api():
    """
    Retorna lista de strings únicos para poblar el combobox,
    pero con un display UNICO por surveyor (incluye código).
    """
    rows = get_surveyores_full_api()

    display_set = set()
    for r in rows:
        nombre = (r.get("nombre") or "").strip()
        apellidos = (r.get("apellidos") or "").strip()
        codigo = (r.get("codigo") or "").strip()

        base = " ".join([nombre, apellidos]).strip() or nombre or codigo
        display = f"{base} ({codigo})" if codigo else base

        if display:
            display_set.add(display)

    return sorted(display_set)


# ============================================================
# puertos (CPP) — NUEVO ENDPOINT
# ============================================================
def get_puertos_cpp_api(pais):
    url = f"{BASE_URL}/cpp/puertos?pais={pais}"
    try:
        resp = api_request("GET", url).json()
        return resp
    except Exception as e:
        print("❌ Error API puertos CPP:", e)
        return []


# ============================================================
# obtener ultimo informe
# ============================================================
def get_ultimo_codigo_servicio_md():
    url = f"{BASE_URL}/servicios_md/ultimo"
    try:
        resp = api_request("GET", url).json()
        return resp.get("ultimo", 0)
    except Exception as e:
        print("❌ Error obteniendo último código ServiciosMD:", e)
        return 0



# ============================================================
# obtener ultimo informe - proveedores
# ============================================================

def get_ultimo_codigo_proveedor():
    url = f"{BASE_URL}/proveedores/ultimo"
    try:
        resp = api_request("GET", url, timeout=10).json()
        return resp.get("ultimo", 0)
    except Exception as e:
        print("❌ Error obteniendo último código proveedor:", e)
        return 0



# ============================================================
# todos los puertos
# ============================================================

def get_puertos_all_api():
    url = f"{BASE_URL}/cpp/puertos_all"
    try:
        resp = api_request("GET", url).json()
        return resp
    except Exception as e:
        print("❌ Error cargando puertos:", e)
        return []

# ============================================================
# eliminar servicio
# ============================================================
def delete_servicio(consec):
    """Eliminar un servicio por consec vía API."""
    try:
        url = f"{BASE_URL}/servicios/{consec}"
        resp = api_request("DELETE", url, timeout=15)
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============================================================
# Cancelar servicio
# ============================================================

def cancelar_servicio_api(consec, data):
    url = f"{BASE_URL}/servicios/cancelar/{consec}"
    try:
        resp = api_request("PUT", url, json=data, timeout=15)
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ============================================================
# CONFIRMAR SERVICIO + GENERAR CONSECUTIVO
# ============================================================

def confirmar_servicio_api(consec, fecha, hora):

    url = f"{BASE_URL}/servicios/confirmar/{consec}"

    payload = {
        "fecha_inicio": fecha,
        "hora_inicio": hora
    }

    try:
        resp = api_request(
            "PUT",
            url,
            json=payload,
            timeout=15
        )

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": resp.text
            }

        return resp.json()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ============================================================
# Demoras
# ============================================================

def actualizar_demoras_api(consec, total):
    r = api_request(
        "PUT",
        f"{BASE_URL}/servicios/demoras/{consec}",
        json={"total": total},
        timeout=15
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# Calcular Demoras
# ============================================================



def calcular_diferencia(f1, h1, f2, h2):
    inicio = datetime.strptime(f"{f1} {h1}", "%Y-%m-%d %H:%M")
    fin = datetime.strptime(f"{f2} {h2}", "%Y-%m-%d %H:%M")
    delta = fin - inicio

    total_min = int(delta.total_seconds() // 60)
    dias = total_min // (24*60)
    horas = (total_min % (24*60)) // 60
    minutos = total_min % 60

    return dias, horas, minutos



# ============================================================
# OBTENER SERVICIO POR CONSEC
# ============================================================
def get_servicio_api(consec: int) -> dict | None:
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/servicios/{consec}",
            timeout=10
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("ERROR get_servicio_api:", repr(e))
        return None

# ============================================================
# EDITAR SERVICIO
# ============================================================
def editar_servicio_api(consec, data):
    url = f"{BASE_URL}/servicios/editar/{consec}"
    try:
        resp = api_request("PUT", url, json=data, timeout=15)

        # Si no es 200, intenta extraer detail
        if resp.status_code != 200:
            try:
                j = resp.json()
                return {
                    "status": "error",
                    "error": j.get("detail") or j.get("error") or resp.text
                }
            except Exception:
                return {"status": "error", "error": resp.text}

        # 200 OK → JSON esperado
        return resp.json()

    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============================================================
# CERRAR OPERACIÓN (FECHA Y HORA DE FINALIZACIÓN)
# ============================================================
def cerrar_operacion_api(consec, fecha_fin, hora_fin):
    url = f"{BASE_URL}/servicios/cerrar/{consec}"

    try:
        resp = api_request(
            "PUT",
            url,
            json={
                "fecha_fin": fecha_fin,
                "hora_fin": hora_fin
            },
            timeout=15
        )

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": resp.text
            }

        return resp.json()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ============================================================
# CALCULAR DURACIÓN (BACKEND)
# ============================================================
def calcular_duracion_api(consec: int):
    """
    Recalcula y guarda la duración del servicio en backend.
    Usa fechas, horas y demoras ya existentes en DB.
    """

    url = f"{BASE_URL}/servicios/calcular_duracion/{consec}"

    try:
        resp = api_request(
            "PUT",
            url,
            timeout=15
        )

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": resp.text
            }

        return resp.json()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# FINALIZAR SERVICIO (ANTES generar_informe)
# ============================================================

def finalizar_servicio_api(consec):

    url = f"{BASE_URL}/servicios/generar_informe/{consec}"

    try:
        resp = api_request(
            "PUT",
            url,
            timeout=15
        )

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": resp.text
            }

        return resp.json()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

# ============================================================
# BILLING — OBTENER FACTURA POR NÚMERO (PREVIEW)
# ============================================================
def get_factura_billing_api(numero_factura: str) -> dict | None:
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/billing/{numero_factura}",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("❌ Error get_factura_billing_api:", repr(e))
        return None


# ============================================================
# BILLING — OBTENER PDF DE FACTURA
# ============================================================
def get_pdf_factura_billing_api(numero_documento: str) -> str | None:
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/billing/pdf/{numero_documento}",
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        return data.get("pdf_path")
    except Exception as e:
        print("❌ Error get_pdf_factura_billing_api:", repr(e))
        return None


# ============================================================
# BANK RECONCILIATION — LISTADO PAGINADO (cash_app)
# ============================================================
def get_bank_reconciliation_api(
    codigo_cliente=None,
    referencia=None,
    ver_todos=False,
    page=1,
    page_size=50
):
    params = {
        "page": page,
        "page_size": page_size,
        "ver_todos": ver_todos
    }

    if codigo_cliente:
        params["codigo_cliente"] = codigo_cliente

    if referencia:
        params["referencia"] = referencia

    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/bank-reconciliation",
            params=params,
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "page": page,
            "page_size": page_size,
            "total": 0,
            "data": [],
            "error": str(e)
        }


# ============================================================
# CLIENTES — SOLO CÓDIGOS Y NOMBRES (FINANZAS)
# (usado por combos en pagos manuales)
# ============================================================
def get_paid_invoices_report_api(
    year=None,
    month=None,
    date_from=None,
    date_to=None,
    cliente=None,
    page=1,
    page_size=500
):
    params = {
        "page": page,
        "page_size": page_size,
    }

    if year:
        params["year"] = year
    if month:
        params["month"] = month
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to
    if cliente:
        params["cliente"] = cliente

    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/bank-reconciliation/paid-invoices-report",
            params=params,
            timeout=30
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "page": page,
            "page_size": page_size,
            "total": 0,
            "summary": {},
            "data": [],
            "error": str(e)
        }


def download_monthly_financial_report_api(year: int, month: int, fmt: str, save_path: str):
    endpoint = "word" if str(fmt).lower() in ("word", "docx") else "pdf"
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/monthly-financial-report/{endpoint}",
            params={"year": int(year), "month": int(month)},
            timeout=90
        )
        r.raise_for_status()
        final_path = _write_report_file_safely(save_path, r.content)
        return {"status": "ok", "path": final_path}
    except PermissionError as e:
        return {"status": "error", "error": f"No se pudo escribir el archivo porque Windows lo tiene bloqueado: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _write_report_file_safely(save_path: str, content: bytes) -> str:
    """
    Escribe reportes evitando que Windows reviente si el archivo elegido esta abierto
    o bloqueado. Si no puede sobrescribir, crea una copia con sufijo numerico.
    Si Windows bloquea toda la carpeta elegida, usa Downloads o AppData local.
    """
    candidates = []
    folders = [os.path.dirname(save_path) or "."]
    user_home = os.path.expanduser("~")
    downloads = os.path.join(user_home, "Downloads")
    local_reports = os.path.join(os.getenv("LOCALAPPDATA") or tempfile.gettempdir(), "ERP-SOM", "reports")
    for folder in (downloads, local_reports, tempfile.gettempdir()):
        if folder and folder not in folders:
            folders.append(folder)

    base, ext = os.path.splitext(os.path.basename(save_path))
    for folder in folders:
        candidates.append(os.path.join(folder, f"{base}{ext}"))
        for idx in range(1, 51):
            candidates.append(os.path.join(folder, f"{base}_{idx}{ext}"))

    last_error = None
    for candidate in candidates:
        try:
            os.makedirs(os.path.dirname(candidate) or ".", exist_ok=True)
            with open(candidate, "wb") as f:
                f.write(content)
            return candidate
        except (PermissionError, OSError) as exc:
            last_error = exc
            continue

    raise PermissionError(last_error or "No se pudo escribir el reporte en ninguna carpeta disponible")


def get_accounting_periods_api():
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/accounting/periods",
            timeout=15
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        print("Error get_accounting_periods_api:", e)
        return []


def get_clientes_finanzas_api():
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/clientes?page=1&page_size=500",
            timeout=15
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        return [
            {
                "codigo": c.get("codigo"),
                "nombre": c.get("nombrecomercial")
            }
            for c in data
        ]
    except Exception as e:
        print("❌ Error clientes finanzas:", e)
        return []


# ============================================================
# INCOMING PAYMENTS — REGISTRAR PAGO MANUAL
# ============================================================
def post_incoming_payment_api(data: dict):
    """
    data esperado:
    {
        "origen": "MANUAL",           # MANUAL | COLLECTIONS | ITP
        "codigo_cliente": "MSL-0001-C",
        "nombre_cliente": "MSL",
        "banco": "BAC",
        "documento": "2202",
        "numero_referencia": "16561516",
        "fecha_pago": "2025-12-19",
        "monto": 1000.00
    }
    """
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/incoming-payments",
            json=data,
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# INCOMING PAYMENTS — LISTAR POR CASH_APP (VIEW APPLIED NUEVO)
# ============================================================
def get_incoming_payments_by_cash_app_api(cash_app_id: int):
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/incoming-payments/by-cash-app/{cash_app_id}",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "cash_app_id": cash_app_id,
            "data": [],
            "error": str(e)
        }


# ============================================================
# INCOMING PAYMENTS — DESAPLICAR (PARCIAL O TOTAL)
# ============================================================
def post_incoming_payment_unapply_api(data: dict):
    """
    data esperado:
    {
        "incoming_payment_id": 5,
        "monto_desaplicado": 500.00,
        "razon_desaplicacion": "ERROR_DE_ASIGNACION"
    }
    """
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/incoming-payments/unapply",
            json=data,
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# DISPUTES — LISTADO BASE (TABLA disputa)
# ============================================================
def get_disputes_api(codigo_cliente=None, page=1, page_size=50):
    params = {
        "page": page,
        "page_size": page_size
    }

    if codigo_cliente:
        params["codigo_cliente"] = codigo_cliente

    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/disputas",
            params=params,
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "page": page,
            "page_size": page_size,
            "data": [],
            "error": str(e)
        }


# ============================================================
# DISPUTES — HISTORIAL (dispute_history)
# ============================================================
def get_dispute_history_api(management_id: int):
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/dispute-management/{management_id}/history",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return []



# ============================================================
# DISPUTES — ACTUALIZAR STATUS
# ============================================================
def post_dispute_status_api(management_id: int, data: dict):
    """
    data = {
        status,
        comentario,
        user
    }
    """
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/dispute-management/{management_id}/status",
            json=data,
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# DISPUTES — KPIs
# ============================================================
def get_disputes_kpis_api():
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/dispute-management/kpis/summary",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "ADO": 0,
            "DDO": 0,
            "IncomingVolume": 0,
            "DisputedAmount": 0,
            "error": str(e)
        }



# ============================================================
# DISPUTES — NC / ND MANUAL
# ============================================================
def post_dispute_note_manual_api(management_id: int, data: dict):
    """
    data = {
        tipo: "NC" | "ND",
        monto,
        moneda,
        comentario,
        user
    }
    """
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/dispute-management/{management_id}/notes/manual",
            json=data,
            timeout=30
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }



# ============================================================
# DISPUTES — NC / ND XML
# ============================================================
def post_dispute_note_xml_api(
    management_id: int,
    tipo: str,
    moneda: str,
    user: str,
    file_path: str
):
    import os

    try:
        with open(file_path, "rb") as f:
            files = {
                "file": (
                    os.path.basename(file_path),
                    f,
                    "application/xml"
                )
            }

            data = {
                "tipo": tipo,
                "moneda": moneda,
                "user": user
            }

            r = api_request(
                "POST",
                f"{BASE_URL}/dispute-management/{management_id}/notes/xml",
                data=data,
                files=files,
                timeout=60
            )
            r.raise_for_status()
            return r.json()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# INVOICE TO PAY — SEARCH
# ============================================================
def get_invoice_to_pay_search_api(
    obligation_type=None,
    payee=None,
    status=None,

    issue_date_from=None,
    issue_date_to=None,

    due_date_from=None,
    due_date_to=None,

    payment_date_from=None,
    payment_date_to=None
):
    params = {}

    # ---------------------------
    # Filtros básicos
    # ---------------------------
    if obligation_type:
        params["obligation_type"] = obligation_type

    if payee:
        params["payee"] = payee

    if status:
        params["status"] = status

    # ---------------------------
    # Fecha factura (issue_date)
    # ---------------------------
    if issue_date_from:
        params["issue_date_from"] = issue_date_from

    if issue_date_to:
        params["issue_date_to"] = issue_date_to

    # ---------------------------
    # Fecha vencimiento (due_date)
    # ---------------------------
    if due_date_from:
        params["due_date_from"] = due_date_from

    if due_date_to:
        params["due_date_to"] = due_date_to

    # ---------------------------
    # Último pago
    # ---------------------------
    if payment_date_from:
        params["payment_date_from"] = payment_date_from

    if payment_date_to:
        params["payment_date_to"] = payment_date_to

    # ---------------------------
    # Request API
    # ---------------------------
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/invoice-to-pay/search",
            params=params,
            timeout=15
        )
        r.raise_for_status()
        return r.json().get("data", [])

    except Exception as e:
        print("❌ Error InvoiceToPay search:", e)
        return []


# ============================================================
# INVOICE TO PAY — KPIs
# ============================================================
def get_invoice_to_pay_kpis_api():
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/invoice-to-pay/kpis",
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("❌ Error InvoiceToPay KPIs:", e)
        return {
            "pending": 0,
            "paid": 0,
            "dpo": 0,
            "upcoming": 0,
            "overdue": 0
        }


# ============================================================
# INVOICE TO PAY — APPLY PAYMENT
# ============================================================
def post_invoice_to_pay_apply_payment_api(data: dict):
    """
    data esperado:
    {
        "obligation_id": int,
        "amount": float,
        "payment_date": "YYYY-MM-DD"
    }
    """

    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/invoice-to-pay/apply-payment",
            params={
                "obligation_id": data.get("obligation_id"),
                "amount": data.get("amount"),
                "payment_date": data.get("payment_date")
            },
            timeout=15
        )

        r.raise_for_status()
        return r.json()

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# INVOICE TO PAY — MANUAL OBLIGATION
# ============================================================
def post_invoice_to_pay_manual_api(data: dict):
    """
    data esperado:
    {
        payee_name,
        obligation_type,
        total,
        currency,
        reference,
        notes,
        payee_type
    }
    """
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/invoice-to-pay/manual",
            json=data,
            timeout=15
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# INVOICE TO PAY — UPLOAD PDF
# ============================================================
def post_invoice_to_pay_upload_pdf_api(
    file_path: str,
    reference: str
):
    try:
        with open(file_path, "rb") as f:
            r = api_request(
                "POST",
                f"{BASE_URL}/invoice-to-pay/upload/pdf",
                files={"file": f},
                data={"reference": reference},
                timeout=20
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }
# ============================================================
# INVOICE TO PAY — DELETE OBLIGATION
# ============================================================
# ============================================================
# LOGRA QUESTIONNAIRES
# ============================================================
def save_logra_report_api(payload: dict):
    try:
        report_id = payload.get("id") if isinstance(payload, dict) else None
        method = "PUT" if report_id else "POST"
        url = f"{BASE_URL}/logra-reports/{int(report_id)}" if report_id else f"{BASE_URL}/logra-reports"
        r = api_request(
            method,
            url,
            json=payload,
            timeout=30
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_logra_reports_api():
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/logra-reports",
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"data": [], "error": str(e)}


def save_logra_agenda_api(payload: dict):
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/logra-reports/agenda-only",
            json=payload,
            timeout=30
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_logra_report_api(report_id: int):
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/logra-reports/{int(report_id)}",
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_logra_ai_report_api(report_id, fmt: str, save_path: str, language: str = "ES"):
    endpoint = "word" if str(fmt).lower() in ("word", "docx") else "pdf"
    if str(report_id).upper() == "ALL":
        url = f"{BASE_URL}/logra-reports/ai-report/all/{endpoint}"
    else:
        url = f"{BASE_URL}/logra-reports/{int(report_id)}/ai-report/{endpoint}"
    try:
        r = api_request(
            "GET",
            url,
            params={"language": (language or "ES").upper()},
            timeout=120
        )
        raise_for_status_with_detail(r)
        with open(save_path, "wb") as f:
            f.write(r.content)
        return {"success": True, "path": save_path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def upload_logra_attachment_api(
    report_id: int,
    form_slug: str,
    section: str,
    item_key: str,
    file_path: str,
    bullet_index=None
):
    try:
        data = {
            "form_slug": form_slug,
            "section": section,
            "item_key": item_key,
        }
        if bullet_index is not None:
            data["bullet_index"] = str(bullet_index)

        with open(file_path, "rb") as f:
            r = api_request(
                "POST",
                f"{BASE_URL}/logra-reports/{int(report_id)}/attachments",
                data=data,
                files={"file": f},
                timeout=60
            )
            raise_for_status_with_detail(r)
            return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_logra_attachments_api(
    report_id: int,
    form_slug: str | None = None,
    section: str | None = None,
    item_key: str | None = None
):
    try:
        params = {}
        if form_slug:
            params["form_slug"] = form_slug
        if section:
            params["section"] = section
        if item_key:
            params["item_key"] = item_key

        r = api_request(
            "GET",
            f"{BASE_URL}/logra-reports/{int(report_id)}/attachments",
            params=params,
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"data": [], "error": str(e)}


def delete_logra_agenda_item_api(report_id: int, agenda_index: int):
    try:
        r = api_request(
            "DELETE",
            f"{BASE_URL}/logra-reports/{int(report_id)}/agenda-items/{int(agenda_index)}",
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_logra_report_api(report_id: int):
    try:
        r = api_request(
            "DELETE",
            f"{BASE_URL}/logra-reports/{int(report_id)}",
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_logra_agenda_item_api(report_id: int, agenda_index: int, payload: dict):
    try:
        r = api_request(
            "PUT",
            f"{BASE_URL}/logra-reports/{int(report_id)}/agenda-items/{int(agenda_index)}",
            json=payload,
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def update_logra_answer_api(report_id: int, payload: dict):
    try:
        r = api_request(
            "PUT",
            f"{BASE_URL}/logra-reports/{int(report_id)}/answers",
            json=payload,
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_logra_attachment_api(attachment_id: int):
    try:
        r = api_request(
            "DELETE",
            f"{BASE_URL}/logra-reports/attachments/{int(attachment_id)}",
            timeout=20
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def open_logra_attachment_api(attachment_id: int):
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/logra-reports/attachments/{int(attachment_id)}/download",
            timeout=60
        )
        raise_for_status_with_detail(r)

        filename = "logra_attachment"
        content_disposition = r.headers.get("content-disposition", "")
        if content_disposition:
            msg = Message()
            msg["content-disposition"] = content_disposition
            parsed = msg.get_filename()
            if parsed:
                filename = parsed
            elif "filename*=" in content_disposition:
                raw = content_disposition.split("filename*=", 1)[1].split(";", 1)[0].strip().strip("\"")
                if "''" in raw:
                    raw = raw.split("''", 1)[1]
                filename = unquote(raw)
            elif "filename=" in content_disposition:
                filename = content_disposition.split("filename=", 1)[1].split(";", 1)[0].strip().strip("\"")

        filename = os.path.basename(filename or "logra_attachment")
        root, ext = os.path.splitext(filename)
        if not ext:
            content_type = (r.headers.get("content-type") or "").split(";", 1)[0].lower()
            ext_map = {
                "application/pdf": ".pdf",
                "application/vnd.ms-excel": ".xls",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                "application/msword": ".doc",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                "image/jpeg": ".jpg",
                "image/png": ".png",
            }
            filename = f"{root or 'logra_attachment'}{ext_map.get(content_type, '')}"

        path = os.path.join(tempfile.gettempdir(), filename)
        with open(path, "wb") as f:
            f.write(r.content)

        os.startfile(path, "open")
        return {"success": True, "path": path}
    except Exception as e:
        return {"success": False, "error": str(e)}


def improve_logra_text_api(payload: dict):
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/reports/ai/improve/logra",
            json=payload,
            timeout=60
        )
        raise_for_status_with_detail(r)
        return r.json()
    except Exception as e:
        return {"success": False, "error": str(e)}


def delete_invoice_to_pay_api(obligation_id: int):
    try:
        r = api_request(
            "DELETE",
            f"{BASE_URL}/invoice-to-pay/{obligation_id}",
            timeout=15
        )
        r.raise_for_status()
        return {"status": "ok"}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ============================================================
# ACCOUNTING
# ============================================================

def get_accounting_ledger_api(
    period=None,
    period_from=None,
    period_to=None,
    origin=None,
    account_code=None
):
    """
    Obtiene el libro contable desde /accounting/ledger

    Filtros soportados:
    - period (YYYY-MM)
    - period_from (YYYY-MM)
    - period_to (YYYY-MM)
    - origin (ITP, COLLECTIONS, CASH_APP, MANUAL)
    - account_code (1101, 2101, 5101, etc.)
    """

    params = {}

    # -----------------------------
    # Periodo único
    # -----------------------------
    if period:
        params["period"] = period

    # -----------------------------
    # Rango de periodos
    # -----------------------------
    if period_from:
        params["period_from"] = period_from

    if period_to:
        params["period_to"] = period_to

    # -----------------------------
    # Otros filtros
    # -----------------------------
    if origin:
        params["origin"] = origin

    if account_code:
        params["account_code"] = account_code

    r = api_request(
        "GET",
        f"{BASE_URL}/accounting/ledger",
        params=params,
        timeout=15
    )
    r.raise_for_status()
    return r.json().get("data", [])



# ============================================================
# ACCOUNTING — MANUAL ENTRY
# ============================================================
def post_accounting_manual_entry_api(payload: dict):
    """
    payload:
    {
        "entry_date": "YYYY-MM-DD",
        "description": "...",
        "lines": [
            {
                "account_code": "1101",
                "account_name": "Bancos",
                "debit": 1000,
                "credit": 0,
                "line_description": "Pago proveedor"
            }
        ]
    }
    """
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/manual-entry",
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# ACCOUNTING - CHART OF ACCOUNTS
# ============================================================

def get_accounting_accounts_api():
    """
    Obtiene el catálogo contable para combobox
    """
    r = api_request(
        "GET",
        f"{BASE_URL}/accounting/accounts",
        timeout=15
    )
    r.raise_for_status()
    return r.json().get("data", [])


def get_accounting_bank_accounts_api():
    """
    Obtiene cuentas bancarias del plan contable para pagos.
    """
    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/accounting/bank-accounts",
            timeout=15
        )
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        accounts = get_accounting_accounts_api()
        banks = []
        for account in accounts:
            code = str(account.get("account_code") or "").strip()
            name = str(account.get("account_name") or "").strip()
            if code in ("1.1.01", "1.1.02"):
                continue
            if (
                code.startswith("1.1.02.")
                or code.startswith("1.1.01.")
                or name.lower().startswith("banco")
            ):
                banks.append(account)
        return banks


def create_accounting_account_api(payload):
    r = api_request("POST", f"{BASE_URL}/accounting/accounts", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def update_accounting_account_api(account_code, payload):
    r = api_request("PUT", f"{BASE_URL}/accounting/accounts/{account_code}", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def get_accounting_period_controls_api():
    r = api_request("GET", f"{BASE_URL}/accounting/period-controls", timeout=15)
    r.raise_for_status()
    return r.json().get("data", [])


def transition_accounting_entry_api(entry_id, action, user, reason=None):
    payload = {"user": user, "role": get_rol() or ""}
    if reason:
        payload["reason"] = reason
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/entry/{entry_id}/{action}",
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def get_finance_audit_api(module=None, entity_type=None, entity_id=None, performed_by=None, limit=200):
    params = {"limit": limit}
    if module:
        params["module"] = module
    if entity_type:
        params["entity_type"] = entity_type
    if entity_id is not None:
        params["entity_id"] = str(entity_id)
    if performed_by:
        params["performed_by"] = performed_by
    r = api_request("GET", f"{BASE_URL}/accounting/audit", params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def get_finance_audit_users_api():
    r = api_request("GET", f"{BASE_URL}/accounting/audit/users", timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def get_accounting_validation_alerts_api(
    period=None,
    period_from=None,
    period_to=None,
    origin=None,
    limit=200,
):
    params = {"limit": limit}
    if period:
        params["period"] = period
    if period_from:
        params["period_from"] = period_from
    if period_to:
        params["period_to"] = period_to
    if origin and origin != "TODOS":
        params["origin"] = origin
    r = api_request(
        "GET",
        f"{BASE_URL}/accounting/validation-alerts",
        params=params,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def post_accounting_ai_analysis_api(payload: dict):
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/ai/analyze",
        json=payload,
        timeout=90,
    )
    raise_for_status_with_detail(r)
    return r.json()


def sync_accounting_auxiliaries_api():
    r = api_request("POST", f"{BASE_URL}/accounting/auxiliaries/sync", timeout=180)
    r.raise_for_status()
    return r.json()


def get_accounting_auxiliary_entities_api(entity_type=None, search=None):
    params = {}
    if entity_type: params["entity_type"] = entity_type
    if search: params["search"] = search
    r = api_request("GET", f"{BASE_URL}/accounting/auxiliaries/entities", params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def create_accounting_auxiliary_entity_api(payload):
    r = api_request("POST", f"{BASE_URL}/accounting/auxiliaries/entities", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def get_accounting_auxiliary_documents_api(entity_id):
    r = api_request("GET", f"{BASE_URL}/accounting/auxiliaries/entities/{entity_id}/documents", timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def create_accounting_auxiliary_document_api(entity_id, payload):
    r = api_request("POST", f"{BASE_URL}/accounting/auxiliaries/entities/{entity_id}/documents", json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def apply_accounting_auxiliary_transaction_api(document_id, payload):
    r = api_request("POST", f"{BASE_URL}/accounting/auxiliaries/documents/{document_id}/transactions",
                    json=payload, timeout=20)
    r.raise_for_status()
    return r.json()


def get_accounting_auxiliary_aging_api(entity_type, as_of=None):
    params = {"entity_type": entity_type}
    if as_of: params["as_of"] = as_of
    r = api_request("GET", f"{BASE_URL}/accounting/auxiliaries/aging", params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def get_accounting_auxiliary_reconciliation_api(period=None):
    params = {"period": period} if period else None
    r = api_request("GET", f"{BASE_URL}/accounting/auxiliaries/reconciliation", params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("data", [])


def get_accounting_auxiliary_settings_api():
    r = api_request("GET", f"{BASE_URL}/accounting/auxiliaries/settings", timeout=20)
    r.raise_for_status()
    return r.json().get("data", [])


def update_accounting_auxiliary_setting_api(entity_type, account_code, user):
    r = api_request("PUT", f"{BASE_URL}/accounting/auxiliaries/settings/{entity_type}",
                    json={"control_account_code": account_code, "user": user}, timeout=20)
    r.raise_for_status()
    return r.json()


# ============================================================
# CENTRO FISCAL COSTA RICA
# ============================================================
def sync_accounting_tax_api():
    r = api_request("POST", f"{BASE_URL}/accounting/tax/sync", timeout=180)
    raise_for_status_with_detail(r)
    return r.json()


def get_tax_documents_api(direction=None, period=None, status=None, quality_only=False):
    params = {"quality_only": quality_only}
    if direction: params["direction"] = direction
    if period: params["period"] = period
    if status: params["status"] = status
    r = api_request("GET", f"{BASE_URL}/accounting/tax/documents", params=params, timeout=45)
    raise_for_status_with_detail(r)
    return r.json()


def get_tax_book_api(direction, period):
    r = api_request("GET", f"{BASE_URL}/accounting/tax/books/{direction}", params={"period": period}, timeout=45)
    raise_for_status_with_detail(r)
    return r.json()


def get_tax_iva_api(period):
    r = api_request("GET", f"{BASE_URL}/accounting/tax/iva", params={"period": period}, timeout=45)
    raise_for_status_with_detail(r)
    return r.json()


def upload_tax_xml_api(path, direction, user="ERP_USER"):
    with open(path, "rb") as fh:
        r = api_request("POST", f"{BASE_URL}/accounting/tax/documents/upload-xml",
                        data={"direction": direction, "user": user},
                        files={"file": (path.split("\\")[-1], fh, "application/xml")}, timeout=90)
    raise_for_status_with_detail(r)
    return r.json()


def upload_tax_hacienda_response_api(document_id, path):
    with open(path, "rb") as fh:
        r = api_request("POST", f"{BASE_URL}/accounting/tax/documents/{document_id}/hacienda-response",
                        files={"file": (path.split("\\")[-1], fh, "application/xml")}, timeout=90)
    raise_for_status_with_detail(r)
    return r.json()


def upload_tax_response_auto_api(path):
    with open(path,"rb") as fh:
        r=api_request("POST",f"{BASE_URL}/accounting/tax/documents/import-hacienda-response",
                      files={"file":(path.split("\\")[-1],fh,"application/xml")},timeout=90)
    raise_for_status_with_detail(r); return r.json()


def get_tax_obligations_api(year=None, period=None, pending_only=False):
    params = {}
    if year:
        params["year"] = year
    if period:
        params["period"] = period
    if pending_only:
        params["pending_only"] = True
    r = api_request("GET", f"{BASE_URL}/accounting/tax/obligations",
                    params=params or None, timeout=30)
    raise_for_status_with_detail(r)
    return r.json()


def search_tax_cabys_api(search=""):
    r = api_request("GET", f"{BASE_URL}/accounting/tax/cabys", params={"search": search}, timeout=30)
    raise_for_status_with_detail(r)
    return r.json().get("data", [])


def get_gmail_fiscal_status_api():
    r=api_request("GET",f"{BASE_URL}/accounting/tax/gmail/status",timeout=30)
    raise_for_status_with_detail(r); return r.json()


def start_gmail_fiscal_oauth_api(user):
    r=api_request("POST",f"{BASE_URL}/accounting/tax/gmail/oauth/start",json={"user":user},timeout=30)
    raise_for_status_with_detail(r); return r.json()


def update_gmail_fiscal_automation_api(enabled,interval_minutes,user):
    r=api_request("PUT",f"{BASE_URL}/accounting/tax/gmail/automation",
                  json={"enabled":enabled,"interval_minutes":interval_minutes,"user":user},timeout=30)
    raise_for_status_with_detail(r); return r.json()


def sync_gmail_fiscal_api(user,max_messages=50):
    r=api_request("POST",f"{BASE_URL}/accounting/tax/gmail/sync",
                  params={"user":user,"max_messages":max_messages},timeout=180)
    raise_for_status_with_detail(r); return r.json()


def get_gmail_fiscal_messages_api(status=None):
    params={"status":status} if status else None
    r=api_request("GET",f"{BASE_URL}/accounting/tax/gmail/messages",params=params,timeout=45)
    raise_for_status_with_detail(r); return r.json()


# ============================================================
# ESPACIO DE TRABAJO DEL CONTADOR
# ============================================================
def get_accountant_dashboard_api(period):
    r = api_request("GET", f"{BASE_URL}/accounting/workspace/dashboard", params={"period": period}, timeout=45)
    raise_for_status_with_detail(r)
    return r.json()


def get_accounting_close_checklist_api(period):
    r = api_request("GET", f"{BASE_URL}/accounting/workspace/close-checklist", params={"period": period}, timeout=45)
    raise_for_status_with_detail(r)
    return r.json()


def update_accounting_close_checklist_api(period, item_code, status, user, notes="", evidence=None):
    r = api_request("PUT", f"{BASE_URL}/accounting/workspace/close-checklist/{period}/{item_code}",
                    json={"status": status, "user": user, "notes": notes, "evidence": evidence or {}}, timeout=30)
    raise_for_status_with_detail(r)
    return r.json()


def get_accounting_guided_close_api(period):
    r = api_request("GET", f"{BASE_URL}/accounting/workspace/guided-close", params={"period": period}, timeout=45)
    raise_for_status_with_detail(r)
    return r.json()


def post_accounting_guided_close_api(period, user, notes=""):
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/workspace/guided-close/{period}/close",
        json={"user": user, "notes": notes or ""},
        timeout=45,
    )
    raise_for_status_with_detail(r)
    return r.json()


def get_accounting_legal_library_api(category=None, query=None):
    params = {}
    if category and category not in ("TODOS", "Todos", "all"):
        params["category"] = category
    if query:
        params["q"] = query
    r = api_request("GET", f"{BASE_URL}/accounting/legal-library/", params=params, timeout=30)
    raise_for_status_with_detail(r)
    return r.json()


def search_accounting_workspace_api(query, limit=30):
    r = api_request("GET", f"{BASE_URL}/accounting/workspace/search", params={"q": query, "limit": limit}, timeout=45)
    raise_for_status_with_detail(r)
    return r.json()


def get_accounting_workspace_preferences_api(user):
    r = api_request("GET", f"{BASE_URL}/accounting/workspace/preferences/{user}", timeout=20)
    raise_for_status_with_detail(r)
    return r.json()


def update_accounting_workspace_preferences_api(user, payload):
    r = api_request("PUT", f"{BASE_URL}/accounting/workspace/preferences/{user}", json=payload, timeout=20)
    raise_for_status_with_detail(r)
    return r.json()


# ============================================================
# ACCOUNTING - GET ENTRY FOR EDIT
# ============================================================

def get_accounting_entry_api(entry_id):
    """
    Obtiene un asiento contable completo por entry_id
    """
    r = api_request(
        "GET",
        f"{BASE_URL}/accounting/entry/{entry_id}",
        timeout=15
    )
    r.raise_for_status()
    return r.json()

# ============================================================
# ACCOUNTING - UPDATE ENTRY
# ============================================================

def update_accounting_entry_api(entry_id, payload):
    """
    Guarda cambios de un asiento contable
    """
    r = api_request(
        "PUT",
        f"{BASE_URL}/accounting/entry/{entry_id}",
        json=payload,
        timeout=15
    )
    r.raise_for_status()
    return r.json()



def post_collections_post_to_accounting_api():
    r = api_request("POST", f"{BASE_URL}/collections/post-to-accounting", timeout=60)
    r.raise_for_status()
    return r.json()

def post_accounting_sync_collections_api():
    r = api_request("POST", f"{BASE_URL}/accounting/sync/collections", timeout=60)
    r.raise_for_status()
    return r.json()



# ============================================================
# ACCOUNTING - SYNC CASH APP
# ============================================================

def post_accounting_sync_cash_app_api():
    """
    Sincroniza pagos (cash_app) → accounting
    Genera asiento Bancos vs CxC
    """
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/sync/cash-app",
        timeout=60
    )
    r.raise_for_status()
    return r.json()



# ============================================================
# ACCOUNTING - SYNC INVOICE TO PAY (ITP)
# ============================================================

def post_accounting_sync_itp_api():
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/sync/itp",
        timeout=60
    )
    r.raise_for_status()
    return r.json()

# ============================================================
# ACCOUNTING - SYNC PAYROL (HHRR)
# ============================================================

def post_accounting_sync_payroll_api():
    return api_request(
        "POST",
        f"{BASE_URL}/accounting/sync/payroll"
    )



# ============================================================
# EXCHANGE RATE – BCCR
# ============================================================
def get_exchange_rate_today_api():
    """
    Obtiene el Tipo de Cambio del día.
    - Si existe en BD → lo retorna (CACHE)
    - Si no existe → BCCR → inserta → retorna
    """

    try:
        r = api_request(
            "GET",
            f"{BASE_URL}/exchange-rate/today",
            timeout=20
        )
        r.raise_for_status()
        return r.json()
    except Exception as today_error:
        # Accounting no debe quedar inutilizable por una caída temporal del BCCR
        # o mientras el backend despliega su mecanismo de respaldo.
        try:
            latest = get_exchange_rate_latest_api()
            latest["source"] = "CACHE_FALLBACK"
            latest["stale"] = True
            latest["warning"] = (
                "BCCR no disponible; se utiliza el último tipo de cambio guardado"
            )
            return latest
        except Exception:
            raise today_error


def get_exchange_rate_latest_api():
    """
    Obtiene el último Tipo de Cambio registrado en BD
    (sin llamar al BCCR)
    """

    r = api_request(
        "GET",
        f"{BASE_URL}/exchange-rate/latest",
        timeout=20
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# ACCOUNTING - ADJUSTMENT ENTRY
# ============================================================

def post_accounting_adjustment_entry_api(payload: dict):
    """
    Crea un ASIENTO DE AJUSTE contable

    payload:
    {
        "original_entry_id": 7,
        "entry_date": "YYYY-MM-DD",
        "lines": [
            {
                "account_code": "1101",
                "account_name": "Cuentas por cobrar",
                "debit": 10000,
                "credit": 0
            },
            {
                "account_code": "4101",
                "account_name": "Ingresos por servicios",
                "debit": 0,
                "credit": 10000
            }
        ]
    }
    """
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/adjustments/create",
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# ACCOUNTING – REVERSE ENTRY
# ============================================================

def post_accounting_reverse_entry_api(entry_id: int):
    """
    Reversa un asiento contable existente creando un nuevo asiento
    con Debe ↔ Haber invertidos.
    """
    r = api_request(
        "POST",
        f"{BASE_URL}/accounting/reverse/{entry_id}",
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()

def post_close_period_api(
    company_code,
    fiscal_year,
    period,
    ledger,
    closed_by
):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/period/close",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger,
            "closed_by": closed_by
        },
        timeout=20
    )

    if r.status_code != 200:
        try:
            detail = r.json().get("detail")
        except Exception:
            detail = r.text
        raise Exception(detail or r.text or "Error al cerrar período")

    return r.json()



# ============================================================
# CLOSING – GL PREVIEW
# ============================================================

def post_closing_gl_preview_api(company_code, fiscal_year, period, ledger="0L"):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/gl/preview",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – GL POST
# ============================================================

def post_closing_gl_post_api(company_code, fiscal_year, period, posted_by, ledger="0L"):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/gl/post",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger,
            "posted_by": posted_by
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – TB PREVIEW
# ============================================================

def post_closing_tb_preview_api(company_code, fiscal_year, period, ledger="0L"):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/tb/preview",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – TB POST
# ============================================================

def post_closing_tb_post_api(company_code, fiscal_year, period, posted_by, ledger="0L"):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/tb/post",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger,
            "posted_by": posted_by
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – P&L POST
# ============================================================

def post_closing_pnl_post_api(
    company_code,
    fiscal_year,
    period,
    equity_account_code,
    equity_account_name,
    posted_by,
    ledger="0L"
):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/pnl/post",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger,
            "equity_account_code": equity_account_code,
            "equity_account_name": equity_account_name,
            "posted_by": posted_by
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – FS POST
# ============================================================

def post_closing_fs_post_api(company_code, fiscal_year, period, posted_by, ledger="0L"):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/fs/post",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger,
            "posted_by": posted_by
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – FY OPEN
# ============================================================

def post_closing_fy_open_api(
    company_code,
    fiscal_year,
    source_fiscal_year,
    posted_by,
    ledger="0L"
):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/fy/open",
        json={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "source_fiscal_year": source_fiscal_year,
            "ledger": ledger,
            "posted_by": posted_by
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – REVERSE BATCH
# ============================================================

def post_closing_reverse_batch_api(batch_id: int, reversed_by: str, reason: str = ""):
    r = api_request(
        "POST",
        f"{BASE_URL}/closing/batch/{batch_id}/reverse",
        json={
            "reversed_by": reversed_by,
            "reason": reason or "Reversa solicitada desde UI"
        },
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – DOWNLOAD BATCH PDF
# ============================================================

def download_closing_batch_pdf_api(batch_id: int, save_path: str):
    """
    Descarga el PDF oficial del batch de cierre
    """
    r = api_request(
        "GET",
        f"{BASE_URL}/closing/reports/batch/{batch_id}/pdf",
        stream=True,
        timeout=TIMEOUT
    )
    r.raise_for_status()

    with open(save_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return save_path


# ============================================================
# Calculo de IVA (CORRECTO)
# ============================================================

def get_accounting_iva_api(period):
    r = api_request(
        "GET",
        f"{BASE_URL}/accounting/iva",
        params={"period": period},
        timeout=20
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# CLOSING – PERIOD STATUS
# ============================================================
def get_closing_period_status(
    company_code: str,
    fiscal_year: int,
    period: int,
    ledger: str = "0L"
) -> dict:
    """
    Consulta el estado del período contable.
    NO modifica datos.
    """

    r = api_request(
        "GET",
        f"{BASE_URL}/closing/period/status",
        params={
            "company_code": company_code,
            "fiscal_year": fiscal_year,
            "period": period,
            "ledger": ledger
        },
        timeout=10
    )

    r.raise_for_status()
    return r.json()


def get_accounting_lines_api():
    r = api_request(
        "GET",
        f"{BASE_URL}/accounting-lines",
        timeout=30
    )
    r.raise_for_status()
    return r.json()



# ============================================================
# INVOICING — FACTURA ELECTRÓNICA XML (ANTICIPADA)
# ============================================================
def post_factura_xml_api(codigo_cliente, nombre_cliente, xml_path):
    payload = {
        "tipo_factura": "XML",
        "codigo_cliente": codigo_cliente,
        "nombre_cliente": nombre_cliente,
        "xml_path": xml_path
    }

    r = api_request(
        "POST",
        f"{BASE_URL}/invoicing/anticipada",
        json=payload,
        timeout=30
    )

    r.raise_for_status()
    return r.json()

# ============================================================
# INVOICING — EMITIR FACTURA ELECTRÓNICA
# ============================================================

def post_invoicing_emitir_api(payload: dict):
    """
    payload:
    {
        servicio_id,
        tipo_factura: "ELECTRONICA",
        numero_documento,
        moneda,
        total,
        termino_pago,
        descripcion
    }
    """
    r = api_request(
        "POST",
        f"{BASE_URL}/invoicing/emitir",
        json=payload,
        timeout=30
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# FACTURACIÓN ANTICIPADA — MANUAL
# ============================================================
def post_invoicing_anticipada_manual_api(
    codigo_cliente: str,
    nombre_cliente: str,
    num_informe: str,
    buque: str,
    operacion: str,
    periodo_operacion: str,
    descripcion: str,
    moneda: str,
    termino_pago: int,
    total: float
):
    payload = {
        "tipo_factura": "MANUAL",
        "codigo_cliente": codigo_cliente,
        "nombre_cliente": nombre_cliente,
        "num_informe": num_informe,
        "buque": buque,
        "operacion": operacion,
        "periodo_operacion": periodo_operacion,
        "descripcion": descripcion,
        "moneda": moneda,
        "termino_pago": int(termino_pago),
        "total": float(total)
    }

    return post_invoicing_anticipada_api(payload)

def post_invoicing_anticipada_xml_api(
    codigo_cliente: str,
    nombre_cliente: str,
    xml_path: str
):
    """
    Envía factura electrónica XML como multipart/form-data
    hacia /invoicing/anticipada/xml
    """

    if not xml_path:
        raise ValueError("xml_path requerido")

    with open(xml_path, "rb") as f:
        files = {
            "file": (
                xml_path.split("\\")[-1],  # Windows safe
                f,
                "application/xml"
            )
        }

        data = {
            "codigo_cliente": str(codigo_cliente),
            "nombre_cliente": str(nombre_cliente)
        }

        r = api_request(
            "POST",
            f"{BASE_URL}/invoicing/anticipada/xml",
            data=data,
            files=files,
            timeout=30
        )

        # DEBUG si algo vuelve a fallar
        if r.status_code >= 400:
            raise Exception(f"{r.status_code} → {r.text}")

        return r.json()

# ============================================================
# INVOICING — FACTURA ANTICIPADA (BASE)
# ============================================================
def post_invoicing_anticipada_api(payload: dict):
    r = api_request(
        "POST",
        f"{BASE_URL}/invoicing/anticipada",
        json=payload,
        timeout=30
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# FACTURA MANUAL (LIGADA A SERVICIO)
# ============================================================
def post_factura_manual_api(payload: dict):
    """
    Crea una factura MANUAL ligada a un servicio
    Endpoint: POST /factura/manual
    """

    r = api_request(
        "POST",
        f"{BASE_URL}/factura/manual",
        json=payload,
        timeout=30
    )

    r.raise_for_status()
    return r.json()



# ============================================================
# OBTENER TÉRMINO DE PAGO (cliente -> cliente_credito)
# ============================================================
def get_termino_pago_cliente_api(nombre_cliente: str) -> dict:
    r = api_request(
        "GET",
        f"{BASE_URL}/factura/termino-pago",
        params={"nombre_cliente": nombre_cliente},
        timeout=20
    )
    r.raise_for_status()
    return r.json()


def post_factura_electronica_xml_api(servicio_id: int, xml_path: str):
    with open(xml_path, "rb") as f:
        files = {
            "file": ("factura.xml", f, "application/xml")
        }
        data = {
            "servicio_id": servicio_id
        }

        r = api_request(
            "POST",
            f"{BASE_URL}/factura/electronica",
            files=files,
            data=data,
            timeout=60
        )

    raise_for_status_with_detail(r)
    return r.json()


# =====================================
# CLIENTE CRÉDITO API
# =====================================
def get_cliente_credito_api(codigo_cliente: str):
    r = api_request(
        "GET",
        f"{BASE_URL}/cliente-credito/{codigo_cliente}",
        timeout=20
    )
    r.raise_for_status()
    return r.json()


def update_cliente_credito_api(codigo_cliente: str, payload: dict):
    r = api_request(
        "PUT",
        f"{BASE_URL}/cliente-credito/{codigo_cliente}",
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()



# ============================================================
# COLLECTIONS – SYNC FROM INVOICING
# ============================================================
def sync_collections_from_invoicing_api():
    """
    Sincroniza facturas desde invoicing hacia collections.
    Inserta solo FACTURAS EMITIDAS no existentes en collections.
    """
    r = api_request(
        "POST",
        f"{BASE_URL}/collections/sync-from-invoicing",
        timeout=30
    )
    r.raise_for_status()
    return r.json()



def aplicar_pago_api(payload: dict):
    """
    POST /collections/pago
    Registra el pago en cash_app (y aplica contra collections si existe).
    """
    r = api_request(
        "POST",
        f"{BASE_URL}/collections/pago",
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()

def aplicar_nota_credito_api(payload: dict):
    r = api_request(
        "POST",
        f"{BASE_URL}/collections/aplicar-nota-credito",
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()




def get_version_info():
    """
    Cliente de versión BLINDADO.

    • Nunca rompe el ERP
    • Nunca bloquea login
    • Payload inválido = NO UPDATE
    """

    try:
        r = requests.get(
            f"{BASE_URL}/version",
            timeout=5
        )
        r.raise_for_status()

        data = r.json()

        # ------------------------------
        # Validación mínima del payload
        # ------------------------------
        latest = data.get("latest_version")

        if not latest:
            return False, {}

        return True, data

    except Exception:
        return False, {}

def verify_identity_api(data):
    r = requests.post(f"{BASE_URL}/auth/reset/verify-identity", json=data, timeout=10)
    r.raise_for_status()
    return r.json()

def verify_totp_api(data):
    r = requests.post(f"{BASE_URL}/auth/reset/verify-totp", json=data, timeout=10)
    r.raise_for_status()
    return r.json()

def set_password_api(data):
    r = requests.post(f"{BASE_URL}/auth/reset/set-password", json=data, timeout=10)
    r.raise_for_status()
    return r.json()


# ============================================================
# CORE REQUEST WRAPPER
# ============================================================

def _headers():
    usuario = get_user()
    rol = get_rol()

    if not usuario:
        raise Exception("Usuario no autenticado")

    rol = (rol or "").strip().lower()

    return {
        "X-User": usuario,
        "X-Role": rol,            # legacy (lo usan otros endpoints)
        "X-User-Role": rol        # ✅ requerido por /comercial/board (evita 422)
    }

# ============================================================
# IA INFORMES
# ============================================================

def api_request(method: str, url: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.update(_headers())

    # ======================================================
    # NORMALIZAR URL (BLINDAJE TOTAL)
    # ======================================================
    if not url.startswith("http://") and not url.startswith("https://"):
        if not url.startswith("/"):
            url = f"/{url}"
        url = f"{BASE_URL}{url}"

    return requests.request(
        method=method,
        url=url,
        headers=headers,
        **kwargs
    )


def raise_for_status_with_detail(response):
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        detail = None
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("message") or payload.get("error")
        except Exception:
            detail = response.text

        detail = str(detail or exc).strip()
        if detail:
            raise requests.exceptions.HTTPError(detail, response=response) from exc
        raise

# ============================================================
# HHRR — EVENTS (API REAL)
# ============================================================

def hr_create_event(data: dict):
    if not isinstance(data, dict):
        raise ValueError("data debe ser dict")

    resp = api_request(
        "POST",
        "/hr/events/",
        json=data,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_list_events(event_type=None, status=None, empleado_id=None):
    params = {}

    if event_type:
        params["event_type"] = event_type

    if status:
        params["status"] = status

    if empleado_id:
        params["empleado_id"] = empleado_id

    resp = api_request(
        "GET",
        "/hr/events/",
        params=params,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_update_event_status(event_id, status, approved_by):
    if not event_id:
        raise ValueError("event_id requerido")

    resp = api_request(
        "POST",
        f"/hr/events/{event_id}/status",
        json={
            "status": status,
            "approved_by": approved_by
        },
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# HHRR — OT LOG (API REAL)
# ============================================================

def hr_create_ot_log(data: dict):
    resp = api_request(
        "POST",
        "/hr/ot-log/",
        json=data,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# =========================================================
# HR — LIST OT LOGS
# =========================================================
def hr_list_ot_logs(
    page=1,
    page_size=50,
    usuario=None,
    tipo=None,
    estado=None
):
    try:
        page = int(page) if str(page).isdigit() else 1
        page_size = int(page_size) if str(page_size).isdigit() else 50

        page = max(page, 1)
        page_size = min(max(page_size, 1), 500)

        params = {
            "page": page,
            "page_size": page_size
        }

        if usuario:
            params["usuario"] = str(usuario).strip()

        if tipo:
            params["tipo"] = str(tipo).strip()

        if estado:
            params["estado"] = str(estado).strip()

        resp = api_request(
            "GET",
            "/hr/ot-log",
            params=params,
            timeout=30
        )

        resp.raise_for_status()

        data = resp.json()

        if not isinstance(data, dict):
            return {"data": [], "total": 0}

        data.setdefault("data", [])
        data.setdefault("total", len(data["data"]))

        return data

    except Exception as e:
        raise Exception(str(e))


def hr_delete_ot_log(log_id: int):
    resp = api_request(
        "DELETE",
        f"/hr/ot-log/{log_id}",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_update_ot_status(log_id: int, estado: str):
    resp = api_request(
        "PUT",
        f"/hr/ot-log/{log_id}/estado",
        json={"estado": estado},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_get_my_summary(year=None, month=None):
    params = {}

    if year:
        params["year"] = year

    if month:
        params["month"] = month

    resp = api_request(
        "GET",
        "/hr/ot-log/me/summary",
        params=params,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# ALIASES LEGACY — UI EXISTENTE
# ============================================================

def listar_eventos_hr(*args, **kwargs):
    return hr_list_events(*args, **kwargs)

def actualizar_estado_evento_hr(event_id, status, approved_by):
    return hr_update_event_status(event_id, status, approved_by)

def crear_ot_log(data: dict):
    return hr_create_ot_log(data)

def listar_ot_logs(*args, **kwargs):
    return hr_list_ot_logs(*args, **kwargs)


# ============================================================
# HHRR — PAYROLL
# ============================================================

def hr_list_payroll_employees():
    resp = api_request(
        "GET",
        "/hr/payroll/employees",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_calculate_payroll(usuario: str, year: int, month: int):
    params = {
        "usuario": usuario,
        "year": year,
        "month": month
    }

    resp = api_request(
        "GET",
        "/hr/payroll/calculate",
        params=params,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_post_payroll(payload: dict):
    resp = api_request(
        "PUT",
        "/hr/payroll/post",
        json=payload,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_list_payroll_runs(year=None, month=None, usuario=None):
    params = {}

    if year:
        params["year"] = year

    if month:
        params["month"] = month

    if usuario:
        params["usuario"] = usuario

    resp = api_request(
        "GET",
        "/hr/payroll/runs",
        params=params,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def get_payslips_api(page=1, page_size=20, year=None, month=None):
    params = {
        "page": page,
        "page_size": page_size
    }

    if year:
        params["year"] = year

    if month:
        params["month"] = month

    resp = api_request(
        "GET",
        "/hr/payroll/payslips",
        params=params,
        timeout=20
    )
    resp.raise_for_status()
    return resp.json()


def hr_download_payslip_pdf(year, month, usuario=None, timeout=30):
    params = {}

    if usuario:
        params["usuario"] = usuario

    resp = api_request(
        "GET",
        f"/hr/payroll/payslips/{year}/{month}/pdf",
        params=params,
        stream=True,
        timeout=timeout
    )
    resp.raise_for_status()
    return resp


# ============================================================
# HHRR — EVENTS UI (CON HEADERS)
# ============================================================

def listar_eventos_hr(usuario, rol):
    headers = {
        "X-User": str(usuario).strip().lower(),
        "X-Role": str(rol).strip().lower()
    }

    resp = api_request(
        "GET",
        "/hr/events/",
        headers=headers,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def crear_evento_hr(
    event_type,
    payload,
    event_date=None,
    usuario=None,
    rol=None
):
    if not event_type:
        raise ValueError("event_type requerido")

    headers = None
    if usuario and rol:
        headers = {
            "X-User": str(usuario).strip().lower(),
            "X-Role": str(rol).strip().lower()
        }

    data = {
        "event_type": event_type,
        "payload": payload or {}
    }

    if event_date:
        data["event_date"] = event_date

    resp = api_request(
        "POST",
        "/hr/events/",
        json=data,
        headers=headers,
        timeout=15
    )

    resp.raise_for_status()
    return resp.json()


def aprobar_evento_hr(event_id, comentario=None):
    data = {}
    if comentario:
        data["comentario"] = comentario

    resp = api_request(
        "PATCH",
        f"/hr/events/{event_id}/approve",
        json=data,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def rechazar_evento_hr(event_id, comentario):
    if not comentario:
        raise ValueError("comentario requerido")

    resp = api_request(
        "PATCH",
        f"/hr/events/{event_id}/reject",
        json={"comentario": comentario},
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def obtener_vacaciones_disponibles():
    resp = api_request(
        "GET",
        "/hr/events/vacaciones/disponibles",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# HHRR — EMPLEADOS
# ============================================================

def hr_listar_empleados(page=1, page_size=50, nombre=None, codigo=None, estado=None, usuario=None):
    params = {
        "page": page,
        "page_size": page_size
    }

    if nombre:
        params["nombre"] = nombre

    if codigo:
        params["codigo"] = codigo

    if estado:
        params["estado"] = estado

    if usuario:
        params["usuario"] = usuario

    resp = api_request(
        "GET",
        "/hr/employees",
        params=params
    )
    resp.raise_for_status()
    return resp.json()


def hr_crear_empleado(payload: dict):
    resp = api_request(
        "POST",
        "/hr/employees",
        json=payload
    )
    resp.raise_for_status()
    return resp.json()


def hr_actualizar_empleado(empleado_id, payload):
    resp = api_request(
        "PUT",
        f"/hr/employees/{empleado_id}",
        json=payload
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# NOTICIAS
# ============================================================

def hr_publicar_noticias(**payload):
    resp = api_request(
        "POST",
        "/noticias",
        json=payload,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def hr_obtener_ultima_noticia():
    resp = api_request(
        "GET",
        "/noticias/latest",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# POLÍTICAS
# ============================================================

def listar_politicas_hr(categoria=None, solo_activas=True):
    params = {"solo_activas": solo_activas}

    if categoria:
        params["categoria"] = categoria

    resp = api_request(
        "GET",
        "/hr/policies",
        params=params,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def crear_politica_hr(payload):
    resp = api_request(
        "POST",
        "/hr/policies",
        json=payload,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def actualizar_politica_hr(policy_id, payload):
    resp = api_request(
        "PUT",
        f"/hr/policies/{policy_id}",
        json=payload,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def eliminar_politica_hr(policy_id):
    resp = api_request(
        "DELETE",
        f"/hr/policies/{policy_id}",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — BOARD
# ============================================================
def get_comercial_board_api(
    cliente=None,
    continente=None,
    pais=None,
    puerto=None,
    surveyor=None,
    estados=None,
    year=None,              # 👈 AÑADIDO
    fecha_desde=None,
    fecha_hasta=None
):
    """
    Llama al endpoint /comercial/board
    Retorna SIEMPRE list[dict]
    """

    params = {}

    def _clean(v):
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    cliente = _clean(cliente)
    continente = _clean(continente)
    pais = _clean(pais)
    puerto = _clean(puerto)
    surveyor = _clean(surveyor)
    fecha_desde = _clean(fecha_desde)
    fecha_hasta = _clean(fecha_hasta)

    if cliente:
        params["cliente"] = cliente
    if continente:
        params["continente"] = continente
    if pais:
        params["pais"] = pais
    if puerto:
        params["puerto"] = puerto
    if surveyor:
        params["surveyor"] = surveyor

    # estados → List[str] para FastAPI
    if estados:
        if isinstance(estados, (list, tuple)):
            estados_norm = [str(e).strip() for e in estados if str(e).strip()]
            if estados_norm:
                params["estados"] = estados_norm
        else:
            s = str(estados).strip()
            if s:
                params["estados"] = [s]

    # 👇 AÑO
    if year is not None:
        params["year"] = int(year)

    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        params["fecha_hasta"] = fecha_hasta

    # URL absoluta blindada
    url = f"{BASE_URL}/comercial/board"
    if url.startswith("/"):
        url = f"{BASE_URL}{url}"

    resp = api_request(
        "GET",
        url,
        params=params,
        timeout=20
    )

    if resp.status_code >= 400:
        try:
            j = resp.json()
            detail = j.get("detail") or j.get("error") or j
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    try:
        data = resp.json()
    except Exception:
        return []

    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]

    if isinstance(data, dict):
        maybe = data.get("data")
        if isinstance(maybe, list):
            return [r for r in maybe if isinstance(r, dict)]
        return []

    return []




# ============================================================
# COMERCIAL — CLIENT VIEW (ANALYTICS)
# ============================================================
def get_comercial_client_view_api(
    year=None,
    year_from=None,
    year_to=None,
    cliente=None,
    servicio=None
):
    """
    GET /comercial/client-view
    Analítica comercial por Cliente / Servicio
    """

    params = {}

    # ---------------- AÑOS ----------------
    if year is not None:
        try:
            params["year"] = int(year)
        except Exception:
            pass

    if year_from is not None:
        try:
            params["year_from"] = int(year_from)
        except Exception:
            pass

    if year_to is not None:
        try:
            params["year_to"] = int(year_to)
        except Exception:
            pass

    # ---------------- FILTROS ----------------
    if cliente:
        cliente = str(cliente).strip()
        if cliente:
            params["cliente"] = cliente

    if servicio:
        servicio = str(servicio).strip()
        if servicio:
            params["servicio"] = servicio

    # ---------------- REQUEST ----------------
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/client-view",
        params=params,
        timeout=30
    )

    # ---------------- ERRORES ----------------
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    # ---------------- PARSEO ----------------
    payload = resp.json() or {}

    return {
        "year_applied": payload.get("year_applied"),
        "available_years": payload.get("available_years", []),
        "kpis": payload.get("kpis", {}),
        "data": payload.get("data", [])
    }


# ============================================================
# COMERCIAL — CLIENTES (DETALLE / LISTADO)
# ============================================================
def get_comercial_clientes_api(
    id: int | None = None,
    codigo: str | None = None,
    nombre: str | None = None
):
    """
    GET /comercial/clientes
    Detalle de clientes para Analytics Comercial
    """

    params = {}

    # ---------------- FILTROS ----------------
    if id is not None:
        try:
            params["id"] = int(id)
        except Exception:
            pass

    if codigo:
        codigo = str(codigo).strip()
        if codigo:
            params["codigo"] = codigo

    if nombre:
        nombre = str(nombre).strip()
        if nombre:
            params["nombre"] = nombre

    # ---------------- REQUEST ----------------
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/clientes",
        params=params,
        timeout=30
    )

    # ---------------- ERRORES ----------------
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    # ---------------- PARSEO ----------------
    payload = resp.json() or {}

    return {
        "total": payload.get("total", 0),
        "data": payload.get("data", [])
    }


# ============================================================
# COMERCIAL — ANALYTICS / PUERTOS (TABLA + PARETO)
# ============================================================
def get_comercial_ports_analytics_api(
    year_from: int | None = None,
    year_to: int | None = None,
    clientes: list[str] | None = None,
    continente: str | None = None,
    pais: str | None = None
):
    """
    GET /comercial/analytics/puertos
    Analítica comercial por puerto (tabla, frecuencia, pareto, márgenes)
    """

    params = {}

    # ---------------- AÑOS ----------------
    if year_from is not None:
        try:
            params["year_from"] = int(year_from)
        except Exception:
            pass

    if year_to is not None:
        try:
            params["year_to"] = int(year_to)
        except Exception:
            pass

    # ---------------- FILTROS ----------------
    if clientes:
        if isinstance(clientes, (list, tuple)):
            clientes_clean = [
                str(c).strip()
                for c in clientes
                if str(c).strip()
            ]
            if clientes_clean:
                params["clientes"] = clientes_clean

    if continente:
        continente = str(continente).strip()
        if continente:
            params["continente"] = continente

    if pais:
        pais = str(pais).strip()
        if pais:
            params["pais"] = pais

    # ---------------- REQUEST ----------------
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/puertos",
        params=params,
        timeout=30
    )

    # ---------------- ERRORES ----------------
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    # ---------------- PARSEO ----------------
    payload = resp.json()

    if not isinstance(payload, dict):
        return {"data": []}

    return {
        "data": payload.get("data", [])
    }



# ============================================================
# COMERCIAL — ANALYTICS / PUERTOS / KPIs
# ============================================================
def get_comercial_ports_kpis_api(
    year_from: int | None = None,
    year_to: int | None = None,
    clientes: list[str] | None = None,
    continente: str | None = None,
    pais: str | None = None
):
    """
    GET /comercial/analytics/puertos/kpis
    KPIs agregados comerciales (backend-only logic)
    """

    params = {}

    # ---------------- AÑOS ----------------
    if year_from is not None:
        try:
            params["year_from"] = int(year_from)
        except Exception:
            pass

    if year_to is not None:
        try:
            params["year_to"] = int(year_to)
        except Exception:
            pass

    # ---------------- FILTROS ----------------
    if clientes:
        if isinstance(clientes, (list, tuple)):
            clientes_clean = [
                str(c).strip()
                for c in clientes
                if str(c).strip()
            ]
            if clientes_clean:
                params["clientes"] = clientes_clean

    if continente:
        continente = str(continente).strip()
        if continente:
            params["continente"] = continente

    if pais:
        pais = str(pais).strip()
        if pais:
            params["pais"] = pais

    # ---------------- REQUEST ----------------
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/puertos/kpis",
        params=params,
        timeout=30
    )

    # ---------------- ERRORES ----------------
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    # ---------------- PARSEO ----------------
    payload = resp.json()

    if not isinstance(payload, dict):
        return {
            "clientes": 0,
            "paises": 0,
            "puertos": 0,
            "facturacion": 0.0,
            "costos": 0.0,
            "margen_bruto": 0.0,
            "margen_neto": 0.0,
            "rentabilidad": 0.0,
            "rentabilidad_pct": 0.0
        }

    return {
        "clientes": payload.get("clientes", 0),
        "paises": payload.get("paises", 0),
        "puertos": payload.get("puertos", 0),
        "facturacion": float(payload.get("facturacion", 0) or 0),
        "costos": float(payload.get("costos", 0) or 0),
        "margen_bruto": float(payload.get("margen_bruto", 0) or 0),
        "margen_neto": float(payload.get("margen_neto", 0) or 0),
        "rentabilidad": float(payload.get("rentabilidad", 0) or 0),
        "rentabilidad_pct": float(payload.get("rentabilidad_pct", 0) or 0),
    }


# ============================================================
# COMERCIAL — ANALYTICS / PUERTOS / FILTROS
# ============================================================
def get_comercial_ports_filters_api():
    """
    GET /comercial/analytics/puertos/filtros
    Años (desde fecha_inicio) y clientes para combobox
    """

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/puertos/filtros",
        timeout=30
    )

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    payload = resp.json()

    if not isinstance(payload, dict):
        return {
            "years": [],
            "clientes": []
        }

    return {
        "years": payload.get("years", []),
        "clientes": payload.get("clientes", [])
    }


# ============================================================
# COMERCIAL — PORTS COVERAGE ANALYTICS API CLIENT
# ============================================================

def get_comercial_ports_coverage_api(
    year_from=None,
    year_to=None,
    cliente=None,
    min_ops=3
):
    """
    Obtiene análisis de cobertura de puertos:
    - Sin operación
    - Operación mínima
    - Operación activa

    Driver: continentes_paises_puertos
    Fuente: servicios
    """

    params = {}

    if year_from:
        params["year_from"] = year_from

    if year_to:
        params["year_to"] = year_to

    if cliente:
        params["cliente"] = cliente

    if min_ops is not None:
        params["min_ops"] = min_ops

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/ports-coverage",
        params=params,
        timeout=30
    )

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    return resp.json()

# ============================================================
# HELPERS — NORMALIZACIÓN DE PARAMS
# ============================================================

def _safe_int(v):
    try:
        return int(v)
    except Exception:
        return None


def _safe_str(v):
    if v is None:
        return None
    v = str(v).strip()
    return v if v else None


# ============================================================
# COMERCIAL — SERVICIOS ANALYTICS POR SERVICIO
# ============================================================
def get_comercial_servicios_by_servicio_api(
    year_from=None,
    year_to=None,
    quarter=None,
    continente=None,
    pais=None,
    puerto=None
):
    """
    Rentabilidad por servicio (operacion)
    • Backend controla años (default / exacto / rango)
    • Quarter es opcional (Q1–Q4)
    """

    params = {}

    # ---------------- AÑOS ----------------
    yf = _safe_int(year_from)
    yt = _safe_int(year_to)

    if yf is not None:
        params["year_from"] = yf
    if yt is not None:
        params["year_to"] = yt

    # ---------------- QUARTER ----------------
    q = _safe_str(quarter)
    if q:
        params["quarter"] = q

    # ---------------- GEO ----------------
    c = _safe_str(continente)
    p = _safe_str(pais)
    pt = _safe_str(puerto)

    if c:
        params["continente"] = c
    if p:
        params["pais"] = p
    if pt:
        params["puerto"] = pt

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/by-servicio",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — SERVICIOS NO OFRECIDOS
# ============================================================
def get_comercial_servicios_no_ofrecidos_api(
    year_from=None,
    year_to=None,
    quarter=None,
    continente=None,
    pais=None,
    puerto=None
):
    """
    Servicios del catálogo NO ejecutados
    (por año / rango / quarter)
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)

    if yf is not None:
        params["year_from"] = yf
    if yt is not None:
        params["year_to"] = yt

    q = _safe_str(quarter)
    if q:
        params["quarter"] = q

    c = _safe_str(continente)
    p = _safe_str(pais)
    pt = _safe_str(puerto)

    if c:
        params["continente"] = c
    if p:
        params["pais"] = p
    if pt:
        params["puerto"] = pt

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/not-offered",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — COSTOS POR SURVEYOR
# ============================================================
def get_comercial_costos_por_surveyor_api(
    year_from=None,
    year_to=None
):
    """
    Costos y rentabilidad por surveyor
    • Backend aplica fecha híbrida (fecha_inicio / num_informe)
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)

    if yf is not None:
        params["year_from"] = yf

    if yt is not None:
        params["year_to"] = yt

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/costos-por-surveyor",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — SERVICIOS POR UBICACIÓN
# ============================================================
def get_comercial_servicios_por_ubicacion_api(
    year_from=None,
    year_to=None
):
    """
    Servicios por continente / país / puerto
    • Backend aplica fecha híbrida (fecha_inicio / num_informe)
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)

    if yf is not None:
        params["year_from"] = yf

    if yt is not None:
        params["year_to"] = yt

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/por-ubicacion",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — KPIs EJECUTIVOS
# ============================================================
def get_comercial_servicios_kpis_api(
    year_from=None,
    year_to=None,
    continente=None,
    pais=None,
    puerto=None,
    operacion=None
):
    """
    KPIs ejecutivos de servicios
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)

    if yf is not None:
        params["year_from"] = yf
    if yt is not None:
        params["year_to"] = yt

    c = _safe_str(continente)
    p = _safe_str(pais)
    pt = _safe_str(puerto)
    op = _safe_str(operacion)

    if c:
        params["continente"] = c
    if p:
        params["pais"] = p
    if pt:
        params["puerto"] = pt
    if op:
        params["operacion"] = op

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/kpis",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — COSTOS SURVEYOR PARETO
# ============================================================
def get_comercial_costos_surveyor_pareto_api(
    year=None,
    operacion=None
):
    """
    Pareto 80/20 de honorarios por surveyor
    """

    params = {}

    y = _safe_int(year)
    if y:
        params["year"] = y

    op = _safe_str(operacion)
    if op:
        params["operacion"] = op

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/costos-surveyor-pareto",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()



# ============================================================
# COMERCIAL — SERVICIOS NO OFRECIDOS
# ============================================================
def get_comercial_servicios_no_ofrecidos_api(
    year_from=None,
    year_to=None,
    quarter=None,
    continente=None,
    pais=None,
    puerto=None
):
    """
    Servicios del catálogo NO ejecutados en el período
    • Quarter opcional
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)
    q = _safe_str(quarter)

    if yf is not None:
        params["year_from"] = yf
    if yt is not None:
        params["year_to"] = yt
    if q:
        params["quarter"] = q

    c = _safe_str(continente)
    p = _safe_str(pais)
    pt = _safe_str(puerto)

    if c:
        params["continente"] = c
    if p:
        params["pais"] = p
    if pt:
        params["puerto"] = pt

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/not-offered",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()



# ============================================================
# COMERCIAL — COSTOS POR SURVEYOR
# ============================================================
def get_comercial_costos_por_surveyor_api(
    year_from=None,
    year_to=None,
    quarter=None
):
    """
    Costos y rentabilidad por surveyor
    • Quarter opcional
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)
    q = _safe_str(quarter)

    if yf is not None:
        params["year_from"] = yf
    if yt is not None:
        params["year_to"] = yt
    if q:
        params["quarter"] = q

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/costos-por-surveyor",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — SERVICIOS POR UBICACIÓN
# ============================================================
def get_comercial_servicios_por_ubicacion_api(
    year_from=None,
    year_to=None,
    quarter=None
):
    """
    Servicios por continente / país / puerto
    • Quarter opcional
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)
    q = _safe_str(quarter)

    if yf is not None:
        params["year_from"] = yf
    if yt is not None:
        params["year_to"] = yt
    if q:
        params["quarter"] = q

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/por-ubicacion",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — KPIs EJECUTIVOS
# ============================================================
def get_comercial_servicios_kpis_api(
    year_from=None,
    year_to=None,
    quarter=None,
    continente=None,
    pais=None,
    puerto=None,
    operacion=None
):
    """
    KPIs ejecutivos de servicios
    • Quarter opcional
    """

    params = {}

    yf = _safe_int(year_from)
    yt = _safe_int(year_to)
    q = _safe_str(quarter)

    if yf is not None:
        params["year_from"] = yf
    if yt is not None:
        params["year_to"] = yt
    if q:
        params["quarter"] = q

    c = _safe_str(continente)
    p = _safe_str(pais)
    pt = _safe_str(puerto)
    op = _safe_str(operacion)

    if c:
        params["continente"] = c
    if p:
        params["pais"] = p
    if pt:
        params["puerto"] = pt
    if op:
        params["operacion"] = op

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/kpis",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()


# ============================================================
# COMERCIAL — COSTOS SURVEYOR PARETO
# ============================================================
def get_comercial_costos_surveyor_pareto_api(
    year=None,
    quarter=None,
    operacion=None
):
    """
    Pareto 80/20 de honorarios por surveyor
    • Quarter opcional
    """

    params = {}

    y = _safe_int(year)
    q = _safe_str(quarter)
    op = _safe_str(operacion)

    if y:
        params["year"] = y
    if q:
        params["quarter"] = q
    if op:
        params["operacion"] = op

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/analytics/servicios/costos-surveyor-pareto",
        params=params,
        timeout=TIMEOUT
    )

    resp.raise_for_status()
    return resp.json()




# ============================================================
# COMERCIAL — PRECIOS (SERVICIOS)
# ============================================================

# ------------------------------------------------------------
# META — DESPLEGABLES (SERVICIOS / CLIENTES / UBICACIONES)
# GET /comercial/precios/meta
# ------------------------------------------------------------
def get_comercial_precios_meta_api():
    """
    Retorna data base para popup de precios:
    - servicios (serviciosmd)
    - clientes (cliente)
    - ubicaciones (continentes / paises / puertos)
    """
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/precios/meta",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# LISTAR PRECIOS
# GET /comercial/precios
# ------------------------------------------------------------
def get_comercial_precios_api():
    """
    Lista todos los precios configurados
    """
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/precios",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# CREAR PRECIO
# POST /comercial/precios
# ------------------------------------------------------------
def post_comercial_precio_api(data: dict):
    """
    data esperado:
    {
        servicio: str,
        cliente: str,
        continente: str | None,
        pais: str | None,
        puerto: str | None,
        precio: float
    }
    """
    resp = api_request(
        "POST",
        f"{BASE_URL}/comercial/precios",
        json=data,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# ACTUALIZAR PRECIO
# PUT /comercial/precios/{precio_id}
# ------------------------------------------------------------
def put_comercial_precio_api(precio_id: int, data: dict):
    """
    data puede incluir:
    {
        servicio?,
        cliente?,
        continente?,
        pais?,
        puerto?,
        precio?,
        activo?
    }
    """
    resp = api_request(
        "PUT",
        f"{BASE_URL}/comercial/precios/{precio_id}",
        json=data,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# ELIMINAR PRECIO
# DELETE /comercial/precios/{precio_id}
# ------------------------------------------------------------
def delete_comercial_precio_api(precio_id: int):
    """
    Elimina un precio por ID
    """
    resp = api_request(
        "DELETE",
        f"{BASE_URL}/comercial/precios/{precio_id}",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()



# ============================================================
# COMERCIAL — COTIZACIONES
# ============================================================

# ------------------------------------------------------------
# META — DESPLEGABLES + PRECIOS
# GET /comercial/cotizaciones/meta
# ------------------------------------------------------------
def get_comercial_cotizaciones_meta_api():
    """
    Retorna data base para popup de cotizaciones:
    - clientes
    - servicios
    - ubicaciones
    - precios activos
    """
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/cotizaciones/meta",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# LISTAR COTIZACIONES
# GET /comercial/cotizaciones
# ------------------------------------------------------------
def get_comercial_cotizaciones_api():
    """
    Lista todas las cotizaciones
    """
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/cotizaciones",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# Conscutivo Cotizaciones
# 
# ------------------------------------------------------------

def get_comercial_next_quotation_number_api():
    """
    Obtiene el siguiente quotation_number desde backend
    Ej: Quotation 00001
    """
    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/cotizaciones/next-quotation-number",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()



# ------------------------------------------------------------
# CREAR COTIZACIÓN
# POST /comercial/cotizaciones
# ------------------------------------------------------------
def post_comercial_cotizacion_api(data: dict):
    """
    data esperado (ALINEADO A public.cotizaciones):

    {
        cliente: str,
        servicio?: str,
        continente?: str,
        pais?: str,
        puerto?: str,
        precio?: float,
        idioma?: 'ES' | 'EN',
        validez?: int,
        status?: str,

        servicio_1?: str,
        precio_1?: float,
        servicio_2?: str,
        precio_2?: float,
        servicio_3?: str,
        precio_3?: float,
        servicio_4?: str,
        precio_4?: float
    }
    """
    resp = api_request(
        "POST",
        f"{BASE_URL}/comercial/cotizaciones",
        json=data,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# ACTUALIZAR COTIZACIÓN
# PUT /comercial/cotizaciones/{id}
# ------------------------------------------------------------
def put_comercial_cotizacion_api(cotizacion_id: int, data: dict):
    """
    Actualiza una cotización existente.

    Ejemplos:
    - Aprobar: {"status": "APROBADO"}
    - Cancelar: {"status": "CANCELADO", "razon_cancelacion": "..."}
    """

    if not isinstance(data, dict) or not data:
        raise ValueError("Debe enviar al menos un campo a actualizar")

    resp = api_request(
        "PUT",
        f"{BASE_URL}/comercial/cotizaciones/{cotizacion_id}",
        json=data,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# APROBAR COTIZACIÓN
# ------------------------------------------------------------
def aprobar_comercial_cotizacion_api(cotizacion_id: int):
    return put_comercial_cotizacion_api(
        cotizacion_id,
        {
            "status": "APROBADO"
        }
    )


# ------------------------------------------------------------
# CANCELAR COTIZACIÓN
# ------------------------------------------------------------
def cancelar_comercial_cotizacion_api(
    cotizacion_id: int,
    razon_cancelacion: str
):
    if not razon_cancelacion:
        raise ValueError("Debe indicar la razón de cancelación")

    return put_comercial_cotizacion_api(
        cotizacion_id,
        {
            "status": "CANCELADO",
            "razon_cancelacion": razon_cancelacion
        }
    )



# ------------------------------------------------------------
# ELIMINAR COTIZACIÓN
# DELETE /comercial/cotizaciones/{id}
# ------------------------------------------------------------
def delete_comercial_cotizacion_api(cotizacion_id: int):
    """
    Elimina una cotización
    """
    resp = api_request(
        "DELETE",
        f"{BASE_URL}/comercial/cotizaciones/{cotizacion_id}",
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()


# ------------------------------------------------------------
# KPIs COTIZACIONES COMERCIALES
# GET /comercial/cotizaciones/kpis
# ------------------------------------------------------------
def get_comercial_cotizaciones_kpis_api(
    year: int | None = None,
    cliente: str | None = None,
    servicio: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    status: str | None = None
):
    params = {}

    if year:
        params["year"] = year
    if cliente:
        params["cliente"] = cliente
    if servicio:
        params["servicio"] = servicio
    if pais:
        params["pais"] = pais
    if puerto:
        params["puerto"] = puerto
    if status:
        params["status"] = status

    resp = api_request(
        "GET",
        f"{BASE_URL}/comercial/cotizaciones/kpis",
        params=params,
        timeout=15
    )
    resp.raise_for_status()
    return resp.json()



# ============================================================
# CONTAINER REPORTS
# ============================================================

def get_container_reports_list_api():
    """
    GET /container-reports/list
    Lista de Container Reports (tabla Informes)
    """
    url = f"{BASE_URL}/container-reports/list"
    return api_request("GET", url).json()


def get_container_report_by_id_api(report_id: int):
    """
    GET /container-reports/{id}
    """
    url = f"{BASE_URL}/container-reports/{report_id}"
    return api_request("GET", url).json()


# ============================================================
# CONTAINER REPORT — CREATE
# ============================================================

def create_container_report_api(payload: dict, user: str = None):
    """
    POST /container-reports
    Crea un Container Report y garantiza respuesta JSON válida
    """

    if not isinstance(payload, dict):
        raise ValueError("payload debe ser dict")

    data = payload.copy()

    # --------------------------------------------------
    # Defaults controlados desde frontend
    # --------------------------------------------------
    data["status"] = data.get("status") or "draft"

    if user:
        data["user"] = user

    # --------------------------------------------------
    # REQUEST (IMPORTANTE: usar endpoint relativo)
    # --------------------------------------------------
    resp = api_request(
        "POST",
        "/container-reports",
        json=data,
        timeout=25
    )

    # --------------------------------------------------
    # VALIDACIÓN RESPUESTA
    # --------------------------------------------------
    if resp is None:
        raise Exception("No response from server")

    if resp.status_code not in (200, 201):
        raise Exception(
            f"Backend error ({resp.status_code}): {resp.text}"
        )

    # --------------------------------------------------
    # JSON SEGURO
    # --------------------------------------------------
    try:
        result = resp.json()

        if not isinstance(result, dict):
            raise Exception("Respuesta inválida del backend")

        return result

    except Exception:
        raise Exception(
            "Invalid JSON response from backend:\n"
            f"{resp.text}"
        )


def update_container_report_api(report_id: int, payload: dict):
    """
    PUT /container-reports/{id}
    """
    url = f"{BASE_URL}/container-reports/{report_id}"
    return api_request("PUT", url, json=payload).json()


def delete_container_report_api(report_id: int):
    """
    DELETE /container-reports/{id}
    """
    url = f"{BASE_URL}/container-reports/{report_id}"
    return api_request("DELETE", url).json()


# ============================================================
# INFORMES — CONTAINER REPORTS
# ============================================================

def get_container_report_excel_api(report_id: int):
    """
    Descarga el Excel del Container Report usando template backend.
    Endpoint:
        GET /container-reports/{report_id}/excel
    Retorna:
        requests.Response (stream binario)
    """
    if not report_id:
        raise ValueError("report_id is required")

    url = f"{BASE_URL}/container-reports/{report_id}/excel"

    # ⚠️ No usamos api_request aquí porque necesitamos el stream binario
    resp = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {get_user()}",
        },
        timeout=TIMEOUT,
        stream=True
    )

    if resp.status_code != 200:
        raise Exception(
            f"Error downloading Excel ({resp.status_code}): {resp.text}"
        )

    return resp

# ============================================================
# CONTAINER REPORTS — FILTROS BASE (CLIENTES / AÑOS)
# ============================================================

def get_container_report_filters_api():
    """
    Obtiene filtros base desde servicios
    (SOLO servicios con num_informe):
    - clientes
    - anios
    """

    url = "/container-reports/filters"

    try:
        resp = api_request("GET", url)

        if not resp or resp.status_code != 200:
            return {
                "clientes": [],
                "anios": []
            }

        data = resp.json() or {}

        return {
            "clientes": data.get("clientes", []),
            "anios": data.get("anios", [])
        }

    except Exception:
        return {
            "clientes": [],
            "anios": []
        }


# ============================================================
# CONTAINER REPORTS — MESES DISPONIBLES
# ============================================================

def get_container_report_months_api(
    cliente: str,
    anio: int
):
    """
    Retorna meses reales disponibles según:
    - cliente
    - año
    """

    if not all([cliente, anio]):
        return []

    url = "/container-reports/filters/months"

    params = {
        "cliente": cliente.strip(),
        "anio": int(anio)
    }

    try:
        resp = api_request("GET", url, params=params)

        if not resp or resp.status_code != 200:
            return []

        data = resp.json() or {}

        return data.get("meses", [])

    except Exception:
        return []


# ============================================================
# CONTAINER REPORTS — VESSELS / CONTAINERS DISPONIBLES
# ============================================================

def get_container_report_vessels_api(
    cliente: str,
    anio: int,
    mes: int
):
    """
    Retorna buques / contenedores reales según:
    - cliente
    - año
    - mes
    """

    if not all([cliente, anio, mes]):
        return []

    url = "/container-reports/filters/vessels"

    params = {
        "cliente": cliente.strip(),
        "anio": int(anio),
        "mes": int(mes)
    }

    try:
        resp = api_request("GET", url, params=params)

        if not resp or resp.status_code != 200:
            return []

        data = resp.json() or {}

        return data.get("buques_contenedor", [])

    except Exception:
        return []


# ============================================================
# CONTAINER REPORTS — INFORMES POR SERVICIO
# ============================================================

def get_container_reports_by_servicio_api(
    cliente: str,
    buque_contenedor: str,
    anio: int,
    mes: int
):
    """
    Retorna SOLO servicios con num_informe
    filtrados por:
    - cliente
    - buque / contenedor
    - año
    - mes
    """

    if not all([cliente, buque_contenedor, anio, mes]):
        return {"total": 0, "data": []}

    url = "/container-reports/informes"

    params = {
        "cliente": cliente.strip(),
        "buque_contenedor": buque_contenedor.strip(),
        "anio": int(anio),
        "mes": int(mes)
    }

    try:
        resp = api_request("GET", url, params=params)

        if not resp or resp.status_code != 200:
            return {"total": 0, "data": []}

        data = resp.json() or {}

        return {
            "total": data.get("total", 0),
            "data": data.get("data", [])
        }

    except Exception:
        return {"total": 0, "data": []}


def generate_container_report_pdf_api(report_id: int):
    """
    POST /container-reports/{report_id}/generate-pdf
    DEVUELVE UN PDF (NO JSON)
    """
    url = f"/container-reports/{report_id}/generate-pdf"
    return api_request(
        "POST",
        url,
        stream=True   # 🔴 CRÍTICO
    )



# ============================================================
# CONTAINER REPORTS — STATUS DISPONIBLES
# ============================================================

def get_container_report_statuses_api():
    """
    GET /container-reports/statuses

    Retorna los status reales disponibles en container_reports.status
    Incluye 'All' para no filtrar.
    """

    url = "/container-reports/statuses"

    try:
        resp = api_request("GET", url)

        if not resp or resp.status_code != 200:
            return ["All"]

        data = resp.json() or {}

        statuses = data.get("data", [])
        if not statuses:
            return ["All"]

        return statuses

    except Exception:
        return ["All"]


# ============================================================
# Descargar PDF DE EXCEL A PDF
# ============================================================

def download_container_report_pdf_api(report_id: int):
    url = f"/container-reports/{report_id}/download-pdf"
    return api_request(
        "GET",
        url,
        stream=True   # 🔴 ESTO ES CRÍTICO
    )


# ============================================================
# PRESENTACIÓN CONTENEDORES
# ============================================================

def get_container_presentation_data_api(container_report_id):
    return api_request(
        "get",
        f"/container-presentation/{container_report_id}"
    )


def generate_container_presentation_pdf_api(report_id: int):
    return api_request(
        "GET",
        f"/container-presentation-pdf/{report_id}/presentation",
        stream=True
    )


def generate_container_unified_pdf_api(report_id: int):
    return api_request(
        "GET",
        f"/container-presentation-pdf/{report_id}/unified",
        stream=True
    )


# ============================================================
# PROYECTOS CÁLCULO — API CLIENT (BLINDADO)
# ============================================================

# ============================================================
# CREATE — CREAR PROYECTO / CALCULO (MULTI-LINE)
# ============================================================
def create_proyecto_calculo_api(payload: dict):
    """
    POST /proyectos-calculo
    payload DEBE incluir:
      - nombre_proyecto: str
      - personal_costos: list[float]
    """
    if not isinstance(payload, dict):
        raise ValueError("payload debe ser dict")

    if not payload.get("nombre_proyecto"):
        raise ValueError("nombre_proyecto es requerido")

    if not isinstance(payload.get("personal_costos"), list):
        raise ValueError("personal_costos debe ser lista")

    url = "/proyectos-calculo"

    resp = api_request(
        "POST",
        url,
        json=payload,
        timeout=20
    )

    if resp is None:
        raise Exception("No response from server")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail") or resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    try:
        return resp.json()
    except Exception:
        raise Exception(f"Invalid JSON response: {resp.text}")


# ============================================================
# LIST — LISTAR PROYECTOS
# ============================================================
def get_proyectos_calculo_api():
    """
    GET /proyectos-calculo
    Retorna:
      { total: int, data: [ proyectos agrupados ] }
    """
    url = "/proyectos-calculo"

    resp = api_request(
        "GET",
        url,
        timeout=15
    )

    if resp is None:
        return {"total": 0, "data": []}

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail") or resp.json()
        except Exception:
            detail = resp.text
        return {
            "total": 0,
            "data": [],
            "error": f"{resp.status_code} → {detail}"
        }

    try:
        return resp.json()
    except Exception:
        return {
            "total": 0,
            "data": [],
            "error": f"Invalid JSON response: {resp.text}"
        }


# ============================================================
# GET — OBTENER PROYECTO POR NOMBRE
# ============================================================
def get_proyecto_calculo_by_nombre_api(nombre_proyecto: str):
    """
    GET /proyectos-calculo/{nombre_proyecto}
    Retorna:
      {
        data: {
          header: {...},
          personas: [...]
        }
      }
    """
    if not nombre_proyecto:
        raise ValueError("nombre_proyecto requerido")

    url = f"/proyectos-calculo/{nombre_proyecto}"

    resp = api_request(
        "GET",
        url,
        timeout=15
    )

    if resp is None:
        raise Exception("No response from server")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail") or resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    try:
        return resp.json()
    except Exception:
        raise Exception(f"Invalid JSON response: {resp.text}")


# ============================================================
# UPDATE — ACTUALIZAR PROYECTO (POR NOMBRE)
# ============================================================
def update_proyecto_calculo_api(nombre_proyecto: str, payload: dict):
    """
    PUT /proyectos-calculo/{nombre_proyecto}
    Actualiza TODAS las filas del proyecto
    """
    if not nombre_proyecto:
        raise ValueError("nombre_proyecto requerido")

    if not isinstance(payload, dict) or not payload:
        raise ValueError("payload debe ser dict no vacío")

    url = f"/proyectos-calculo/{nombre_proyecto}"

    resp = api_request(
        "PUT",
        url,
        json=payload,
        timeout=20
    )

    if resp is None:
        raise Exception("No response from server")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail") or resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    try:
        return resp.json()
    except Exception:
        raise Exception(f"Invalid JSON response: {resp.text}")


# ============================================================
# DELETE — ELIMINAR PROYECTO (POR NOMBRE)
# ============================================================
def delete_proyecto_calculo_api(nombre_proyecto: str):
    """
    DELETE /proyectos-calculo/{nombre_proyecto}
    Elimina TODAS las filas del proyecto
    """
    if not nombre_proyecto:
        raise ValueError("nombre_proyecto requerido")

    url = f"/proyectos-calculo/{nombre_proyecto}"

    resp = api_request(
        "DELETE",
        url,
        timeout=15
    )

    if resp is None:
        raise Exception("No response from server")

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail") or resp.json()
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    try:
        return resp.json()
    except Exception:
        # DELETE puede no devolver body
        return {"success": True}


# ============================================================
# VESSEL REPORTS — GRAIN SAMPLING (API CLIENT ALIGNED)
# ============================================================




# ============================================================
# INTERNAL RESPONSE HANDLER (HARDENED)
# ============================================================

def _handle_response(resp):

    if resp is None:
        raise Exception("No response from server")

    if resp.status_code == 404:
        return None

    if resp.status_code not in (200, 201):
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    try:
        return resp.json()
    except Exception:
        raise Exception("Invalid JSON response from server")


# ============================================================
# CREATE — 1:1 WITH CURRENT FRONTEND (BLINDADO)
# ============================================================

def create_vessel_grain_sampling_api(payload: dict):
    """
    POST /vessel-grain-sampling

    Payload aligned 100% with GrainSamplingVesselForm
    Backend additionally updates:
        servicios.status_informe = 'Created'
        (based on cert_no == num_informe)
    """

    # --------------------------------------------------------
    # VALIDACIÓN DE PAYLOAD
    # --------------------------------------------------------
    if not isinstance(payload, dict):
        raise ValueError("payload must be dict")

    required_fields = [
        "cert_no",
        "place_date",
        "vessel_name",
        "requested_by",
    ]

    for field in required_fields:
        if not payload.get(field):
            raise ValueError(f"Missing required field: {field}")

    # --------------------------------------------------------
    # REQUEST
    # --------------------------------------------------------
    resp = api_request(
        "POST",
        "/vessel-grain-sampling",
        json=payload,
        timeout=25
    )

    # --------------------------------------------------------
    # BLINDAJE DE RESPUESTA
    # --------------------------------------------------------
    if resp is None:
        raise Exception("No response from server")

    if resp.status_code != 200:
        raise Exception(
            f"Backend error ({resp.status_code}): {resp.text}"
        )

    # --------------------------------------------------------
    # JSON SEGURO
    # --------------------------------------------------------
    try:
        data = resp.json()
    except Exception:
        raise Exception(
            "Invalid JSON response from backend:\n"
            f"{resp.text}"
        )

    # --------------------------------------------------------
    # VALIDACIÓN LÓGICA
    # --------------------------------------------------------
    if not isinstance(data, dict):
        raise Exception("Invalid response structure from backend")

    if not data.get("success"):
        raise Exception(data.get("detail", "Unknown backend error"))

    return data


# ============================================================
# LIST — GRID VIEW
# ============================================================

def get_vessel_grain_sampling_list_api():
    """
    GET /vessel-grain-sampling

    Devuelve:
    {
        success: bool,
        count: int,
        data: list
    }
    """

    resp = api_request(
        "GET",
        "/vessel-grain-sampling",
        timeout=15
    )

    try:
        data = _handle_response(resp)

        # Hardening defensivo
        if not isinstance(data, dict):
            return {"success": False, "count": 0, "data": []}

        data.setdefault("success", False)
        data.setdefault("count", 0)
        data.setdefault("data", [])

        return data

    except Exception:
        return {
            "success": False,
            "count": 0,
            "data": []
        }


# ============================================================
# GET BY ID — FULL REPORT
# ============================================================

def get_vessel_grain_sampling_by_id_api(report_id: int):
    """
    GET /vessel-grain-sampling/{id}

    Devuelve:
    {
        success: bool,
        data: {...}
    }
    """

    if not report_id:
        raise ValueError("report_id requerido")

    resp = api_request(
        "GET",
        f"/vessel-grain-sampling/{report_id}",
        timeout=15
    )

    data = _handle_response(resp)

    # Hardening
    if not isinstance(data, dict) or "data" not in data:
        raise ValueError("Respuesta inválida del servidor")

    return data


# ============================================================
# UPDATE — FULL UPDATE
# ============================================================

def update_vessel_grain_sampling_api(report_id: int, payload: dict):
    """
    PUT /vessel-grain-sampling/{id}

    Payload debe estar alineado con:
    {
        cert_no,
        place_date,
        vessel_name,
        requested_by,
        captain,
        chief_officer,
        arrival_buoy_time,
        nor_tendered_time,
        holds_opening_time,
        sampling_start_time,
        sampling_end_time,
        products,
        products_total,
        supervision,
        conclusion
    }
    """

    if not report_id:
        raise ValueError("report_id requerido")

    if not isinstance(payload, dict):
        raise ValueError("payload debe ser dict")

    resp = api_request(
        "PUT",
        f"/vessel-grain-sampling/{report_id}",
        json=payload,
        timeout=25
    )

    return _handle_response(resp)


# ============================================================
# DELETE
# ============================================================

def delete_vessel_grain_sampling_api(report_id: int):
    """
    DELETE /vessel-grain-sampling/{id}
    """

    if not report_id:
        raise ValueError("report_id requerido")

    resp = api_request(
        "DELETE",
        f"/vessel-grain-sampling/{report_id}",
        timeout=15
    )

    return _handle_response(resp)


# ============================================================
# AI — GRAIN SAMPLING IMPROVE (BILINGUAL SUPPORTED)
# ============================================================

def improve_grain_sampling_api(
    text: str,
    vessel: str | None = None,
    location: str | None = None,
    product: str | None = None,
    authority: str | None = None,
    language: str = "ES"   # 🔥 NUEVO
):
    """
    POST /reports/ai/improve/grain

    Mejora narrativa de reporte de muestreo de granos.
    Soporta idioma:
        - "ES" → Español
        - "EN" → English
    """

    if not text or not text.strip():
        raise ValueError("text es requerido")

    # 🔒 Normalización de idioma
    language = (language or "ES").upper()
    if language not in ("ES", "EN"):
        language = "ES"

    payload = {
        "text": text.strip(),
        "vessel": vessel,
        "location": location,
        "product": product,
        "authority": authority,
        "language": language,  # 🔥 NUEVO
    }

    resp = api_request(
        "POST",
        "/reports/ai/improve/grain",
        json=payload,
        timeout=30  # ligeramente mayor para IA
    )

    if resp is None:
        raise Exception("No response from server")

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text
        raise Exception(f"{resp.status_code} → {detail}")

    try:
        data = resp.json()
        return data.get("text", "").strip()
    except Exception:
        raise Exception("Invalid JSON response from AI service")

# ============================================================
# SERVICES SELECTOR — GRAIN SAMPLING (DYNAMIC + YEAR/MONTH)
# ============================================================

def get_services_for_grain_sampling_api(
    continente: str | None = None,
    pais: str | None = None,
    puerto: str | None = None,
    cliente: str | None = None,
    buque: str | None = None,
    operacion: str | None = None,
    year: int | None = None,
    month: int | None = None
):
    """
    GET /vessel-grain-sampling/services-selector

    Soporta:
    - Filtros dinámicos simultáneos
    - Filtro por año (fecha_inicio)
    - Filtro por mes (fecha_inicio)
    - Filtro por operacion (reemplaza estado)

    Retorna:
    {
        success: bool,
        count: int,
        data: [...],
        filters: {
            continentes: [],
            paises: [],
            puertos: [],
            clientes: [],
            buques: [],
            operaciones: [],
            years: [],
            months: []
        }
    }
    """

    params = {}

    # =====================================================
    # FILTROS BASE
    # =====================================================
    if continente:
        params["continente"] = continente

    if pais:
        params["pais"] = pais

    if puerto:
        params["puerto"] = puerto

    if cliente:
        params["cliente"] = cliente

    if buque:
        params["buque"] = buque

    if operacion:
        params["operacion"] = operacion

    # =====================================================
    # FILTRO AÑO / MES
    # =====================================================
    if year is not None:
        params["year"] = int(year)

    if month is not None:
        params["month"] = int(month)

    # =====================================================
    # REQUEST
    # =====================================================
    resp = api_request(
        "GET",
        "/vessel-grain-sampling/services-selector",
        params=params,
        timeout=15
    )

    # =====================================================
    # BLINDAJE
    # =====================================================
    if resp is None:
        return {
            "success": False,
            "count": 0,
            "data": [],
            "filters": {}
        }

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail")
        except Exception:
            detail = resp.text

        raise Exception(f"{resp.status_code} → {detail}")

    data = resp.json()

    return {
        "success": data.get("success", False),
        "count": data.get("count", 0),
        "data": data.get("data", []),
        "filters": data.get("filters", {})
    }



# ============================================================
# STATUS INFORMES — LIST (GRID)
# ============================================================

def get_status_informes_api(
    status=None,
    continente=None,
    pais=None,
    puerto=None,
    operacion=None,
    year=None,
    month=None
):
    """
    GET /status-informes

    Devuelve:
    {
        success: bool,
        count: int,
        data: list
    }
    """

    params = {}

    # -------------------------------
    # Normalización segura
    # -------------------------------
    if status:
        params["status"] = status.strip()

    if continente:
        params["continente"] = continente.strip()

    if pais:
        params["pais"] = pais.strip()

    if puerto:
        params["puerto"] = puerto.strip()

    if operacion:
        params["operacion"] = operacion.strip()

    # Year / Month deben ser INT
    try:
        if year:
            params["year"] = int(year)
    except Exception:
        pass

    try:
        if month:
            params["month"] = int(month)
    except Exception:
        pass

    # -------------------------------
    # Request
    # -------------------------------
    resp = api_request(
        "GET",
        "/status-informes",
        params=params,
        timeout=15
    )

    if resp is None:
        return {"success": False, "count": 0, "data": []}

    if resp.status_code != 200:
        return {
            "success": False,
            "count": 0,
            "data": []
        }

    # -------------------------------
    # JSON seguro
    # -------------------------------
    try:
        data = resp.json()

        if not isinstance(data, dict):
            return {"success": False, "count": 0, "data": []}

        return {
            "success": data.get("success", False),
            "count": data.get("count", 0),
            "data": data.get("data", [])
        }

    except Exception:
        return {
            "success": False,
            "count": 0,
            "data": []
        }


# ============================================================
# STATUS INFORMES — AVAILABLE STATUSES (COMBOBOX)
# ============================================================

def get_status_informes_statuses_api():
    """
    GET /status-informes/statuses

    Devuelve:
    {
        success: bool,
        data: [list of statuses]
    }
    """

    resp = api_request(
        "GET",
        "/status-informes/statuses",
        timeout=10
    )

    if resp is None:
        return []

    if resp.status_code != 200:
        return []

    try:
        data = resp.json()

        if not isinstance(data, dict):
            return []

        return data.get("data", []) or []

    except Exception:
        return []


# ============================================================
# STATUS INFORMES — UPDATE STATUS
# ============================================================

def update_status_informe_api(consec: int, new_status: str):
    """
    PUT /status-informes/{consec}
    """

    if not consec:
        raise ValueError("consec requerido")

    if not new_status:
        raise ValueError("new_status requerido")

    resp = api_request(
        "PUT",
        f"/status-informes/{consec}",
        json={"status_informe": new_status},
        timeout=15
    )

    if resp is None:
        raise Exception("No response from backend")

    if resp.status_code != 200:
        raise Exception(
            f"Backend error ({resp.status_code}): {resp.text}"
        )

    try:
        return resp.json()
    except Exception:
        raise Exception(
            "Invalid JSON response from backend:\n"
            f"{resp.text}"
        )



# ============================================================
# APPROVE + GET PDF
# ============================================================

def approve_vessel_grain_sampling_api(report_id: int):

    resp = api_request(
        "PUT",
        f"{BASE_URL}/vessel-grain-sampling/{report_id}/approve",
        timeout=60,
        stream=True
    )

    if resp.status_code != 200:
        raise Exception(resp.text)

    return resp


# ============================================================
# GENERATE WORD
# ============================================================

def generate_grain_sampling_word_api(report_id: int):

    resp = api_request(
        "POST",
        f"{BASE_URL}/vessel-grain-sampling/{report_id}/generate-word",
        timeout=60,
        stream=True
    )

    if resp.status_code != 200:
        raise Exception(resp.text)

    return resp


# =========================================================
# GENERATE VESSEL PRESENTATION PDF
# =========================================================
def generate_vessel_presentation_pdf_api(report_id: int):

    import requests

    url = f"{BASE_URL}/vessel-grain-sampling/{report_id}/presentation-pdf"

    try:
        response = requests.post(
            url,
            timeout=60,
            stream=True
        )

        # 🔴 Si backend devuelve error HTTP
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }

        return response

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =========================================================
# GET VESSEL PRESENTATION DATA
# =========================================================
def get_vessel_presentation_data_api(report_id: int):

    import requests

    url = f"{BASE_URL}/vessel-grain-sampling/{report_id}/presentation-data"

    try:
        response = requests.get(url, timeout=15)

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }

        return response.json()

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }



# =========================================================
# GENERATE VESSEL UNIFIED PDF
# =========================================================
def generate_vessel_unified_pdf_api(report_id: int):
    """
    Llama al endpoint:
    POST /vessel-grain-sampling/{id}/unified-pdf
    Devuelve stream del PDF unificado
    """

    import requests

    url = f"{BASE_URL}/vessel-grain-sampling/{report_id}/unified-pdf"

    try:
        response = requests.post(
            url,
            stream=True,
            timeout=120  # tiempo suficiente para generar ambos PDFs
        )

        return response

    except Exception as e:
        return {
            "error": f"Unified PDF API error: {str(e)}"
        }






# =========================================================
# VESSEL TRUCK SUPERVISION API
# =========================================================


def create_vessel_truck_supervision_api(data: dict):
    """
    POST /vessel-truck-supervision/
    """
    response = api_request(
        "POST",
        "/vessel-truck-supervision/",
        json=data
    )

    if not response.ok:
        raise Exception(response.text)

    return response.json()


def get_vessel_truck_supervision_list_api():
    """
    GET /vessel-truck-supervision/
    """
    response = api_request(
        "GET",
        "/vessel-truck-supervision/"
    )

    if not response.ok:
        raise Exception(response.text)

    return response.json()


def get_vessel_truck_supervision_by_id_api(report_id: int):
    """
    GET /vessel-truck-supervision/{id}
    """
    response = api_request(
        "GET",
        f"/vessel-truck-supervision/{report_id}"
    )

    if not response.ok:
        raise Exception(response.text)

    return response.json()


def update_vessel_truck_supervision_api(report_id: int, data: dict):
    """
    PUT /vessel-truck-supervision/{id}
    """
    response = api_request(
        "PUT",
        f"/vessel-truck-supervision/{report_id}",
        json=data
    )

    if not response.ok:
        raise Exception(response.text)

    return response.json()


# =========================================================
# VESSEL TRUCK SUPERVISION - SERVICIOS FILTER
# =========================================================

def filter_servicios_vessel_truck_api(filters: dict):
    """
    GET /vessel-truck-supervision/servicios-filter

    Retorna:
    {
        "filters": {...},
        "data": [...],
        "count": int
    }
    """

    try:
        # -----------------------------------------------------
        # LIMPIAR FILTROS VACÍOS
        # -----------------------------------------------------
        clean_filters = {
            k: v for k, v in filters.items()
            if v not in [None, "", []]
        }

        # -----------------------------------------------------
        # NORMALIZAR TIPOS
        # -----------------------------------------------------
        if "anio" in clean_filters:
            try:
                clean_filters["anio"] = int(clean_filters["anio"])
            except:
                del clean_filters["anio"]

        if "mes" in clean_filters:
            try:
                clean_filters["mes"] = int(clean_filters["mes"])
            except:
                del clean_filters["mes"]

        # -----------------------------------------------------
        # REQUEST
        # -----------------------------------------------------
        response = api_request(
            "GET",
            "/vessel-truck-supervision/servicios-filter",
            params=clean_filters
        )

        if not response.ok:
            try:
                error_json = response.json()
                raise Exception(error_json.get("detail", response.text))
            except:
                raise Exception(response.text)

        data = response.json()

        # -----------------------------------------------------
        # VALIDAR ESTRUCTURA
        # -----------------------------------------------------
        if not isinstance(data, dict):
            raise Exception("Respuesta inválida del servidor.")

        if "filters" not in data:
            data["filters"] = {}

        if "data" not in data:
            data["data"] = []

        if "count" not in data:
            data["count"] = len(data["data"])

        return data

    except Exception as e:
        raise Exception(f"Error consultando servicios: {str(e)}")



# =========================================================
# TRUCK SUPERVISION AI
# =========================================================
def improve_truck_supervision_api(payload: dict):
    """
    POST /reports/ai/improve/truck
    """

    response = api_request(
        "POST",
        "/reports/ai/improve/truck",
        json=payload
    )

    if not response.ok:
        raise Exception(response.text)

    return response.json()



# =========================================================
# TRUCK SUPERVISION Approve generar PDF
# =========================================================


def approve_vessel_truck_supervision_api(report_id: int):

    try:
        url = f"{BASE_URL}/vessel-truck-supervision/{report_id}/approve"

        response = requests.post(url)

        if response.status_code != 200:
            return {
                "success": False,
                "message": response.json().get("detail", "Unknown error")
            }

        return {
            "success": True,
            "file_bytes": response.content
        }

    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


def get_vessel_truck_supervision_by_id_api(report_id: int):
    """
    Obtiene datos del reporte vessel truck supervision
    """

    try:
        url = f"{BASE_URL}/vessel-truck-supervision/{report_id}"
        response = requests.get(url)

        if response.status_code != 200:
            return {
                "success": False,
                "error": response.json().get("detail", "Unknown error")
            }

        return response.json()

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }



def generate_truck_presentation_pdf_api(report_id: int):
    """
    Genera PDF de presentación Truck Supervision
    Devuelve response streaming
    """

    try:
        url = f"{BASE_URL}/vessel-truck-supervision/{report_id}/presentation"

        response = requests.get(
            url,
            stream=True
        )

        return response

    except Exception as e:
        return {
            "error": str(e)
        }



def generate_truck_unified_pdf_api(report_id: int):
    """
    Genera PDF unificado:
    Presentation + Report + Attachments
    Devuelve response streaming
    """

    try:
        url = f"{BASE_URL}/vessel-truck-supervision/{report_id}/unified"

        response = requests.get(
            url,
            stream=True
        )

        return response

    except Exception as e:
        return {
            "error": str(e)
        }






# =========================================================
# DRAFT SURVEY — FILTER SERVICIOS
# =========================================================

def filter_servicios_draft_api(
    year=None,
    month=None,
    continente=None,
    pais=None,
    puerto=None,
    operacion=None
):
    """
    Llama a:
    GET /draft-survey/servicios/filter
    """

    try:
        params = {}

        if year:
            params["year"] = year
        if month:
            params["month"] = month
        if continente:
            params["continente"] = continente
        if pais:
            params["pais"] = pais
        if puerto:
            params["puerto"] = puerto
        if operacion:
            params["operacion"] = operacion

        response = requests.get(
            f"{BASE_URL}/draft-survey/servicios/filter",
            params=params,
            timeout=30
        )

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================
# DRAFT SURVEY — CREATE
# =========================================================
def create_draft_survey_api(payload: dict):
    """
    POST /draft-survey/
    Retorna el JSON del backend (incluye general_id) para no romper el form.
    En error retorna {"success": False, "error": "...", "detail": "...", "status_code": n}
    """

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        return {
            "success": False,
            "error": "payload inválido (debe ser dict)",
            "detail": None,
            "status_code": None
        }

    url = f"{BASE_URL}/draft-survey/"

    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=(10, 60)
        )

        status = response.status_code

        # Intentar parsear JSON siempre
        try:
            data = response.json()
        except ValueError:
            data = None

        # HTTP error
        if not response.ok:
            backend_msg = None
            if isinstance(data, dict):
                backend_msg = data.get("detail") or data.get("error") or data.get("message")

            return {
                "success": False,
                "error": backend_msg or f"HTTP {status}",
                "detail": response.text if response.text else data,
                "status_code": status
            }

        # ✅ Éxito: devolver exactamente lo que manda el backend
        # (tu UI necesita general_id aquí)
        if isinstance(data, dict):
            return data

        # Si backend devolvió algo raro (list/None)
        return {
            "success": False,
            "error": "Respuesta inesperada del backend (no es JSON dict)",
            "detail": data,
            "status_code": status
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Timeout al conectar/leer respuesta del backend",
            "detail": None,
            "status_code": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "No se pudo conectar al backend (ConnectionError)",
            "detail": None,
            "status_code": None
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"RequestException: {str(e)}",
            "detail": None,
            "status_code": None
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error inesperado: {str(e)}",
            "detail": None,
            "status_code": None
        }

# =========================================================
# DRAFT SURVEY — LIST ALL
# =========================================================

def list_draft_surveys_api():
    """
    GET /draft-survey/
    """

    try:
        response = requests.get(
            f"{BASE_URL}/draft-survey/",
            timeout=30
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}

# =========================================================
# DRAFT SURVEY — GET BY ID
# =========================================================

def get_draft_survey_by_id_api(general_id: int):
    """
    GET /draft-survey/{general_id}
    """

    try:
        response = requests.get(
            f"{BASE_URL}/draft-survey/{general_id}",
            timeout=30
        )

        if response.status_code == 404:
            return {"success": False, "error": "Not found"}

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}

# =========================================================
# DRAFT SURVEY — UPDATE FULL (BLINDADO REAL)
# =========================================================
def update_full_draft_survey_api(general_id, payload):
    """
    PUT /draft-survey/{general_id}

    - Usa api_request() para respetar headers de sesión
    - Soporta general_id (int) o draft_report_number (str)
    - Devuelve JSON consistente
    - No rompe si la respuesta no viene en JSON
    """

    try:
        if general_id is None or str(general_id).strip() == "":
            return {
                "success": False,
                "error": "general_id vacío o inválido"
            }

        if not isinstance(payload, dict):
            return {
                "success": False,
                "error": "payload inválido: debe ser dict"
            }

        identifier = str(general_id).strip()
        url = f"{BASE_URL}/draft-survey/{identifier}"

        print("===================================")
        print("UPDATE FULL DRAFT SURVEY API")
        print("URL:", url)
        print("IDENTIFIER:", identifier)
        print("PAYLOAD:")
        print(payload)
        print("===================================")

        response = api_request(
            "PUT",
            url,
            json=payload,
            timeout=60
        )

        print("===================================")
        print("STATUS CODE PUT:", response.status_code)
        print("RESPONSE TEXT PUT:")
        print(response.text)
        print("===================================")

        try:
            data = response.json()
        except Exception:
            data = None

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": data if isinstance(data, dict) else response.text
            }

        if isinstance(data, dict):
            return data

        return {
            "success": False,
            "error": "Respuesta inválida del backend",
            "detail": response.text
        }

    except requests.Timeout:
        return {
            "success": False,
            "error": "Timeout al actualizar Draft Survey"
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": f"Error de red: {str(e)}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# =========================================================
# 🔥 COMPAT WRAPPER (NO ROMPE UI EXISTENTE)
# =========================================================

def update_draft_survey_api(general_id, payload: dict):
    """
    Wrapper para mantener compatibilidad con UI existente.
    Acepta general_id o draft_report_number.
    """

    return update_full_draft_survey_api(str(general_id), payload)

# =========================================================
# preview excel draft survey
# =========================================================

def preview_draft_survey_excel_api(payload: dict):
    """
    POST /draft-survey/preview/excel
    Retorna bytes del XLSX si ok, si no retorna {"success": False, "error": "..."}
    """
    try:
        response = requests.post(
            f"{BASE_URL}/draft-survey/preview/excel",
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            try:
                return {"success": False, "error": response.json().get("detail")}
            except Exception:
                return {"success": False, "error": response.text}

        return {"success": True, "content": response.content}

    except Exception as e:
        return {"success": False, "error": str(e)}



# =========================================================
# BALLAST — CREATE
# POST /draft-survey-extra/ballast/{draft_survey_id}
# =========================================================
def create_draft_survey_ballast_api(draft_survey_id, payload: dict):
    """
    Crea/guarda Ballast para un Draft Survey.

    SOPORTA:
      - general_id (int)
      - draft_report_number (str)

    Retorna SIEMPRE un dict con:
      - success: bool
      - data: dict | list | None
      - error: str | None
      - status_code: int | None
    """

    # -------------------------
    # Validaciones rápidas
    # -------------------------
    if draft_survey_id is None or str(draft_survey_id).strip() == "":
        return {
            "success": False,
            "data": None,
            "error": "draft_survey_id inválido (vacío)",
            "status_code": None
        }

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        return {
            "success": False,
            "data": None,
            "error": "payload inválido (debe ser dict)",
            "status_code": None
        }

    identifier = str(draft_survey_id).strip()
    url = f"{BASE_URL}/draft-survey-extra/ballast/{identifier}"

    # -------------------------
    # DEBUG
    # -------------------------
    print("===================================")
    print("CREATE BALLAST API")
    print("URL:", url)
    print("IDENTIFIER:", identifier)
    print("PAYLOAD:")
    print(payload)
    print("===================================")

    # -------------------------
    # Request
    # -------------------------
    try:
        response = api_request(
            "POST",
            url,
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=(10, 60)  # (connect, read)
        )

        status = response.status_code

        print("===================================")
        print("BALLAST CREATE STATUS:", status)
        print("BALLAST CREATE RESPONSE TEXT:")
        print(response.text)
        print("===================================")

        # Intentar parsear JSON (aunque venga error)
        try:
            data = response.json()
        except ValueError:
            data = None

        # Si HTTP no fue OK
        if not response.ok:
            backend_msg = None
            if isinstance(data, dict):
                backend_msg = (
                    data.get("detail")
                    or data.get("error")
                    or data.get("message")
                )

            return {
                "success": False,
                "data": data,
                "error": backend_msg or f"HTTP {status} al crear ballast",
                "status_code": status
            }

        # OK
        return {
            "success": True,
            "data": data,
            "error": None,
            "status_code": status
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "data": None,
            "error": "Timeout al conectar/leer respuesta del backend",
            "status_code": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "data": None,
            "error": "No se pudo conectar al backend (ConnectionError)",
            "status_code": None
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "data": None,
            "error": f"RequestException: {str(e)}",
            "status_code": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Error inesperado: {str(e)}",
            "status_code": None
        }


# =========================================================
# BALLAST — GET
# GET /draft-survey-extra/ballast/{draft_survey_id}
# =========================================================

def get_draft_survey_ballast_api(draft_survey_id: int):

    try:
        response = requests.get(
            f"{BASE_URL}/draft-survey-extra/ballast/{draft_survey_id}",
            timeout=30
        )
        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================
# BALLAST — UPDATE
# PUT /draft-survey-extra/ballast/{draft_survey_id}
# =========================================================
def update_draft_survey_ballast_api(draft_survey_id, payload: dict):
    """
    Actualiza Ballast para un Draft Survey.

    SOPORTA:
      - general_id (int)
      - draft_report_number (str)

    Retorna SIEMPRE:
      - success: bool
      - data: dict | None
      - error: str | None
      - status_code: int | None
    """

    # -----------------------------------------------------
    # VALIDACIONES
    # -----------------------------------------------------
    if draft_survey_id is None or str(draft_survey_id).strip() == "":
        return {
            "success": False,
            "data": None,
            "error": "draft_survey_id inválido",
            "status_code": None
        }

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        return {
            "success": False,
            "data": None,
            "error": "payload inválido (debe ser dict)",
            "status_code": None
        }

    identifier = str(draft_survey_id).strip()
    url = f"{BASE_URL}/draft-survey-extra/ballast/{identifier}"

    # -----------------------------------------------------
    # DEBUG
    # -----------------------------------------------------
    print("===================================")
    print("UPDATE BALLAST API")
    print("URL:", url)
    print("IDENTIFIER:", identifier)
    print("PAYLOAD:")
    print(payload)
    print("===================================")

    # -----------------------------------------------------
    # REQUEST
    # -----------------------------------------------------
    try:
        response = api_request(
            "PUT",
            url,
            json=payload,
            timeout=(10, 60)
        )

        status = response.status_code

        print("===================================")
        print("BALLAST UPDATE STATUS:", status)
        print("BALLAST UPDATE RESPONSE TEXT:")
        print(response.text)
        print("===================================")

        # Intentar parsear JSON
        try:
            data = response.json()
        except ValueError:
            data = None

        # HTTP error
        if not response.ok:
            backend_msg = None
            if isinstance(data, dict):
                backend_msg = (
                    data.get("detail")
                    or data.get("error")
                    or data.get("message")
                )

            return {
                "success": False,
                "data": data,
                "error": backend_msg or f"HTTP {status} al actualizar ballast",
                "status_code": status
            }

        # OK
        return {
            "success": True,
            "data": data,
            "error": None,
            "status_code": status
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "data": None,
            "error": "Timeout al actualizar ballast",
            "status_code": None
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "data": None,
            "error": "No se pudo conectar al backend",
            "status_code": None
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "data": None,
            "error": f"RequestException: {str(e)}",
            "status_code": None
        }

    except Exception as e:
        return {
            "success": False,
            "data": None,
            "error": f"Error inesperado: {str(e)}",
            "status_code": None
        }



# =========================================================
# WORD REPORT — CREATE
# POST /draft-survey-extra/word/{draft_survey_id}
# =========================================================

def create_draft_survey_word_api(draft_survey_id: int, payload: dict):

    try:
        payload = payload or {}

        def _clean_value(v):
            if v is None:
                return None
            if isinstance(v, str):
                vv = v.strip()
                if vv == "":
                    return None
                if vv.lower() in ("none", "null"):
                    return None
                return vv
            return v

        cleaned = {}
        for k, v in payload.items():
            if not isinstance(k, str):
                continue
            cleaned[k] = _clean_value(v)

        response = requests.post(
            f"{BASE_URL}/draft-survey-extra/word/{draft_survey_id}",
            json=cleaned,
            timeout=60
        )

        # -------------------------------------------------
        # 🔒 SI NO ES 2xx, DEVOLVER ERROR "REAL" (NO JSON ROTO)
        # -------------------------------------------------
        if not (200 <= response.status_code < 300):
            try:
                err_json = response.json()
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": err_json.get("detail", err_json)
                }
            except Exception:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }

        # 2xx
        try:
            return response.json()
        except Exception:
            return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}



# =========================================================
# DRAFT SURVEY — CASCADE FILTERS
# GET /draft-survey-filters/
# =========================================================

def get_draft_survey_filters_api(
    continent=None,
    country=None,
    year=None,
    month=None,
    port=None,
    client=None
):

    try:

        params = {}

        if continent:
            params["continent"] = continent

        if country:
            params["country"] = country

        if year:
            params["year"] = year

        if month:
            params["month"] = month

        if port:
            params["port"] = port

        if client:
            params["client"] = client

        response = requests.get(
            f"{BASE_URL}/draft-survey-filters/",
            params=params,
            timeout=60
        )

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}



# =========================================================
# get draft unified
# 
# =========================================================

def get_full_draft_survey_api(draft_report_number: str):

    try:
        import requests

        url = f"{BASE_URL}/draft-survey/unified/{draft_report_number}"

        response = requests.get(url)

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json().get("data")

    except Exception as e:
        print("GET FULL DRAFT ERROR:", e)
        return None


# =========================================================
# put draft unified
# 
# =========================================================

def update_full_draft_survey_api(draft_report_number: str, payload: dict):

    try:
        import requests

        url = f"{BASE_URL}/draft-survey/unified/{draft_report_number}"

        response = requests.put(url, json=payload)

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()

    except Exception as e:
        print("UPDATE FULL DRAFT ERROR:", e)
        raise

# =========================================================
# post draft unified
# 
# =========================================================

def create_full_draft_survey_api(payload: dict):

    try:
        import requests

        url = f"{BASE_URL}/draft-survey/unified"

        response = requests.post(url, json=payload)

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()

    except Exception as e:
        print("CREATE FULL DRAFT ERROR:", e)
        raise


# =========================================================
# UPDATE WORD REPORT
# =========================================================

def update_draft_survey_word_api(draft_survey_id: int, payload: dict):
    """
    PUT /word/{draft_survey_id}

    Actualiza completamente el Word Report asociado al draft_survey_id.
    Bloquea si está Approved.
    """

    import requests

    url = f"{API_BASE_URL}/word/{draft_survey_id}"

    try:
        response = requests.put(
            url,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.HTTPError as e:
        try:
            detail = response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        raise Exception(f"Error updating Word Report: {detail}")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Connection error updating Word Report: {str(e)}")











def get_draft_survey_headers_api():

    try:
        import requests

        url = f"{BASE_URL}/draft-survey-headers/"

        response = requests.get(url, timeout=60)

        if response.status_code != 200:
            return {
                "success": False,
                "message": response.text
            }

        return response.json()

    except Exception as e:
        return {
            "success": False,
            "message": f"GET HEADERS ERROR: {e}"
        }





def get_full_draft_survey_api(draft_report_number: str):

    try:
        import requests

        url = f"{BASE_URL}/draft-survey/unified/{draft_report_number}"

        response = requests.get(url, timeout=60)

        if response.status_code == 404:
            return {
                "success": False,
                "message": "Draft report not found"
            }

        if response.status_code != 200:
            return {
                "success": False,
                "message": response.text
            }

        return response.json()

    except Exception as e:
        return {
            "success": False,
            "message": f"GET UNIFIED ERROR: {e}"
        }




# =========================================================
# GENERATE WORD PDF (GET BY REPORT NUMBER - ERP VERSION)
# =========================================================
def generate_draft_survey_word_pdf_api(draft_report_number: str):

    # -----------------------------------------------------
    # 1️⃣ VALIDACIÓN
    # -----------------------------------------------------
    draft_report_number = str(draft_report_number or "").strip()

    if not draft_report_number:
        return {
            "success": False,
            "message": "draft_report_number is required"
        }

    try:
        url = f"{BASE_URL}/draft-survey-word/generate/{draft_report_number}"

        response = requests.get(
            url,
            timeout=180  # LibreOffice puede tardar
        )

        # -------------------------------------------------
        # 2️⃣ HTTP ERROR
        # -------------------------------------------------
        if response.status_code != 200:

            try:
                error_detail = response.json().get("detail")
            except Exception:
                error_detail = response.text

            return {
                "success": False,
                "message": error_detail or "Error generating Word PDF"
            }

        # -------------------------------------------------
        # 3️⃣ VALIDAR CONTENIDO
        # -------------------------------------------------
        if not response.content:
            return {
                "success": False,
                "message": "Backend returned empty PDF content"
            }

        return {
            "success": True,
            "content": response.content
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "message": "Backend timeout during PDF generation"
        }

    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "message": "Cannot connect to backend. Is FastAPI running?"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}"
        }



# =========================================================
# DRAFT SURVEY — GENERATE EXCEL PDF
# GET /draft-survey-excel/generate-pdf/{draft_report_number}
# =========================================================

def generate_draft_survey_excel_pdf_api(draft_report_number: str):

    draft_report_number = str(draft_report_number or "").strip()

    if not draft_report_number:
        return {
            "success": False,
            "error": "draft_report_number is required"
        }

    try:

        response = requests.get(
            f"{BASE_URL}/draft-survey-excel/generate-pdf/{draft_report_number}",
            timeout=120
        )

        # ---------------------------------------
        # ERROR RESPONSES
        # ---------------------------------------
        if response.status_code != 200:

            try:
                detail = response.json().get("detail")
            except Exception:
                detail = response.text

            return {
                "success": False,
                "error": detail or "Server error"
            }

        # ---------------------------------------
        # SUCCESS
        # ---------------------------------------
        return {
            "success": True,
            "content": response.content,  # PDF bytes
            "filename": f"{draft_report_number}_DRAFT_SURVEY.pdf"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }



def generate_draft_survey_final_pdf_api(draft_report_number: str):

    draft_report_number = str(draft_report_number or "").strip()

    if not draft_report_number:
        return {"success": False, "error": "draft_report_number is required"}

    try:
        r = requests.get(
            f"{BASE_URL}/draft-survey-final/generate/{draft_report_number}",
            timeout=180
        )

        if r.status_code != 200:
            try:
                detail = r.json().get("detail")
            except Exception:
                detail = r.text

            return {"success": False, "error": detail or "Server error"}

        return {
            "success": True,
            "content": r.content,
            "filename": f"{draft_report_number}_FINAL.pdf"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}




def generate_draft_survey_presentation_pdf_api(draft_report_number):

    import requests

    try:
        response = requests.get(
            f"{BASE_URL}/draft-survey-word/presentation/{draft_report_number}",
            timeout=120,
            stream=True
        )

        return response

    except Exception as e:
        return {"success": False, "error": str(e)}



def generate_draft_survey_unified_pdf_api(draft_report_number):

    import requests

    try:
        response = requests.get(
            f"{BASE_URL}/draft-survey-final/unified/{draft_report_number}",
            timeout=180,
            stream=True
        )

        return response

    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================
# INTERNAL: SAFE JSON
# =========================================================
def _safe_json_response(response):
    try:
        return response.json()
    except Exception:
        return {
            "success": False,
            "error": f"HTTP {response.status_code}",
            "detail": response.text
        }


def _clean_bunker_numeric_payload(payload: dict) -> dict:
    cleaned = dict(payload or {})

    fixed_numeric_fields = {
        "gross_tonnage",
        "bunker_delivery_declared",
        "rob_diff",
        "plus_consumption",
        "generator_until_aps",
        "cons_dept",
        "me_to_sea_buoy",
        "draft",
        "draft_fwd",
        "draft_aft",
        "trim",
        "list",
        "log_eosp_vlsfo", "log_eosp_hfso", "log_eosp_mdo", "log_eosp_lsmgo",
        "log_pob_vlsfo", "log_pob_hfso", "log_pob_mdo", "log_pob_lsmgo",
        "log_fwe_vlsfo", "log_fwe_hfso", "log_fwe_mdo", "log_fwe_lsmgo",
        "log_bunker_vlsfo", "log_bunker_hfso", "log_bunker_mdo", "log_bunker_lsmgo",
        "log_at_survey_vlsfo", "log_at_survey_hfso", "log_at_survey_mdo", "log_at_survey_lsmgo",
        "cons_sea_loaded_vlsfo", "cons_sea_loaded_hfso", "cons_sea_loaded_mdo", "cons_sea_loaded_lsmgo",
        "cons_sea_ballast_vlsfo", "cons_sea_ballast_hfso", "cons_sea_ballast_mdo", "cons_sea_ballast_lsmgo",
        "cons_port_ship_gear_vlsfo", "cons_port_ship_gear_hfso", "cons_port_ship_gear_mdo", "cons_port_ship_gear_lsmgo",
        "cons_port_shore_gear_vlsfo", "cons_port_shore_gear_hfso", "cons_port_shore_gear_mdo", "cons_port_shore_gear_lsmgo",
    }
    numeric_suffixes = (
        "_volume_m3",
        "_temp_c",
        "_temp_f",
        "_density_15c",
        "_weight_mt",
    )

    def normalize(value):
        if value is None:
            return None
        text = str(value).strip().replace(" ", "")
        if not text:
            return None
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            float(text)
            return text
        except Exception:
            return None

    for key in list(cleaned.keys()):
        is_tank_numeric = (
            key.startswith(("vlsfo_tank_", "mgo_tank_"))
            and key.endswith(numeric_suffixes)
        )
        is_figure_numeric = (
            key.startswith("bunker_figure_")
            and key.endswith(("_ifo", "_vlsfo", "_lsmgo"))
        )
        if key in fixed_numeric_fields or is_tank_numeric or is_figure_numeric:
            cleaned[key] = normalize(cleaned.get(key))

    return cleaned


# =========================================================
# CREATE
# POST /vessel-bunker-reports/
# =========================================================
def create_vessel_bunker_report_api(payload: dict):

    try:
        payload = _clean_bunker_numeric_payload(payload)
        response = requests.post(
            f"{BASE_URL}/vessel-bunker-reports/",
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================
# UPDATE (FULL PUT)
# PUT /vessel-bunker-reports/{id}
# =========================================================
def update_vessel_bunker_report_api(report_id: int, payload: dict):

    try:
        payload = _clean_bunker_numeric_payload(payload)
        response = requests.put(
            f"{BASE_URL}/vessel-bunker-reports/{int(report_id)}",
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================
# GET BY ID
# GET /vessel-bunker-reports/{id}
# =========================================================
def get_vessel_bunker_report_api(report_id: int):

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-bunker-reports/{int(report_id)}",
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================
# GET ALL (PAGINADO + BUSQUEDA)
# GET /vessel-bunker-reports/?limit=..&offset=..&q=..
# =========================================================
def get_all_vessel_bunker_reports_api(limit: int = 200, offset: int = 0, q: str = None):

    try:
        params = {
            "limit": int(limit or 200),
            "offset": int(offset or 0),
        }
        if q is not None and str(q).strip() != "":
            params["q"] = str(q).strip()

        response = requests.get(
            f"{BASE_URL}/vessel-bunker-reports/",
            params=params,
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {"success": False, "error": str(e)}




# =========================================================
# VESSEL BUNKER — GENERATE EXCEL
# =========================================================
def generate_vessel_bunker_excel_api(report_id: int):

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-bunker-excel/generate/{report_id}",
            timeout=120
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return {
            "success": True,
            "content": response.content
        }

    except Exception as e:
        return {"success": False, "error": str(e)}



# =========================================================
# VESSEL BUNKER — GENERATE FINAL PDF (3 SHEETS MERGED)
# GET /vessel-bunker-excel/generate-pdf/{report_id}
# =========================================================

def generate_vessel_bunker_pdf_api(report_id: int):

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-bunker-excel/generate-pdf/{report_id}",
            timeout=180  # Excel + LibreOffice pueden tardar
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return {
            "success": True,
            "content": response.content  # 🔥 PDF binario
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }



# =========================================================
# VESSEL BUNKER — PRESENTATION PDF
# GET /vessel-bunker-reports/presentation/{report_id}
# =========================================================

def get_vessel_bunker_presentation_pdf(report_id: int):

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-bunker-reports/presentation/{int(report_id)}",
            timeout=120,
            stream=True
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return {
            "success": True,
            "content": response.content
        }

    except Exception as e:
        return {"success": False, "error": str(e)}



# =========================================================
# PREVIEW EXCEL (NO DB)
# POST /vessel-bunker-preview/excel
# =========================================================
def preview_vessel_bunker_excel_api(payload: dict):

    try:
        response = requests.post(
            f"{BASE_URL}/vessel-bunker-preview/excel",
            json=payload,
            timeout=120
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return {
            "success": True,
            "content": response.content
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# CARGO CONDITION — AI IMPROVE
# POST /reports/ai/improve/cargo-condition
# =========================================================

def improve_cargo_condition_ai_api(
    section: str,
    language: str,
    vessel: str = None,
    port: str = None,
    text: str = None,
    items: list = None
):
    """
    Llama al endpoint AI para mejorar Cargo Condition.

    Soporta:
    - text (str)
    - items (list[str])
    """

    try:
        # -----------------------------------------------------
        # VALIDACIONES BÁSICAS
        # -----------------------------------------------------
        if not section:
            return {
                "success": False,
                "error": "Section is required"
            }

        language = (language or "ES").upper()
        if language not in ("ES", "EN"):
            language = "ES"

        # -----------------------------------------------------
        # PAYLOAD BASE
        # -----------------------------------------------------
        payload = {
            "section": section,
            "language": language,
            "vessel": vessel,
            "port": port
        }

        # -----------------------------------------------------
        # MULTI BULLET MODE
        # -----------------------------------------------------
        if isinstance(items, list) and items:
            payload["items"] = items

        # -----------------------------------------------------
        # SINGLE TEXT MODE
        # -----------------------------------------------------
        elif text and text.strip():
            payload["text"] = text.strip()

        else:
            return {
                "success": False,
                "error": "Text or items required"
            }

        # -----------------------------------------------------
        # REQUEST
        # -----------------------------------------------------
        response = requests.post(
            f"{BASE_URL}/reports/ai/improve/cargo-condition",
            json=payload,
            timeout=90
        )

        # -----------------------------------------------------
        # HTTP ERROR HANDLING
        # -----------------------------------------------------
        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        data = response.json()

        # -----------------------------------------------------
        # NORMALIZACIÓN DEFENSIVA
        # -----------------------------------------------------
        return {
            "success": data.get("success", False),
            "language": data.get("language"),
            "text": data.get("text"),
            "items": data.get("items")
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }



# =========================================================
# VESSEL CARGO CONDITION SURVEYS
# =========================================================


# ---------------------------------------------------------
# CREATE
# POST /vessel-cargo-condition-surveys/
# ---------------------------------------------------------
def create_vessel_cargo_condition_api(payload: dict):

    try:
        response = requests.post(
            f"{BASE_URL}/vessel-cargo-condition-surveys/",
            json=(payload or {}),
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------
# GET ALL
# GET /vessel-cargo-condition-surveys/
# ---------------------------------------------------------
def get_all_vessel_cargo_condition_api():

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-cargo-condition-surveys/",
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------
# GET BY ID
# GET /vessel-cargo-condition-surveys/{id}
# ---------------------------------------------------------
def get_vessel_cargo_condition_by_id_api(record_id: int):

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-cargo-condition-surveys/{int(record_id)}",
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------
# UPDATE (FULL PUT)
# PUT /vessel-cargo-condition-surveys/{id}
# ---------------------------------------------------------
def update_vessel_cargo_condition_api(record_id: int, payload: dict):

    try:
        response = requests.put(
            f"{BASE_URL}/vessel-cargo-condition-surveys/{int(record_id)}",
            json=(payload or {}),
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return response.json()

    except Exception as e:
        return {"success": False, "error": str(e)}



# =========================================================
# WORD — GENERATE CARGO CONDITION
# GET /vessel-cargo-condition-surveys/word/{id}
# =========================================================
def generate_vessel_cargo_condition_word_api(record_id: int, save_path: str):

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-cargo-condition-surveys/word/{int(record_id)}",
            timeout=120,
            stream=True
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        # Guardar archivo en disco
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return {
            "success": True,
            "path": save_path
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# =========================================================
# PRESENTATION PDF — DOWNLOAD
# GET /vessel-cargo-condition-surveys/presentation/{id}
# =========================================================

def download_vessel_cargo_condition_presentation_pdf(record_id: int):

    try:
        response = requests.get(
            f"{BASE_URL}/vessel-cargo-condition-surveys/presentation/{int(record_id)}",
            timeout=120,
            stream=True
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return {
            "success": True,
            "content": response.content
        }

    except Exception as e:
        return {"success": False, "error": str(e)}



# ============================================================
# SAFE JSON RESPONSE
# ============================================================

def _safe_json_response(response):
    try:
        return response.json()
    except Exception:
        return {
            "success": False,
            "error": "Invalid JSON response",
            "detail": response.text
        }


# ============================================================
# CREATE CRANE INSPECTION
# POST /vessel-crane-inspection
# ============================================================

def create_crane_inspection_api(payload: dict):

    try:

        response = requests.post(
            f"{BASE_URL}/vessel-crane-inspection",
            json=(payload or {}),
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# UPDATE CRANE INSPECTION
# PUT /vessel-crane-inspection/{id}
# ============================================================

def update_crane_inspection_api(report_id: int, payload: dict):

    try:

        response = requests.put(
            f"{BASE_URL}/vessel-crane-inspection/{int(report_id)}",
            json=(payload or {}),
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# APPROVE CRANE INSPECTION
# PUT /vessel-crane-inspection/{id}
# ============================================================

def approve_crane_inspection_api(report_id: int):

    try:

        payload = {
            "approve": True
        }

        response = requests.put(
            f"{BASE_URL}/vessel-crane-inspection/{int(report_id)}",
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# GET LIST
# GET /vessel-crane-inspection
# ============================================================

def get_crane_inspections_api():

    try:

        response = requests.get(
            f"{BASE_URL}/vessel-crane-inspection",
            timeout=60
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        return _safe_json_response(response)

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# ============================================================
# GET ONE
# GET /vessel-crane-inspection/{id}
# ============================================================

def get_crane_inspection_api(report_id: int):

    try:

        if not report_id:
            return {
                "success": False,
                "error": "Invalid report ID"
            }

        url = f"{BASE_URL}/vessel-crane-inspection/{int(report_id)}"

        response = requests.get(
            url,
            timeout=60
        )

        # ----------------------------------------------------
        # HTTP ERROR
        # ----------------------------------------------------

        if response.status_code != 200:

            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "detail": response.text
            }

        # ----------------------------------------------------
        # SAFE JSON PARSE
        # ----------------------------------------------------

        try:

            data = response.json()

        except Exception:

            return {
                "success": False,
                "error": "Invalid JSON response",
                "detail": response.text
            }

        # ----------------------------------------------------
        # NORMALIZE RESPONSE
        # ----------------------------------------------------

        if not isinstance(data, dict):

            return {
                "success": False,
                "error": "Invalid API format",
                "detail": data
            }

        # si backend ya trae success
        if "success" in data:
            return data

        # fallback (por si backend devuelve solo objeto)
        return {
            "success": True,
            "data": data
        }

    except requests.exceptions.Timeout:

        return {
            "success": False,
            "error": "Request timeout while loading crane inspection report"
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# GENERATE CRANE INSPECTION WORD
# =========================================================

def generate_crane_inspection_word_api(record_id):

    try:

        url = f"{BASE_URL}/vessel-crane-inspection-reports/{record_id}/generate-word"

        r = requests.get(
            url,
            headers=_headers(),
            timeout=120
        )

        if r.status_code != 200:

            return {
                "success": False,
                "error": r.text
            }

        return {
            "success": True,
            "file_bytes": r.content
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# CRANE INSPECTION PRESENTATION PDF
# =========================================================

def generate_crane_inspection_presentation_api(record_id: int):

    try:

        url = f"{BASE_URL}/vessel-crane-inspection-reports/{record_id}/presentation"

        response = requests.get(
            url,
            headers=_headers(),
            stream=True
        )

        if response.status_code != 200:

            raise Exception(response.text)

        temp_dir = tempfile.mkdtemp()

        pdf_path = os.path.join(
            temp_dir,
            f"Crane_Inspection_Presentation_{record_id}.pdf"
        )

        with open(pdf_path, "wb") as f:

            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return pdf_path

    except Exception as e:

        raise RuntimeError(str(e))



# =========================================================
# AI CRANE INSPECTION
# =========================================================

def improve_crane_inspection_ai_api(section, language, vessel, port, items):

    try:

        url = f"{BASE_URL}/reports/ai/improve/crane-inspection"

        payload = {
            "section": section,
            "language": language,
            "vessel": vessel,
            "port": port,
            "items": items
        }

        response = requests.post(
            url,
            headers=_headers(),
            json=payload,
            timeout=60
        )

        # -------------------------------------------------
        # HTTP ERROR
        # -------------------------------------------------

        if response.status_code != 200:

            try:
                error = response.json()
                msg = error.get("detail") or error
            except Exception:
                msg = response.text

            return {
                "success": False,
                "error": msg
            }

        # -------------------------------------------------
        # PARSE RESPONSE
        # -------------------------------------------------

        data = response.json()

        if not isinstance(data, dict):

            return {
                "success": False,
                "error": "Invalid AI response"
            }

        return {
            "success": bool(data.get("success")),
            "items": data.get("items", []),
            "error": data.get("error")
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }



# =========================================================
# CREATE VESSEL CONDITION SURVEY
# =========================================================

def create_vessel_condition_survey_api(payload):

    r = requests.post(
        f"{BASE_URL}/vessel-condition-surveys",
        json=payload,
        timeout=TIMEOUT
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# UPDATE VESSEL CONDITION SURVEY
# =========================================================

def update_vessel_condition_survey_api(record_id: int, payload: dict):

    r = requests.put(
        f"{BASE_URL}/vessel-condition-surveys/id/{int(record_id)}",
        json=payload,
        timeout=TIMEOUT
    )

    r.raise_for_status()
    return r.json()


# =========================================================
# GET VESSEL CONDITION SURVEY
# =========================================================

def get_vessel_condition_survey_api(report_number):

    r = requests.get(
        f"{BASE_URL}/vessel-condition-surveys/{report_number}",
        timeout=TIMEOUT
    )

    r.raise_for_status()

    return r.json()


def get_vessel_condition_survey_by_id_api(record_id: int):
    r = requests.get(
        f"{BASE_URL}/vessel-condition-surveys/id/{record_id}",
        timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json()


# =========================================================
# GET ALL VESSEL CONDITION SURVEYS
# =========================================================

def get_all_vessel_condition_surveys_api():

    r = requests.get(
        f"{BASE_URL}/vessel-condition-surveys",
        timeout=TIMEOUT
    )

    r.raise_for_status()

    return r.json()



# =========================================================
# VESSEL CONDITION SURVEY AI
# =========================================================
def improve_vessel_condition_text_api(payload):

    r = requests.post(
        f"{BASE_URL}/reports/ai/improve/vessel-condition",
        json=payload,
        timeout=TIMEOUT
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# DOWNLOAD VESSEL CONDITION SURVEY WORD
# =========================================================

def download_vessel_condition_survey_word(report_id):

    url = f"{BASE_URL}/vessel-condition-surveys/word/{report_id}"

    response = requests.get(
        url,
        timeout=TIMEOUT
    )

    if response.status_code != 200:
        raise Exception(
            f"Error generating Word report: {response.text}"
        )

    filename = f"vessel_condition_survey_{report_id}.docx"

    temp_path = os.path.join(
        tempfile.gettempdir(),
        filename
    )

    with open(temp_path, "wb") as f:
        f.write(response.content)

    return temp_path


# =========================================================
# PORT CAPTANCY POST
# =========================================================

def create_port_captancy_report_api(payload: dict):

    url = f"{BASE_URL}/port-captancy-reports"

    response = requests.post(
        url,
        json=payload,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# PORT CAPTANCY PUT
# =========================================================

def update_port_captancy_report_api(report_number: str, payload: dict):

    url = f"{BASE_URL}/port-captancy-reports/{report_number}"

    response = requests.put(
        url,
        json=payload,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return response.json()


# =========================================================
# PORT CAPTANCY GET
# =========================================================

def get_port_captancy_report_api(report_number: str):

    url = f"{BASE_URL}/port-captancy-reports/{report_number}"

    response = requests.get(
        url,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    data = response.json()

    if isinstance(data, dict) and "data" in data:
        return data["data"]

    return data

# =========================================================
# PORT CAPTANCY GET ALL
# =========================================================

def get_all_port_captancy_reports_api():

    url = f"{BASE_URL}/port-captancy-reports"

    response = requests.get(
        url,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return response.json()



# =========================================================
# PORT CAPTANCY AI
# =========================================================
def improve_port_captancy_api(payload):

    url = f"{BASE_URL}/reports/ai/improve/port-captancy"

    response = requests.post(
        url,
        json=payload,
        timeout=TIMEOUT
    )

    response.raise_for_status()

    return response.json()



# =========================================================
# VESSEL CONDITION SURVEY
# GENERATE PRESENTATION PDF
# =========================================================

def generate_vessel_condition_presentation_api(record_id: int):

    try:

        import requests
        import os
        import tempfile

        url = f"{BASE_URL}/vessel-condition-surveys/presentation/{record_id}"

        response = requests.get(url, stream=True)

        if response.status_code != 200:
            raise Exception(
                f"API Error {response.status_code}: {response.text}"
            )

        temp_dir = tempfile.gettempdir()

        file_path = os.path.join(
            temp_dir,
            f"vessel_condition_presentation_{record_id}.pdf"
        )

        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return file_path

    except Exception as e:

        raise Exception(
            f"No se pudo generar la presentación:\n{str(e)}"
        )


# =========================================================
# VESSEL CONDITION SURVEY
# GET BY ID (USADO POR POPUPS)
# =========================================================

def get_vessel_condition_survey_by_id_api(record_id: int):

    try:

        import requests

        url = f"{BASE_URL}/vessel-condition-surveys/id/{record_id}"

        r = requests.get(url, timeout=TIMEOUT)

        if r.status_code != 200:
            return {
                "success": False,
                "error": r.text
            }

        return r.json()

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_vessel_condition_survey_by_id_wrapped_api(record_id):

    import requests

    url = f"{BASE_URL}/vessel-condition-surveys/by-id/{record_id}"

    r = requests.get(url)

    if r.status_code != 200:
        return {
            "success": False,
            "error": r.text
        }

    return r.json()




# =========================================================
# GENERATE PORT CAPTANCY WORD
# =========================================================

def generate_port_captancy_word_api(record_id: int):

    import os
    import tempfile
    import requests

    url = f"{BASE_URL}/port-captancy-reports/{record_id}/word"

    r = requests.get(url)

    if r.status_code != 200:
        raise Exception(r.text)

    temp_dir = tempfile.gettempdir()

    file_path = os.path.join(
        temp_dir,
        f"port_captancy_{record_id}.docx"
    )

    with open(file_path, "wb") as f:
        f.write(r.content)

    return file_path


# =========================================================
# GENERATE PORT CAPTANCY PRESENTATION
# =========================================================

def generate_port_captancy_presentation_api(record_id: int):

    import os
    import tempfile
    import requests

    url = f"{BASE_URL}/port-captancy-reports/presentation/{record_id}"

    r = requests.get(url)

    if r.status_code != 200:
        raise Exception(r.text)

    temp_dir = tempfile.gettempdir()

    file_path = os.path.join(
        temp_dir,
        f"port_captancy_presentation_{record_id}.pdf"
    )

    with open(file_path, "wb") as f:
        f.write(r.content)

    return file_path


# =========================================================
# GET PORT CAPTANCY BY ID
# =========================================================

def get_port_captancy_report_by_id_api(record_id: int):

    import requests

    url = f"{BASE_URL}/port-captancy-reports/id/{record_id}"

    r = requests.get(url)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# =========================================================
# WEIGHT CERTIFICATES — CREATE
# =========================================================

def create_weight_certificate_api(payload: dict):

    url = f"{BASE_URL}/weight-certificates"

    r = requests.post(
        url,
        json=payload,
        timeout=60
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# WEIGHT CERTIFICATES — UPDATE
# =========================================================

def update_weight_certificate_api(record_id: int, payload: dict):

    url = f"{BASE_URL}/weight-certificates/{record_id}"

    r = requests.put(
        url,
        json=payload,
        timeout=60
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# WEIGHT CERTIFICATES — GET ALL
# =========================================================

def get_weight_certificates_api():

    url = f"{BASE_URL}/weight-certificates"

    r = requests.get(
        url,
        timeout=60
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# WEIGHT CERTIFICATES — GET BY ID
# =========================================================

def get_weight_certificate_api(record_id: int):

    url = f"{BASE_URL}/weight-certificates/{record_id}"

    r = requests.get(
        url,
        timeout=60
    )

    r.raise_for_status()

    return r.json()


# =========================================================
# WEIGHT CERTIFICATE — GENERATE WORD
# =========================================================

def generate_weight_certificate_word_api(record_id):

    url = f"{BASE_URL}/weight-certificates/{record_id}/word"

    r = requests.get(
        url,
        timeout=120
    )

    r.raise_for_status()

    return r.content



# =========================================================
# WEIGHT CERTIFICATE — GENERATE PDF
# =========================================================

def generate_weight_certificate_pdf_api(record_id):

    url = f"{BASE_URL}/weight-certificates/{record_id}/pdf"

    r = requests.get(
        url,
        timeout=120
    )

    r.raise_for_status()

    return r.content


# =========================================================
# VESSEL HOLDS INSPECTION CERTIFICATES
# =========================================================

def create_vessel_holds_certificate_api(payload):

    r = requests.post(
        f"{BASE_URL}/vessel-holds-inspection-certificates",
        json=payload
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# =========================================================

def update_vessel_holds_certificate_api(record_id, payload):

    r = requests.put(
        f"{BASE_URL}/vessel-holds-inspection-certificates/{record_id}",
        json=payload
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# =========================================================

def get_vessel_holds_certificates_api():

    r = requests.get(
        f"{BASE_URL}/vessel-holds-inspection-certificates"
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# =========================================================

def get_vessel_holds_certificate_api(record_id):

    r = requests.get(
        f"{BASE_URL}/vessel-holds-inspection-certificates/{record_id}"
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# =========================================================
# GENERATE HOLDS EXCEL
# =========================================================

def generate_holds_excel_api(record_id):

    import requests

    url = f"{BASE_URL}/vessel-holds-inspection-certificates/{record_id}/excel"

    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(response.text)

    return response.content


# =========================================================
# GENERATE HOLDS INSPECTION CERTIFICATE PDF
# =========================================================

def generate_vessel_holds_pdf_api(record_id):

    url = f"{BASE_URL}/vessel-holds-inspection-certificates/{record_id}/pdf"

    response = requests.get(
        url,
        timeout=TIMEOUT
    )

    if response.status_code != 200:
        raise Exception(response.text)

    return response.content


# =========================================================
# SAMPLING CERTIFICATES
# =========================================================

def create_sampling_certificate_api(payload):

    url = f"{BASE_URL}/sampling-certificates"

    r = requests.post(url, json=payload, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


def update_sampling_certificate_api(record_id, payload):

    url = f"{BASE_URL}/sampling-certificates/{record_id}"

    r = requests.put(url, json=payload, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


def get_sampling_certificates_api():

    url = f"{BASE_URL}/sampling-certificates"

    r = requests.get(url, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


def get_sampling_certificate_api(record_id):

    url = f"{BASE_URL}/sampling-certificates/{record_id}"

    r = requests.get(url, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# =========================================================
# GENERATE EXCEL
# =========================================================

def generate_sampling_excel_api(record_id):

    url = f"{BASE_URL}/sampling-certificates/{record_id}/excel"

    r = requests.get(url, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.content


# =========================================================
# GENERATE PDF
# =========================================================

def generate_sampling_pdf_api(record_id):

    url = f"{BASE_URL}/sampling-certificates/{record_id}/pdf"

    r = requests.get(url, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.content



# =========================================================
# SEALING CERTIFICATES
# =========================================================

def get_sealing_certificates_api():
    """
    GET ALL sealing certificates
    Siempre devuelve LIST
    """

    url = f"{BASE_URL}/sealing-certificates"

    try:

        response = requests.get(
            url,
            timeout=TIMEOUT
        )

    except requests.RequestException as e:
        raise Exception(f"Connection error: {str(e)}")

    if response.status_code != 200:
        raise Exception(response.text)

    try:
        data = response.json()
    except Exception:
        raise Exception("Invalid JSON response from API")

    if data is None:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return [data]

    return []


# =========================================================

def get_sealing_certificate_api(record_id: int):
    """
    GET sealing certificate by id
    Siempre devuelve DICT
    """

    url = f"{BASE_URL}/sealing-certificates/{record_id}"

    try:

        response = requests.get(
            url,
            timeout=TIMEOUT
        )

    except requests.RequestException as e:
        raise Exception(f"Connection error: {str(e)}")

    if response.status_code != 200:
        raise Exception(response.text)

    try:
        data = response.json()
    except Exception:
        raise Exception("Invalid JSON response from API")

    if data is None:
        return {}

    if isinstance(data, dict):
        return data

    if isinstance(data, list) and len(data) > 0:

        first = data[0]

        if isinstance(first, dict):
            return first

    raise Exception(f"Unexpected API response: {data}")


# =========================================================

def create_sealing_certificate_api(payload: dict):
    """
    POST create sealing certificate
    Siempre devuelve DICT con id
    """

    url = f"{BASE_URL}/sealing-certificates"

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=TIMEOUT
        )

    except requests.RequestException as e:
        raise Exception(f"Connection error: {str(e)}")

    if response.status_code not in (200, 201):
        raise Exception(response.text)

    try:
        data = response.json()
    except Exception:
        raise Exception("Invalid JSON response from API")

    # -------------------------------
    # RESPUESTA NORMAL
    # -------------------------------
    if isinstance(data, dict):
        return data

    # -------------------------------
    # LISTA
    # -------------------------------
    if isinstance(data, list):

        if len(data) == 0:
            return {}

        first = data[0]

        if isinstance(first, dict):
            return first

        if isinstance(first, int):
            return {"id": first}

    # -------------------------------
    # DESCONOCIDO
    # -------------------------------
    raise Exception(f"Unexpected API response: {data}")


# =========================================================

def update_sealing_certificate_api(record_id: int, payload: dict):
    """
    PUT update sealing certificate
    Siempre devuelve DICT
    """

    url = f"{BASE_URL}/sealing-certificates/{record_id}"

    try:

        response = requests.put(
            url,
            json=payload,
            timeout=TIMEOUT
        )

    except requests.RequestException as e:
        raise Exception(f"Connection error: {str(e)}")

    if response.status_code not in (200, 201):
        raise Exception(response.text)

    try:
        data = response.json()
    except Exception:
        raise Exception("Invalid JSON response from API")

    if isinstance(data, dict):
        return data

    if isinstance(data, list) and len(data) > 0:

        first = data[0]

        if isinstance(first, dict):
            return first

    return {"success": True}


# ============================================================
# GENERATE SEALING CERTIFICATE EXCEL
# ============================================================

def generate_sealing_excel_api(record_id: int):

    url = f"{BASE_URL}/sealing-certificates/{record_id}/excel"

    response = requests.get(
        url,
        timeout=TIMEOUT
    )

    if response.status_code != 200:
        raise Exception(response.text)

    return response.content




# ============================================================
# GENERATE SEALING CERTIFICATE PDF
# ============================================================

def generate_sealing_pdf_api(record_id: int):

    url = f"{BASE_URL}/sealing-certificates/{record_id}/pdf"

    response = requests.get(
        url,
        timeout=TIMEOUT
    )

    if response.status_code != 200:
        raise Exception(response.text)

    return response.content




# ============================================================
# CREATE LASHING CERTIFICATE
# ============================================================

def create_lashing_certificate_api(payload: dict):

    url = f"{BASE_URL}/lashing-certificates/"

    r = requests.post(
        url,
        json=payload,
        timeout=TIMEOUT
    )

    if r.status_code not in (200, 201):
        raise Exception(r.text)

    try:
        return r.json()
    except Exception:
        raise Exception("Invalid API response")


# ============================================================
# GENERATE LASHING CERTIFICATE WORD
# ============================================================

def generate_lashing_certificate_word_api(record_id):

    url = f"{BASE_URL}/lashing-certificates/{record_id}/word"

    r = requests.get(
        url,
        timeout=TIMEOUT
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.content


# ============================================================
# GENERATE LASHING CERTIFICATE PDF
# ============================================================

def generate_lashing_certificate_pdf_api(record_id):

    url = f"{BASE_URL}/lashing-certificates/{record_id}/pdf"

    r = requests.get(
        url,
        timeout=TIMEOUT
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.content



# ============================================================
# LASHING CERTIFICATES
# ============================================================

def get_lashing_certificates_api():

    url = f"{BASE_URL}/lashing-certificates"

    r = requests.get(url, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# ============================================================

def get_lashing_certificate_api(record_id):

    url = f"{BASE_URL}/lashing-certificates/{record_id}"

    r = requests.get(url, timeout=TIMEOUT)

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# ============================================================

def create_lashing_certificate_api(payload: dict):

    url = f"{BASE_URL}/lashing-certificates/"

    r = requests.post(
        url,
        json=payload,
        timeout=TIMEOUT
    )

    if r.status_code not in (200, 201):
        raise Exception(r.text)

    return r.json()


# ============================================================

def update_lashing_certificate_api(record_id, payload: dict):

    url = f"{BASE_URL}/lashing-certificates/{record_id}"

    r = requests.put(
        url,
        json=payload,
        timeout=TIMEOUT
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.json()


# ============================================================
# GENERATE WORD
# ============================================================

def generate_lashing_certificate_word_api(record_id):

    url = f"{BASE_URL}/lashing-certificates/{record_id}/word"

    r = requests.get(
        url,
        timeout=TIMEOUT
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.content


# ============================================================
# GENERATE PDF
# ============================================================

def generate_lashing_certificate_pdf_api(record_id):

    url = f"{BASE_URL}/lashing-certificates/{record_id}/pdf"

    r = requests.get(
        url,
        timeout=TIMEOUT
    )

    if r.status_code != 200:
        raise Exception(r.text)

    return r.content


# =========================================================
# DASHBOARD SERVICIOS
# =========================================================

def get_dashboard_servicios_api(
    anio=None,
    pais=None,
    puerto=None,
    cliente=None
):

    import requests

    url = f"{BASE_URL}/dashboard/servicios"

    params = {}

    if anio:
        params["anio"] = anio

    if pais:
        params["pais"] = pais

    if puerto:
        params["puerto"] = puerto

    if cliente:
        params["cliente"] = cliente

    response = requests.get(
        url,
        params=params,
        timeout=TIMEOUT
    )

    if response.status_code != 200:
        raise Exception(response.text)

    return response.json()


# ============================================================
# DASHBOARD FINANZAS
# ============================================================

def get_dashboard_finanzas_resumen_api(
    anio: Optional[int] = None,
    cliente: Optional[str] = None
):

    url = f"{BASE_URL}/dashboard-finanzas/resumen"

    params = {}

    if anio:
        params["anio"] = anio

    if cliente:
        params["cliente"] = cliente

    resp = api_request(
        "GET",
        url,
        params=params
    )

    return resp.json()



# ============================================================
# DASHBOARD COMERCIAL
# ============================================================

def get_dashboard_comercial_filtros_api(
    anio: Optional[int] = None,
    pais: Optional[str] = None,
    puerto: Optional[str] = None,
    cliente: Optional[str] = None,
    operacion: Optional[str] = None
):

    url = f"{BASE_URL}/dashboard-comercial/filtros"

    params = {}

    if anio:
        params["anio"] = anio

    if pais:
        params["pais"] = pais

    if puerto:
        params["puerto"] = puerto

    if cliente:
        params["cliente"] = cliente

    if operacion:
        params["operacion"] = operacion

    resp = api_request(
        "GET",
        url,
        params=params
    )

    return resp.json()


def get_dashboard_comercial_resumen_api(
    anio: Optional[int] = None,
    pais: Optional[str] = None,
    puerto: Optional[str] = None,
    cliente: Optional[str] = None,
    operacion: Optional[str] = None
):

    url = f"{BASE_URL}/dashboard-comercial/resumen"

    params = {}

    if anio:
        params["anio"] = anio

    if pais:
        params["pais"] = pais

    if puerto:
        params["puerto"] = puerto

    if cliente:
        params["cliente"] = cliente

    if operacion:
        params["operacion"] = operacion

    resp = api_request(
        "GET",
        url,
        params=params
    )

    return resp.json()


# ============================================================
# DASHBOARD INFORMES
# ============================================================

def get_dashboard_informes_filtros_api(
    anio=None,
    pais=None,
    puerto=None,
    cliente=None,
    operacion=None,
    tipo_informe=None
):

    url = f"{BASE_URL}/dashboard-informes/filtros"

    params = {}

    if anio:
        params["anio"] = anio
    if pais:
        params["pais"] = pais
    if puerto:
        params["puerto"] = puerto
    if cliente:
        params["cliente"] = cliente
    if operacion:
        params["operacion"] = operacion
    if tipo_informe:
        params["tipo_informe"] = tipo_informe

    resp = api_request("GET", url, params=params)

    return resp.json()


def get_dashboard_informes_resumen_api(
    anio=None,
    pais=None,
    puerto=None,
    cliente=None,
    operacion=None,
    tipo_informe=None
):

    url = f"{BASE_URL}/dashboard-informes/resumen"

    params = {}

    if anio:
        params["anio"] = anio
    if pais:
        params["pais"] = pais
    if puerto:
        params["puerto"] = puerto
    if cliente:
        params["cliente"] = cliente
    if operacion:
        params["operacion"] = operacion
    if tipo_informe:
        params["tipo_informe"] = tipo_informe

    try:

        resp = api_request(
            "GET",
            url,
            params=params
        )

        if resp is None:
            raise Exception("El servidor no respondió")

        if resp.status_code != 200:

            try:
                data = resp.json()
                msg = data.get("detail", str(data))
            except Exception:
                msg = resp.text

            raise Exception(msg)

        try:
            data = resp.json()
        except Exception:
            raise Exception("Respuesta inválida del servidor")

        if data is None:
            raise Exception("El servidor devolvió datos vacíos")

        if not isinstance(data, dict):
            raise Exception(f"Respuesta inesperada del API: {data}")

        return data

    except Exception as e:

        if str(e) == "None":
            raise Exception("Error interno del API")

        raise


# =========================================================
# SERVICIOS SURVEYORS (FLAT)
# =========================================================

def get_servicio_surveyors_api(consec: int):
    """
    GET surveyors por servicio
    """
    try:
        url = f"{BASE_URL}/servicios-surveyors/{consec}"

        response = api_request(
            "GET",
            url,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()

    except Exception as e:
        raise Exception(f"Error GET surveyors: {e}")


def save_servicio_surveyors_api(consec: int, payload: dict):
    """
    POST / PUT surveyors (usa PUT para reemplazar)
    """
    try:
        url = f"{BASE_URL}/servicios-surveyors/{consec}"

        response = api_request(
            "PUT",
            url,
            json=payload,
            timeout=TIMEOUT
        )

        if response.status_code not in (200, 201):
            raise Exception(response.text)

        return response.json()

    except Exception as e:
        raise Exception(f"Error SAVE surveyors: {e}")


def create_servicio_surveyors_api(consec: int, payload: dict):
    """
    POST inicial (opcional)
    """
    try:
        url = f"{BASE_URL}/servicios-surveyors/{consec}"

        response = api_request(
            "POST",
            url,
            json=payload,
            timeout=TIMEOUT
        )

        if response.status_code not in (200, 201):
            raise Exception(response.text)

        return response.json()

    except Exception as e:
        raise Exception(f"Error CREATE surveyors: {e}")


def get_surveyors_catalog_api():
    """
    GET catálogo surveyors
    """
    try:
        url = f"{BASE_URL}/servicios-surveyors/catalogo/lista"

        response = api_request(
            "GET",
            url,
            timeout=TIMEOUT
        )

        if response.status_code != 200:
            raise Exception(response.text)

        return response.json()

    except Exception as e:
        try:
            rows = get_surveyores_full_api()
            data = []
            seen = set()

            for row in rows:
                if not isinstance(row, dict):
                    continue

                nombre = (row.get("nombre") or "").strip()
                apellidos = (row.get("apellidos") or "").strip()
                codigo = (row.get("codigo") or "").strip()
                display = " ".join([nombre, apellidos]).strip() or nombre or codigo

                if not display:
                    continue

                key = display.lower()
                if key in seen:
                    continue

                seen.add(key)
                data.append(
                    {
                        "id": codigo,
                        "codigo": codigo,
                        "nombre": display,
                        "apellidos": "",
                    }
                )

            return {"data": data}
        except Exception as fallback_error:
            raise Exception(
                f"Error GET catalogo surveyors: {e}; fallback /surveyores: {fallback_error}"
            )
