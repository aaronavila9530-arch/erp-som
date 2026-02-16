import os
import tempfile
from docx import Document


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_grain_vessel.docx"
    )
)


# =====================================================
# INTERNAL — SAFE RUN REPLACEMENT (NO ROMPE ESTILOS)
# =====================================================
def _replace_in_paragraphs(paragraphs, placeholders: dict):

    for p in paragraphs:
        for run in p.runs:

            if not run.text:
                continue

            for key, value in placeholders.items():
                if key in run.text:
                    run.text = run.text.replace(key, str(value))
                    break  # 🔒 IMPORTANTE


def _replace_in_tables(tables, placeholders):

    for table in tables:
        for row in table.rows:
            for cell in row.cells:

                _replace_in_paragraphs(cell.paragraphs, placeholders)

                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


# =====================================================
# MAIN
# =====================================================
def generate_vessel_presentation_doc(data: dict) -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Presentation template not found: {TEMPLATE_PATH}"
        )

    if not isinstance(data, dict):
        raise ValueError("Invalid data payload — expected dict")

    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{cert_no}": str(data.get("cert_no") or ""),
        "{vessel_name}": str(data.get("vessel_name") or ""),
        "{ship_grt}": str(data.get("ship_grt") or ""),
        "{ship_nrt}": str(data.get("ship_nrt") or ""),
        "{requested_by}": str(data.get("requested_by") or ""),
        "{sampling_start_time}": str(
            data.get("sampling_start_time") or ""
        ),
    }

    # BODY
    _replace_in_paragraphs(doc.paragraphs, placeholders)
    _replace_in_tables(doc.tables, placeholders)

    # HEADERS / FOOTERS (MUY IMPORTANTE)
    for section in doc.sections:
        _replace_in_paragraphs(section.header.paragraphs, placeholders)
        _replace_in_tables(section.header.tables, placeholders)

        _replace_in_paragraphs(section.footer.paragraphs, placeholders)
        _replace_in_tables(section.footer.tables, placeholders)

    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)

    doc.save(output_path)

    return output_path
