import calendar
import os
import tempfile
from datetime import date, timedelta
from decimal import Decimal

from psycopg2.extras import RealDictCursor


BLUE = "#123A63"
LIGHT_BLUE = "#E8F0F8"
GREY = "#F4F6F8"


def _period_bounds(year: int, month: int):
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    if month == 1:
        prev_start = date(year - 1, 12, 1)
    else:
        prev_start = date(year, month - 1, 1)
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
    return f"${_f(value):,.2f}"


def _pct(current, previous):
    previous = _f(previous)
    current = _f(current)
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100.0


def _trend_sentence(label, current, previous):
    pct = _pct(current, previous)
    if pct is None:
        if _f(current) > 0:
            return f"{label} recorded {_money(current)} with no comparable value in the previous month."
        return f"{label} did not register activity during the month."
    direction = "increased" if pct >= 0 else "decreased"
    return f"{label} {direction} by {abs(pct):.1f}% versus the previous month, moving from {_money(previous)} to {_money(current)}."


def _fetch_one(cur, sql, params):
    cur.execute(sql, params)
    row = cur.fetchone() or {}
    return row


def _fetch_all(cur, sql, params):
    cur.execute(sql, params)
    return cur.fetchall() or []


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

    collections = _fetch_one(cur, """
        WITH payments AS (
            SELECT ca.codigo_cliente, ca.nombre_cliente, ca.fecha_pago, ca.monto_pagado AS amount
            FROM cash_app ca
            WHERE ca.monto_pagado > 0 AND ca.tipo_aplicacion = 'PAGO'
            UNION ALL
            SELECT ip.codigo_cliente, ip.nombre_cliente, ip.fecha_pago, ip.monto AS amount
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
        SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
        FROM payments
        WHERE fecha_pago BETWEEN %s AND %s
    """, (start, end))

    prev_collections = _fetch_one(cur, """
        WITH payments AS (
            SELECT ca.codigo_cliente, ca.nombre_cliente, ca.fecha_pago, ca.monto_pagado AS amount
            FROM cash_app ca
            WHERE ca.monto_pagado > 0 AND ca.tipo_aplicacion = 'PAGO'
            UNION ALL
            SELECT ip.codigo_cliente, ip.nombre_cliente, ip.fecha_pago, ip.monto AS amount
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
        SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count
        FROM payments
        WHERE fecha_pago BETWEEN %s AND %s
    """, (prev_start, prev_end))

    ar = _fetch_one(cur, """
        SELECT
            COALESCE(SUM(saldo_pendiente), 0) AS total,
            COUNT(*) AS count
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
        LIMIT 5
    """, (end,))

    top_collections = _fetch_all(cur, """
        WITH payments AS (
            SELECT ca.codigo_cliente, ca.nombre_cliente, ca.fecha_pago, ca.monto_pagado AS amount
            FROM cash_app ca
            WHERE ca.monto_pagado > 0 AND ca.tipo_aplicacion = 'PAGO'
            UNION ALL
            SELECT ip.codigo_cliente, ip.nombre_cliente, ip.fecha_pago, ip.monto AS amount
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
        SELECT nombre_cliente, COALESCE(SUM(amount), 0) AS total
        FROM payments
        WHERE fecha_pago BETWEEN %s AND %s
        GROUP BY nombre_cliente
        ORDER BY total DESC
        LIMIT 5
    """, (start, end))

    itp_paid = _fetch_one(cur, """
        SELECT COALESCE(SUM(
            CASE WHEN currency = 'CRC' THEN (total - balance) / 500.0 ELSE (total - balance) END
        ), 0) AS total, COUNT(*) AS count
        FROM payment_obligations
        WHERE status IN ('PAID','PARTIAL')
          AND last_payment_date BETWEEN %s AND %s
    """, (start, end))

    itp_next = _fetch_one(cur, """
        SELECT COALESCE(SUM(
            CASE WHEN currency = 'CRC' THEN balance / 500.0 ELSE balance END
        ), 0) AS total, COUNT(*) AS count
        FROM payment_obligations
        WHERE status IN ('PENDING','PARTIAL')
          AND due_date BETWEEN %s AND %s
    """, (next_start, next_end))

    avg_days = _fetch_one(cur, """
        SELECT ROUND(AVG(ca.fecha_pago::date - i.fecha_emision::date), 1) AS days
        FROM cash_app ca
        JOIN invoicing i
          ON ltrim(i.numero_documento, '0') = ltrim(ca.numero_documento, '0')
         AND i.codigo_cliente = ca.codigo_cliente
         AND i.tipo_documento = 'FACTURA'
        WHERE ca.monto_pagado > 0
          AND ca.fecha_pago BETWEEN %s AND %s
    """, (start, end))

    top_billing = _fetch_all(cur, """
        SELECT nombre_cliente, COALESCE(SUM(total), 0) AS total
        FROM invoicing
        WHERE tipo_documento = 'FACTURA'
          AND fecha_emision BETWEEN %s AND %s
        GROUP BY nombre_cliente
        ORDER BY total DESC
        LIMIT 5
    """, (start, end))

    cur.close()

    revenue_total = _f(revenue.get("total"))
    prev_revenue_total = _f(prev_revenue.get("total"))
    collections_total = _f(collections.get("total"))
    prev_collections_total = _f(prev_collections.get("total"))
    itp_total = _f(itp_paid.get("total"))
    ar_total = _f(ar.get("total"))
    net_cash = collections_total - itp_total
    month_name = calendar.month_name[month]
    prev_month_name = calendar.month_name[prev_start.month]
    next_month_name = calendar.month_name[next_start.month]

    if net_cash >= 0:
        liquidity_text = f"The month closed with a positive operating cash movement of {_money(net_cash)} after comparing collections against recorded payments."
    else:
        liquidity_text = f"The month closed with a negative operating cash movement of {_money(abs(net_cash))}; short-term disbursements exceeded recovered cash."

    if ar_total > revenue_total and revenue_total > 0:
        ar_text = "Accounts receivable remain above the month billing volume, so collection follow-up should stay as a priority."
    elif ar_total > 0:
        ar_text = "Accounts receivable remain active but are within a manageable range compared with monthly billing."
    else:
        ar_text = "No open accounts receivable were identified at the report cut-off."

    days = avg_days.get("days")
    if days is None:
        trend_text = "Payment-cycle data was not sufficient to calculate an average invoice-to-payment trend for the month."
    elif _f(days) <= 60:
        trend_text = f"Average invoice-to-payment timing was {_f(days):.1f} days, within the target 30-60 day recovery window."
    else:
        trend_text = f"Average invoice-to-payment timing was {_f(days):.1f} days, above the target 30-60 day recovery window."

    return {
        "period": {
            "year": year,
            "month": month,
            "month_name": month_name,
            "label": f"{month_name} {year}",
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
            "next_payables": _f(itp_next.get("total")),
            "next_payables_count": int(itp_next.get("count") or 0),
            "net_cash": net_cash,
            "avg_days_to_pay": _f(days) if days is not None else None,
        },
        "tables": {
            "top_ar": [dict(r) for r in top_ar],
            "top_collections": [dict(r) for r in top_collections],
            "top_billing": [dict(r) for r in top_billing],
        },
        "narrative": {
            "summary": (
                f"{month_name} {year} generated {_money(revenue_total)} in invoices and recovered "
                f"{_money(collections_total)} in collections. "
                f"{_trend_sentence('Billing', revenue_total, prev_revenue_total)} "
                f"{_trend_sentence('Collections', collections_total, prev_collections_total)} "
                f"{liquidity_text}"
            ),
            "collections": (
                f"Collections for {month_name} totaled {_money(collections_total)} across "
                f"{int(collections.get('count') or 0)} recorded payment entries. "
                f"Open receivables at the cut-off total {_money(ar_total)} across {int(ar.get('count') or 0)} invoices. "
                f"{ar_text}"
            ),
            "payment_trend": trend_text,
            "billing": (
                f"Invoice issuance reached {_money(revenue_total)} from {int(revenue.get('count') or 0)} invoices. "
                f"The previous comparable month, {prev_month_name} {prev_start.year}, recorded {_money(prev_revenue_total)}."
            ),
            "payables": (
                f"Invoice-to-pay disbursements recorded during the month totaled {_money(itp_total)}. "
                f"The next month schedule currently shows {_money(_f(itp_next.get('total')))} pending across "
                f"{int(itp_next.get('count') or 0)} obligations."
            ),
            "conclusion": (
                f"The financial position for {month_name} {year} should be read around three controls: "
                f"cash recovered ({_money(collections_total)}), new billing ({_money(revenue_total)}), "
                f"and open receivables ({_money(ar_total)}). "
                f"{'The month supports a positive liquidity stance.' if net_cash >= 0 else 'The month requires tighter cash scheduling.'} "
                f"Management should continue monitoring collections concentration and the next-month payment calendar."
            ),
        },
    }


