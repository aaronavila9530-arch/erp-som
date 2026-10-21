from typing import Any, List, Dict
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

from Modulos.Finanzas.sections.Accounting.reports.build_fc_from_trial_balance import (
    build_fc_from_trial_balance
)


def export_fc_pdf_from_fc(fc_or_rows: Any):
    """
    Exporta Estado de Flujo de Efectivo (Método Indirecto) a PDF

    ✔ Acepta FC ya construido (dict)
    ✔ Acepta accounting_lines (list) y construye FC automáticamente
    ✔ Save As interno
    ✔ SIN errores de style
    ✔ Platypus (correcto)
    """

    # ==================================================
    # NORMALIZACIÓN DE ENTRADA
    # ==================================================
    if isinstance(fc_or_rows, list):
        fc = build_fc_from_trial_balance(fc_or_rows)
    elif isinstance(fc_or_rows, dict):
        fc = fc_or_rows
    else:
        raise ValueError(
            "export_fc_pdf_from_fc esperaba un FC (dict) "
            "o accounting_lines (list)"
        )

    # ==================================================
    # VALIDACIÓN FUERTE DE FC
    # ==================================================
    required_keys = [
        "operacion",
        "neto_operacion",
        "inversion",
        "neto_inversion",
        "financiamiento",
        "neto_financiamiento",
        "variacion_efectivo",
        "efectivo_inicio",
        "efectivo_final",
        "period_label",
    ]

    for k in required_keys:
        if k not in fc:
            raise ValueError(f"Flujo de Efectivo inválido. Falta clave '{k}'")

    # ==================================================
    # SAVE AS
    # ==================================================
    file_path = filedialog.asksaveasfilename(
        title="Guardar Estado de Flujo de Efectivo (PDF)",
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
        spaceAfter=10,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="SubtitleCenter",
        fontSize=10,
        leading=12,
        alignment=TA_CENTER,
        spaceAfter=18
    ))

    styles.add(ParagraphStyle(
        name="Section",
        fontSize=10,
        leading=12,
        spaceBefore=12,
        spaceAfter=6,
        fontName="Helvetica-Bold"
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
        Paragraph("ESTADO DE FLUJO DE EFECTIVO", styles["TitleCenter"])
    )

    elements.append(
        Paragraph(
            f"Por el período terminado el {fc['period_label']}",
            styles["SubtitleCenter"]
        )
    )

    # ==================================================
    # HELPERS
    # ==================================================
    def build_table(rows: List[List[Any]]):
        table = Table(
            rows,
            colWidths=[360, 120],
            repeatRows=0
        )

        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))

        return table

    def fmt_amount(val) -> str:
        try:
            return f"{float(val):,.2f}"
        except Exception:
            return "0.00"

    # ==================================================
    # OPERACIÓN
    # ==================================================
    elements.append(
        Paragraph(
            "FLUJO DE EFECTIVO DE ACTIVIDADES DE OPERACIÓN",
            styles["Section"]
        )
    )

    data = []
    for item in fc["operacion"]:
        data.append([item.get("label", ""), fmt_amount(item.get("amount", 0))])

    data.append([
        "Flujo Neto de Actividades de Operación",
        fmt_amount(fc["neto_operacion"])
    ])

    elements.append(build_table(data))
    elements.append(Spacer(1, 12))

    # ==================================================
    # INVERSIÓN
    # ==================================================
    elements.append(
        Paragraph(
            "FLUJO DE EFECTIVO DE ACTIVIDADES DE INVERSIÓN",
            styles["Section"]
        )
    )

    data = []
    for item in fc["inversion"]:
        data.append([item.get("label", ""), fmt_amount(item.get("amount", 0))])

    data.append([
        "Flujo Neto de Actividades de Inversión",
        fmt_amount(fc["neto_inversion"])
    ])

    elements.append(build_table(data))
    elements.append(Spacer(1, 12))

    # ==================================================
    # FINANCIAMIENTO
    # ==================================================
    elements.append(
        Paragraph(
            "FLUJO DE EFECTIVO DE ACTIVIDADES DE FINANCIAMIENTO",
            styles["Section"]
        )
    )

    data = []
    for item in fc["financiamiento"]:
        data.append([item.get("label", ""), fmt_amount(item.get("amount", 0))])

    data.append([
        "Flujo Neto de Actividades de Financiamiento",
        fmt_amount(fc["neto_financiamiento"])
    ])

    elements.append(build_table(data))
    elements.append(Spacer(1, 12))

    # ==================================================
    # EFECTIVO
    # ==================================================
    data = [
        ["AUMENTO / (DISMINUCIÓN) NETO DE EFECTIVO", fmt_amount(fc["variacion_efectivo"])],
        ["Efectivo al Inicio del Periodo", fmt_amount(fc["efectivo_inicio"])],
        ["EFECTIVO AL FINAL DEL PERIODO", fmt_amount(fc["efectivo_final"])],
    ]

    elements.append(build_table(data))

    # ==================================================
    # BUILD
    # ==================================================
    doc.build(elements)

    return file_path


# 🔑 Alias de compatibilidad
export_fc_pdf = export_fc_pdf_from_fc
