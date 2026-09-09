from datetime import date
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from tkinter import filedialog, messagebox
import tempfile
import shutil
import os
from branding import company_display_name, footer_text, logo_asset, watermark_asset
from Modulos.Finanzas.date_utils import to_long_english_date


# ============================================================
# HEADER / FOOTER
# ============================================================
def _draw_header_footer(canvas, doc, branding_data=None):
    width, height = landscape(LETTER)
    branding_data = branding_data or {}
    header_path = logo_asset(branding_data)
    watermark_path = watermark_asset(branding_data)

    if header_path and os.path.exists(header_path):
        canvas.drawImage(
            header_path,
            x=40,
            y=height - 120,
            width=160,
            preserveAspectRatio=True,
            mask="auto"
        )

    if watermark_path and os.path.exists(watermark_path):
        canvas.saveState()
        canvas.setFillAlpha(0.1)
        canvas.drawImage(
            watermark_path,
            x=width / 2 - 200,
            y=height / 2 - 200,
            width=400,
            preserveAspectRatio=True,
            mask="auto"
        )
        canvas.restoreState()

    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(width / 2, 40, " - ".join(footer_text(branding_data).splitlines()))


# ============================================================
# GENERAR ESTADO DE CUENTA PDF (HORIZONTAL – REPLICA WORD)
# ============================================================
def generar_estado_cuenta_pdf(
    idioma,
    cliente,
    resumen_kpis,
    facturas,
    datos_bancarios,
    company_code=None,
    company_name=None,
):

    hoy = to_long_english_date(date.today())
    branding_data = {"company_code": company_code, "company_name": company_name}
    display_company = company_display_name(branding_data)

    filename = f"Estado_Cuenta_{cliente}_{hoy}.pdf"
    path = filedialog.asksaveasfilename(
        initialfile=filename,
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")]
    )

    if not path:
        return False

    try:
        temp_dir = os.path.dirname(path)
        with tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix=".pdf") as tmp:
            temp_path = tmp.name

        doc = SimpleDocTemplate(
            temp_path,
            pagesize=landscape(LETTER),
            leftMargin=40,
            rightMargin=40,
            topMargin=120,
            bottomMargin=70
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="Body", fontSize=10, leading=14))
        styles.add(ParagraphStyle(name="InvoiceNumber", fontSize=7, leading=8))

        elements = []

        total_ar = resumen_kpis["total_ar"]
        overdue = resumen_kpis["overdue"]

        if idioma == "ES":
            body = (
                f"Estimado/a {cliente},<br/><br/>"
                f"<b>Asunto:</b> Estado de cuenta {display_company} – Cliente {cliente} – {hoy}<br/><br/>"
                f"Por medio del presente le compartimos el estado de cuenta al día de hoy, "
                f"el cual refleja un balance adeudado total de {total_ar:,.2f}, "
                f"de los cuales {overdue:,.2f} se encuentran vencidos.<br/><br/>"
                f"El balance se compone de la siguiente manera:"
            )
        else:
            body = (
                f"Dear {cliente},<br/><br/>"
                f"<b>Subject:</b> Statement of Account {display_company} – Client {cliente} – {hoy}<br/><br/>"
                f"Please find below the statement of account as of today, reflecting a total "
                f"outstanding balance of {total_ar:,.2f}, of which {overdue:,.2f} are overdue.<br/><br/>"
                f"Breakdown of outstanding balance:"
            )

        elements.append(Paragraph(body, styles["Body"]))
        elements.append(Spacer(1, 12))

        for k, v in resumen_kpis["buckets"].items():
            elements.append(Paragraph(f"{k}: {v:,.2f}", styles["Body"]))

        elements.append(Spacer(1, 16))

        elements.append(
            Paragraph(
                "Datos bancarios:" if idioma == "ES" else "Bank details:",
                styles["Body"]
            )
        )

        for k, v in datos_bancarios.items():
            if v:
                elements.append(Paragraph(f"{k}: {v}", styles["Body"]))

        elements.append(Spacer(1, 16))

        # ================= TABLA =================
        table_data = [[
            "Número Documento",
            "Fecha Emisión",
            "Fecha Vencimiento",
            "Aging",
            "Total",
            "Buque",
            "Operación",
            "Num. Informe"
        ]]

        for f in facturas:
            table_data.append([
                Paragraph(str(f.get("numero_documento") or ""), styles["InvoiceNumber"]),
                to_long_english_date(f.get("fecha_emision", "")),
                to_long_english_date(f.get("fecha_vencimiento", "")),
                f.get("aging_dias", ""),
                f"{float(f.get('total') or 0):,.2f}",
                f.get("buque_contenedor", ""),
                f.get("operacion", ""),
                f.get("num_informe", "")
            ])

        available_width = doc.width

        col_widths = [
            available_width * 0.23,
            available_width * 0.12,
            available_width * 0.12,
            available_width * 0.06,
            available_width * 0.10,
            available_width * 0.12,
            available_width * 0.12,
            available_width * 0.14,
        ]

        table = Table(table_data, repeatRows=1, colWidths=col_widths)

        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (3, 1), (4, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))

        elements.append(table)

        doc.build(
            elements,
            onFirstPage=lambda canvas, doc: _draw_header_footer(canvas, doc, branding_data),
            onLaterPages=lambda canvas, doc: _draw_header_footer(canvas, doc, branding_data),
        )

        shutil.move(temp_path, path)

        messagebox.showinfo(
            "Estado de cuenta",
            "Estado de cuenta generado correctamente."
        )
        return True

    except Exception as e:
        messagebox.showerror(
            "Error",
            f"No se pudo generar el estado de cuenta.\n\n{e}"
        )
        return False
