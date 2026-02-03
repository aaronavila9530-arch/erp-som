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
    # HEADER / GENERAL
    # =====================================================
    _safe_set(ws, "B4", report.get("report_no"))
    _safe_set(ws, "E4", report.get("bl"))
    _safe_set(ws, "B5", report.get("seals"))
    _safe_set(ws, "E5", report.get("appointment"))
    _safe_set(ws, "B6", report.get("shippers"))

    _safe_set(ws, "B8", report.get("inspection_place"))
    _safe_set(ws, "E8", report.get("contact_person"))
    _safe_set(ws, "B9", report.get("on_behalf_of"))
    _safe_set(ws, "E9", report.get("consignee_notify"))

    _safe_set(ws, "B11", report.get("vessel"))
    _safe_set(ws, "E11", report.get("contact_datetime"))

    _safe_set(ws, "B12", report.get("init_inspection_datetime"))
    _safe_set(ws, "C12", report.get("init_to"))
    _safe_set(ws, "E12", report.get("final_inspection_datetime"))
    _safe_set(ws, "F12", report.get("final_to"))

    # =====================================================
    # CONTAINER DESCRIPTION (CHECKBOXES)
    # =====================================================
    _check(ws, "C15", report.get("container_size_20"))
    _check(ws, "D15", report.get("container_size_40"))

    _check(ws, "C16", report.get("container_type_dry"))
    _check(ws, "D16", report.get("container_type_reefer"))
    _check(ws, "E16", report.get("container_type_iso"))
    _check(ws, "F16", report.get("container_type_flat_rack"))

    _check(ws, "C17", report.get("container_load_fcl"))
    _check(ws, "D17", report.get("container_load_lcl"))

    # =====================================================
    # CAUSE OF INSPECTION
    # =====================================================
    _check(ws, "B20", report.get("cause_seals_bl"))
    _check(ws, "C20", report.get("cause_change_seals"))
    _check(ws, "D20", report.get("cause_customs"))
    _check(ws, "E20", report.get("cause_transfer"))
    _check(ws, "F20", report.get("cause_leaking"))
    _check(ws, "B21", report.get("cause_damage"))
    _check(ws, "C21", report.get("cause_stuff_condition"))

    _safe_set(ws, "B22", report.get("cause_detail"))

    # =====================================================
    # GOODS & PACKAGES
    # =====================================================
    _safe_set(ws, "B25", report.get("goods_description"))

    _check(ws, "B27", report.get("package_carton"))
    _check(ws, "C27", report.get("package_bags"))
    _check(ws, "D27", report.get("package_boxes"))
    _check(ws, "E27", report.get("package_drums"))
    _check(ws, "F27", report.get("package_pallets"))
    _check(ws, "B28", report.get("package_bulk"))
    _check(ws, "C28", report.get("package_bales"))
    _check(ws, "D28", report.get("package_crates"))
    _check(ws, "E28", report.get("package_other"))

    _safe_set(ws, "B29", report.get("qty_1"))
    _safe_set(ws, "C29", report.get("qty_2"))
    _safe_set(ws, "D29", report.get("qty_3"))

    _safe_set(ws, "B31", report.get("package_marking"))
    _safe_set(ws, "B33", report.get("goods_condition"))

    # =====================================================
    # NARRATIVES
    # =====================================================
    _safe_set(ws, "B35", report.get("damage_details"))
    _safe_set(ws, "B38", report.get("remarks"))
    _safe_set(ws, "B41", report.get("conclusion"))
    _safe_set(ws, "B44", report.get("picture_link"))

    # =====================================================
    # DOCUMENTS
    # =====================================================
    _check(ws, "B47", report.get("doc_bl"))
    _check(ws, "C47", report.get("doc_packing_list"))
    _check(ws, "D47", report.get("doc_shipping_invoice"))
    _check(ws, "E47", report.get("doc_cargo_manifest"))
    _check(ws, "F47", report.get("doc_commercial_invoice"))
    _check(ws, "B48", report.get("doc_delivery_record"))
    _check(ws, "C48", report.get("doc_notice_loss"))
    _check(ws, "D48", report.get("doc_insurance_policy"))
    _check(ws, "E48", report.get("doc_other"))

    # =====================================================
    # QUALITY
    # =====================================================
    _check(ws, "B51", report.get("quality_packing_exam"))
    _check(ws, "C51", report.get("quality_un_witness"))
    _check(ws, "D51", report.get("quality_visual_exam"))
    _check(ws, "E51", report.get("quality_product_exam"))
    _check(ws, "F51", report.get("quality_documents"))
    _check(ws, "B52", report.get("quality_sanitary_cert"))
    _check(ws, "C52", report.get("quality_phytosanitary_cert"))
    _check(ws, "D52", report.get("quality_factory_cert"))
    _check(ws, "E52", report.get("quality_origin_cert"))

    # =====================================================
    # PERSONS
    # =====================================================
    _safe_set(ws, "B55", report.get("person_1"))
    _safe_set(ws, "B56", report.get("person_2"))
    _safe_set(ws, "B57", report.get("person_3"))

    _safe_set(ws, "E55", report.get("created_at"))
    _safe_set(ws, "E56", report.get("updated_at"))

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
