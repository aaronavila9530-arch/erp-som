from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import os
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Depends, Header, HTTPException
from psycopg2.extras import RealDictCursor
import requests

from database import get_db
from rbac_service import has_permission


router = APIRouter(prefix="/exchange-rate", tags=["Exchange Rate"])


def require_permission(module: str, action: str):
    def checker(x_user_role: str = Header(..., alias="X-User-Role")):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(status_code=403, detail="No autorizado")
    return checker


BCCR_OLD_URL = (
    "https://gee.bccr.fi.cr/Indicadores/Suscripciones/WS/"
    "wsindicadoreseconomicos.asmx/ObtenerIndicadoresEconomicos"
)
BCCR_API_BASE = os.getenv(
    "BCCR_API_BASE",
    "https://apim.bccr.fi.cr/SDDE/api/Bccr.Ge.SDDE.Publico.Indicadores.API",
).rstrip("/")
BCCR_EMAIL = os.getenv("BCCR_EMAIL", "aaron.avila@hotmail.es")
BCCR_DEFAULT_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJCQ0NSLVNEREUiLCJzdWIiOiJhYXJvbi5hdmlsYUBob3RtYWlsLmVzIiwiYXVkIjoiU0RERS1TaXRpb0V4dGVybm8iLCJleHAiOjI1MzQwMjMwMDgwMCwibmJmIjoxNzg1MjYxNDY5LCJpYXQiOjE3ODUyNjE0NjksImp0aSI6IjI4MjlmYjgzLWIzNGQtNGQxOC1hNTg1LWNmNGE1YjY1NGU3MiIsImVtYWlsIjoiYWFyb24uYXZpbGFAaG90bWFpbC5lcyJ9."
    "KV0awZgT8tGlW0zlTj2cvznxanEOcAxCloRZb7APwRg"
)
BCCR_TOKEN = os.getenv("BCCR_API_TOKEN") or os.getenv("BCCR_TOKEN") or BCCR_DEFAULT_TOKEN
if BCCR_TOKEN == "S8L8LAT0VI":
    BCCR_TOKEN = BCCR_DEFAULT_TOKEN
BCCR_NOMBRE = os.getenv("BCCR_APP_NAME", "MSL")

INDICADOR_COMPRA = "317"
INDICADOR_VENTA = "318"


def _parse_bccr_date(raw: str) -> date:
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("Fecha BCCR vacia")
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha BCCR no soportado: {raw}")


def _date_variants(value: date) -> list[str]:
    return [
        value.strftime("%Y/%m/%d"),
        value.strftime("%Y-%m-%d"),
        value.strftime("%d/%m/%Y"),
    ]


def _number(value) -> float:
    text = str(value or "").strip().replace(",", ".")
    if not text:
        raise ValueError("Valor BCCR vacio")
    return float(Decimal(text))


