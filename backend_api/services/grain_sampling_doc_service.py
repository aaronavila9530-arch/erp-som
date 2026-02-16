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
    # REPLACE PLACEHOLDERS WITHOUT DESTROYING FORMAT
    # ========================================================

    def replace_in_paragraph(paragraph, data_dict):

        for key, value in data_dict.items():

            placeholder = f"{{{key}}}"

            # Si el placeholder no aparece ni siquiera en el texto completo, saltamos
            if placeholder not in paragraph.text:
                continue

            # Caso 1: placeholder completo dentro de un solo run
            for run in paragraph.runs:
                if placeholder in run.text:
                    run.text = run.text.replace(
                        placeholder,
                        safe(value)
                    )

            # Caso 2: placeholder dividido en múltiples runs
            # Reconstruimos texto solo para detectar, pero NO destruimos formato
            full_text = "".join(run.text for run in paragraph.runs)

            if placeholder in full_text:

                new_text = full_text.replace(placeholder, safe(value))

                # Ahora redistribuimos carácter por carácter
                index = 0
                for run in paragraph.runs:
                    length = len(run.text)
                    run.text = new_text[index:index + length]
                    index += length

    # ========================================================
    # BODY
    # ========================================================

    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph, data)

    # ========================================================
    # TABLES
    # ========================================================

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph, data)

    # ========================================================
    # HEADERS & FOOTERS
    # ========================================================

    for section in doc.sections:

        for paragraph in section.header.paragraphs:
            replace_in_paragraph(paragraph, data)

        for paragraph in section.footer.paragraphs:
            replace_in_paragraph(paragraph, data)

    # ========================================================
    # SAVE TEMP FILE
    # ========================================================

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"{data.get('cert_no', 'grain_sampling')}.docx"
    )

    doc.save(output_path)

    return output_path
