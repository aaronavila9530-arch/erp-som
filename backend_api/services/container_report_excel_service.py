import os
import tempfile
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


# =====================================================
# RUTA ABSOLUTA BLINDADA AL TEMPLATE
# =====================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

TEMPLATE_PATH = os.path.join(
    BASE_DIR,
    "templates",
    "container_report_template.xlsx"
)


def generate_container_report_excel(report: dict) -> str:
    """
    Genera un Excel de Container Report usando un template base.
    Retorna el path del archivo generado.
    """

    # -------------------------------------------------
    # VALIDACIONES FUERTES
    # -------------------------------------------------
    if not isinstance(report, dict):
        raise ValueError("Report data must be a dictionary")

    if not os.path.isfile(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Excel template not found at path:\n{TEMPLATE_PATH}"
        )

    try:
        wb = load_workbook(TEMPLATE_PATH)
    except InvalidFileException:
        raise RuntimeError(
            "Template file is not a valid Excel (.xlsx). "
            "Open it in Excel and re-save it as .xlsx."
        )
    except Exception as e:
        raise RuntimeError(
            f"Error loading Excel template:\n{str(e)}"
        )

    ws = wb.active

    # =====================================================
    # MAPEO 1:1 — AJUSTA SEGÚN TU TEMPLATE REAL
    # =====================================================
    ws["B4"] = report.get("report_no", "")
    ws["E4"] = report.get("bl", "")

    ws["B6"] = report.get("inspection_place", "")
    ws["E6"] = report.get("vessel", "")

    ws["B8"] = report.get("contact_datetime", "")
    ws["E8"] = report.get("appointment", "")

    ws["B12"] = report.get("goods_description", "")
    ws["B18"] = report.get("damage_details", "")
    ws["B24"] = report.get("remarks", "")
    ws["B30"] = report.get("conclusion", "")

    # Checks
    ws["C40"] = "✔" if report.get("container_size_20") else ""
    ws["D40"] = "✔" if report.get("container_size_40") else ""

    # =====================================================
    # GENERACIÓN SEGURA DE ARCHIVO TEMPORAL
    # =====================================================
    try:
        fd, output_path = tempfile.mkstemp(
            suffix=".xlsx",
            prefix=f"container_report_{report.get('id', 'x')}_"
        )
        os.close(fd)

        wb.save(output_path)

    except Exception as e:
        raise RuntimeError(
            f"Error generating Excel file:\n{str(e)}"
        )

    return output_path
