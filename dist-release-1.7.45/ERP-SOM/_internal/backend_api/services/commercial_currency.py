"""Currency provenance for legacy service fees and USD commercial analytics."""
from threading import Lock

from fastapi import Depends, Header, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from rbac_service import has_permission
from services.tenanting import company_code


_ready = False
_lock = Lock()
# Confirmed by the owner on 2026-10-12; exact matches, never amount heuristics.
CONFIRMED_CRC = (
    ("MV NORSE STRIDE", "2026-05-30", 1850940),
    ("MV LINA AKSOY", "2026-07-02", 1101750),
    ("MV SANTAA CAROLINA", "2026-07-14", 1023780),
)

RATE_SQL = """SELECT rate, rate_date FROM exchange_rate
    WHERE rate > 0 AND rate_date <= CURRENT_DATE
    ORDER BY rate_date DESC, rate DESC LIMIT 1"""

# All callers interpolate this expression before aggregating, not after SUM.
HONORARIOS_USD = f"""(CASE
    WHEN COALESCE(s.honorarios, 0) = 0 THEN 0
    WHEN COALESCE(s.honorarios_moneda, 'USD') = 'CRC'
        THEN CAST(s.honorarios AS NUMERIC) / CAST((SELECT rate FROM ({RATE_SQL}) commercial_fx) AS NUMERIC)
    ELSE CAST(s.honorarios AS NUMERIC) END)"""


def ensure_currency_schema(conn):
    global _ready
    with _lock:
        if _ready:
            return
        try:
            with conn.cursor() as cur:
                cur.execute("ALTER TABLE servicios ADD COLUMN IF NOT EXISTS honorarios_moneda TEXT")
                for vessel, day, amount in CONFIRMED_CRC:
                    cur.execute("""SELECT consec FROM servicios
                        WHERE COALESCE(NULLIF(TRIM(company_code), ''), 'MSL-CR') = 'MSL-CR'
                          AND UPPER(TRIM(buque_contenedor)) = %s
                          AND fecha_inicio::date = %s::date AND honorarios = %s
                          AND honorarios_moneda IS NULL FOR UPDATE""", (vessel, day, amount))
                    matches = cur.fetchall()
                    if len(matches) > 1:
                        raise RuntimeError("La correccion de moneda identifica varios servicios")
                    if matches:
                        cur.execute("UPDATE servicios SET honorarios_moneda = 'CRC' WHERE consec = %s", (matches[0][0],))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        _ready = True


def currency_context(conn, company="MSL-CR"):
    ensure_currency_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(RATE_SQL)
        rate = cur.fetchone()
        cur.execute("""SELECT COUNT(*) AS total FROM servicios
            WHERE COALESCE(honorarios, 0) <> 0 AND honorarios_moneda = 'CRC'
              AND COALESCE(NULLIF(TRIM(company_code), ''), 'MSL-CR') = %s""", (company,))
        needs_rate = cur.fetchone()["total"]
    if needs_rate and not rate:
        raise HTTPException(503, "Falta tipo de cambio BCCR en Accounting; no se pueden calcular margenes USD")
    return {
        "currency": "USD",
        "rate": float(rate["rate"]) if rate else None,
        "rate_date": str(rate["rate_date"]) if rate else None,
    }


def require_commercial_currency(
    x_user_role: str = Header(..., alias="X-User-Role"),
    x_company_code: str = Header("MSL-CR", alias="X-Company-Code"), conn=Depends(get_db)
):
    if not has_permission(x_user_role, "comercial", "view"):
        raise HTTPException(403, "No autorizado")
    return currency_context(conn, company_code(x_company_code))
