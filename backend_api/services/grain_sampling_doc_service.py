import os
import tempfile
from docx import Document


# ============================================================
# GENERATE GRAIN SAMPLING WORD REPORT (FORMAT SAFE)
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
        return "" if value is None else str(value)

    # ========================================================
    # SAFE RUN-LEVEL REPLACEMENT
    # SOLO reemplaza el placeholder exacto
    # NO reconstruye párrafo
    # NO toca formato
    # NO redistribuye texto
    # ========================================================

    def replace_in_paragraph(paragraph, data_dict):

        for key, value in data_dict.items():

            placeholder = f"{{{key}}}"

            # Buscar placeholder completo en el texto visible
            if placeholder not in paragraph.text:
                continue

            # Caso simple: placeholder está completo en un run
            for run in paragraph.runs:
                if placeholder in run.text:
                    run.text = run.text.replace(
                        placeholder,
                        safe(value)
                    )

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
    # HEADERS & FOOTERS (SIN DESTRUIR IMÁGENES)
    # ========================================================

    for section in doc.sections:

        # Header
        header = section.header
        for paragraph in header.paragraphs:
            replace_in_paragraph(paragraph, data)

        for table in header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph, data)

        # Footer
        footer = section.footer
        for paragraph in footer.paragraphs:
            replace_in_paragraph(paragraph, data)

        for table in footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph, data)

    # ========================================================
    # SAVE TEMP FILE (RAILWAY SAFE)
    # ========================================================

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"{data.get('cert_no', 'grain_sampling')}.docx"
    )

    doc.save(output_path)

    return output_path