def _safe_filename(label, extension):
    return f"MSL_Financial_Report_{label.replace(' ', '_')}.{extension}"


def generate_monthly_financial_pdf(conn, year: int, month: int):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

    data = build_monthly_financial_data(conn, year, month)
    label = data["period"]["label"]
    tmp_dir = tempfile.mkdtemp(prefix="erp_som_financial_report_")
    path = os.path.join(tmp_dir, _safe_filename(label, "pdf"))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontSize=28, textColor=colors.HexColor(BLUE), leading=32))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], textColor=colors.HexColor(BLUE), spaceBefore=16, spaceAfter=8))
    styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=10.5, leading=15, spaceAfter=8))

    story = [
        Spacer(1, 120),
        Paragraph("Marine Surveyors & Logistics", styles["CoverTitle"]),
        Paragraph(f"Financial Report - {label}", styles["Title"]),
        Spacer(1, 24),
        Paragraph("Monthly financial performance, collections recovery, invoicing, payables schedule and management conclusions.", styles["Body"]),
        PageBreak(),
    ]

    _append_pdf_section(story, styles, "Monthly Summary", data["narrative"]["summary"])
    _append_pdf_kpis(story, data)
    _append_pdf_section(story, styles, "Collections Recovery", data["narrative"]["collections"])
    _append_pdf_table(story, "Top Collections", data["tables"]["top_collections"])
    _append_pdf_section(story, styles, "Payment Trend", data["narrative"]["payment_trend"])
    _append_pdf_section(story, styles, "Invoice & Billing", data["narrative"]["billing"])
    _append_pdf_table(story, "Top Billing Clients", data["tables"]["top_billing"])
    _append_pdf_section(story, styles, "Invoice To Pay", data["narrative"]["payables"])
    _append_pdf_table(story, "Open Accounts Receivable", data["tables"]["top_ar"])
    _append_pdf_section(story, styles, "Financial Report Conclusions", data["narrative"]["conclusion"])

    doc = SimpleDocTemplate(path, pagesize=LETTER, rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54)
    doc.build(story)
    return path, _safe_filename(label, "pdf")


