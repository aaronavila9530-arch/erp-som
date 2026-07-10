import calendar
import json
import os
import tempfile
from datetime import date, timedelta
from decimal import Decimal
from html import escape

from psycopg2.extras import RealDictCursor


BLUE = "#123A63"
DARK = "#1F2933"
TEAL = "#2D9CDB"
GREEN = "#27AE60"
ORANGE = "#F2994A"
RED = "#C0392B"
GREY = "#F4F6F8"
LIGHT_BLUE = "#E8F0F8"
CHART_COLORS = [BLUE, TEAL, GREEN, ORANGE, RED, "#7F8C8D", "#8E44AD"]


def _period_bounds(year: int, month: int):
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    prev_start = date(year - 1, 12, 1) if month == 1 else date(year, month - 1, 1)
    prev_end = start - timedelta(days=1)
    next_month = 1 if month == 12 else month + 1
    next_year = year + 1 if month == 12 else year
    next_start = date(next_year, next_month, 1)
    next_end = date(next_year, next_month, calendar.monthrange(next_year, next_month)[1])
    return start, end, prev_start, prev_end, next_start, next_end


def _f(value):
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _money(value):
    return f"USD {_f(value):,.2f}"


def _short_money(value):
    amount = _f(value)
    if abs(amount) >= 1000:
        return f"USD {amount / 1000:,.1f}K"
    return f"USD {amount:,.0f}"


def _pct(current, previous):
    previous = _f(previous)
    current = _f(current)
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


