import os
import tempfile
import subprocess
from docx import Document


# =====================================================
# TEMPLATE PATH (PRODUCTION SAFE)
# =====================================================
TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_containers.docx"
    )
)


# =====================================================
# GENERATE PRESENTATION PDF
# =====================================================
def generate_presentation_pdf(data: dict) -> str:
    """
    Genera PDF desde presentation_containers.docx
    Reemplaza placeholders sin perder formato
    """

    # -------------------------------------------------
    # VALIDATIONS
    # -------------------------------------------------
    if not os.path.isfile(TEMPLATE_PATH):
        raise RuntimeError(
            f"Presentation template not found at runtime: {TEMPLATE_PATH}"
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
    # SAFE TEXT REPLACEMENT (RUN LEVEL)
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
    # CONVERT TO PDF (LIBREOFFICE)
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
            "LibreOffice (soffice) not available in runtime environment"
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"DOCX to PDF conversion failed: {e.stderr.decode(errors='ignore')}"
        )

    # -------------------------------------------------
    # VALIDATE OUTPUT
    # -------------------------------------------------
    pdf_path = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    )

    if not os.path.isfile(pdf_path):
        raise RuntimeError("PDF generation failed — output not created")

    return pdf_path
