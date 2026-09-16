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


def _collections_risk(cur, company: str, client_code: str, credit_currency: str, rate: Decimal) -> dict[str, Any]:
    cur.execute(
        """
        SELECT
            moneda,
            COALESCE(SUM(saldo_pendiente),0) AS total,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(CASE WHEN fecha_vencimiento < CURRENT_DATE THEN saldo_pendiente ELSE 0 END),0) AS overdue_total,
            COUNT(*) FILTER (WHERE fecha_vencimiento < CURRENT_DATE) AS overdue_count,
            COALESCE(MAX(CASE WHEN fecha_vencimiento < CURRENT_DATE THEN CURRENT_DATE - fecha_vencimiento ELSE 0 END),0) AS max_days_overdue
        FROM collections
        WHERE company_code = %s
          AND codigo_cliente = %s
          AND saldo_pendiente > 0
        GROUP BY moneda
        """,
        (company, client_code),
    )
    open_ar = Decimal("0.00")
    overdue_ar = Decimal("0.00")
    invoice_count = 0
    overdue_count = 0
    max_days_overdue = 0
    ar_by_currency = []
    for currency, total, count, overdue_total, overdue_docs, days_overdue in cur.fetchall():
        source_currency = currency or "USD"
        subtotal = _money(total)
        overdue_subtotal = _money(overdue_total)
        ar_by_currency.append({"currency": source_currency, "amount": float(subtotal)})
        open_ar += _convert(subtotal, source_currency, credit_currency, rate)
        overdue_ar += _convert(overdue_subtotal, source_currency, credit_currency, rate)
        invoice_count += int(count or 0)
        overdue_count += int(overdue_docs or 0)
        max_days_overdue = max(max_days_overdue, int(days_overdue or 0))
    return {
        "open_ar": open_ar.quantize(MONEY, rounding=ROUND_HALF_UP),
        "overdue_ar": overdue_ar.quantize(MONEY, rounding=ROUND_HALF_UP),
        "invoice_count": invoice_count,
        "overdue_count": overdue_count,
        "max_days_overdue": max_days_overdue,
        "ar_by_currency": ar_by_currency,
    }


