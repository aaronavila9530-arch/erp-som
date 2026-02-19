import os
import tempfile
from datetime import datetime, date
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "draft_survey_template.xlsx"
    )
)


class DraftSurveyExcelGenerator:

    def _safe_set(self, ws: Worksheet, cell: str, value):
        # Mismo enfoque que ya usas en ContainerReportExcelGenerator (merged cells safe)
        for merged in ws.merged_cells.ranges:
            if cell in merged:
                ws.cell(row=merged.min_row, column=merged.min_col).value = value
                return
        ws[cell].value = value

    def _safe_set_date(self, ws: Worksheet, cell: str, value):
        """
        Acepta:
        - dd-mm-yyyy
        - yyyy-mm-dd
        - ISO datetime
        """
        if not value:
            return

        parsed = None

        try:
            if isinstance(value, (datetime, date)):
                parsed = value
            elif isinstance(value, str):
                v = value.strip()

                # yyyy-mm-dd...
                if "-" in v and len(v.split("-")[0]) == 4:
                    parsed = datetime.strptime(v.split(" ")[0], "%Y-%m-%d")
                else:
                    # dd-mm-yyyy...
                    parsed = datetime.strptime(v.split(" ")[0], "%d-%m-%Y")
        except Exception:
            parsed = None

        if not parsed:
            return

        for merged in ws.merged_cells.ranges:
            if cell in merged:
                c = ws.cell(row=merged.min_row, column=merged.min_col)
                c.value = parsed
                c.number_format = "DD-MM-YYYY"
                return

        ws[cell].value = parsed
        ws[cell].number_format = "DD-MM-YYYY"


def generate_draft_survey_excel(payload: dict) -> str:
    """
    Genera un XLSX temporal usando el template y payload del DraftSurveyForm.
    Mantiene fórmulas del template (Excel recalcula al abrir).
    """
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Draft Survey template not found: {TEMPLATE_PATH}")

    gen = DraftSurveyExcelGenerator()

    # data_only=False => preserva fórmulas
    wb = load_workbook(TEMPLATE_PATH, data_only=False)
    ws = wb.active

    # ✅ Forzar recálculo al abrir en Excel
    try:
        wb.calculation.fullCalcOnLoad = True
    except Exception:
        pass

    # =========================================================
    # MAPPING: payload key -> cell
    # =========================================================
    # 🔥 Aquí pones el mapeo real según tu template.
    # Te dejo ejemplos típicos + debes ajustar celdas a tu archivo.
    map_text = {
        "vessel_mv": "C5",
        "survey_no": "H5",
        "vessel_previous_names": "C6",
        "survey_requested_by": "C10",
        "call_letters": "C7",
        "flag": "C8",
        "registry": "H8",
        "built_year": "C9",
        "by": "H9",
    }

    for k, cell in map_text.items():
        val = payload.get(k)
        if val not in [None, ""]:
            gen._safe_set(ws, cell, val)

    # Fechas ejemplo (ajusta)
    gen._safe_set_date(ws, "C15", payload.get("init_date"))
    gen._safe_set_date(ws, "H15", payload.get("final_date"))

    # Draft block ejemplo (ajusta)
    gen._safe_set(ws, "C20", payload.get("init_time_from"))
    gen._safe_set(ws, "D20", payload.get("init_time_to"))
    gen._safe_set(ws, "C21", payload.get("init_cargo"))
    gen._safe_set(ws, "C22", payload.get("init_port_from"))
    gen._safe_set(ws, "D22", payload.get("init_port_to"))

    # =========================================================
    # SAVE TEMP FILE
    # =========================================================
    fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(tmp_path)

    return tmp_path
