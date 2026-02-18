import os
import tempfile
from docx import Document


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "vessel_truck_supervision.docx"
    )
)


# =====================================================
# SAFE REPLACEMENT (NO ROMPE ESTILOS)
# =====================================================
def _replace_in_paragraphs(paragraphs, placeholders: dict):

    for p in paragraphs:
        for run in p.runs:

            if not run.text:
                continue

            for key, value in placeholders.items():
                if key in run.text:
                    run.text = run.text.replace(key, str(value))
                    break


def _replace_in_tables(tables, placeholders):

    for table in tables:
        for row in table.rows:
            for cell in row.cells:

                _replace_in_paragraphs(cell.paragraphs, placeholders)

                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


# =====================================================
# GENERATE DOCX
# =====================================================
def generate_vessel_truck_supervision_doc(report_data: dict):

    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{{CERT_NO}}": report_data.get("cert_no", ""),
        "{{PORT}}": report_data.get("port", ""),
        "{{COUNTRY}}": report_data.get("country", ""),
        "{{REPORT_DATE}}": str(report_data.get("report_date", "")),

        "{{VESSEL_NAME}}": report_data.get("vessel_name", ""),
        "{{FLAG}}": report_data.get("flag_port_registry", ""),
        "{{GRT}}": report_data.get("grt", ""),
        "{{NRT}}": report_data.get("nrt", ""),
        "{{IMO}}": report_data.get("imo_no", ""),
        "{{BUILD_YEAR}}": report_data.get("build_year", ""),

        "{{CAPTAIN}}": report_data.get("captain", ""),
        "{{CHIEF_OFFICER}}": report_data.get("chief_officer", ""),

        "{{ARRIVAL_DATE}}": str(report_data.get("arrival_date", "")),
        "{{INSPECTION_DATE}}": str(report_data.get("inspection_date", "")),
        "{{SUPERVISION_COMPLETED_DATE}}": str(report_data.get("supervision_completed_date", "")),

        "{{PROCESS_TEXT}}": report_data.get("process_text", ""),
        "{{CONCLUSION_TEXT}}": report_data.get("conclusion_text", ""),

        "{{FINDINGS_DOCUMENTAL}}": report_data.get("findings_documental_text", ""),
        "{{FINDINGS_OPERATIONAL}}": report_data.get("findings_operational_text", ""),
        "{{INCIDENTS}}": report_data.get("incidents_text", "")
    }

    _replace_in_paragraphs(doc.paragraphs, placeholders)
    _replace_in_tables(doc.tables, placeholders)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(temp_file.name)

    return temp_file.name
