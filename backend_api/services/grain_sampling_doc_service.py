import os
import tempfile
from docx import Document
from resource_utils import resource_path


# ============================================================
# GENERATE GRAIN SAMPLING WORD REPORT
# ============================================================

def generate_grain_sampling_doc(data: dict) -> str:

    # ========================================================
    # LOAD TEMPLATE (PORTABLE)
    # ========================================================
    template_path = resource_path(
        os.path.join("templates", "Supervision_Muestreo_Granos.docx")
    )

    if not os.path.exists(template_path):
        raise Exception("Template not found in /templates directory")

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
    # SAVE TEMP FILE
    # ========================================================
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(
        temp_dir,
        f"{data.get('cert_no', 'grain_sampling')}.docx"
    )

    doc.save(output_path)

    return output_path
