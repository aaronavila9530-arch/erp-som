import os
import tempfile
import subprocess
from docx import Document


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentación_containers.doc"
    )
)


def generate_presentation_pdf(data: dict) -> str:
    """
    Genera PDF desde presentación_containers.doc
    """

    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{{CERT_NO}}": data["cert_no"],
        "{{CONTAINER}}": data["container"],
        "{{TO}}": data["to"],
        "{{PLACE}}": data["place"],
        "{{DATE}}": data["date"]
    }

    for p in doc.paragraphs:
        for key, value in placeholders.items():
            if key in p.text:
                p.text = p.text.replace(key, value or "")

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

    pdf_name = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    return os.path.join(output_dir, pdf_name)
