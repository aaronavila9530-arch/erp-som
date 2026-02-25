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

        "Draft": {
            "date_fields": ["init_date", "final_date"],
            "fields": {

                # =====================================================
                # INITIAL — TOP
                # =====================================================

                "init_date": "T2",
                "init_time_from": "T3",
                "init_time_to": "T4",
                "cargo": "AB2",
                "port_from": "AB3",
                "port_to": "AB4",

                # =====================================================
                # INITIAL — DRAFT READINGS
                # =====================================================

                "init_draft_fwd_port": "A8",
                "init_draft_fwd_stb": "F8",
                "init_draft_mid_port": "A9",
                "init_draft_mid_stb": "F9",
                "init_draft_aft_port": "A10",
                "init_draft_aft_stb": "F10",

                "init_draft_fwd_marks": "V8",
                "init_draft_mid_marks": "V9",
                "init_draft_aft_marks": "V10",

                "init_sg": "I13",
                "init_lpp": "M13",

                # =====================================================
                # INITIAL — FIGURES
                # =====================================================

                "init_tpc_p": "Q16",
                "init_tpc_s": "U16",
                "init_bl_figure": "M35",

                # =====================================================
                # INITIAL — DEDUCTIONS
                # =====================================================

                "init_ballast": "G18",
                "init_fresh_water": "G19",
                "init_fuel_oil": "G20",
                "init_diesel_oil": "G21",
                "init_lub_oil": "G22",
                "init_slop": "G23",
                "init_swimming_pool": "G24",
                "init_others": "G25",

                # =====================================================
                # INITIAL — HYDRO 1 (CUADRO 1)
                # 4 filas EXACTAS:
                #   F1: draft/disp/tpc/lcf
                #   F2: draft/disp/tpc/lcf
                #   F3: draft_mtc / mtc+50 / mtc-50
                #   F4: mtc+50 / mtc-50
                # =====================================================

                # Fila 1
                "init_hydro1_draft_1": "BG27",
                "init_hydro1_disp_1":  "BH27",
                "init_hydro1_tpc_1":   "BI27",
                "init_hydro1_lcf_1":   "BJ27",

                # Fila 2
                "init_hydro1_draft_2": "BG29",
                "init_hydro1_disp_2":  "BH29",
                "init_hydro1_tpc_2":   "BI29",
                "init_hydro1_lcf_2":   "BJ29",

                # Fila 3
                "init_hydro1_draft_mtc":  "BG31",
                "init_hydro1_mtc_p50_1":  "BH31",
                "init_hydro1_mtc_m50_1":  "BJ31",

                # Fila 4
                "init_hydro1_mtc_p50_2":  "BH33",
                "init_hydro1_mtc_m50_2":  "BJ33",


                # =====================================================
                # INITIAL — HYDRO 2 (CUADRO 2)
                # MISMA ESTRUCTURA, SOLO CAMBIA EL BLOQUE DE CELDAS
                # =====================================================

                # Fila 1
                "init_hydro2_draft_1": "BG36",
                "init_hydro2_disp_1":  "BH36",
                "init_hydro2_tpc_1":   "BI36",
                "init_hydro2_lcf_1":   "BJ36",

                # Fila 2
                "init_hydro2_draft_2": "BG38",
                "init_hydro2_disp_2":  "BH38",
                "init_hydro2_tpc_2":   "BI38",
                "init_hydro2_lcf_2":   "BJ38",

                # Fila 3
                "init_hydro2_draft_mtc":  "BG40",
                "init_hydro2_mtc_p50_1":  "BH40",
                "init_hydro2_mtc_m50_1":  "BJ40",

                # Fila 4
                "init_hydro2_mtc_p50_2":  "BH42",
                "init_hydro2_mtc_m50_2":  "BJ42",

                # =====================================================
                # FINAL — TOP
                # =====================================================

                "final_date": "AS2",
                "final_time_from": "AS3",
                "final_time_to": "AS4",

                # =====================================================
                # FINAL — DRAFT READINGS
                # =====================================================

                "final_draft_fwd_port": "Z8",
                "final_draft_fwd_stb": "Z9",
                "final_draft_mid_port": "Z10",
                "final_draft_mid_stb": "AD8",
                "final_draft_aft_port": "AD9",
                "final_draft_aft_stb": "AD10",

                "final_draft_fwd_marks": "AU8",
                "final_draft_mid_marks": "AU9",
                "final_draft_aft_marks": "AU10",

                "final_sg": "AH13",
                "final_lpp": "AL13",

                # =====================================================
                # FINAL — FIGURES
                # =====================================================

                "final_tpc_p": "AP16",
                "final_tpc_s": "AT16",
                "final_bl_figure": "AG35",

                # =====================================================
                # FINAL — DEDUCTIONS
                # =====================================================

                "final_fuel_oil": "AS20",
                "final_diesel_oil": "AS21",
                "final_lub_oil": "AS22",
                "final_slop": "AS23",
                "final_swimming_pool": "AS24",
                "final_others": "AS25",

                # =====================================================
                # FINAL — HYDRO 1 (CUADRO 1 — 4 FILAS)
                # =====================================================

                # Fila 1
                "final_hydro1_draft_1": "BG27",
                "final_hydro1_disp_1":  "BH27",
                "final_hydro1_tpc_1":   "BI27",
                "final_hydro1_lcf_1":   "BJ27",

                # Fila 2
                "final_hydro1_draft_2": "BG29",
                "final_hydro1_disp_2":  "BH29",
                "final_hydro1_tpc_2":   "BI29",
                "final_hydro1_lcf_2":   "BJ29",

                # Fila 3
                "final_hydro1_draft_mtc": "BG31",
                "final_hydro1_mtc_p50_1": "BH31",
                "final_hydro1_mtc_m50_1": "BJ31",

                # Fila 4
                "final_hydro1_mtc_p50_2": "BH33",
                "final_hydro1_mtc_m50_2": "BJ33",


                # =====================================================
                # FINAL — HYDRO 2 (CUADRO 2 — 4 FILAS)
                # =====================================================

                # Fila 1
                "final_hydro2_draft_1": "BG36",
                "final_hydro2_disp_1":  "BH36",
                "final_hydro2_tpc_1":   "BI36",
                "final_hydro2_lcf_1":   "BJ36",

                # Fila 2
                "final_hydro2_draft_2": "BG38",
                "final_hydro2_disp_2":  "BH38",
                "final_hydro2_tpc_2":   "BI38",
                "final_hydro2_lcf_2":   "BJ38",

                # Fila 3
                "final_hydro2_draft_mtc": "BG40",
                "final_hydro2_mtc_p50_1": "BH40",
                "final_hydro2_mtc_m50_1": "BJ40",

                # Fila 4
                "final_hydro2_mtc_p50_2": "BH42",
                "final_hydro2_mtc_m50_2": "BJ42",

                # =====================================================
                # SIGNATURES
                # =====================================================

                "chief_officer": "AN29",
                "master": "AN32",
                "msl_surveyor": "AN35",
            }
        }   # ← cierra "Draft"
        ,

        "Deductions": {
            "date_fields": [],
            "fields": {

                # =====================================================
                # INITIAL BALLAST (SOUNDING + VOLUME + DENSITY)
                # =====================================================

                "init_FPT_sounding": "G11",
                "init_FPT_volume": "J11",
                "init_FPT_density": "M11",

                "init_WBT 1P_sounding": "G12",
                "init_WBT 1P_volume": "J12",
                "init_WBT 1P_density": "M12",

                "init_WBT 1S_sounding": "G13",
                "init_WBT 1S_volume": "J13",
                "init_WBT 1S_density": "M13",

                "init_WBT 2P_sounding": "G14",
                "init_WBT 2P_volume": "J14",
                "init_WBT 2P_density": "M14",

                "init_WBT 2S_sounding": "G15",
                "init_WBT 2S_volume": "J15",
                "init_WBT 2S_density": "M15",

                "init_WBT 3P_sounding": "G16",
                "init_WBT 3P_volume": "J16",
                "init_WBT 3P_density": "M16",

                "init_WBT 3S_sounding": "G17",
                "init_WBT 3S_volume": "J17",
                "init_WBT 3S_density": "M17",

                "init_WBT 4P_sounding": "G18",
                "init_WBT 4P_volume": "J18",
                "init_WBT 4P_density": "M18",

                "init_WBT 4S_sounding": "G19",
                "init_WBT 4S_volume": "J19",
                "init_WBT 4S_density": "M19",

                "init_WBT 5P_sounding": "G20",
                "init_WBT 5P_volume": "J20",
                "init_WBT 5P_density": "M20",

                "init_WBT 5S_sounding": "G21",
                "init_WBT 5S_volume": "J21",
                "init_WBT 5S_density": "M21",

                "init_APT_sounding": "G22",
                "init_APT_volume": "J22",
                "init_APT_density": "M22",

                "init_SLOP TANK_sounding": "G23",
                "init_SLOP TANK_volume": "J23",
                "init_SLOP TANK_density": "M23",

                "init_FW WASH_sounding": "G24",
                "init_FW WASH_volume": "J24",
                "init_FW WASH_density": "M24",

                # --------- TANQUES 15–20 (AJUSTAR NOMBRES SEGÚN TEMPLATE) ---------

                "init_WBT 6P_sounding": "G25",
                "init_WBT 6P_volume": "J25",
                "init_WBT 6P_density": "M25",

                "init_WBT 6S_sounding": "G26",
                "init_WBT 6S_volume": "J26",
                "init_WBT 6S_density": "M26",

                "init_WBT 7P_sounding": "G27",
                "init_WBT 7P_volume": "J27",
                "init_WBT 7P_density": "M27",

                "init_WBT 7S_sounding": "G28",
                "init_WBT 7S_volume": "J28",
                "init_WBT 7S_density": "M28",

                "init_WBT 8P_sounding": "G29",
                "init_WBT 8P_volume": "J29",
                "init_WBT 8P_density": "M29",

                "init_WBT 8S_sounding": "G30",
                "init_WBT 8S_volume": "J30",
                "init_WBT 8S_density": "M30",

                # =====================================================
                # INITIAL FRESH WATER (HEIGHT + VOLUME)
                # =====================================================

                "init_FW P_height": "D47",
                "init_FW P_volume": "J47",

                "init_FW S_height": "D48",
                "init_FW S_volume": "J48",

                "init_FW DIST_height": "D49",
                "init_FW DIST_volume": "J49",

                # =====================================================
                # FINAL BALLAST (SOUNDING + VOLUME + DENSITY)
                # =====================================================

                "final_FPT_sounding": "W11",
                "final_FPT_volume": "Z11",
                "final_FPT_density": "AC11",

                "final_WBT 1P_sounding": "W12",
                "final_WBT 1P_volume": "Z12",
                "final_WBT 1P_density": "AC12",

                "final_WBT 1S_sounding": "W13",
                "final_WBT 1S_volume": "Z13",
                "final_WBT 1S_density": "AC13",

                "final_WBT 2P_sounding": "W14",
                "final_WBT 2P_volume": "Z14",
                "final_WBT 2P_density": "AC14",

                "final_WBT 2S_sounding": "W15",
                "final_WBT 2S_volume": "Z15",
                "final_WBT 2S_density": "AC15",

                "final_WBT 3P_sounding": "W16",
                "final_WBT 3P_volume": "Z16",
                "final_WBT 3P_density": "AC16",

                "final_WBT 3S_sounding": "W17",
                "final_WBT 3S_volume": "Z17",
                "final_WBT 3S_density": "AC17",

                "final_WBT 4P_sounding": "W18",
                "final_WBT 4P_volume": "Z18",
                "final_WBT 4P_density": "AC18",

                "final_WBT 4S_sounding": "W19",
                "final_WBT 4S_volume": "Z19",
                "final_WBT 4S_density": "AC19",

                "final_WBT 5P_sounding": "W20",
                "final_WBT 5P_volume": "Z20",
                "final_WBT 5P_density": "AC20",

                "final_WBT 5S_sounding": "W21",
                "final_WBT 5S_volume": "Z21",
                "final_WBT 5S_density": "AC21",

                "final_APT_sounding": "W22",
                "final_APT_volume": "Z22",
                "final_APT_density": "AC22",

                "final_SLOP TANK_sounding": "W23",
                "final_SLOP TANK_volume": "Z23",
                "final_SLOP TANK_density": "AC23",

                "final_FW WASH_sounding": "W24",
                "final_FW WASH_volume": "Z24",
                "final_FW WASH_density": "AC24",

                # --------- TANQUES 15–20 (AJUSTAR NOMBRES SEGÚN TEMPLATE) ---------

                "final_WBT 6P_sounding": "W25",
                "final_WBT 6P_volume": "Z25",
                "final_WBT 6P_density": "AC25",

                "final_WBT 6S_sounding": "W26",
                "final_WBT 6S_volume": "Z26",
                "final_WBT 6S_density": "AC26",

                "final_WBT 7P_sounding": "W27",
                "final_WBT 7P_volume": "Z27",
                "final_WBT 7P_density": "AC27",

                "final_WBT 7S_sounding": "W28",
                "final_WBT 7S_volume": "Z28",
                "final_WBT 7S_density": "AC28",

                "final_WBT 8P_sounding": "W29",
                "final_WBT 8P_volume": "Z29",
                "final_WBT 8P_density": "AC29",

                "final_WBT 8S_sounding": "W30",
                "final_WBT 8S_volume": "Z30",
                "final_WBT 8S_density": "AC30",

                # =====================================================
                # FINAL FRESH WATER (HEIGHT + VOLUME)
                # =====================================================

                "final_FW P_height": "W47",
                "final_FW P_volume": "AC47",

                "final_FW S_height": "W48",
                "final_FW S_volume": "AC48",

                "final_FW DIST_height": "W49",
                "final_FW DIST_volume": "AC49",
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
            # -------------------------------------------------
            # 1) Si ya es datetime o date → usar directo
            # -------------------------------------------------
            if isinstance(value, (datetime, date)):
                parsed = value

            # -------------------------------------------------
            # 2) Si es string → intentar múltiples formatos
            # -------------------------------------------------
            elif isinstance(value, str):

                v = value.strip().split(" ")[0]

                # Intentar formatos comunes usados en el ERP
                date_formats = [
                    "%m-%d-%Y",  # 02-20-2026  ← DateEntry actual
                    "%d-%m-%Y",  # 20-02-2026
                    "%Y-%m-%d",  # 2026-02-20
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                    "%Y/%m/%d",
                ]

                for fmt in date_formats:
                    try:
                        parsed = datetime.strptime(v, fmt)
                        break
                    except Exception:
                        continue

        except Exception:
            parsed = None

        # -------------------------------------------------
        # Si no logró parsear, salir silenciosamente
        # -------------------------------------------------
        if not parsed:
            return

        # -------------------------------------------------
        # Manejo seguro de merged cells
        # -------------------------------------------------
        for merged in ws.merged_cells.ranges:
            if cell in merged:
                c = ws.cell(row=merged.min_row, column=merged.min_col)
                c.value = parsed
                c.number_format = "DD-MM-YYYY"
                return

        # -------------------------------------------------
        # Celda normal
        # -------------------------------------------------
        ws[cell].value = parsed
        ws[cell].number_format = "DD-MM-YYYY"


def generate_draft_survey_excel(payload: dict, variant: str = "final") -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Draft Survey template not found: {TEMPLATE_PATH}")

    gen = DraftSurveyExcelGenerator()
    wb = load_workbook(TEMPLATE_PATH, data_only=False)

    # =========================================================
    # VARIANT CONTROL (FINAL / INTERMEDIATE)
    # =========================================================
    try:

        title_text = "FINAL DRAFT SURVEY"
        if (variant or "").lower() == "intermediate":
            title_text = "INTERMEDIATE DRAFT SURVEY"

        if "Draft" in wb.sheetnames:

            ws_title = wb["Draft"]

            # -------------------------------------------------
            # FORCE WRITE (MERGE-SAFE, UNMERGE/REMARGE)
            # -------------------------------------------------
            def _force_write(ws: Worksheet, target_cell: str, value):

                # 1) Buscar si target_cell cae dentro de un merged range
                hit_range = None
                for mr in list(ws.merged_cells.ranges):
                    # mr.bounds => (min_col, min_row, max_col, max_row)
                    min_col, min_row, max_col, max_row = mr.bounds
                    # Convertir target_cell a (col, row)
                    from openpyxl.utils.cell import coordinate_to_tuple
                    row, col = coordinate_to_tuple(target_cell)

                    if (min_row <= row <= max_row) and (min_col <= col <= max_col):
                        hit_range = str(mr)  # ejemplo: "AO1:AR1"
                        break

                # 2) Si está dentro de un merge → UNMERGE, escribir, MERGE
                if hit_range:
                    ws.unmerge_cells(hit_range)

                    # Escribir en la celda objetivo (ya no está merged)
                    ws[target_cell].value = value

                    # Excel suele mostrar el valor del top-left al volver a mergear,
                    # así que también lo ponemos.
                    from openpyxl.utils.cell import range_boundaries, get_column_letter
                    min_c, min_r, max_c, max_r = range_boundaries(hit_range)
                    top_left = f"{get_column_letter(min_c)}{min_r}"
                    ws[top_left].value = value

                    ws.merge_cells(hit_range)
                    return

                # 3) Si no estaba merged → escribir normal
                ws[target_cell].value = value

            # 🔥 Forzar ambos
            _force_write(ws_title, "Z6", title_text)
            _force_write(ws_title, "AP1", title_text)

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