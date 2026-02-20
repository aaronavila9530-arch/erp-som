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

        "General": {
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

        "draft": {
            "date_fields": ["init_date", "final_date"],
            "fields": {

                # =====================================================
                # INITIAL BLOCK
                # =====================================================

                "init_date": "T2",
                "init_time_from": "T3",
                "init_time_to": "T4",
                "init_cargo": "AB2",
                "init_port_from": "AB3",
                "init_port_to": "AB4",

                # DRAFT READINGS
                "init_draft_fwd_port": "A8",
                "init_draft_fwd_stb": "A9",
                "init_draft_mid_port": "A10",
                "init_draft_mid_stb": "E8",
                "init_draft_aft_port": "E9",
                "init_draft_aft_stb": "E10",

                # TRIM BLOCK
                "init_sg": "I13",
                "init_lpp": "M13",

                # ============================
                # NUEVOS CAMPOS INITIAL
                # ============================

                "init_tpc_p": "O16",
                "init_tpc_s": "U16",
                "init_bl_figure": "M35",

                # ============================
                # HYDRO INITIAL (YELLOW)
                # ============================

                "init_hydro_draft": "I28",
                "init_hydro_mtc_plus_50": "I29",
                "init_hydro_draft_minus": "I30",
                "init_hydro_draft_plus": "M28",
                "init_hydro_mtc_minus_50": "M29",
                "init_hydro_lcf": "M30",

                # DEDUCTIONS
                "init_ballast": "G18",
                "init_fresh_water": "G19",
                "init_fuel_oil": "G20",
                "init_diesel_oil": "G21",
                "init_lub_oil": "G22",
                "init_slop": "G23",
                "init_swimming_pool": "G24",
                "init_others": "G25",

                # =====================================================
                # FINAL BLOCK
                # =====================================================

                "final_date": "AS2",
                "final_time_from": "AS3",
                "final_time_to": "AS4",

                "final_draft_fwd_port": "Z8",
                "final_draft_fwd_stb": "Z9",
                "final_draft_mid_port": "Z10",
                "final_draft_mid_stb": "AD8",
                "final_draft_aft_port": "AD9",
                "final_draft_aft_stb": "AD10",

                "final_sg": "AH13",

                # ============================
                # NUEVOS CAMPOS FINAL
                # ============================

                "final_tpc_p": "AP16",
                "final_tpc_s": "AT16",
                "final_bl_figure": "AG35",

                # ============================
                # HYDRO FINAL (YELLOW)
                # ============================

                "final_hydro_draft": "AH28",
                "final_hydro_mtc_plus_50": "AH29",
                "final_hydro_draft_minus": "AH30",
                "final_hydro_draft_plus": "AL28",
                "final_hydro_mtc_minus_50": "AL29",
                "final_hydro_lcf": "AL30",

                "final_fuel_oil": "AS20",
                "final_diesel_oil": "AS21",
                "final_lub_oil": "AS22",
                "final_slop": "AS23",
                "final_swimming_pool": "AS24",
                "final_others": "AS25",

                # =====================================================
                # FIRMAS
                # =====================================================

                "chief_officer": "AN29",
                "master": "AN32",
                "msl_surveyor": "AN35",
            }
        },

        "deductions": {
            "date_fields": [],
            "fields": {

                # =====================================================
                # INITIAL BALLAST
                # =====================================================

                "init_FPT_sounding": "D8",
                "init_FPT_volume": "E8",
                "init_FPT_density": "F8",

                "init_WBT 1P_sounding": "D9",
                "init_WBT 1P_volume": "E9",
                "init_WBT 1P_density": "F9",

                "init_WBT 1S_sounding": "D10",
                "init_WBT 1S_volume": "E10",
                "init_WBT 1S_density": "F10",

                "init_WBT 2P_sounding": "D11",
                "init_WBT 2P_volume": "E11",
                "init_WBT 2P_density": "F11",

                "init_WBT 2S_sounding": "D12",
                "init_WBT 2S_volume": "E12",
                "init_WBT 2S_density": "F12",

                "init_WBT 3P_sounding": "D13",
                "init_WBT 3P_volume": "E13",
                "init_WBT 3P_density": "F13",

                "init_WBT 3S_sounding": "D14",
                "init_WBT 3S_volume": "E14",
                "init_WBT 3S_density": "F14",

                "init_WBT 4P_sounding": "D15",
                "init_WBT 4P_volume": "E15",
                "init_WBT 4P_density": "F15",

                "init_WBT 4S_sounding": "D16",
                "init_WBT 4S_volume": "E16",
                "init_WBT 4S_density": "F16",

                "init_WBT 5P_sounding": "D17",
                "init_WBT 5P_volume": "E17",
                "init_WBT 5P_density": "F17",

                "init_WBT 5S_sounding": "D18",
                "init_WBT 5S_volume": "E18",
                "init_WBT 5S_density": "F18",

                "init_APT_sounding": "D19",
                "init_APT_volume": "E19",
                "init_APT_density": "F19",

                "init_SLOP TANK_volume": "E20",
                "init_FW WASH_volume": "E21",

                # =====================================================
                # INITIAL FRESH WATER
                # =====================================================

                "init_FW P_volume": "E24",

                "init_FW S_volume": "E25",

                "init_FW DIST_volume": "E26",

                # =====================================================
                # FINAL BALLAST
                # =====================================================

                "final_FPT_sounding": "J8",
                "final_FPT_volume": "K8",
                "final_FPT_density": "L8",

                "final_WBT 1P_sounding": "J9",
                "final_WBT 1P_volume": "K9",
                "final_WBT 1P_density": "L9",

                "final_WBT 1S_sounding": "J10",
                "final_WBT 1S_volume": "K10",
                "final_WBT 1S_density": "L10",

                "final_WBT 2P_sounding": "J11",
                "final_WBT 2P_volume": "K11",
                "final_WBT 2P_density": "L11",

                "final_WBT 2S_sounding": "J12",
                "final_WBT 2S_volume": "K12",
                "final_WBT 2S_density": "L12",

                "final_WBT 3P_sounding": "J13",
                "final_WBT 3P_volume": "K13",
                "final_WBT 3P_density": "L13",

                "final_WBT 3S_sounding": "J14",
                "final_WBT 3S_volume": "K14",
                "final_WBT 3S_density": "L14",

                "final_WBT 4P_sounding": "J15",
                "final_WBT 4P_volume": "K15",
                "final_WBT 4P_density": "L15",

                "final_WBT 4S_sounding": "J16",
                "final_WBT 4S_volume": "K16",
                "final_WBT 4S_density": "L16",

                "final_WBT 5P_sounding": "J17",
                "final_WBT 5P_volume": "K17",
                "final_WBT 5P_density": "L17",

                "final_WBT 5S_sounding": "J18",
                "final_WBT 5S_volume": "K18",
                "final_WBT 5S_density": "L18",

                "final_APT_sounding": "J19",
                "final_APT_volume": "K19",
                "final_APT_density": "L19",

                "final_SLOP TANK_sounding": "J20",
                "final_SLOP TANK_volume": "K20",
                "final_SLOP TANK_density": "L20",

                "final_FW WASH_sounding": "J21",
                "final_FW WASH_volume": "K21",
                "final_FW WASH_density": "L21",

                # =====================================================
                # FINAL FRESH WATER
                # =====================================================

                "final_FW P_volume": "K24",

                "final_FW S_volume": "K25",

                "final_FW DIST_volume": "K26",
            }
        }
    }   # ← ESTA llave faltaba (cierra EXCEL_MAPPING)

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
