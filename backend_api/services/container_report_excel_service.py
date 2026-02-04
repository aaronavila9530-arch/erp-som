import os
import tempfile
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from datetime import datetime


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "container_report_template.xlsx"
    )
)


# =====================================================
# SAFE WRITE (SOPORTA MERGED CELLS)
# =====================================================
def _safe_set(ws: Worksheet, cell: str, value):
    for merged in ws.merged_cells.ranges:
        if cell in merged:
            ws.cell(
                row=merged.min_row,
                column=merged.min_col
            ).value = value
            return
    ws[cell].value = value


def _safe_set_date(ws: Worksheet, cell: str, value):
    if not value:
        return

    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
    except Exception:
        pass

    for merged in ws.merged_cells.ranges:
        if cell in merged:
            c = ws.cell(
                row=merged.min_row,
                column=merged.min_col
            )
            c.value = value
            c.number_format = "DD-MM-YYYY"
            return

    ws[cell].value = value
    ws[cell].number_format = "DD-MM-YYYY"


def _safe_hyperlink(ws: Worksheet, cell: str, url: str):
    for merged in ws.merged_cells.ranges:
        if cell in merged:
            c = ws.cell(
                row=merged.min_row,
                column=merged.min_col
            )
            c.value = url
            c.hyperlink = url
            c.style = "Hyperlink"
            return

    ws[cell].value = url
    ws[cell].hyperlink = url
    ws[cell].style = "Hyperlink"


def _check(ws: Worksheet, cell: str, flag: bool):
    _safe_set(ws, cell, "✔" if flag else "")


