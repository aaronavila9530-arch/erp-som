import os
import tempfile
from docx import Document


TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../templates/presentation_grain_vessel.docx"
)


def _replace_in_paragraph(paragraph, replacements):

    for run in paragraph.runs:
        for key, val in replacements.items():
            if key in run.text:
                run.text = run.text.replace(key, str(val))


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

    # 🔹 Reemplazar en párrafos normales
    for p in doc.paragraphs:
        _replace_in_paragraph(p, replacements)

    # 🔹 Reemplazar en tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    _replace_in_paragraph(p, replacements)

    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)

    doc.save(output_path)

    return output_path
