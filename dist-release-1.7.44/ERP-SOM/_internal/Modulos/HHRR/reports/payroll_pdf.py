from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import cm
import os
from datetime import date

from Modulos.HHRR.date_utils import to_long_english_date


# ============================================================
# CONSTANTES COSTA RICA 2026 (SOLO PARA DESGLOSE VISUAL)
# ============================================================

TRAMOS_RENTA = [
    (918000, 0.00),
    (1347000, 0.10),
    (2364000, 0.15),
    (4727000, 0.20),
    (float("inf"), 0.25)
]

DEDUCCIONES_TRABAJADOR = {
    "SEM": 0.055,
    "IVM": 0.0433,
    "BANCO_POPULAR": 0.01
}

CARGAS_PATRONALES = {
    "SEM": 0.0925,
    "IVM": 0.0558,
    "BP_CC": 0.0025,
    "BP_LPT": 0.0025,
    "FODESAF": 0.05,
    "IMAS": 0.005,
    "INA": 0.015,
    "FCL": 0.015,
    "OPC": 0.02,
    "INS": 0.01
}


# ============================================================
# FORMATO NUMÉRICO
# ============================================================

def fmt(valor: float) -> str:
    """Formato monetario 1,234,567.89"""
    return f"{valor:,.2f}"


def generar_colilla_pdf(path: str, data: dict, year: int, month: int):
    """
    Genera colilla de pago en formato horizontal con header corporativo
    y desglose legal de deducciones.
    """

    # ---------------------------------------------------------
    # DOCUMENTO
    # ---------------------------------------------------------
    doc = SimpleDocTemplate(
        path,
        pagesize=landscape(LETTER),
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---------------------------------------------------------
    # HEADER (PEQUEÑO / ESQUINA SUPERIOR IZQUIERDA)
    # ---------------------------------------------------------
    assets_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "assets",
            "header.png"
        )
    )

    if os.path.exists(assets_path):
        header = Image(
            assets_path,
            width=8 * cm,
            height=2.2 * cm,
            hAlign="LEFT"
        )
        elements.append(header)
        elements.append(Spacer(1, 8))

    # ---------------------------------------------------------
    # TITULO
    # ---------------------------------------------------------
    title_style = ParagraphStyle(
        "TitleStyle",
        fontSize=13,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=10
    )

    elements.append(
        Paragraph(
            f"<b>Comprobante de Pago</b><br/>"
            f"Periodo: {month}/{year}<br/>"
            f"Empresa: MSL Marine Surveyors and Logistics Group SRL",
            title_style
        )
    )

    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # DATOS DEL EMPLEADO
    # ---------------------------------------------------------
    info_table = Table(
        [
            ["Empleado:", f"{data['nombre']} {data['apellidos']}"],
            ["Cédula:", data.get("cedula_id", "N/D")],
            ["Usuario:", data["usuario"]],
            ["Jornada:", data["jornada"]],
            ["Tipo de pago:", data["pago"]],
            ["Fecha emisión:", to_long_english_date(date.today())]
        ],
        colWidths=[6 * cm, 16 * cm]
    )

    info_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )

    elements.append(info_table)
    elements.append(Spacer(1, 12))

    # =========================================================
    # RESUMEN DE DEVENGOS  (NUEVO – SOLO ESTO SE AGREGA)
    # =========================================================

    devengos_rows = [
        ["Resumen de Devengos", "Detalle", "Monto"],
        ["Salario Base", "", fmt(data["salario_base"])],
        ["Horas Extra", f"{data.get('horas_ot', 0)} horas", fmt(data.get("pago_horas_extra", 0.0))],
        ["Total Devengado", "", fmt(data["salario_bruto"])]
    ]

    devengos_table = Table(devengos_rows, colWidths=[8 * cm, 4 * cm, 6 * cm])
    devengos_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
            ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
        ])
    )

    elements.append(devengos_table)
    elements.append(Spacer(1, 12))

    salario_bruto = data["salario_bruto"]

    # ---------------------------------------------------------
    # DEDUCCIONES TRABAJADOR
    # ---------------------------------------------------------
    ded_rows = [["Deducción Trabajador", "%", "Monto"]]

    for k, tasa in DEDUCCIONES_TRABAJADOR.items():
        ded_rows.append([
            k,
            f"{tasa * 100:.2f} %",
            fmt(salario_bruto * tasa)
        ])

    ded_rows.append([
        "Total Deducciones",
        "",
        fmt(data["deducciones_trabajador"])
    ])

    ded_table = Table(ded_rows, colWidths=[8 * cm, 4 * cm, 6 * cm])
    ded_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
    ]))

    elements.append(ded_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # RENTA
    # ---------------------------------------------------------
    renta_tramo = 0.0
    for limite, tasa in TRAMOS_RENTA:
        if salario_bruto <= limite:
            renta_tramo = tasa
            break

    renta_table = Table(
        [
            ["Impuesto Renta", "% Aplicado", "Monto"],
            ["Renta", f"{renta_tramo * 100:.2f} %", fmt(data["impuesto_renta"])]
        ],
        colWidths=[8 * cm, 4 * cm, 6 * cm]
    )

    renta_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    elements.append(renta_table)
    elements.append(Spacer(1, 10))

    # ---------------------------------------------------------
    # CARGAS PATRONALES (INFORMATIVO)
    # ---------------------------------------------------------
    patronal_rows = [["Carga Patronal", "%", "Monto"]]

    total_patronal = 0
    for k, tasa in CARGAS_PATRONALES.items():
        monto = salario_bruto * tasa
        total_patronal += monto
        patronal_rows.append([
            k,
            f"{tasa * 100:.2f} %",
            fmt(monto)
        ])

    patronal_rows.append([
        "Total Cargas Patronales",
        "",
        fmt(total_patronal)
    ])

    patronal_table = Table(patronal_rows, colWidths=[8 * cm, 4 * cm, 6 * cm])
    patronal_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9),
    ]))

    elements.append(patronal_table)
    elements.append(Spacer(1, 12))

    # ---------------------------------------------------------
    # NETO A PAGAR
    # ---------------------------------------------------------
    neto_style = ParagraphStyle(
        "NetoStyle",
        fontSize=12,
        leading=14,
        alignment=TA_RIGHT
    )

    elements.append(
        Paragraph(
            f"<b>Neto a pagar: {fmt(data['salario_neto'])}</b>",
            neto_style
        )
    )

    # ---------------------------------------------------------
    # BUILD
    # ---------------------------------------------------------
    doc.build(elements)
