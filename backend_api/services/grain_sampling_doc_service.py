import os
import tempfile
from docx import Document


# ============================================================
# GENERATE GRAIN SAMPLING WORD REPORT (FULL SAFE VERSION)
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
    # SMART PLACEHOLDER REPLACEMENT
    # Reemplaza aunque esté dividido en múltiples runs
    # Solo limpia los runs involucrados
    # No reconstruye el párrafo completo
    # No toca imágenes
    # ========================================================

    def replace_in_paragraph(paragraph, data_dict):

        if not paragraph.runs:
            return

        # Texto completo lógico
        full_text = "".join(run.text for run in paragraph.runs)

        for key, value in data_dict.items():

            placeholder = f"{{{key}}}"

            if placeholder not in full_text:
                continue

            replacement = safe(value)

            # Ubicación exacta del placeholder
            start_index = full_text.find(placeholder)
            end_index = start_index + len(placeholder)

            current_pos = 0
            first_run_index = None

            # Detectar runs involucrados
            for i, run in enumerate(paragraph.runs):

                run_text = run.text
                run_len = len(run_text)

                run_start = current_pos
                run_end = current_pos + run_len

                if run_end > start_index and run_start < end_index:

                    if first_run_index is None:
                        first_run_index = i

                    # Limpiar solo texto del placeholder en este run
                    run.text = ""

                current_pos += run_len

            # Insertar valor completo en el primer run afectado
            if first_run_index is not None:
                paragraph.runs[first_run_index].text = replacement

            # Actualizar full_text para múltiples placeholders
            full_text = full_text.replace(placeholder, replacement)

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
