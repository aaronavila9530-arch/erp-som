import os
import tempfile
from docx import Document


# ============================================================
# GENERATE GRAIN SAMPLING WORD REPORT (FORMAT PRESERVING)
# ============================================================

def generate_grain_sampling_doc(data: dict) -> str:

    # ========================================================
    # LOAD TEMPLATE
    # ========================================================

    base_dir = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.abspath(
        os.path.join(
            base_dir,
            "..",
            "templates",
            "Supervision_Muestreo_Granos.docx"
        )
    )

    if not os.path.exists(template_path):
        raise Exception(f"Template not found at: {template_path}")

    doc = Document(template_path)

    # ========================================================
    # SAFE VALUE
    # ========================================================

    def safe(value):
        return "" if value is None else str(value)

    # ========================================================
    # ULTRA SAFE REPLACEMENT
    # Mantiene runs originales
    # Mantiene formato
    # No borra imágenes
    # No colapsa estilos
    # ========================================================

    def replace_in_paragraph(paragraph, data_dict):

        if not paragraph.runs:
            return

        # Texto lógico completo
        full_text = "".join(run.text for run in paragraph.runs)

        modified = False

        for key, value in data_dict.items():
            placeholder = f"{{{key}}}"
            if placeholder in full_text:
                full_text = full_text.replace(
                    placeholder,
                    safe(value)
                )
                modified = True

        if not modified:
            return

        # Ahora reescribimos carácter por carácter
        index = 0

        for run in paragraph.runs:

            original_length = len(run.text)

            if original_length == 0:
                continue

            run.text = full_text[index:index + original_length]
            index += original_length

        # Si el nuevo texto es más largo que la suma original,
        # lo agregamos al último run SIN romper formato
        if index < len(full_text):
            paragraph.runs[-1].text += full_text[index:]

    # ========================================================
    # PROCESS BODY
    # ========================================================

    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph, data)

    # ========================================================
    # PROCESS TABLES
    # ========================================================

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph, data)

    # ========================================================
    # PROCESS HEADERS & FOOTERS
    # ========================================================

    for section in doc.sections:

        # HEADER
        header = section.header

        for paragraph in header.paragraphs:
            replace_in_paragraph(paragraph, data)

        for table in header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph, data)

        # FOOTER
        footer = section.footer

        for paragraph in footer.paragraphs:
            replace_in_paragraph(paragraph, data)

        for table in footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph, data)

    # ========================================================
    # SAVE FILE
    # ========================================================

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"{data.get('cert_no', 'grain_sampling')}.docx"
    )

    doc.save(output_path)

    return output_path
