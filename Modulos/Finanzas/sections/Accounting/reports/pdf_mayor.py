from typing import Any, List
from tkinter import filedialog

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors

from Modulos.Finanzas.sections.Accounting.reports.build_mayor_from_lines import (
    build_mayor_from_lines
)


def export_mayor_pdf_from_lines(rows_or_built: Any):
    """
    Exporta Libro Mayor a PDF

    ✔ MISMA lógica visual que el Excel
    ✔ Flujo continuo
    ✔ Save As interno
    ✔ SIN company_code
    ✔ Style 100% blindado (NO colisiones)
    """

    # ==================================================
    # NORMALIZACIÓN
    # ==================================================
    if isinstance(rows_or_built, list):
        mayor = build_mayor_from_lines(rows_or_built)
    elif isinstance(rows_or_built, dict):
        mayor = rows_or_built
    else:
        raise ValueError("export_mayor_pdf_from_lines esperaba dict o list")

    if "accounts" not in mayor:
        raise ValueError("Libro Mayor inválido")

    # ==================================================
    # SAVE AS
    # ==================================================
    file_path = filedialog.asksaveasfilename(
        title="Guardar Libro Mayor (PDF)",
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")]
    )
    if not file_path:
        return None

    # ==================================================
    # DOCUMENTO
    # ==================================================
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # ⚠️ NOMBRES ÚNICOS (NO EXISTEN EN SAMPLE)
    styles.add(ParagraphStyle(
        name="LM_Title",
        fontName="Helvetica-Bold",
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        name="LM_Subtitle",
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=16
    ))

    styles.add(ParagraphStyle(
        name="LM_Account",
        fontName="Helvetica-Bold",
        fontSize=10,
        alignment=TA_LEFT,
        spaceBefore=12,
        spaceAfter=6
    ))

    elements = []

    # ==================================================
    # ENCABEZADO
    # ==================================================
    elements.append(
        Paragraph("LIBRO MAYOR", styles["LM_Title"])
    )
    elements.append(
        Paragraph(f"Periodo {mayor['period_label']}", styles["LM_Subtitle"])
    )

    # ==================================================
    # HELPERS
    # ==================================================
    def fmt(val):
        try:
            return f"{float(val):,.2f}"
        except Exception:
            return "0.00"

    def build_table(data: List[List[str]]):
        table = Table(
            data,
            colWidths=[80, 55, 215, 70, 70]
        )
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        return table

    # ==================================================
    # DATA (MISMO ORDEN QUE EXCEL)
    # ==================================================
    for acc in mayor["accounts"]:

        elements.append(
            Paragraph(acc["account"], styles["LM_Account"])
        )

        table_data = [[
            "Fecha", "Asiento", "Detalle", "Debe", "Haber"
        ]]

        for l in acc["lines"]:
            table_data.append([
                str(l.get("date", "")),
                str(l.get("entry_id", "")),
                str(l.get("detail", "")),
                fmt(l.get("debit", 0)),
                fmt(l.get("credit", 0)),
            ])

        table_data.append([
            "",
            "",
            "TOTAL",
            fmt(acc["total_debit"]),
            fmt(acc["total_credit"]),
        ])

        elements.append(build_table(table_data))
        elements.append(Spacer(1, 14))

    # ==================================================
    # BUILD
    # ==================================================
    doc.build(elements)
    return file_path


# 🔑 Alias compatible con popup
export_mayor_pdf = export_mayor_pdf_from_lines