def _month_label(year: int, month: int):
    q = ((month - 1) // 3) + 1
    month_in_q = ((month - 1) % 3) + 1
    return f"Reporte financiero, Mes {month_in_q} Q{q} FY{str(year)[-2:]}"


def _fetch_one(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchone() or {}


def _fetch_all(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall() or []


def _payments_cte():
    return """
        WITH payments AS (
            SELECT ca.codigo_cliente, ca.nombre_cliente, ca.fecha_pago, ca.monto_pagado AS amount, ca.numero_documento
            FROM cash_app ca
            WHERE ca.monto_pagado > 0 AND ca.tipo_aplicacion = 'PAGO'
            UNION ALL
            SELECT ip.codigo_cliente, ip.nombre_cliente, ip.fecha_pago, ip.monto AS amount, ip.documento AS numero_documento
            FROM incoming_payments ip
            WHERE ip.monto > 0
              AND NOT EXISTS (
                  SELECT 1 FROM cash_app ca2
                  WHERE ltrim(ca2.numero_documento, '0') = ltrim(ip.documento, '0')
                    AND ca2.codigo_cliente = ip.codigo_cliente
                    AND COALESCE(ca2.referencia, '') = COALESCE(ip.numero_referencia, '')
                    AND ca2.fecha_pago = ip.fecha_pago
                    AND ca2.monto_pagado = ip.monto
              )
        )
    """


def build_monthly_financial_data(conn, year: int, month: int):
    start, end, prev_start, prev_end, next_start, next_end = _period_bounds(year, month)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    revenue = _fetch_one(cur, """
        SELECT COALESCE(SUM(total), 0) AS total, COUNT(*) AS count
        FROM invoicing
        WHERE tipo_documento = 'FACTURA'
          AND fecha_emision BETWEEN %s AND %s
    """, (start, end))

    prev_revenue = _fetch_one(cur, """
        SELECT COALESCE(SUM(total), 0) AS total, COUNT(*) AS count
        FROM invoicing
        WHERE tipo_documento = 'FACTURA'
          AND fecha_emision BETWEEN %s AND %s
    """, (prev_start, prev_end))

    collections = _fetch_one(cur, _payments_cte() + """
        SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
        FROM payments
        WHERE fecha_pago BETWEEN %s AND %s
    """, (start, end))

    prev_collections = _fetch_one(cur, _payments_cte() + """
        SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
        FROM payments
        WHERE fecha_pago BETWEEN %s AND %s
    """, (prev_start, prev_end))

    top_collections = _fetch_all(cur, _payments_cte() + """
        SELECT nombre_cliente, COALESCE(SUM(amount), 0) AS total
        FROM payments
        WHERE fecha_pago BETWEEN %s AND %s
        GROUP BY nombre_cliente
        ORDER BY total DESC
        LIMIT 7
    """, (start, end))

    ar = _fetch_one(cur, """
        SELECT COALESCE(SUM(saldo_pendiente), 0) AS total, COUNT(*) AS count
        FROM collections
        WHERE saldo_pendiente > 0
          AND tipo_documento = 'FACTURA'
          AND fecha_emision <= %s
    """, (end,))

    top_ar = _fetch_all(cur, """
        SELECT nombre_cliente, COALESCE(SUM(saldo_pendiente), 0) AS total
        FROM collections
        WHERE saldo_pendiente > 0
          AND tipo_documento = 'FACTURA'
          AND fecha_emision <= %s
        GROUP BY nombre_cliente
        ORDER BY total DESC
        LIMIT 7
    """, (end,))

    ar_aging = _fetch_all(cur, """
        SELECT bucket AS nombre_cliente, COALESCE(SUM(saldo_pendiente), 0) AS total
        FROM (
            SELECT saldo_pendiente,
                   CASE
                       WHEN fecha_vencimiento IS NULL THEN 'No due date'
                       WHEN (%s::date - fecha_vencimiento) <= 0 THEN 'Current'
                       WHEN (%s::date - fecha_vencimiento) BETWEEN 1 AND 30 THEN '1-30 days'
                       WHEN (%s::date - fecha_vencimiento) BETWEEN 31 AND 60 THEN '31-60 days'
                       WHEN (%s::date - fecha_vencimiento) BETWEEN 61 AND 90 THEN '61-90 days'
                       ELSE 'Over 90 days'
                   END AS bucket
            FROM collections
            WHERE saldo_pendiente > 0
              AND tipo_documento = 'FACTURA'
              AND fecha_emision <= %s
        ) x
        GROUP BY bucket
        ORDER BY MIN(CASE bucket
            WHEN 'Current' THEN 1
            WHEN '1-30 days' THEN 2
            WHEN '31-60 days' THEN 3
            WHEN '61-90 days' THEN 4
            WHEN 'Over 90 days' THEN 5
            ELSE 6
        END)
    """, (end, end, end, end, end))

    payment_trend = _fetch_all(cur, _payments_cte() + """
        SELECT bucket AS nombre_cliente, COUNT(*)::numeric AS total
        FROM (
            SELECT CASE
                       WHEN i.fecha_emision IS NULL THEN 'Unmatched'
                       WHEN (p.fecha_pago::date - i.fecha_emision::date) <= 30 THEN '0-30 days'
                       WHEN (p.fecha_pago::date - i.fecha_emision::date) <= 60 THEN '31-60 days'
                       WHEN (p.fecha_pago::date - i.fecha_emision::date) <= 90 THEN '61-90 days'
                       WHEN (p.fecha_pago::date - i.fecha_emision::date) <= 120 THEN '91-120 days'
                       ELSE 'Over 120 days'
                   END AS bucket
            FROM payments p
            LEFT JOIN invoicing i
              ON ltrim(i.numero_documento, '0') = ltrim(p.numero_documento, '0')
             AND i.codigo_cliente = p.codigo_cliente
             AND i.tipo_documento = 'FACTURA'
            WHERE p.fecha_pago <= %s
        ) x
        GROUP BY bucket
        ORDER BY MIN(CASE bucket
            WHEN '0-30 days' THEN 1
            WHEN '31-60 days' THEN 2
            WHEN '61-90 days' THEN 3
            WHEN '91-120 days' THEN 4
            WHEN 'Over 120 days' THEN 5
            ELSE 6
        END)
    """, (end,))

    billing_trend = _fetch_all(cur, """
        SELECT TO_CHAR(DATE_TRUNC('month', fecha_emision), 'Mon YYYY') AS nombre_cliente,
               COALESCE(SUM(total), 0) AS total,
               COUNT(*) AS count
        FROM invoicing
        WHERE tipo_documento = 'FACTURA'
          AND fecha_emision BETWEEN %s AND %s
        GROUP BY DATE_TRUNC('month', fecha_emision)
        ORDER BY DATE_TRUNC('month', fecha_emision)
    """, (date(year, 1, 1), end))

    prev_year_trend = _fetch_all(cur, """
        SELECT EXTRACT(MONTH FROM fecha_emision)::int AS month_num,
               TO_CHAR(DATE_TRUNC('month', fecha_emision), 'Mon') AS nombre_cliente,
               COALESCE(SUM(total), 0) AS total
        FROM invoicing
        WHERE tipo_documento = 'FACTURA'
          AND fecha_emision BETWEEN %s AND %s
        GROUP BY EXTRACT(MONTH FROM fecha_emision), DATE_TRUNC('month', fecha_emision)
        ORDER BY EXTRACT(MONTH FROM fecha_emision)
    """, (date(year - 1, 1, 1), date(year - 1, month, calendar.monthrange(year - 1, month)[1])))

    current_year_trend = _fetch_all(cur, """
        SELECT EXTRACT(MONTH FROM fecha_emision)::int AS month_num,
               TO_CHAR(DATE_TRUNC('month', fecha_emision), 'Mon') AS nombre_cliente,
               COALESCE(SUM(total), 0) AS total
        FROM invoicing
        WHERE tipo_documento = 'FACTURA'
          AND fecha_emision BETWEEN %s AND %s
        GROUP BY EXTRACT(MONTH FROM fecha_emision), DATE_TRUNC('month', fecha_emision)
        ORDER BY EXTRACT(MONTH FROM fecha_emision)
    """, (date(year, 1, 1), end))

    top_billing = _fetch_all(cur, """
        SELECT nombre_cliente, COALESCE(SUM(total), 0) AS total
        FROM invoicing
        WHERE tipo_documento = 'FACTURA'
          AND fecha_emision BETWEEN %s AND %s
        GROUP BY nombre_cliente
        ORDER BY total DESC
        LIMIT 7
    """, (start, end))

    itp_paid = _fetch_one(cur, """
        SELECT COALESCE(SUM(
            CASE WHEN currency = 'CRC' THEN (total - balance) / 500.0 ELSE (total - balance) END
        ), 0) AS total, COUNT(*) AS count
        FROM payment_obligations
        WHERE status IN ('PAID','PARTIAL')
          AND last_payment_date BETWEEN %s AND %s
    """, (start, end))

    payables_open = _fetch_one(cur, """
        SELECT COALESCE(SUM(
            CASE WHEN currency = 'CRC' THEN balance / 500.0 ELSE balance END
        ), 0) AS total, COUNT(*) AS count
        FROM payment_obligations
        WHERE status IN ('PENDING','PARTIAL')
          AND due_date <= %s
    """, (end,))

    top_payables_open = _fetch_all(cur, """
        SELECT payee_name AS nombre_cliente, COALESCE(SUM(
            CASE WHEN currency = 'CRC' THEN balance / 500.0 ELSE balance END
        ), 0) AS total
        FROM payment_obligations
        WHERE status IN ('PENDING','PARTIAL')
          AND due_date <= %s
        GROUP BY payee_name
        ORDER BY total DESC
        LIMIT 7
    """, (end,))

    next_receivables = _fetch_one(cur, """
        SELECT COALESCE(SUM(saldo_pendiente), 0) AS total, COUNT(*) AS count
        FROM collections
        WHERE saldo_pendiente > 0
          AND tipo_documento = 'FACTURA'
          AND fecha_vencimiento BETWEEN %s AND %s
    """, (next_start, next_end))

    top_next_receivables = _fetch_all(cur, """
        SELECT nombre_cliente, COALESCE(SUM(saldo_pendiente), 0) AS total
        FROM collections
        WHERE saldo_pendiente > 0
          AND tipo_documento = 'FACTURA'
          AND fecha_vencimiento BETWEEN %s AND %s
        GROUP BY nombre_cliente
        ORDER BY total DESC
        LIMIT 7
    """, (next_start, next_end))

    next_payables = _fetch_one(cur, """
        SELECT COALESCE(SUM(
            CASE WHEN currency = 'CRC' THEN balance / 500.0 ELSE balance END
        ), 0) AS total, COUNT(*) AS count
        FROM payment_obligations
        WHERE status IN ('PENDING','PARTIAL')
          AND due_date BETWEEN %s AND %s
    """, (next_start, next_end))

    top_next_payables = _fetch_all(cur, """
        SELECT payee_name AS nombre_cliente, COALESCE(SUM(
            CASE WHEN currency = 'CRC' THEN balance / 500.0 ELSE balance END
        ), 0) AS total
        FROM payment_obligations
        WHERE status IN ('PENDING','PARTIAL')
          AND due_date BETWEEN %s AND %s
        GROUP BY payee_name
        ORDER BY total DESC
        LIMIT 7
    """, (next_start, next_end))

    avg_days = _fetch_one(cur, _payments_cte() + """
        SELECT ROUND(AVG(p.fecha_pago::date - i.fecha_emision::date), 1) AS days
        FROM payments p
        JOIN invoicing i
          ON ltrim(i.numero_documento, '0') = ltrim(p.numero_documento, '0')
         AND i.codigo_cliente = p.codigo_cliente
         AND i.tipo_documento = 'FACTURA'
        WHERE p.fecha_pago BETWEEN %s AND %s
    """, (start, end))

    cur.close()

    revenue_total = _f(revenue.get("total"))
    prev_revenue_total = _f(prev_revenue.get("total"))
    collections_total = _f(collections.get("total"))
    prev_collections_total = _f(prev_collections.get("total"))
    ar_total = _f(ar.get("total"))
    itp_total = _f(itp_paid.get("total"))
    payables_open_total = _f(payables_open.get("total"))
    next_receivables_total = _f(next_receivables.get("total"))
    next_payables_total = _f(next_payables.get("total"))
    net_cash = collections_total - itp_total
    next_net_outlook = next_receivables_total - next_payables_total
    month_name = calendar.month_name[month]
    prev_month_name = calendar.month_name[prev_start.month]
    next_month_name = calendar.month_name[next_start.month]

    data = {
        "period": {
            "year": year,
            "month": month,
            "month_name": month_name,
            "label": f"{month_name} {year}",
            "report_label": _month_label(year, month),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "previous_label": f"{prev_month_name} {prev_start.year}",
            "next_label": f"{next_month_name} {next_start.year}",
        },
        "metrics": {
            "revenue": revenue_total,
            "revenue_count": int(revenue.get("count") or 0),
            "previous_revenue": prev_revenue_total,
            "collections": collections_total,
            "collections_count": int(collections.get("count") or 0),
            "previous_collections": prev_collections_total,
            "ar_open": ar_total,
            "ar_count": int(ar.get("count") or 0),
            "itp_paid": itp_total,
            "itp_paid_count": int(itp_paid.get("count") or 0),
            "payables_open": payables_open_total,
            "payables_open_count": int(payables_open.get("count") or 0),
            "next_receivables": next_receivables_total,
            "next_receivables_count": int(next_receivables.get("count") or 0),
            "next_payables": next_payables_total,
            "next_payables_count": int(next_payables.get("count") or 0),
            "next_net_outlook": next_net_outlook,
            "net_cash": net_cash,
            "avg_days_to_pay": _f(avg_days.get("days")) if avg_days.get("days") is not None else None,
        },
        "tables": {
            "top_collections": [dict(r) for r in top_collections],
            "top_ar": [dict(r) for r in top_ar],
            "ar_aging": [dict(r) for r in ar_aging],
            "payment_trend": [dict(r) for r in payment_trend],
            "billing_trend": [dict(r) for r in billing_trend],
            "top_billing": [dict(r) for r in top_billing],
            "top_payables_open": [dict(r) for r in top_payables_open],
            "top_next_receivables": [dict(r) for r in top_next_receivables],
            "top_next_payables": [dict(r) for r in top_next_payables],
            "prev_year_trend": [dict(r) for r in prev_year_trend],
            "current_year_trend": [dict(r) for r in current_year_trend],
        },
    }
    data["narrative"] = _build_financial_narrative(data)
    return data


def _compact_rows(rows, limit=6):
    return [
        {"name": str(r.get("nombre_cliente") or "N/A"), "amount": round(_f(r.get("total")), 2)}
        for r in (rows or [])[:limit]
    ]


def _build_financial_narrative(data):
    ai = _ai_financial_narrative(data)
    if ai:
        return ai
    return _fallback_financial_narrative(data)


def _ai_financial_narrative(data):
    try:
        from ai.maritime_ai import _get_openai_client

        client = _get_openai_client()
        metrics = data["metrics"]
        period = data["period"]
        payload = {
            "period": period,
            "metrics": metrics,
            "top_collections": _compact_rows(data["tables"]["top_collections"]),
            "top_ar": _compact_rows(data["tables"]["top_ar"]),
            "ar_aging": _compact_rows(data["tables"]["ar_aging"]),
            "payment_trend": _compact_rows(data["tables"]["payment_trend"]),
            "billing_trend": _compact_rows(data["tables"]["billing_trend"]),
            "top_billing": _compact_rows(data["tables"]["top_billing"]),
            "top_payables_open": _compact_rows(data["tables"]["top_payables_open"]),
            "top_next_receivables": _compact_rows(data["tables"]["top_next_receivables"]),
            "top_next_payables": _compact_rows(data["tables"]["top_next_payables"]),
            "prev_year_trend": _compact_rows(data["tables"]["prev_year_trend"]),
            "current_year_trend": _compact_rows(data["tables"]["current_year_trend"]),
        }
        prompt = (
            "Eres CFO y analista financiero de Marine Surveyors & Logistics. "
            "Genera narrativa ejecutiva en espanol para un reporte financiero mensual, usando SOLO los datos entregados. "
            "No inventes numeros. Si un dato es cero, explicalo con prudencia como falta de registros o sin actividad registrada. "
            "Devuelve JSON valido con estas llaves exactas: introduction, collections, receivables, payment_trend, "
            "billing, payables, next_month_outlook, year_comparison, risk, conclusion. "
            "Cada valor debe ser un texto profesional de 2 a 4 parrafos cortos, estilo informe ejecutivo, "
            "con interpretacion y recomendaciónes cuando aplique."
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.25,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
        )
        text = response.choices[0].message.content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.split("\n", 1)[-1]
        parsed = json.loads(text)
        required = [
            "introduction", "collections", "receivables", "payment_trend", "billing",
            "payables", "next_month_outlook", "year_comparison", "risk", "conclusion",
        ]
        return {key: str(parsed.get(key) or "").strip() for key in required}
    except Exception:
        return None


def _fallback_financial_narrative(data):
    p = data["period"]
    m = data["metrics"]
    billing_pct = _pct(m["revenue"], m["previous_revenue"])
    collections_pct = _pct(m["collections"], m["previous_collections"])
    concentration = _compact_rows(data["tables"]["top_ar"], 2)
    top_ar = ", ".join(f"{r['name']} ({_short_money(r['amount'])})" for r in concentration) or "sin concentración visible"
    top_collections = ", ".join(
        f"{r['name']} ({_short_money(r['amount'])})" for r in _compact_rows(data["tables"]["top_collections"], 3)
    ) or "sin recuperaciones registradas"

    billing_sentence = (
        "no cuenta con comparativo del mes anterior"
        if billing_pct is None else f"vario {billing_pct:+.1f}% contra el mes anterior"
    )
    collections_sentence = (
        "no cuenta con comparativo del mes anterior"
        if collections_pct is None else f"vario {collections_pct:+.1f}% contra el mes anterior"
    )
    risk_level = "controlado" if m["next_net_outlook"] >= 0 and m["ar_open"] >= m["payables_open"] else "sensible"

    return {
        "introduction": (
            f"El presente análisis evalúa la situación financiera, comercial y operativa de la compañía al cierre de "
            f"{p['label']}, considerando facturación, recuperación de cartera, cuentas por cobrar, cuentas por pagar, "
            f"liquidez operativa y riesgos asociados a la continuidad del negocio.\n\n"
            f"Durante el período se registraron {_money(m['revenue'])} en facturación y {_money(m['collections'])} "
            f"en cobranzas. El resultado debe leerse junto con una cartera abierta de {_money(m['ar_open'])} y "
            f"obligaciones pendientes por {_money(m['payables_open'])}, lo cual permite dimensionar la capacidad "
            f"de caja y la presión operativa de corto plazo."
        ),
        "collections": (
            f"Con base en los resultados de cobranza del período, se recuperaron {_money(m['collections'])} en "
            f"{m['collections_count']} registros de pago. Las principales contribuciones fueron {top_collections}.\n\n"
            f"La cobranza {collections_sentence}. Este comportamiento refleja la efectividad del seguimiento de cartera "
            f"y permite identificar si la liquidez depende de pocos clientes o de una base mas diversificada."
        ),
        "receivables": (
            f"Las cuentas por cobrar abiertas ascienden a {_money(m['ar_open'])} distribuidas en {m['ar_count']} facturas. "
            f"Los principales saldos se concentran en {top_ar}.\n\n"
            f"Esta composición permite priorizar gestiones de alto impacto. Mientras mayor sea la concentración en pocos "
            f"clientes, mayor debe ser la disciplina de seguimiento, confirmación de fechas de pago y control de riesgo crediticio."
        ),
        "payment_trend": (
            f"La tendencia de pago se evalúa con base en la antigüedad entre emisión de factura y recuperación. "
            f"El promedio observado para el período es "
            f"{m['avg_days_to_pay']:.1f} dias." if m["avg_days_to_pay"] is not None else
            "La tendencia de pago no cuenta con información suficiente para calcular un promedio confiable en este período."
        ),
        "billing": (
            f"La facturación de {p['label']} alcanzó {_money(m['revenue'])} en {m['revenue_count']} facturas y "
            f"{billing_sentence}. Este indicador muestra el pulso comercial del mes y permite evalúar si la compañía "
            f"mantiene suficiente generacion de ingresos para sostener su estructura operativa.\n\n"
            f"Cuando la facturación se desacelera, la compañía queda mas expuesta a la recuperación de cartera previa. "
            f"Por ello, el análisis debe observar simultaneamente ventas, cobros y cuentas por pagar."
        ),
        "payables": (
            f"Las cuentas por pagar abiertas al cierre ascienden a {_money(m['payables_open'])}, mientras que los pagos "
            f"registrados durante el período suman {_money(m['itp_paid'])}. Esta estructura evidencia la carga de "
            f"compromisos que debe administrarse frente a la caja recuperada.\n\n"
            f"Los rubros de mayor peso deben revisarse por recurrencia, necesidad operativa y posibilidad de negociacion "
            f"sin afectar la calidad del servicio."
        ),
        "next_month_outlook": (
            f"Para {p['next_label']}, la vista prospectiva muestra {_money(m['next_receivables'])} en cuentas por cobrar "
            f"esperadas por vencimiento y {_money(m['next_payables'])} en cuentas por pagar programadas. El resultado neto "
            f"proyectado es {_money(m['next_net_outlook'])} antes de nuevas facturas, cobros adicionales o ajustes posteriores.\n\n"
            f"Este outlook debe utilizarse como agenda de caja: priorizar cobros de mayor impacto, confirmar promesas de pago "
            f"y calendarizar obligaciones para evitar presión innecesaria al inicio del mes."
        ),
        "year_comparison": (
            f"El comparativo anual permite ubicar el desempeno de {p['label']} frente al comportamiento historico reciente. "
            f"La lectura principal es identificar si el mes responde a una tendencia sostenida, una recuperación puntual o "
            f"una desaceleracion que requiera acciones comerciales.\n\n"
            f"El seguimiento mensual debe enfocarse en volumen facturado, cantidad de operaciones, ticket promedio y "
            f"concentración por cliente."
        ),
        "risk": (
            f"El riesgo financiero actual se considera {risk_level}. La compañía debe observar tres factores: dependencia "
            f"de recuperación de cartera, concentración de ingresos en pocos clientes y compromisos fijos que consumen caja "
            f"de forma recurrente.\n\n"
            f"Cualquier atraso material en cobranza puede reducir el margen de maniobra. Por tanto, se recomienda mantener "
            f"contencion de gastos no esenciales y seguimiento semanal de cartera y obligaciones."
        ),
        "conclusion": (
            f"El cierre de {p['label']} muestra una posición que debe gestionarse con disciplina: la estabilidad depende de "
            f"convertir cuentas por cobrar en efectivo, sostener la facturación y calendarizar adecuadamente los pagos.\n\n"
            f"La recomendación ejecutiva es reforzar el seguimiento de clientes relevantes, proteger caja, evitar compromisos "
            f"no esenciales y utilizar el outlook de {p['next_label']} como base de planificación financiera."
        ),
    }


def _safe_filename(label, extension):
    return f"MSL_Financial_Report_{label.replace(' ', '_').replace(',', '')}.{extension}"


def _chart_image(rows, title, path, kind="bar"):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return None

    rows = [r for r in (rows or []) if _f(r.get("total")) > 0][:7]
    width, height = 900, 430
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    try:
        title_font = ImageFont.truetype("arial.ttf", 28)
        label_font = ImageFont.truetype("arial.ttf", 17)
        small_font = ImageFont.truetype("arial.ttf", 15)
    except Exception:
        title_font = label_font = small_font = None

    draw.text((30, 22), title, fill=DARK, font=title_font)
    draw.line((30, 64, width - 30, 64), fill="#D9E2EC", width=2)
    if not rows:
        draw.text((330, 205), "No records for this period", fill="#697386", font=label_font)
        img.save(path)
        return path

    if kind == "pie":
        total = sum(_f(r.get("total")) for r in rows) or 1
        start_angle = 0
        box = (70, 105, 360, 395)
        for idx, row in enumerate(rows):
            amount = _f(row.get("total"))
            angle = amount / total * 360
            draw.pieslice(box, start=start_angle, end=start_angle + angle, fill=CHART_COLORS[idx % len(CHART_COLORS)])
            start_angle += angle
        legend_x = 430
        for idx, row in enumerate(rows):
            y = 115 + idx * 38
            draw.rectangle((legend_x, y, legend_x + 22, y + 22), fill=CHART_COLORS[idx % len(CHART_COLORS)])
            pct = _f(row.get("total")) / total * 100
            label = str(row.get("nombre_cliente") or "N/A")[:28]
            draw.text((legend_x + 32, y - 1), f"{label} - {pct:.1f}% - {_short_money(row.get('total'))}", fill=DARK, font=small_font)
    else:
        max_value = max(_f(r.get("total")) for r in rows) or 1
        chart_left, chart_top, chart_right, bar_h = 260, 96, 830, 30
        for idx, row in enumerate(rows):
            y = chart_top + idx * 45
            label = str(row.get("nombre_cliente") or "N/A")[:24]
            draw.text((35, y + 5), label, fill=DARK, font=small_font)
            bar_w = int((_f(row.get("total")) / max_value) * (chart_right - chart_left))
            color = CHART_COLORS[idx % len(CHART_COLORS)]
            draw.rounded_rectangle((chart_left, y, chart_left + bar_w, y + bar_h), radius=6, fill=color)
            draw.text((chart_left + bar_w + 10, y + 5), _short_money(row.get("total")), fill=DARK, font=small_font)
        draw.line((chart_left, chart_top - 10, chart_left, chart_top + len(rows) * 45), fill="#BCCCDC", width=1)
    img.save(path)
    return path


def _build_charts(data, tmp_dir):
    tables = data["tables"]
    charts = {
        "collections": _chart_image(tables["top_collections"], "Distribución de cuentas por cobrar recuperadas", os.path.join(tmp_dir, "collections.png"), "pie"),
        "ar": _chart_image(tables["top_ar"], "Cuentas por cobrar a recuperar", os.path.join(tmp_dir, "ar.png"), "bar"),
        "ar_aging": _chart_image(tables["ar_aging"], "Antigüedad de cuentas por cobrar", os.path.join(tmp_dir, "ar_aging.png"), "bar"),
        "payment_trend": _chart_image(tables["payment_trend"], "Tendencia de pago por antigüedad", os.path.join(tmp_dir, "payment_trend.png"), "bar"),
        "billing": _chart_image(tables["billing_trend"], "Facturación mensual", os.path.join(tmp_dir, "billing.png"), "bar"),
        "payables": _chart_image(tables["top_payables_open"], "Cuentas por pagar", os.path.join(tmp_dir, "payables.png"), "pie"),
        "next_ar": _chart_image(tables["top_next_receivables"], "Cobros esperados próximo mes", os.path.join(tmp_dir, "next_ar.png"), "bar"),
        "next_payables": _chart_image(tables["top_next_payables"], "Pagos programados próximo mes", os.path.join(tmp_dir, "next_payables.png"), "bar"),
    }
    return charts


def generate_monthly_financial_pdf(conn, year: int, month: int):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    data = build_monthly_financial_data(conn, year, month)
    label = data["period"]["label"]
    tmp_dir = tempfile.mkdtemp(prefix="erp_som_financial_report_")
    charts = _build_charts(data, tmp_dir)
    path = os.path.join(tmp_dir, _safe_filename(label, "pdf"))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverCompany", parent=styles["Title"], fontSize=30, textColor=colors.HexColor(BLUE), leading=36, alignment=1))
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontSize=24, textColor=colors.HexColor(DARK), leading=30, alignment=1))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], textColor=colors.HexColor(BLUE), fontSize=18, spaceBefore=8, spaceAfter=10))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=10.8, leading=16, spaceAfter=10))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8.5, leading=11, textColor=colors.HexColor("#52606D")))

    story = []
    story.extend(_pdf_cover(data, styles))
    story.append(PageBreak())
    _pdf_section(story, styles, "Introducción ejecutiva", data["narrative"]["introduction"], None, data)
    _pdf_section(story, styles, "Collections Recovery", data["narrative"]["collections"], charts["collections"], data, data["tables"]["top_collections"])
    _pdf_section(story, styles, "Cuentas por cobrar a recuperar", data["narrative"]["receivables"], charts["ar"], data, data["tables"]["top_ar"])
    _pdf_section(story, styles, "Antigüedad de cartera", "La siguiente distribución permite separar cartera vigente de saldos vencidos y priorizar gestiones según impacto y antigüedad.", charts["ar_aging"], data, data["tables"]["ar_aging"])
    _pdf_section(story, styles, "Tendencia de pago", data["narrative"]["payment_trend"], charts["payment_trend"], data, data["tables"]["payment_trend"])
    _pdf_section(story, styles, "Facturación", data["narrative"]["billing"], charts["billing"], data, data["tables"]["top_billing"])
    _pdf_section(story, styles, "Cuentas por pagar", data["narrative"]["payables"], charts["payables"], data, data["tables"]["top_payables_open"])
    _pdf_section(story, styles, f"Cronograma y outlook - {data['period']['next_label']}", data["narrative"]["next_month_outlook"], charts["next_ar"], data, data["tables"]["top_next_receivables"], extra_chart=charts["next_payables"])
    _pdf_section(story, styles, f"Comparativo {year - 1} vs {year}", data["narrative"]["year_comparison"], None, data, _comparison_rows(data))
    _pdf_section(story, styles, "Análisis de riesgo financiero", data["narrative"]["risk"], None, data)
    _pdf_section(story, styles, "Conclusion reporte financiero", data["narrative"]["conclusion"], None, data)

    doc = SimpleDocTemplate(path, pagesize=LETTER, rightMargin=50, leftMargin=50, topMargin=46, bottomMargin=42)
    doc.build(story)
    return path, _safe_filename(label, "pdf")


