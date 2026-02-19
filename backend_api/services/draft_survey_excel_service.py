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

    # =========================================================
    # MASTER MAPPING STRUCTURE (FULL TEMPLATE 1:1)
    # =========================================================
    EXCEL_MAPPING = {

        "GENERAL": {
            "date_fields": [],
            "fields": {

                # HEADER
                "vessel_mv": "X1",
                "survey_no": "X3",
                "call_letters": "AI3",
                "vessel_previous_names": "J6",

                # REGISTRY BLOCK
                "flag": "C8",
                "registry": "M8",
                "built_year": "W8",
                "by": "AA8",

                # OFFICERS
                "master": "H10",
                "chief_officer": "H11",
                "chief_engineer": "H12",
                "witness_draughts": "H13",
                "witness_sounding": "H14",

                # SURVEY INFO
                "initial_surveyors": "AB10",
                "final_surveyors": "AB11",
                "survey_requested_by": "AB12",
                "on_account_of": "AB13",
                "attended_also_by": "AB14",

                # LOCATIONS
                "init_ships_location": "H16",
                "final_ships_location": "AB16",

                # DIMENSIONS
                "length_overall": "M18",
                "length_between_pp": "M19",
                "extreme_breadth": "M20",
                "moulded_breadth": "M21",
                "depth_overall_incl_keel_plate": "M22",
                "moulded_depth": "M23",
                "summer_draught": "M24",
                "summer_freeboard": "M25",

                # CONSTANTS / TONNAGE
                "constant_declared": "AG18",
                "constant_calculated": "AG19",
                "light_displacement": "AG20",
                "light_shipweight_plan": "AG21",
                "summer_displacement": "AG22",
                "summer_deadweight": "AG23",
                "net_register_tons": "AG24",
                "gross_register_tons": "AG25",

                # HYDROSTATIC
                "hydro_tables_issued": "L32",
            }
        },

        "DRAFT": {
            "date_fields": ["init_date", "final_date"],
            "fields": {

                # =====================================================
                # INITIAL BLOCK
                # =====================================================

                "init_date": "C4",
                "init_time_from": "C5",
                "init_time_to": "D5",
                "init_cargo": "F5",
                "init_port_from": "C6",
                "init_port_to": "D6",

                # DRAFT READINGS
                "init_draft_fwd_port": "B12",
                "init_draft_fwd_stb": "C12",
                "init_draft_mid_port": "B13",
                "init_draft_mid_stb": "C13",
                "init_draft_aft_port": "B14",
                "init_draft_aft_stb": "C14",

                # TRIM BLOCK
                "init_atrim": "B16",
                "init_ttrim": "C16",
                "init_sg": "D16",
                "init_lpp": "E16",
                "init_mmm": "H16",

                # HYDRO BLOCK
                "init_lcf": "B18",
                "init_tpc": "C18",
                "init_mtc_plus_50": "D18",
                "init_mtc_minus_50": "E18",

                # DEDUCTIONS
                "init_ballast": "B20",
                "init_fresh_water": "B21",
                "init_fuel_oil": "B22",
                "init_diesel_oil": "B23",
                "init_lub_oil": "B24",
                "init_slop": "B25",
                "init_swimming_pool": "B26",
                "init_others": "B27",
                "init_deductions": "E30",

                # CONDITIONS
                "cond_sounding_pipes": "B34",
                "cond_draft_marks": "B35",
                "cond_swell_initial": "B36",
                "cond_swell_final": "B37",
                "cond_hydrostatic_tables": "B38",
                "cond_distance_to_marks": "B39",
                "cond_ballast_tables": "B40",

                # =====================================================
                # FINAL BLOCK
                # =====================================================

                "final_date": "J4",
                "final_time_from": "J5",
                "final_time_to": "K5",

                "final_draft_fwd_port": "I12",
                "final_draft_fwd_stb": "J12",
                "final_draft_mid_port": "I13",
                "final_draft_mid_stb": "J13",
                "final_draft_aft_port": "I14",
                "final_draft_aft_stb": "J14",

                "final_atrim": "I16",
                "final_ttrim": "J16",
                "final_sg": "K16",
                "final_lpp": "L16",
                "final_mmm": "O16",

                "final_lcf": "I18",
                "final_tpc": "J18",
                "final_mtc_plus_50": "K18",
                "final_mtc_minus_50": "L18",

                "final_ballast": "I20",
                "final_fresh_water": "I21",
                "final_fuel_oil": "I22",
                "final_diesel_oil": "I23",
                "final_lub_oil": "I24",
                "final_slop": "I25",
                "final_swimming_pool": "I26",
                "final_others": "I27",
                "final_deductions": "L30"
            }
        }
    }

    # =========================================================
    # SAFE SETTERS (MERGE SAFE + NUMERIC SAFE + BOOL SAFE)
    # =========================================================
    def _safe_set(self, ws: Worksheet, cell: str, value):

        if value in [None, ""]:
            return

        # Normalizar booleanos a YES/NO si aplica
        if isinstance(value, bool):
            value = "YES" if value else "NO"

        # Intentar convertir a número si es numérico
        try:
            if isinstance(value, str):
                v = value.replace(",", ".")
                if v.replace(".", "", 1).isdigit():
                    value = float(v)
        except Exception:
            pass

        # Manejo de merged cells
        for merged in ws.merged_cells.ranges:
            if cell in merged:
                ws.cell(row=merged.min_row, column=merged.min_col).value = value
                return

        ws[cell].value = value


    def _safe_set_date(self, ws: Worksheet, cell: str, value):

        if not value:
            return

        parsed = None

        try:
            if isinstance(value, (datetime, date)):
                parsed = value
            elif isinstance(value, str):
                v = value.strip()

                if "-" in v and len(v.split("-")[0]) == 4:
                    parsed = datetime.strptime(v.split(" ")[0], "%Y-%m-%d")
                else:
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

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Draft Survey template not found: {TEMPLATE_PATH}")

    gen = DraftSurveyExcelGenerator()
    wb = load_workbook(TEMPLATE_PATH, data_only=False)

    try:
        wb.calculation.fullCalcOnLoad = True
    except Exception:
        pass

    # =========================================================
    # APPLY MULTI-SHEET MAPPING
    # =========================================================
    for sheet_name, config in gen.EXCEL_MAPPING.items():

        if sheet_name not in wb.sheetnames:
            continue

        ws = wb[sheet_name]

        for field, cell in config["fields"].items():

            value = payload.get(field)

            if value in [None, ""]:
                continue

            if field in config["date_fields"]:
                gen._safe_set_date(ws, cell, value)
            else:
                gen._safe_set(ws, cell, value)

    fd, tmp_path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    wb.save(tmp_path)

    return tmp_path