def _walk_json(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _extract_rate_from_api_payload(payload: dict, today: date) -> tuple[float, date]:
    candidates = []
    for item in _walk_json(payload):
        keys = {str(key).lower(): key for key in item}
        date_key = next((keys[key] for key in ("fecha", "des_fecha", "fechadato") if key in keys), None)
        value_key = next((
            keys[key] for key in (
                "valor",
                "num_valor",
                "valordatoporperiodo",
                "valordato",
                "valorindicador",
                "valor_dato_por_periodo",
            )
            if key in keys
        ), None)
        if not date_key or not value_key:
            continue
        try:
            rate_date = _parse_bccr_date(str(item.get(date_key)))
            if rate_date <= today:
                candidates.append((rate_date, _number(item.get(value_key))))
        except (ValueError, InvalidOperation):
            continue
    if not candidates:
        raise ValueError("La respuesta BCCR no contiene series utilizables")
    rate_date, rate = sorted(candidates, key=lambda row: row[0], reverse=True)[0]
    return rate, rate_date


def _fetch_tc_venta_from_bccr_api(today: date) -> tuple[float, date]:
    if not BCCR_TOKEN:
        raise ValueError("BCCR_API_TOKEN/BCCR_TOKEN no configurado")

    url = f"{BCCR_API_BASE}/indicadoresEconomicos/{INDICADOR_VENTA}/series"
    start = today - timedelta(days=10)
    headers = {
        "Authorization": f"Bearer {BCCR_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "ERP-SOM/1.0",
    }
    last_error = None
    for start_text in _date_variants(start):
        for end_text in _date_variants(today):
            params = {"fechaInicio": start_text, "fechaFin": end_text, "idioma": "ES"}
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                return _extract_rate_from_api_payload(response.json(), today)
            except Exception as exc:
                last_error = exc
    raise ValueError(f"BCCR API no disponible: {last_error}")


def _fetch_tc_venta_from_bccr_old(today: date) -> tuple[float, date]:
    today_text = today.strftime("%d/%m/%Y")
    params = {
        "Indicador": INDICADOR_VENTA,
        "FechaInicio": today_text,
        "FechaFinal": today_text,
        "Nombre": BCCR_NOMBRE,
        "SubNiveles": "N",
        "CorreoElectronico": BCCR_EMAIL,
        "Token": BCCR_TOKEN,
    }
    response = requests.get(BCCR_OLD_URL, params=params, timeout=30)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    ns = {"ns": "http://ws.sdde.bccr.fi.cr"}
    value_node = root.find(".//ns:NUM_VALOR", ns) or root.find(".//NUM_VALOR")
    date_node = root.find(".//ns:DES_FECHA", ns) or root.find(".//DES_FECHA")
    if value_node is None or date_node is None:
        raise ValueError(f"NUM_VALOR/DES_FECHA no encontrados. XML: {response.text[:300]}")
    return _number(value_node.text), _parse_bccr_date(date_node.text)


def _fetch_tc_venta_from_bccr(today: date) -> tuple[float, date]:
    try:
        return _fetch_tc_venta_from_bccr_api(today)
    except Exception as api_error:
        try:
            return _fetch_tc_venta_from_bccr_old(today)
        except Exception as old_error:
            raise HTTPException(
                status_code=503,
                detail=f"BCCR no disponible. API nueva: {api_error}; WS anterior: {old_error}",
            )


@router.get("/today")
def get_today_exchange_rate(conn=Depends(get_db)):
    if not conn:
        raise HTTPException(500, "No DB connection")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    today = date.today()

    cur.execute("""
        SELECT rate, rate_date, source
        FROM exchange_rate
        WHERE rate_date = %s
        LIMIT 1
    """, (today,))
    row = cur.fetchone()
    if row:
        return {"rate": float(row["rate"]), "date": row["rate_date"].isoformat(), "source": "CACHE"}

    try:
        rate, rate_date = _fetch_tc_venta_from_bccr(today)
    except Exception as bccr_error:
        conn.rollback()
        cur.execute("""
            SELECT rate, rate_date, source
            FROM exchange_rate
            WHERE rate_date <= %s
            ORDER BY rate_date DESC
            LIMIT 1
        """, (today,))
        fallback = cur.fetchone()
        if fallback:
            fallback_date = fallback["rate_date"]
            return {
                "rate": float(fallback["rate"]),
                "date": fallback_date.isoformat(),
                "source": "CACHE_FALLBACK",
                "stale": fallback_date != today,
                "warning": (
                    "BCCR no disponible o token no valido para la API nueva; "
                    f"se utiliza el ultimo tipo de cambio guardado ({fallback_date.isoformat()})"
                ),
            }
        raise HTTPException(503, "BCCR no disponible y no existe un tipo de cambio guardado") from bccr_error

    try:
        cur.execute("""
            INSERT INTO exchange_rate (rate, rate_date, source)
            VALUES (%s, %s, 'BCCR')
        """, (rate, rate_date))
        conn.commit()
    except Exception:
        conn.rollback()
        cur.execute("""
            SELECT rate, rate_date, source
            FROM exchange_rate
            WHERE rate_date = %s
            LIMIT 1
        """, (rate_date,))
        row2 = cur.fetchone()
        if row2:
            return {
                "rate": float(row2["rate"]),
                "date": row2["rate_date"].isoformat(),
                "source": "CACHE",
                "stale": row2["rate_date"] != today,
            }
        raise

    return {"rate": float(rate), "date": rate_date.isoformat(), "source": "BCCR", "stale": rate_date != today}


@router.get("/latest")
def get_latest_exchange_rate(conn=Depends(get_db)):
    if not conn:
        raise HTTPException(500, "No DB connection")

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT rate, rate_date, source
        FROM exchange_rate
        ORDER BY rate_date DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="No hay tipo de cambio registrado")
    return {"rate": float(row["rate"]), "date": row["rate_date"].isoformat(), "source": row.get("source") or "BCCR"}