def _pdf_cover(data, styles):
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors

    p = data["period"]
    return [
        Spacer(1, 120),
        Paragraph("Marine Surveyors &<br/>Logistics", styles["CoverCompany"]),
        Spacer(1, 18),
        Paragraph("Alajuela, Costa Rica", styles["Body"]),
        Spacer(1, 75),
        Paragraph(escape(p["report_label"]), styles["CoverTitle"]),
        Spacer(1, 70),
        _pdf_kpi_table(data),
        Spacer(1, 70),
        Paragraph("Aarón Ávila Vargas", styles["Body"]),
    ]


def _pdf_kpi_table(data):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    m = data["metrics"]
    rows = [
        ["Facturación", "Cobranza", "Cartera", "CxP", "Outlook neto"],
        [_short_money(m["revenue"]), _short_money(m["collections"]), _short_money(m["ar_open"]), _short_money(m["payables_open"]), _short_money(m["next_net_outlook"])],
    ]
    table = Table(rows, colWidths=[92, 92, 92, 92, 92])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor(GREY)),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7DEE8")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _pdf_section(story, styles, title, text, chart_path, data, table_rows=None, extra_chart=None):
    from reportlab.platypus import Image, PageBreak, Paragraph, Spacer

    story.append(Paragraph(escape(title), styles["Section"]))
    for paragraph in str(text or "").split("\n\n"):
        if paragraph.strip():
            story.append(Paragraph(escape(paragraph.strip()), styles["Body"]))
    if chart_path and os.path.exists(chart_path):
        story.append(Spacer(1, 6))
        story.append(Image(chart_path, width=475, height=227))
    if extra_chart and os.path.exists(extra_chart):
        story.append(Spacer(1, 8))
        story.append(Image(extra_chart, width=475, height=227))
    if table_rows is not None:
        story.append(Spacer(1, 8))
        story.append(_pdf_table(table_rows))
    story.append(PageBreak())