def _append_pdf_section(story, styles, title, text):
    from reportlab.platypus import Paragraph

    story.append(Paragraph(title, styles["Section"]))
    story.append(Paragraph(text, styles["Body"]))


def _append_pdf_kpis(story, data):
    from reportlab.lib import colors
    from reportlab.platypus import Spacer, Table, TableStyle

    metrics = data["metrics"]
    rows = [
        ["Metric", "Amount"],
        ["Billing", _money(metrics["revenue"])],
        ["Collections", _money(metrics["collections"])],
        ["Open AR", _money(metrics["ar_open"])],
        ["Payments", _money(metrics["itp_paid"])],
        ["Net cash movement", _money(metrics["net_cash"])],
    ]
    table = Table(rows, colWidths=[260, 160])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7DEE8")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor(GREY)),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))


def _append_pdf_table(story, title, rows):
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

    story.append(Paragraph(title, getSampleStyleSheet()["Heading2"]))
    table_data = [["Client", "Amount"]]
    if rows:
        for row in rows:
            table_data.append([str(row.get("nombre_cliente") or "N/A"), _money(row.get("total"))])
    else:
        table_data.append(["No records for this period", "0.00"])
    table = Table(table_data, colWidths=[310, 110])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(LIGHT_BLUE)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7DEE8")),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 8))


def generate_monthly_financial_docx(conn, year: int, month: int):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    data = build_monthly_financial_data(conn, year, month)
    label = data["period"]["label"]
    tmp_dir = tempfile.mkdtemp(prefix="erp_som_financial_report_")
    path = os.path.join(tmp_dir, _safe_filename(label, "docx"))

    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.8)
    section.right_margin = Inches(0.8)

    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("Marine Surveyors & Logistics")
    run.bold = True
    run.font.size = Pt(24)
    run.font.color.rgb = RGBColor(18, 58, 99)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(f"Financial Report - {label}")
    run.bold = True
    run.font.size = Pt(16)

    doc.add_paragraph("Monthly financial performance, collections recovery, invoicing, payables schedule and management conclusions.")
    doc.add_page_break()

    _docx_section(doc, "Monthly Summary", data["narrative"]["summary"])
    _docx_kpis(doc, data)
    _docx_section(doc, "Collections Recovery", data["narrative"]["collections"])
    _docx_table(doc, "Top Collections", data["tables"]["top_collections"])
    _docx_section(doc, "Payment Trend", data["narrative"]["payment_trend"])
    _docx_section(doc, "Invoice & Billing", data["narrative"]["billing"])
    _docx_table(doc, "Top Billing Clients", data["tables"]["top_billing"])
    _docx_section(doc, "Invoice To Pay", data["narrative"]["payables"])
    _docx_table(doc, "Open Accounts Receivable", data["tables"]["top_ar"])
    _docx_section(doc, "Financial Report Conclusions", data["narrative"]["conclusion"])

    doc.save(path)
    return path, _safe_filename(label, "docx")


def _docx_section(doc, title, text):
    p = doc.add_heading(title, level=1)
    for run in p.runs:
        run.font.color.rgb = None
    doc.add_paragraph(text)


def _docx_kpis(doc, data):
    metrics = data["metrics"]
    rows = [
        ("Billing", _money(metrics["revenue"])),
        ("Collections", _money(metrics["collections"])),
        ("Open AR", _money(metrics["ar_open"])),
        ("Payments", _money(metrics["itp_paid"])),
        ("Net cash movement", _money(metrics["net_cash"])),
    ]
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Metric"
    table.rows[0].cells[1].text = "Amount"
    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = value
    doc.add_paragraph()


def _docx_table(doc, title, rows):
    doc.add_heading(title, level=2)
    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Client"
    table.rows[0].cells[1].text = "Amount"
    if rows:
        for row in rows:
            cells = table.add_row().cells
            cells[0].text = str(row.get("nombre_cliente") or "N/A")
            cells[1].text = _money(row.get("total"))
    else:
        cells = table.add_row().cells
        cells[0].text = "No records for this period"
        cells[1].text = "0.00"
    doc.add_paragraph()
