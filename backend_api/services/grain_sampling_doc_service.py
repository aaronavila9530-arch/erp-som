import os
import tempfile
from docx import Document


# ============================================================
# GENERATE GRAIN SAMPLING WORD REPORT
# ============================================================

def generate_grain_sampling_doc(data: dict) -> str:

    # ========================================================
    # LOAD TEMPLATE (BACKEND SAFE)
    # ========================================================

    base_dir = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.join(
        base_dir,
        "..",
        "templates",
        "Supervision_Muestreo_Granos.docx"
    )

    template_path = os.path.abspath(template_path)

    if not os.path.exists(template_path):
        raise Exception(f"Template not found at: {template_path}")

    doc = Document(template_path)

    # ========================================================
    # SAFE VALUE
    # ========================================================

    def safe(value):
        if value is None:
            return ""
        return str(value)

    # ========================================================
    # RUN-SAFE PLACEHOLDER REPLACEMENT
    # ========================================================

    def replace_placeholders_in_paragraph(paragraph, data_dict):

        if not paragraph.runs:
            return

        full_text = "".join(run.text for run in paragraph.runs)

        replaced = False

        for key, value in data_dict.items():
            placeholder = f"{{{key}}}"
            if placeholder in full_text:
                full_text = full_text.replace(placeholder, safe(value))
                replaced = True

        if replaced:
            # Clear existing runs
            for run in paragraph.runs:
                run.text = ""

            # Put full replaced text in first run
            paragraph.runs[0].text = full_text

    # ========================================================
    # BODY
    # ========================================================

    for paragraph in doc.paragraphs:
        replace_placeholders_in_paragraph(paragraph, data)

    # ========================================================
    # TABLES
    # ========================================================

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_placeholders_in_paragraph(paragraph, data)

    # ========================================================
    # HEADERS & FOOTERS
    # ========================================================

    for section in doc.sections:

        # Header
        for paragraph in section.header.paragraphs:
            replace_placeholders_in_paragraph(paragraph, data)

        # Footer
        for paragraph in section.footer.paragraphs:
            replace_placeholders_in_paragraph(paragraph, data)

    # ========================================================
    # SAVE TEMP FILE (RAILWAY SAFE)
    # ========================================================

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"{data.get('cert_no', 'grain_sampling')}.docx"
    )

    doc.save(output_path)

    return output_path