def _pdf_table(rows):
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    table_data = [["Detalle", "Monto"]]
    for row in rows or []:
        table_data.append([str(row.get("nombre_cliente") or row.get("name") or "N/A"), _money(row.get("total") or row.get("amount"))])
    if len(table_data) == 1:
        table_data.append(["No records for this period", "USD 0.00"])
    table = Table(table_data, colWidths=[330, 130])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LIGHT_BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7DEE8")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _comparison_rows(data):
    rows = []
    current = {int(r.get("month_num") or 0): _f(r.get("total")) for r in data["tables"]["current_year_trend"]}
    previous = {int(r.get("month_num") or 0): _f(r.get("total")) for r in data["tables"]["prev_year_trend"]}
    for month_num in sorted(set(current) | set(previous)):
        month_name = calendar.month_abbr[month_num]
        rows.append({
            "nombre_cliente": month_name,
            "total": current.get(month_num, 0) - previous.get(month_num, 0),
        })
    return rows


def generate_monthly_financial_docx(conn, year: int, month: int):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    data = build_monthly_financial_data(conn, year, month)
    label = data["period"]["label"]
    tmp_dir = tempfile.mkdtemp(prefix="erp_som_financial_report_")
    charts = _build_charts(data, tmp_dir)
    path = os.path.join(tmp_dir, _safe_filename(label, "docx"))

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.65)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Marine Surveyors &\nLogistics")
    run.bold = True
    run.font.size = Pt(26)
    run.font.color.rgb = RGBColor(18, 58, 99)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(data["period"]["report_label"])
    run.bold = True
    run.font.size = Pt(18)

    doc.add_paragraph("Alajuela, Costa Rica").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph("Aarón Ávila Vargas").alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_page_break()

    _docx_section(doc, "Introducción ejecutiva", data["narrative"]["introduction"])
    _docx_section(doc, "Collections Recovery", data["narrative"]["collections"], charts["collections"], data["tables"]["top_collections"])
    _docx_section(doc, "Cuentas por cobrar a recuperar", data["narrative"]["receivables"], charts["ar"], data["tables"]["top_ar"])
    _docx_section(doc, "Antigüedad de cartera", "Distribución de cartera por antigüedad para priorizar recuperación.", charts["ar_aging"], data["tables"]["ar_aging"])
    _docx_section(doc, "Tendencia de pago", data["narrative"]["payment_trend"], charts["payment_trend"], data["tables"]["payment_trend"])
    _docx_section(doc, "Facturación", data["narrative"]["billing"], charts["billing"], data["tables"]["top_billing"])
    _docx_section(doc, "Cuentas por pagar", data["narrative"]["payables"], charts["payables"], data["tables"]["top_payables_open"])
    _docx_section(doc, f"Cronograma y outlook - {data['period']['next_label']}", data["narrative"]["next_month_outlook"], charts["next_ar"], data["tables"]["top_next_receivables"])
    if charts["next_payables"] and os.path.exists(charts["next_payables"]):
        doc.add_picture(charts["next_payables"], width=Inches(6.4))
    _docx_section(doc, f"Comparativo {year - 1} vs {year}", data["narrative"]["year_comparison"], None, _comparison_rows(data))
    _docx_section(doc, "Análisis de riesgo financiero", data["narrative"]["risk"])
    _docx_section(doc, "Conclusion reporte financiero", data["narrative"]["conclusion"])

    doc.save(path)
    return path, _safe_filename(label, "docx")


def _docx_section(doc, title, text, chart_path=None, rows=None):
    from docx.shared import Inches

    doc.add_heading(title, level=1)
    for paragraph in str(text or "").split("\n\n"):
        if paragraph.strip():
            doc.add_paragraph(paragraph.strip())
    if chart_path and os.path.exists(chart_path):
        doc.add_picture(chart_path, width=Inches(6.4))
    if rows is not None:
        _docx_table(doc, rows)
    doc.add_page_break()


def _docx_table(doc, rows):
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Detalle"
    table.rows[0].cells[1].text = "Monto"
    if rows:
        for row in rows:
            cells = table.add_row().cells
            cells[0].text = str(row.get("nombre_cliente") or row.get("name") or "N/A")
            cells[1].text = _money(row.get("total") or row.get("amount"))
    else:
        cells = table.add_row().cells
        cells[0].text = "No records for this period"
        cells[1].text = "USD 0.00"
