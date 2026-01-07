from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from tkinter import filedialog
from datetime import datetime

THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def export_diario_excel(rows: list[dict], fiscal_year: int, period: int):
    """
    Exporta Libro Diario DIRECTAMENTE desde accounting_lines.

    Reglas:
    - NO usa company_code / company_name
    - Fiscal year y period vienen del POPUP (no se calculan aquí)
    - created_at es la fecha real por línea
    """

    if not rows:
        raise ValueError("No hay datos para exportar")

    # =============================
    # SAVE AS
    # =============================
    file_path = filedialog.asksaveasfilename(
        title="Guardar Libro Diario",
        defaultextension=".xlsx",
        filetypes=[("Excel", "*.xlsx")]
    )
    if not file_path:
        return None

    period_label = f"{int(fiscal_year)}-{int(period):02d}"

    wb = Workbook()
    ws = wb.active
    ws.title = "Libro Diario"

    # =============================
    # ANCHOS
    # =============================
    widths = {
        "A": 14,  # Fecha
        "B": 12,  # Asiento
        "C": 14,  # Cuenta
        "D": 35,  # Nombre de la Cuenta
        "E": 16,  # Debe
        "F": 16,  # Haber
        "G": 40,  # Detalle
        "H": 18,  # Origen
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    # =============================
    # ENCABEZADO (SIN EMPRESA)
    # =============================
    ws.merge_cells("A1:H1")
    ws["A1"] = "LIBRO DIARIO"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Período fiscal: {period_label}"
    ws["A2"].font = Font(bold=True, size=12)
    ws["A2"].alignment = Alignment(horizontal="center")

    row = 4

    # =============================
    # CABECERAS
    # =============================
    headers = [
        "Fecha",
        "Asiento",
        "Cuenta",
        "Nombre de la Cuenta",
        "Debe",
        "Haber",
        "Detalle",
        "Origen"
    ]

    for col, h in enumerate(headers, start=1):
        c = ws.cell(row=row, column=col, value=h)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.border = BORDER

    row += 1

    total_debe = 0.0
    total_haber = 0.0

    # =============================
    # DATA (SQL PURO)
    # =============================
    for r in rows:
        # created_at real
        fecha = r.get("created_at")
        try:
            fecha = datetime.fromisoformat(fecha)
        except Exception:
            pass

        ws.cell(row=row, column=1, value=fecha)
        ws.cell(row=row, column=2, value=r.get("entry_id"))
        ws.cell(row=row, column=3, value=r.get("account_code"))
        ws.cell(row=row, column=4, value=r.get("account_name"))

        debe = float(r.get("debit") or 0)
        haber = float(r.get("credit") or 0)

        ws.cell(row=row, column=5, value=debe)
        ws.cell(row=row, column=6, value=haber)
        ws.cell(row=row, column=7, value=r.get("line_description", ""))
        ws.cell(row=row, column=8, value=r.get("origin", ""))

        ws.cell(row=row, column=5).number_format = "#,##0.00"
        ws.cell(row=row, column=6).number_format = "#,##0.00"

        total_debe += debe
        total_haber += haber

        for c in range(1, 9):
            ws.cell(row=row, column=c).border = BORDER

        row += 1

    # =============================
    # TOTALES
    # =============================
    ws.cell(row=row, column=4, value="TOTALES").font = Font(bold=True)
    ws.cell(row=row, column=5, value=total_debe).font = Font(bold=True)
    ws.cell(row=row, column=6, value=total_haber).font = Font(bold=True)

    ws.cell(row=row, column=5).number_format = "#,##0.00"
    ws.cell(row=row, column=6).number_format = "#,##0.00"

    for c in range(1, 9):
        ws.cell(row=row, column=c).border = BORDER

    wb.save(file_path)
    return file_path
