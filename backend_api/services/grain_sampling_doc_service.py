import os
import tempfile
from docx import Document


# ============================================================
# GENERATE GRAIN SAMPLING WORD REPORT (ULTRA SAFE)
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
    # ADVANCED PLACEHOLDER REPLACEMENT
    # Detecta placeholders partidos en múltiples runs
    # Solo reemplaza el bloque específico
    # No destruye imágenes ni formato externo
    # ========================================================

    def replace_in_paragraph(paragraph, data_dict):

        if not paragraph.runs:
            return

        full_text = "".join(run.text for run in paragraph.runs)

        for key, value in data_dict.items():

            placeholder = f"{{{key}}}"

            if placeholder not in full_text:
                continue

            replacement = safe(value)
            new_full_text = full_text.replace(placeholder, replacement)

            # Ahora redistribuimos texto de forma segura
            # pero SIN alterar estructura de runs que contienen imágenes

            index = 0
            for run in paragraph.runs:

                original_length = len(run.text)

                if original_length == 0:
                    continue

                run.text = new_full_text[index:index + original_length]
                index += original_length

            full_text = new_full_text

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
    # SAVE TEMP FILE
    # ========================================================

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"{data.get('cert_no', 'grain_sampling')}.docx"
    )

    doc.save(output_path)

    return output_path