def _payment_trend(cur, company: str, client_code: str, termino_pago: Any) -> dict[str, Any]:
    terms = int(termino_pago or 0)
    try:
        cur.execute(
            """
            SELECT
                AVG(ca.fecha_pago::date - COALESCE(c.fecha_vencimiento::date, c.fecha_emision::date + COALESCE(%s::int, 0))) AS avg_days_after_due,
                AVG(ca.fecha_pago::date - c.fecha_emision::date) AS avg_days_to_pay,
                COUNT(DISTINCT ca.numero_documento) AS paid_documents,
                MAX(ca.fecha_pago::date) AS last_payment_date
            FROM cash_app ca
            JOIN collections c
              ON c.company_code = ca.company_code
             AND c.codigo_cliente = ca.codigo_cliente
             AND ltrim(c.numero_documento, '0') = ltrim(ca.numero_documento, '0')
             AND c.tipo_documento = 'FACTURA'
            WHERE ca.company_code = %s
              AND ca.codigo_cliente = %s
              AND ca.tipo_aplicacion = 'PAGO'
              AND ca.fecha_pago IS NOT NULL
              AND c.fecha_emision IS NOT NULL
            """,
            (terms, company, client_code),
        )
        row = cur.fetchone()
    except Exception:
        row = None

    if not row or row[2] in (None, 0):
        return {
            "trend": "SIN_HISTORIAL",
            "label": "Sin historial de pago aplicado",
            "avg_days_to_pay": None,
            "avg_days_after_due": None,
            "paid_documents": 0,
            "last_payment_date": None,
            "severity": "warning",
        }

    avg_after_due = int(round(row[0] or 0))
    avg_to_pay = int(round(row[1] or 0))
    paid_documents = int(row[2] or 0)
    last_payment_date = row[3].isoformat() if hasattr(row[3], "isoformat") else row[3]
    if avg_after_due <= 0:
        trend = "BUENO"
        label = "Paga dentro del plazo"
        severity = "ok"
    elif avg_after_due <= 15:
        trend = "MEDIO"
        label = f"Paga en promedio {avg_after_due} dias despues del vencimiento"
        severity = "warning"
    else:
        trend = "LENTO"
        label = f"Paga lento: promedio {avg_after_due} dias despues del vencimiento"
        severity = "danger"
    return {
        "trend": trend,
        "label": label,
        "avg_days_to_pay": avg_to_pay,
        "avg_days_after_due": avg_after_due,
        "paid_documents": paid_documents,
        "last_payment_date": last_payment_date,
        "severity": severity,
    }


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
            trend = {
                "trend": "SIN_CONFIG",
                "label": "No se puede medir tendencia sin configuracion crediticia",
                "avg_days_to_pay": None,
                "avg_days_after_due": None,
                "paid_documents": 0,
                "last_payment_date": None,
                "severity": "danger",
            }
            alerts = [
                "Cliente sin configuracion crediticia.",
                "Debe aprobarse release antes de crear el servicio.",
            ]
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
                "payment_trend": trend,
                "risk_alerts": alerts,
                "risk_summary": " | ".join(alerts),
                "advisory_requires_ack": True,
            }

        termino_pago, limite_credito, moneda, estado_credito, hold_manual, observaciones = credit
        credit_currency = (moneda or "USD").upper()
        credit_limit = _money(limite_credito)
        projected = _convert(_money(projected_amount), projected_currency, credit_currency, rate)

        collections_risk = _collections_risk(cur, company, client_code, credit_currency, rate)
        open_ar = collections_risk["open_ar"]
        overdue_ar = collections_risk["overdue_ar"]
        ar_by_currency = collections_risk["ar_by_currency"]
        trend = _payment_trend(cur, company, client_code, termino_pago)

        projected_exposure = (open_ar + projected).quantize(MONEY, rounding=ROUND_HALF_UP)
        available = (credit_limit - projected_exposure).quantize(MONEY, rounding=ROUND_HALF_UP)
        over_amount = max(Decimal("0.00"), -available).quantize(MONEY, rounding=ROUND_HALF_UP)
        status = "CLEAR"
        reason_code = "OK"
        message = "Cliente dentro del limite crediticio."
        alerts: list[str] = []

        if str(estado_credito or "").upper() == "HOLD" or bool(hold_manual):
            status = "REQUIRES_RELEASE"
            reason_code = "MANUAL_HOLD"
            message = f"Cliente {client_name} esta en hold crediticio."
            alerts.append("Cliente bloqueado por hold crediticio/manual.")
        elif credit_limit <= 0:
            status = "REQUIRES_RELEASE"
            reason_code = "ZERO_LIMIT"
            message = f"Cliente {client_name} no tiene limite crediticio disponible."
            alerts.append("Cliente sin limite crediticio disponible.")
        elif projected_exposure > credit_limit:
            status = "REQUIRES_RELEASE"
            reason_code = "OVERLIMIT"
            message = (
                f"Cliente {client_name} excede limite {credit_currency} "
                f"{credit_limit:,.2f}; exposicion proyectada {projected_exposure:,.2f}."
            )
            alerts.append(f"Excede el limite por {credit_currency} {over_amount:,.2f}.")

        if overdue_ar > 0:
            alerts.append(
                f"Tiene {collections_risk['overdue_count']} factura(s) vencida(s) por "
                f"{credit_currency} {overdue_ar:,.2f}; mayor atraso {collections_risk['max_days_overdue']} dias."
            )
        if trend.get("trend") in {"LENTO", "MEDIO", "SIN_HISTORIAL"}:
            alerts.append(f"Payment trend: {trend.get('label')}.")
        if status == "CLEAR" and credit_limit > 0:
            available_pct = (available / credit_limit) if credit_limit else Decimal("0")
            if available_pct <= Decimal("0.20"):
                alerts.append(f"Disponible bajo: {credit_currency} {available:,.2f} despues del servicio.")
        if alerts and status == "CLEAR":
            message = f"Cliente {client_name} dentro del limite, con alertas de riesgo."
        risk_summary = " | ".join(alerts) if alerts else "Sin alertas criticas de credito."

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
            "overdue_ar": float(overdue_ar),
            "open_invoice_count": collections_risk["invoice_count"],
            "overdue_invoice_count": collections_risk["overdue_count"],
            "max_days_overdue": collections_risk["max_days_overdue"],
            "open_ar_by_currency": ar_by_currency,
            "projected_amount": float(projected),
            "projected_exposure": float(projected_exposure),
            "available": float(available),
            "over_amount": float(over_amount),
            "estado_credito": estado_credito or "ACTIVE",
            "hold_manual": bool(hold_manual),
            "observaciones": observaciones,
            "exchange_rate": float(rate),
            "payment_trend": trend,
            "risk_alerts": alerts,
            "risk_summary": risk_summary,
            "advisory_requires_ack": bool(alerts),
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
