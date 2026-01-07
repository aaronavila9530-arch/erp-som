import requests
from typing import Optional
from datetime import datetime


BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"
TIMEOUT = 30

# ============================================================
# USER ROLE (RBAC)
# ============================================================

_current_user_role: Optional[str] = None


def set_user_role(role: str):
    global _current_user_role
    _current_user_role = role


def get_user_role() -> Optional[str]:
    return _current_user_role


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
# SURVEYORS
# ============================================================
def get_surveyores_api():
    url = f"{BASE_URL}/surveyores?page=1&page_size=500"
    resp = api_request("GET", url).json()
    return resp.get("data", [])

def get_surveyores_nombres_api():
    resp = get_surveyores_api()
    return [s["nombre"] for s in resp]

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
# Marcar Por Confirmar
# ============================================================
def marcar_por_confirmar_api(consec):
    try:
        url = f"{BASE_URL}/servicios/por_confirmar/{consec}"
        r = api_request("PUT", url, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ============================================================
# Marcar confirmado
# ============================================================

def confirmar_servicio_api(consec, fecha, hora):
    url = f"{BASE_URL}/servicios/confirmar/{consec}"
    payload = {
        "fecha_inicio": fecha,
        "hora_inicio": hora
    }
    try:
        resp = api_request("PUT", url, json=payload, timeout=15)
        return resp.json()
    except Exception as e:
        return {"status": "error", "error": str(e)}

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
# GENERAR / CONFIRMAR INFORME
# ============================================================
def confirmar_informe_api(consec):
    url = f"{BASE_URL}/servicios/generar_informe/{consec}"

    try:
        resp = api_request("PUT", url, timeout=15)

        # Backend siempre debe devolver JSON
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

def generar_informe_api(consec):
    return api_request(
        "PUT",
        f"{BASE_URL}/servicios/generar_informe/{consec}",
        timeout=15
    ).json()

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
    try:
        r = api_request(
            "POST",
            f"{BASE_URL}/accounting/manual-entry",
            json=payload,
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
# EXCHANGE RATE – BCCR
# ============================================================
def get_exchange_rate_today_api():
    """
    Obtiene el Tipo de Cambio del día.
    - Si existe en BD → lo retorna (CACHE)
    - Si no existe → BCCR → inserta → retorna
    """

    r = api_request(
        "GET",
        f"{BASE_URL}/exchange-rate/today",
        timeout=20
    )
    r.raise_for_status()
    return r.json()


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


def _headers():
    role = get_user_role()

    if not role:
        raise Exception("Rol de usuario no definido")

    return {
        "X-User-Role": role
    }

def api_request(method: str, url: str, **kwargs):
    """
    Wrapper central para TODAS las llamadas HTTP
    Inyecta X-User-Role automáticamente
    """
    headers = kwargs.pop("headers", {})
    headers.update(_headers())

    return requests.request(
        method=method,
        url=url,
        headers=headers,
        **kwargs
    )

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

        r = requests.post(
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

        r = requests.post(
            f"{BASE_URL}/factura/electronica",
            files=files,
            data=data,
            timeout=60
        )

    r.raise_for_status()
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
    r = requests.post(
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
    r = requests.post(
        f"{BASE_URL}/collections/pago",
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()

def aplicar_nota_credito_api(payload: dict):
    r = requests.post(
        f"{BASE_URL}/collections/aplicar-nota-credito",
        json=payload,
        timeout=20
    )
    r.raise_for_status()
    return r.json()
