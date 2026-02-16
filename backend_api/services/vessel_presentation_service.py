import os
import tempfile
from docx import Document


TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../templates/presentation_grain_vessel.docx"
)


def generate_vessel_presentation_doc(data: dict) -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError("Presentation template not found")

    doc = Document(TEMPLATE_PATH)

    replacements = {
        "{cert_no}": data.get("cert_no", ""),
        "{vessel_name}": data.get("vessel_name", ""),
        "{ship_grt}": str(data.get("ship_grt", "")),
        "{ship_nrt}": str(data.get("ship_nrt", "")),
        "{requested_by}": data.get("requested_by", ""),
        "{sampling_start_time}": str(data.get("sampling_start_time", "")).split(" ")[0],
    }

    for p in doc.paragraphs:
        for key, val in replacements.items():
            if key in p.text:
                p.text = p.text.replace(key, val)

    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)

    doc.save(output_path)

    return output_path
