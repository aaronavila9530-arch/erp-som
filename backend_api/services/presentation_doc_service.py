import os
import tempfile
import subprocess
from docx import Document


# =====================================================
# TEMPLATE PATH
# =====================================================
TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentación_containers.docx"
    )
)


# =====================================================
# GENERATE PRESENTATION PDF
# =====================================================
def generate_presentation_pdf(data: dict) -> str:
    """
    Genera PDF desde presentación_containers.docx
    Reemplaza placeholders de forma segura sin perder formato
    """

    # -------------------------------------------------
    # VALIDATIONS
    # -------------------------------------------------
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Presentation template not found: {TEMPLATE_PATH}"
        )

    if not isinstance(data, dict):
        raise ValueError("Invalid data payload — expected dict")

    # -------------------------------------------------
    # LOAD TEMPLATE
    # -------------------------------------------------
    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{{CERT_NO}}": str(data.get("cert_no") or ""),
        "{{CONTAINER}}": str(data.get("container") or ""),
        "{{TO}}": str(data.get("to") or ""),
        "{{PLACE}}": str(data.get("place") or ""),
        "{{DATE}}": str(data.get("date") or "")
    }

    # -------------------------------------------------
    # SAFE TEXT REPLACEMENT (RUN-LEVEL)
    # -------------------------------------------------
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            text = run.text
            for key, value in placeholders.items():
                if key in text:
                    text = text.replace(key, value)
            run.text = text

    # -------------------------------------------------
    # SAVE TEMP DOCX
    # -------------------------------------------------
    fd, docx_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(docx_path)

    output_dir = tempfile.mkdtemp()

    # -------------------------------------------------
    # CONVERT TO PDF (LibreOffice Headless)
    # -------------------------------------------------
    try:
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--nologo",
                "--nolockcheck",
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

    # -------------------------------------------------
    # VALIDATE OUTPUT
    # -------------------------------------------------
    pdf_name = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    pdf_path = os.path.join(output_dir, pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError(
            "PDF generation failed — output file not found"
        )

    return pdf_path
