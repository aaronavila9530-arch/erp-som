from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from datetime import date


def generar_colilla_pdf(path, empleado, periodo, calculo):

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=LETTER)

    elementos = []

    elementos.append(Paragraph("<b>COLILLA DE PAGO</b>", styles["Title"]))
    elementos.append(Paragraph(f"Empleado: {empleado['nombre']} {empleado['apellidos']}", styles["Normal"]))
    elementos.append(Paragraph(f"Periodo: {periodo}", styles["Normal"]))
    elementos.append(Paragraph(f"Fecha emisión: {date.today()}", styles["Normal"]))

    # -------------------------
    # DEVENGOS
    # -------------------------
    tabla_devengos = Table([
        ["Salario Bruto", f"{calculo['salario_bruto']:.2f}"]
    ])

    tabla_devengos.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black)
    ]))

    elementos.append(tabla_devengos)

    # -------------------------
    # DEDUCCIONES OBRERO
    # -------------------------
    data_obrero = [["Deducción", "Monto"]]
    for k, v in calculo["obrero"].items():
        data_obrero.append([k, f"{v:.2f}"])

    data_obrero.append(["TOTAL OBRERO", f"{calculo['total_obrero']:.2f}"])

    tabla_obrero = Table(data_obrero)
    tabla_obrero.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey)
    ]))

    elementos.append(tabla_obrero)

    elementos.append(
        Paragraph(f"<b>Salario Neto: {calculo['salario_neto']:.2f}</b>", styles["Heading2"])
    )

    doc.build(elementos)
