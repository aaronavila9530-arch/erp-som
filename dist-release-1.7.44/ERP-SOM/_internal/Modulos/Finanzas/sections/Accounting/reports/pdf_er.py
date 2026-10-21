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
from typing import Dict, Any, List


def export_er_pdf_from_er(
    er: Dict[str, Any],
    fiscal_year: int,
    period: int
):
    """
    Exporta Estado de Resultados en PDF
    desde un ER ya construido (build_er_from_lines)

    ✔ NO recibe accounting_lines
    ✔ NO recalcula
    ✔ SOLO renderiza
    """

    # ==================================================
    # VALIDACIÓN FUERTE
    # ==================================================
    if not isinstance(er, dict):
        raise ValueError("ER inválido: se esperaba dict.")

    required_keys = [
        "ingresos", "total_ingresos",
        "costos", "total_costos",
        "utilidad_bruta",
        "gastos_operativos", "total_gastos_operativos",
        "utilidad_operativa",
        "otros",
        "utilidad_antes_impuestos",
        "impuesto_renta",
        "utilidad_neta",
    ]

    for k in required_keys:
        if k not in er:
            raise ValueError(f"ER inválido. Falta clave '{k}'")

    def safe_list(v) -> List[dict]:
        return v if isinstance(v, list) else []

    ingresos = safe_list(er["ingresos"])
    costos = safe_list(er["costos"])
    gastos_operativos = safe_list(er["gastos_operativos"])
    otros = safe_list(er["otros"])

    # ==================================================
    # SAVE AS
    # ==================================================
    file_path = filedialog.asksaveasfilename(
        title="Guardar Estado de Resultados (PDF)",
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")]
    )
    if not file_path:
        return None

    period_label = f"{int(fiscal_year)}-{int(period):02d}"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    # ==================================================
    # STYLES (🔥 NOMBRES ÚNICOS)
    # ==================================================
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ER_Title",
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=10,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="ER_SubTitle",
        fontSize=10,
        alignment=TA_CENTER,
        spaceAfter=15
    ))

    styles.add(ParagraphStyle(
        name="ER_Section",
        fontSize=10,
        spaceBefore=12,
        spaceAfter=6,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="ER_Right",
        fontSize=10,
        alignment=TA_RIGHT
    ))

    styles.add(ParagraphStyle(
        name="ER_BoldLeft",
        parent=styles["Normal"],
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="ER_BoldRight",
        parent=styles["ER_Right"],
        fontName="Helvetica-Bold"
    ))

    elements = []

    # ==================================================
    # ENCABEZADO
    # ==================================================
    elements.append(Paragraph("ESTADO DE RESULTADOS", styles["ER_Title"]))
    elements.append(
        Paragraph(
            f"Por el período terminado el {period_label}",
            styles["ER_SubTitle"]
        )
    )

    # ==================================================
    # HELPERS
    # ==================================================
    def section(title: str):
        elements.append(Spacer(1, 8))
        elements.append(Paragraph(title, styles["ER_Section"]))

    def line(label: str, amount: Any, bold: bool = False):
        try:
            amount = float(amount)
        except Exception:
            amount = 0.0

        left = styles["ER_BoldLeft"] if bold else styles["Normal"]
        right = styles["ER_BoldRight"] if bold else styles["ER_Right"]

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
    # INGRESOS
    # ==================================================
    section("INGRESOS")
    for item in ingresos:
        line(item.get("label", ""), item.get("amount", 0))

    line("Total Ingresos", er["total_ingresos"], bold=True)

    # ==================================================
    # COSTOS
    # ==================================================
    section("(-) COSTOS")
    for item in costos:
        line(item.get("label", ""), item.get("amount", 0))

    line("Total Costos", er["total_costos"], bold=True)

    # ==================================================
    # UTILIDAD BRUTA
    # ==================================================
    section("UTILIDAD BRUTA")
    line("Utilidad Bruta", er["utilidad_bruta"], bold=True)

    # ==================================================
    # GASTOS OPERATIVOS
    # ==================================================
    section("(-) GASTOS OPERATIVOS")
    for item in gastos_operativos:
        line(item.get("label", ""), item.get("amount", 0))

    line("Total Gastos Operativos", er["total_gastos_operativos"], bold=True)

    # ==================================================
    # OTROS
    # ==================================================
    if otros:
        section("(+/-) OTROS INGRESOS Y GASTOS")
        for item in otros:
            line(item.get("label", ""), item.get("amount", 0))

    # ==================================================
    # RESULTADOS FINALES
    # ==================================================
    section("UTILIDAD ANTES DE IMPUESTOS")
    line("Utilidad Antes de Impuestos", er["utilidad_antes_impuestos"], bold=True)

    section("(-) IMPUESTO SOBRE LA RENTA")
    line("Impuesto sobre la Renta", er["impuesto_renta"])

    section("UTILIDAD NETA DEL PERIODO")
    line("Utilidad Neta del Periodo", er["utilidad_neta"], bold=True)

    # ==================================================
    # BUILD
    # ==================================================
    doc.build(elements)
    return file_path
