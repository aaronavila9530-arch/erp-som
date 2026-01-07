from typing import Any, List
from tkinter import filedialog

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle
)
from reportlab.lib import colors

from Modulos.Finanzas.sections.Accounting.reports.build_tb_from_lines import (
    build_tb_from_lines
)


def export_tb_pdf_from_lines(rows_or_built: Any):
    """
    Exporta Balance de Comprobación (TB) a PDF

    ✔ Acepta TB ya construido (dict)
    ✔ Acepta accounting_lines (list)
    ✔ Save As interno
    ✔ SIN company_code
    ✔ Styles robustos (no fallan al guardar)
    """

    # ==================================================
    # NORMALIZACIÓN
    # ==================================================
    if isinstance(rows_or_built, list):
        tb = build_tb_from_lines(rows_or_built)
    elif isinstance(rows_or_built, dict):
        tb = rows_or_built
    else:
        raise ValueError("export_tb_pdf_from_lines esperaba dict o list")

    # ==================================================
    # VALIDACIÓN
    # ==================================================
    if "rows" not in tb:
        raise ValueError("Balance de Comprobación inválido")

    # ==================================================
    # SAVE AS
    # ==================================================
    file_path = filedialog.asksaveasfilename(
        title="Guardar Balance de Comprobación (PDF)",
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

    styles.add(ParagraphStyle(
        name="TitleCenter",
        fontSize=14,
        leading=16,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        spaceAfter=10
    ))

    styles.add(ParagraphStyle(
        name="SubtitleCenter",
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=16
    ))

    styles.add(ParagraphStyle(
        name="NormalRight",
        fontSize=9,
        leading=11,
        alignment=TA_RIGHT
    ))

    elements = []

    # ==================================================
    # ENCABEZADO
    # ==================================================
    elements.append(
        Paragraph("BALANCE DE COMPROBACIÓN", styles["TitleCenter"])
    )

    elements.append(
        Paragraph(
            f"Periodo {tb['period_label']}",
            styles["SubtitleCenter"]
        )
    )

    # ==================================================
    # HELPERS
    # ==================================================
    def fmt_amount(val) -> str:
        try:
            return f"{float(val):,.2f}"
        except Exception:
            return "0.00"

    def build_table(data: List[List[str]]):
        table = Table(
            data,
            colWidths=[230, 80, 80, 80, 80],
            repeatRows=1
        )

        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONT", (0, 1), (-1, -1), "Helvetica"),
            ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))

        return table

    # ==================================================
    # TABLA
    # ==================================================
    table_data = [
        ["Cuenta", "Debe", "Haber", "Saldo Deudor", "Saldo Acreedor"]
    ]

    for r in tb["rows"]:
        table_data.append([
            str(r["account"]),
            fmt_amount(r["debit"]),
            fmt_amount(r["credit"]),
            fmt_amount(r["saldo_deudor"]),
            fmt_amount(r["saldo_acreedor"]),
        ])

    table_data.append([
        "TOTAL",
        fmt_amount(tb["total_debit"]),
        fmt_amount(tb["total_credit"]),
        fmt_amount(tb["total_saldo_deudor"]),
        fmt_amount(tb["total_saldo_acreedor"]),
    ])

    elements.append(build_table(table_data))

    # ==================================================
    # BUILD
    # ==================================================
    doc.build(elements)

    return file_path


# 🔑 Alias compatible con popup
export_tb_pdf = export_tb_pdf_from_lines
