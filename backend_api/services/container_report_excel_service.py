import os
import tempfile
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "container_report_template.xlsx"
    )
)


def _safe_set(ws: Worksheet, cell: str, value):
    """
    Escribe valor respetando celdas combinadas.
    """
    for merged in ws.merged_cells.ranges:
        if cell in merged:
            ws.cell(row=merged.min_row, column=merged.min_col).value = value
            return
    ws[cell].value = value


def generate_container_report_excel(report: dict) -> str:
    """
    Genera un Excel de Container Report usando template base.
    Retorna path del archivo generado.
    """

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Excel template not found: {TEMPLATE_PATH}")

    try:
        wb = load_workbook(TEMPLATE_PATH)
    except Exception as e:
        raise RuntimeError(f"Error loading Excel template: {e}")

    ws = wb.active

    # =====================================================
    # MAPEO SEGURO (SOPORTA MERGED CELLS)
    # =====================================================
    _safe_set(ws, "B4", report.get("report_no"))
    _safe_set(ws, "E4", report.get("bl"))

    _safe_set(ws, "B6", report.get("inspection_place"))
    _safe_set(ws, "E6", report.get("vessel"))

    _safe_set(ws, "B8", report.get("contact_datetime"))
    _safe_set(ws, "E8", report.get("appointment"))

    _safe_set(ws, "B12", report.get("goods_description"))
    _safe_set(ws, "B18", report.get("damage_details"))
    _safe_set(ws, "B24", report.get("remarks"))
    _safe_set(ws, "B30", report.get("conclusion"))

    # Checks
    _safe_set(ws, "C40", "✔" if report.get("container_size_20") else "")
    _safe_set(ws, "D40", "✔" if report.get("container_size_40") else "")

    # =====================================================
    # ARCHIVO TEMPORAL
    # =====================================================
    fd, output_path = tempfile.mkstemp(
        suffix=".xlsx",
        prefix=f"container_report_{report.get('id', 'x')}_"
    )
    os.close(fd)

    wb.save(output_path)
    return output_path
