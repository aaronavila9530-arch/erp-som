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
    # REPLACE PLACEHOLDERS
    # ========================================================

    for paragraph in doc.paragraphs:
        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    placeholder,
                    safe(value)
                )

    # ========================================================
    # TABLE SUPPORT
    # ========================================================

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in data.items():
                    placeholder = f"{{{key}}}"
                    if placeholder in cell.text:
                        cell.text = cell.text.replace(
                            placeholder,
                            safe(value)
                        )

    # ========================================================
    # SAVE TEMP FILE (RAILWAY SAFE)
    # ========================================================

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"{data.get('cert_no', 'grain_sampling')}.docx"
    )

    doc.save(output_path)

    return output_path
