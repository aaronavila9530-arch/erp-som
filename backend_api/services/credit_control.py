from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import database


MONEY = Decimal("0.01")


def _money(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(MONEY, rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _normalize(value: Any) -> str:
    return str(value or "").strip().lower()


def _latest_exchange_rate(cur) -> Decimal:
    try:
        cur.execute(
            """
            SELECT rate
            FROM exchange_rate
            WHERE rate IS NOT NULL
            ORDER BY rate_date DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        if row and row[0]:
            return _money(row[0])
    except Exception:
        pass
    return Decimal("500.00")


def _convert(amount: Decimal, source: str, target: str, rate: Decimal) -> Decimal:
    source = (source or "USD").upper()
    target = (target or "USD").upper()
    if source == target:
        return amount
    if source == "CRC" and target == "USD":
        return (amount / rate).quantize(MONEY, rounding=ROUND_HALF_UP)
    if source == "USD" and target == "CRC":
        return (amount * rate).quantize(MONEY, rounding=ROUND_HALF_UP)
    return amount


def ensure_credit_control_schema() -> None:
    database.sql(
        """
        ALTER TABLE servicios
          ADD COLUMN IF NOT EXISTS credit_status VARCHAR(30),
          ADD COLUMN IF NOT EXISTS credit_decision TEXT,
          ADD COLUMN IF NOT EXISTS credit_checked_at TIMESTAMP,
          ADD COLUMN IF NOT EXISTS credit_release_by VARCHAR(120),
          ADD COLUMN IF NOT EXISTS credit_release_at TIMESTAMP,
          ADD COLUMN IF NOT EXISTS credit_release_reason TEXT
        """
    )
    database.sql(
        """
        CREATE TABLE IF NOT EXISTS credit_order_releases (
            id SERIAL PRIMARY KEY,
            company_code VARCHAR(30) NOT NULL,
            service_consec INTEGER,
            codigo_cliente VARCHAR(80),
            cliente TEXT,
            projected_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
            currency VARCHAR(10) NOT NULL DEFAULT 'USD',
            credit_limit NUMERIC(18,2) NOT NULL DEFAULT 0,
            open_ar NUMERIC(18,2) NOT NULL DEFAULT 0,
            projected_exposure NUMERIC(18,2) NOT NULL DEFAULT 0,
            over_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
            decision VARCHAR(30) NOT NULL,
            reason_code VARCHAR(60),
            approved_by VARCHAR(120),
            approved_role VARCHAR(60),
            approval_reason TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def resolve_client(company: str, client_ref: str) -> dict[str, Any] | None:
    conn = database.get_conn()
    try:
        cur = conn.cursor()
        text = str(client_ref or "").strip()
        cur.execute(
            """
            SELECT codigo, nombrejuridico, nombrecomercial
            FROM cliente
            WHERE company_code = %s
              AND (
                    LOWER(TRIM(codigo)) = LOWER(TRIM(%s))
                 OR LOWER(TRIM(nombrejuridico)) = LOWER(TRIM(%s))
                 OR LOWER(TRIM(nombrecomercial)) = LOWER(TRIM(%s))
              )
            LIMIT 1
            """,
            (company, text, text, text),
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "codigo_cliente": row[0],
            "nombrejuridico": row[1],
            "nombrecomercial": row[2],
            "display_name": row[2] or row[1] or row[0],
        }
    finally:
        database.release_conn(conn)


def build_credit_decision(
    company: str,
    client_ref: str,
    projected_amount: Any = 0,
    projected_currency: str = "USD",
) -> dict[str, Any]:
    ensure_credit_control_schema()
    conn = database.get_conn()
    try:
        cur = conn.cursor()
        client = resolve_client(company, client_ref)
        client_code = client["codigo_cliente"] if client else str(client_ref or "").strip()
        client_name = client["display_name"] if client else str(client_ref or "").strip()

        cur.execute(
            """
            SELECT termino_pago, limite_credito, moneda, estado_credito, hold_manual, observaciones
            FROM cliente_credito
            WHERE company_code = %s
              AND codigo_cliente = %s
            LIMIT 1
            """,
            (company, client_code),
        )
        credit = cur.fetchone()
        rate = _latest_exchange_rate(cur)
        if not credit:
            credit_currency = (projected_currency or "USD").upper()
            projected = _money(projected_amount)
            return {
                "status": "REQUIRES_RELEASE",
                "requires_release": True,
                "reason_code": "NO_CREDIT_CONFIG",
                "message": f"Cliente {client_name or client_ref} no tiene configuracion crediticia.",
                "codigo_cliente": client_code,
                "cliente": client_name,
                "currency": credit_currency,
                "credit_limit": 0.0,
                "open_ar": 0.0,
                "projected_amount": float(projected),
                "projected_exposure": float(projected),
                "available": float(-projected),
                "over_amount": float(projected),
                "exchange_rate": float(rate),
            }

        termino_pago, limite_credito, moneda, estado_credito, hold_manual, observaciones = credit
        credit_currency = (moneda or "USD").upper()
        credit_limit = _money(limite_credito)
        projected = _convert(_money(projected_amount), projected_currency, credit_currency, rate)

        cur.execute(
            """
            SELECT moneda, COALESCE(SUM(saldo_pendiente),0) AS total
            FROM collections
            WHERE company_code = %s
              AND codigo_cliente = %s
              AND saldo_pendiente > 0
            GROUP BY moneda
            """,
            (company, client_code),
        )
        open_ar = Decimal("0.00")
        ar_by_currency = []
        for currency, total in cur.fetchall():
            subtotal = _money(total)
            ar_by_currency.append({"currency": currency or "USD", "amount": float(subtotal)})
            open_ar += _convert(subtotal, currency or "USD", credit_currency, rate)

        projected_exposure = (open_ar + projected).quantize(MONEY, rounding=ROUND_HALF_UP)
        available = (credit_limit - projected_exposure).quantize(MONEY, rounding=ROUND_HALF_UP)
        over_amount = max(Decimal("0.00"), -available).quantize(MONEY, rounding=ROUND_HALF_UP)
        status = "CLEAR"
        reason_code = "OK"
        message = "Cliente dentro del limite crediticio."

        if str(estado_credito or "").upper() == "HOLD" or bool(hold_manual):
            status = "REQUIRES_RELEASE"
            reason_code = "MANUAL_HOLD"
            message = f"Cliente {client_name} esta en hold crediticio."
        elif credit_limit <= 0:
            status = "REQUIRES_RELEASE"
            reason_code = "ZERO_LIMIT"
            message = f"Cliente {client_name} no tiene limite crediticio disponible."
        elif projected_exposure > credit_limit:
            status = "REQUIRES_RELEASE"
            reason_code = "OVERLIMIT"
            message = (
                f"Cliente {client_name} excede limite {credit_currency} "
                f"{credit_limit:,.2f}; exposicion proyectada {projected_exposure:,.2f}."
            )

        return {
            "status": status,
            "requires_release": status == "REQUIRES_RELEASE",
            "reason_code": reason_code,
            "message": message,
            "codigo_cliente": client_code,
            "cliente": client_name,
            "termino_pago": termino_pago,
            "currency": credit_currency,
            "credit_limit": float(credit_limit),
            "open_ar": float(open_ar),
            "open_ar_by_currency": ar_by_currency,
            "projected_amount": float(projected),
            "projected_exposure": float(projected_exposure),
            "available": float(available),
            "over_amount": float(over_amount),
            "estado_credito": estado_credito or "ACTIVE",
            "hold_manual": bool(hold_manual),
            "observaciones": observaciones,
            "exchange_rate": float(rate),
        }
    finally:
        database.release_conn(conn)


def assert_release_allowed(role: str | None) -> None:
    if str(role or "").strip().lower() not in {"admin", "master"}:
        raise PermissionError("Solo admin o master puede liberar una venta con hold/sobregiro crediticio.")


def mark_service_credit_decision(
    service_consec: int,
    company: str,
    decision: dict[str, Any],
    approved_by: str | None = None,
    approved_role: str | None = None,
    approval_reason: str | None = None,
) -> None:
    ensure_credit_control_schema()
    status = "RELEASED" if decision.get("requires_release") else "CLEAR"
    database.sql(
        """
        UPDATE servicios
        SET credit_status = %s,
            credit_decision = %s,
            credit_checked_at = CURRENT_TIMESTAMP,
            credit_release_by = %s,
            credit_release_at = CASE WHEN %s IS NULL THEN NULL ELSE CURRENT_TIMESTAMP END,
            credit_release_reason = %s
        WHERE consec = %s
          AND company_code = %s
        """,
        (
            status,
            decision.get("message"),
            approved_by,
            approved_by,
            approval_reason,
            service_consec,
            company,
        ),
    )
    if decision.get("requires_release"):
        database.sql(
            """
            INSERT INTO credit_order_releases (
                company_code, service_consec, codigo_cliente, cliente,
                projected_amount, currency, credit_limit, open_ar,
                projected_exposure, over_amount, decision, reason_code,
                approved_by, approved_role, approval_reason
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                company,
                service_consec,
                decision.get("codigo_cliente"),
                decision.get("cliente"),
                decision.get("projected_amount") or 0,
                decision.get("currency") or "USD",
                decision.get("credit_limit") or 0,
                decision.get("open_ar") or 0,
                decision.get("projected_exposure") or 0,
                decision.get("over_amount") or 0,
                status,
                decision.get("reason_code"),
                approved_by,
                approved_role,
                approval_reason,
            ),
        )