# =====================================================
# MAIN GENERATOR
# =====================================================
def generate_container_report_excel(report: dict) -> str:
    """
    Genera Excel 1:1 del Container Report usando template.
    """

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Excel template not found: {TEMPLATE_PATH}")

    wb = load_workbook(TEMPLATE_PATH)
    ws = wb.active

    # =====================================================
    # REPORT LINK (AGREGADO)
    # =====================================================
    _safe_set(ws, "AD3", report.get("linked_report_number"))
    _safe_set(ws, "Q3", report.get("container_type_text"))

    _safe_set(ws, "C5", report.get("report_no"))
    _safe_set(ws, "E6", report.get("bl"))
    _safe_set(ws, "E7", report.get("seals"))
    _safe_set(ws, "E8", report.get("appointment"))
    _safe_set(ws, "E9", report.get("shippers"))

    _safe_set(ws, "Q5", report.get("inspection_place"))
    _safe_set(ws, "Q6", report.get("contact_person"))
    _safe_set(ws, "Z8", report.get("on_behalf_of"))
    _safe_set(ws, "Z9", report.get("consignee_notify"))

    _safe_set(ws, "AB5", report.get("vessel"))

    # =====================================================
    # DATES — FORMAT DD-MM-YYYY (SAFE)
    # =====================================================
    _safe_set_date(ws, "AD6", report.get("contact_datetime"))
    _safe_set_date(ws, "P7", report.get("init_inspection_datetime"))
    _safe_set_date(ws, "V7", report.get("init_to"))
    _safe_set_date(ws, "AD7", report.get("final_inspection_datetime"))
    _safe_set_date(ws, "AI7", report.get("final_to"))

    # =====================================================
    # CONTAINER DESCRIPTION
    # =====================================================
    _check(ws, "A12", report.get("container_size_20"))
    _check(ws, "A13", report.get("container_size_40"))

    _check(ws, "E12", report.get("container_type_dry"))
    _check(ws, "E13", report.get("container_type_reefer"))
    _check(ws, "I12", report.get("container_type_iso"))
    _check(ws, "I13", report.get("container_type_flat_rack"))

    _check(ws, "N12", report.get("container_load_fcl"))
    _check(ws, "N13", report.get("container_load_lcl"))

    # =====================================================
    # CAUSE OF INSPECTION
    # =====================================================
    _check(ws, "Q12", report.get("cause_seals_bl"))
    _check(ws, "Q13", report.get("cause_change_seals"))
    _check(ws, "W12", report.get("cause_customs"))
    _check(ws, "W13", report.get("cause_transfer"))
    _check(ws, "AB12", report.get("cause_leaking"))
    _check(ws, "AB13", report.get("cause_damage"))
    _check(ws, "AG12", report.get("cause_stuff_condition"))
    _check(ws, "AG13", report.get("cause_stuff_condition"))

    _safe_set(ws, "I14", report.get("cause_detail"))

    # =====================================================
    # GOODS & PACKAGES
    # =====================================================
    _safe_set(ws, "B17", report.get("goods_description"))

    _check(ws, "U17", report.get("package_carton"))
    _check(ws, "U18", report.get("package_bags"))
    _check(ws, "U19", report.get("package_boxes"))
    _check(ws, "Y17", report.get("package_drums"))
    _check(ws, "Y18", report.get("package_pallets"))
    _check(ws, "Y19", report.get("package_bulk"))
    _check(ws, "AB17", report.get("package_bales"))
    _check(ws, "AB18", report.get("package_crates"))
    _check(ws, "AB19", report.get("package_other"))

    _safe_set(ws, "AF17", report.get("qty_1_left"))
    _safe_set(ws, "AI17", report.get("qty_1_right"))
    _safe_set(ws, "AF18", report.get("qty_2_left"))
    _safe_set(ws, "AI18", report.get("qty_2_right"))
    _safe_set(ws, "AF19", report.get("qty_3_left"))
    _safe_set(ws, "AI19", report.get("qty_3_right"))

    _safe_set(ws, "B22", report.get("package_marking"))
    _safe_set(ws, "B25", report.get("goods_condition"))

    # =====================================================
    # NARRATIVES
    # =====================================================
    _safe_set(ws, "B27", report.get("damage_details"))
    _safe_set(ws, "B31", report.get("remarks"))
    _safe_set(ws, "B37", report.get("conclusion"))

    picture_link = report.get("picture_link")
    if picture_link:
        _safe_hyperlink(ws, "B42", picture_link)

    # =====================================================
    # DOCUMENTS
    # =====================================================
    _check(ws, "A42", report.get("doc_bl"))
    _check(ws, "A43", report.get("doc_packing_list"))
    _check(ws, "A44", report.get("doc_shipping_invoice"))
    _check(ws, "A45", report.get("doc_cargo_manifest"))
    _check(ws, "A46", report.get("doc_commercial_invoice"))
    _check(ws, "A47", report.get("doc_delivery_record"))
    _check(ws, "A48", report.get("doc_notice_loss"))
    _check(ws, "A49", report.get("doc_insurance_policy"))
    _check(ws, "A50", report.get("doc_other"))

    # =====================================================
    # QUALITY
    # =====================================================
    _check(ws, "J42", report.get("quality_packing_exam"))
    _check(ws, "J43", report.get("quality_un_witness"))
    _check(ws, "J44", report.get("quality_visual_exam"))
    _check(ws, "J45", report.get("quality_product_exam"))
    _check(ws, "J46", report.get("quality_documents"))
    _check(ws, "J47", report.get("quality_sanitary_cert"))
    _check(ws, "J48", report.get("quality_phytosanitary_cert"))
    _check(ws, "J49", report.get("quality_factory_cert"))
    _check(ws, "J50", report.get("quality_origin_cert"))

    # =====================================================
    # INSPECTED CONTAINER
    # =====================================================
    _safe_set(ws, "W45", report.get("ic_manuf"))
    _safe_set(ws, "W46", report.get("ic_csc"))
    _safe_set(ws, "X47", report.get("ic_max_gw"))
    _safe_set(ws, "X48", report.get("ic_tare"))

    # =====================================================
    # GENERAL DETAILS
    # =====================================================
    _check(ws, "P55", report.get("new_commodity"))
    _check(ws, "V55", report.get("used_commodity"))
    _safe_set(ws, "W52", report.get("net_weight"))
    _safe_set(ws, "W53", report.get("gross_weight"))
    _safe_set(ws, "W54", report.get("volume"))

    # =====================================================
    # TRANSFER TO CONTAINER
    # =====================================================
    _safe_set(ws, "AF45", report.get("tr_number"))
    _safe_set(ws, "AF46", report.get("tr_manuf"))
    _safe_set(ws, "AF47", report.get("tr_csc"))
    _safe_set(ws, "AF48", report.get("tr_seal"))
    _safe_set(ws, "AG49", report.get("tr_max_gw"))
    _safe_set(ws, "AG50", report.get("tr_tare"))

    # =====================================================
    # SCOPE OF INSPECTION
    # =====================================================
    _check(ws, "AB52", report.get("scope_100"))
    _check(ws, "AB53", report.get("scope_random"))
    _safe_set(ws, "AB54", report.get("scope_items"))

    # =====================================================
    # PERSONS PRESENT
    # =====================================================
    _safe_set(ws, "B56", report.get("person_1_name"))
    _safe_set(ws, "N56", report.get("person_1_position"))

    _safe_set(ws, "B57", report.get("person_2_name"))
    _safe_set(ws, "N57", report.get("person_2_position"))

    _safe_set(ws, "B58", report.get("person_3_name"))
    _safe_set(ws, "N58", report.get("person_3_position"))

    # =====================================================
    # SAVE TEMP FILE
    # =====================================================
    fd, output_path = tempfile.mkstemp(
        suffix=".xlsx",
        prefix=f"container_report_{report.get('id', 'x')}_"
    )
    os.close(fd)

    wb.save(output_path)
    return output_path
