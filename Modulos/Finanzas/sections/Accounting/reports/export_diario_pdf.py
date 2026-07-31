from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from tkinter import filedialog
from Modulos.Finanzas.date_utils import to_long_english_date


def export_diario_pdf(rows: list[dict], fiscal_year: int, period: int):
    """
    Exporta Libro Diario en PDF DIRECTAMENTE desde accounting_lines.

    ✔ NO usa company_code
    ✔ NO usa company_name
    ✔ Fiscal year y period vienen del POPUP
    ✔ created_at es la fecha real por línea
    """

    if not rows:
        raise ValueError("No hay datos para exportar")

    # =============================
    # SAVE AS
    # =============================
    file_path = filedialog.asksaveasfilename(
        title="Guardar Libro Diario (PDF)",
        defaultextension=".pdf",
        filetypes=[("PDF", "*.pdf")]
    )

    if not file_path:
        return None

    period_label = f"{int(fiscal_year)}-{int(period):02d}"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="TitleCenter",
        alignment=1,
        fontSize=14,
        spaceAfter=10,
        fontName="Helvetica-Bold"
    ))

    elements = []

    # =============================
    # ENCABEZADO (SIN EMPRESA)
    # =============================
    elements.append(Paragraph("LIBRO DIARIO", styles["TitleCenter"]))
    elements.append(
        Paragraph(f"Período fiscal: {period_label}", styles["Normal"])
    )
    elements.append(Paragraph("<br/>", styles["Normal"]))

    # =============================
    # TABLA
    # =============================
    data = [[
        "Fecha",
        "Asiento",
        "Cuenta",
        "Nombre de la Cuenta",
        "Debe",
        "Haber",
        "Detalle",
        "Origen"
    ]]

    total_debe = 0.0
    total_haber = 0.0

    for r in rows:
        fecha = to_long_english_date(r.get("created_at"))

        debe = float(r.get("debit") or 0)
        haber = float(r.get("credit") or 0)

        total_debe += debe
        total_haber += haber

        data.append([
            fecha,
            r.get("entry_id"),
            r.get("account_code"),
            r.get("account_name"),
            f"{debe:,.2f}",
            f"{haber:,.2f}",
            r.get("line_description", ""),
            r.get("origin", "")
        ])

    # =============================
    # TOTALES
    # =============================
    data.append([
        "",
        "",
        "",
        "TOTALES",
        f"{total_debe:,.2f}",
        f"{total_haber:,.2f}",
        "",
        ""
    ])

    table = Table(
        data,
        repeatRows=1,
        colWidths=[
            70,   # Fecha
            55,   # Asiento
            65,   # Cuenta
            150,  # Nombre
            80,   # Debe
            80,   # Haber
            180,  # Detalle
            90    # Origen
        ]
    )

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),

        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),

        ("ALIGN", (4, 1), (5, -2), "RIGHT"),
        ("ALIGN", (4, -1), (5, -1), "RIGHT"),

        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
    ]))

    elements.append(table)

    doc.build(elements)
    return file_path
