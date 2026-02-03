import os
import tempfile
from openpyxl import load_workbook


TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "templates",
    "container_report_template.xlsx"
)


def generate_container_report_excel(report: dict) -> str:
    """
    Genera un Excel de Container Report usando template base.
    Retorna path del archivo generado.
    """

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError("Excel template not found")

    wb = load_workbook(TEMPLATE_PATH)
    ws = wb.active

    # =====================================================
    # MAPEO 1:1 — AJUSTA SEGÚN TU TEMPLATE REAL
    # =====================================================
    ws["B4"] = report.get("report_no")
    ws["E4"] = report.get("bl")
    ws["B6"] = report.get("inspection_place")
    ws["E6"] = report.get("vessel")

    ws["B8"] = report.get("contact_datetime")
    ws["E8"] = report.get("appointment")

    ws["B12"] = report.get("goods_description")
    ws["B18"] = report.get("damage_details")
    ws["B24"] = report.get("remarks")
    ws["B30"] = report.get("conclusion")

    # Checks (ejemplo)
    ws["C40"] = "✔" if report.get("container_size_20") else ""
    ws["D40"] = "✔" if report.get("container_size_40") else ""

    # =====================================================
    # GENERAR ARCHIVO TEMPORAL
    # =====================================================
    fd, output_path = tempfile.mkstemp(
        suffix=".xlsx",
        prefix=f"container_report_{report.get('id', 'x')}_"
    )
    os.close(fd)

    wb.save(output_path)
    return output_path
