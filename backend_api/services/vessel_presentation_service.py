import os
import tempfile
from docx import Document


TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../templates/presentation_grain_vessel.docx"
)


def _replace_in_paragraph(paragraph, replacements):

    if not paragraph.runs:
        return

    full_text = "".join(run.text for run in paragraph.runs)

    replaced = False

    for key, val in replacements.items():
        if key in full_text:
            full_text = full_text.replace(key, str(val))
            replaced = True

    if replaced:
        # Mantener estilo del primer run
        first_run = paragraph.runs[0]

        for run in paragraph.runs:
            run.text = ""

        first_run.text = full_text


def _replace_in_doc(doc, replacements):

    # Párrafos normales
    for p in doc.paragraphs:
        _replace_in_paragraph(p, replacements)

    # Tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p, replacements)


def generate_vessel_presentation_doc(data: dict) -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError("Presentation template not found")

    doc = Document(TEMPLATE_PATH)

    replacements = {
        "{cert_no}": data.get("cert_no", ""),
        "{vessel_name}": data.get("vessel_name", ""),
        "{ship_grt}": data.get("ship_grt", ""),
        "{ship_nrt}": data.get("ship_nrt", ""),
        "{requested_by}": data.get("requested_by", ""),
        "{sampling_start_time}": data.get("sampling_start_time", ""),
    }

    _replace_in_doc(doc, replacements)

    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)

    doc.save(output_path)

    return output_path


