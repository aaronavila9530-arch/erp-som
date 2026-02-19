import os
import tempfile
import subprocess
from docx import Document


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_truck_supervision.docx"
    )
)


def _replace_in_paragraphs(paragraphs, placeholders: dict):
    for p in paragraphs:
        for run in p.runs:
            if not run.text:
                continue
            for key, value in placeholders.items():
                if key in run.text:
                    run.text = run.text.replace(key, value)
                    break


def _replace_in_tables(tables, placeholders):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, placeholders)
                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


def generate_truck_supervision_presentation_pdf(data: dict) -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{cert_no}": str(data.get("cert_no") or ""),
        "{vessel_name}": str(data.get("vessel_name") or ""),
        "{ship_grt}": str(data.get("grt") or ""),
        "{ship_nrt}": str(data.get("nrt") or ""),
        "{requested_by}": str(data.get("customer") or ""),
        "{sampling_start_time}": str(data.get("report_date") or "")
    }

    _replace_in_paragraphs(doc.paragraphs, placeholders)
    _replace_in_tables(doc.tables, placeholders)

    for section in doc.sections:
        _replace_in_paragraphs(section.header.paragraphs, placeholders)
        _replace_in_tables(section.header.tables, placeholders)

        _replace_in_paragraphs(section.footer.paragraphs, placeholders)
        _replace_in_tables(section.footer.tables, placeholders)

    fd, docx_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(docx_path)

    output_dir = tempfile.mkdtemp()

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            docx_path
        ],
        check=True
    )

    pdf_path = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    )

    return pdf_path
