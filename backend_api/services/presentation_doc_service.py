import os
import tempfile
import subprocess
from docx import Document


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentación_containers.docx"
    )
)


def generate_presentation_pdf(data: dict) -> str:
    """
    Genera PDF desde presentación_containers.docx
    """

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Presentation template not found: {TEMPLATE_PATH}"
        )

    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{{CERT_NO}}": data.get("cert_no") or "",
        "{{CONTAINER}}": data.get("container") or "",
        "{{TO}}": data.get("to") or "",
        "{{PLACE}}": data.get("place") or "",
        "{{DATE}}": data.get("date") or ""
    }

    # =====================================================
    # SAFE TEXT REPLACEMENT (NO FORMAT LOSS)
    # =====================================================
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            for key, value in placeholders.items():
                if key in run.text:
                    run.text = run.text.replace(key, value)

    # =====================================================
    # SAVE TEMP DOCX
    # =====================================================
    fd, docx_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(docx_path)

    output_dir = tempfile.mkdtemp()

    # =====================================================
    # CONVERT TO PDF (LibreOffice)
    # =====================================================
    try:
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
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )
    except FileNotFoundError:
        raise RuntimeError(
            "LibreOffice (soffice) is not installed or not available in PATH"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Error converting DOCX to PDF: {e.stderr.decode(errors='ignore')}"
        )

    pdf_name = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF generation failed — output file not found")

    return pdf_path
