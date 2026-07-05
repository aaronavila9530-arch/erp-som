from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Table,
    TableStyle,
    Spacer
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from tkinter import filedialog
from typing import Any, List

from Modulos.Finanzas.sections.Accounting.reports.build_esf_from_trial_balance import (
    build_esf_from_trial_balance
)


def export_esf_pdf_from_esf(esf_or_rows: Any):
    """
    Exporta Estado de Situación Financiera a PDF

    ✔ Acepta ESF ya construido (dict)
    ✔ Acepta accounting_lines (list) y construye ESF automáticamente
    ✔ Save As interno
    ✔ NO recalcula dos veces
    ✔ Blindado total
    """

    # ==================================================
    # NORMALIZACIÓN DE ENTRADA
    # ==================================================
    if isinstance(esf_or_rows, list):
        esf = build_esf_from_trial_balance(esf_or_rows)
    elif isinstance(esf_or_rows, dict):
        esf = esf_or_rows
    else:
        raise ValueError(
            "export_esf_pdf_from_esf esperaba un ESF (dict) "
            "o accounting_lines (list)"
        )

    # ==================================================
    # VALIDACIÓN FUERTE
    # ==================================================
    required_keys = [
        "activo_corriente",
        "total_activo_corriente",
        "activo_no_corriente",
        "total_activo_no_corriente",
        "total_activo",
        "pasivo_corriente",
        "total_pasivo_corriente",
        "pasivo_no_corriente",
        "total_pasivo_no_corriente",
        "total_pasivo",
        "patrimonio",
        "total_patrimonio",
        "total_pasivo_patrimonio",
        "period_label",
        "fiscal_year",
    ]

    for k in required_keys:
        if k not in esf:
            raise ValueError(f"ESF inválido. Falta clave '{k}'")

    # ==================================================
    # NORMALIZADORES
    # ==================================================
    def safe_list(val) -> List[dict]:
        return val if isinstance(val, list) else []

    def safe_amount(val) -> float:
        try:
            return float(val)
        except Exception:
            return 0.0

    activo_corriente = safe_list(esf["activo_corriente"])
    activo_no_corriente = safe_list(esf["activo_no_corriente"])
    pasivo_corriente = safe_list(esf["pasivo_corriente"])
    pasivo_no_corriente = safe_list(esf["pasivo_no_corriente"])
    patrimonio = safe_list(esf["patrimonio"])

    fiscal_year = int(esf["fiscal_year"])
    period_label = str(esf["period_label"])

    # ==================================================
    # SAVE AS
    # ==================================================
    file_path = filedialog.asksaveasfilename(
        title="Guardar Estado de Situación Financiera (PDF)",
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
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # 🔒 ESTILOS PROPIOS (NO colisionan con ReportLab)
    styles.add(ParagraphStyle(
        name="ESF_Title",
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="ESF_SubTitle",
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=15
    ))

    styles.add(ParagraphStyle(
        name="ESF_Section",
        fontSize=10,
        spaceBefore=12,
        spaceAfter=6,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="ESF_Right",
        fontSize=10,
        alignment=TA_RIGHT
    ))

    elements = []

    # ==================================================
    # ENCABEZADO
    # ==================================================
    elements.append(
        Paragraph("ESTADO DE SITUACIÓN FINANCIERA", styles["ESF_Title"])
    )
    elements.append(
        Paragraph(f"Al {period_label} del {fiscal_year}", styles["ESF_SubTitle"])
    )

    # ==================================================
    # HELPERS
    # ==================================================
    def section(title: str):
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(title, styles["ESF_Section"]))

    def line(label: str, amount: Any, bold: bool = False):
        amount = safe_amount(amount)

        left = styles["Normal"]
        right = styles["ESF_Right"]

        if bold:
            left = ParagraphStyle(
                "ESF_Bold_Left",
                parent=styles["Normal"],
                fontName="Helvetica-Bold"
            )
            right = ParagraphStyle(
                "ESF_Bold_Right",
                parent=styles["ESF_Right"],
                fontName="Helvetica-Bold"
            )

        table = Table(
            [[
                Paragraph(str(label), left),
                Paragraph(f"{amount:,.2f}", right)
            ]],
            colWidths=[350, 110]
        )

        table.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.25, colors.grey),
            ("LEFTPADDING", (0, 0), (-1, 0), 4),
            ("RIGHTPADDING", (0, 0), (-1, 0), 4),
            ("TOPPADDING", (0, 0), (-1, 0), 3),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 3),
        ]))

        elements.append(table)

    # ==================================================
    # ACTIVO
    # ==================================================
    section("ACTIVO")

    section("Activo Corriente")
    for item in activo_corriente:
        line(item.get("label", ""), item.get("amount", 0))

    line("Total Activo Corriente", esf["total_activo_corriente"], bold=True)

    section("Activo No Corriente")
    for item in activo_no_corriente:
        line(item.get("label", ""), item.get("amount", 0))

    line("Total Activo No Corriente", esf["total_activo_no_corriente"], bold=True)
    line("TOTAL ACTIVO", esf["total_activo"], bold=True)

    # ==================================================
    # PASIVO
    # ==================================================
    section("PASIVO")

    section("Pasivo Corriente")
    for item in pasivo_corriente:
        line(item.get("label", ""), item.get("amount", 0))

    line("Total Pasivo Corriente", esf["total_pasivo_corriente"], bold=True)

    section("Pasivo No Corriente")
    for item in pasivo_no_corriente:
        line(item.get("label", ""), item.get("amount", 0))

    line("Total Pasivo No Corriente", esf["total_pasivo_no_corriente"], bold=True)
    line("TOTAL PASIVO", esf["total_pasivo"], bold=True)

    # ==================================================
    # PATRIMONIO
    # ==================================================
    section("PATRIMONIO")

    for item in patrimonio:
        line(item.get("label", ""), item.get("amount", 0))

    line("TOTAL PATRIMONIO", esf["total_patrimonio"], bold=True)

    # ==================================================
    # TOTAL FINAL
    # ==================================================
    section("TOTAL PASIVO Y PATRIMONIO")
    line(
        "Total Pasivo y Patrimonio",
        esf["total_pasivo_patrimonio"],
        bold=True
    )

    # ==================================================
    # BUILD
    # ==================================================
    doc.build(elements)
    return file_path


# 🔑 Alias para imports existentes
export_esf_pdf = export_esf_pdf_from_esf
