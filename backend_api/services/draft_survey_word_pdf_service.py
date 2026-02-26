import os
import tempfile
import subprocess
from pathlib import Path
from docx import Document


# ============================================================
# GENERATE DRAFT SURVEY WORD PDF (LIBREOFFICE VERSION)
# ============================================================

def generate_draft_survey_word_pdf(data: dict) -> str:

    # ========================================================
    # VALIDACIONES
    # ========================================================

    if not isinstance(data, dict):
        raise ValueError("Invalid payload. Expected dict.")

    # ========================================================
    # TEMPLATE PATH (RELATIVE — SAFE FOR RAILWAY & EXE)
    # ========================================================

    base_dir = os.path.dirname(os.path.abspath(__file__))

    template_path = os.path.abspath(
        os.path.join(
            base_dir,
            "..",
            "templates",
            "draft_word_template.docx"
        )
    )

    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Template not found at: {template_path}"
        )

    # ========================================================
    # LOAD DOCUMENT
    # ========================================================

    doc = Document(template_path)

    def safe(value):
        return "" if value is None else str(value)

    # ========================================================
    # SAFE REPLACEMENT (FORMATO PRESERVADO)
    # ========================================================

    def replace_in_paragraph(paragraph):

        if not paragraph.runs:
            return

        full_text = "".join(run.text for run in paragraph.runs)

        modified = False

        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in full_text:
                full_text = full_text.replace(
                    placeholder,
                    safe(value)
                )
                modified = True

        if not modified:
            return

        index = 0

        for run in paragraph.runs:
            length = len(run.text)
            if length == 0:
                continue

            run.text = full_text[index:index + length]
            index += length

        if index < len(full_text):
            paragraph.runs[-1].text += full_text[index:]

    # BODY
    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph)

    # TABLES
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph)

    # HEADERS & FOOTERS
    for section in doc.sections:

        for paragraph in section.header.paragraphs:
            replace_in_paragraph(paragraph)

        for table in section.header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph)

        for paragraph in section.footer.paragraphs:
            replace_in_paragraph(paragraph)

        for table in section.footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph)

    # ========================================================
    # SAVE TEMP DOCX
    # ========================================================

    fd, temp_docx = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(temp_docx)

    # ========================================================
    # CONVERT USING LIBREOFFICE (HEADLESS)
    # ========================================================

    output_dir = tempfile.mkdtemp(prefix="draft_word_pdf_")
    libre_profile = tempfile.mkdtemp(prefix="lo_profile_")

    cmd = [
        "soffice",
        "--headless",
        "--nologo",
        "--nodefault",
        "--nolockcheck",
        "--nofirststartwizard",
        "--norestore",
        f"-env:UserInstallation=file://{libre_profile}",
        "--convert-to",
        "pdf:writer_pdf_Export",
        "--outdir",
        output_dir,
        temp_docx
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"LibreOffice PDF conversion failed:\n{result.stderr}"
        )

    pdf_name = Path(temp_docx).with_suffix(".pdf").name
    pdf_path = os.path.join(output_dir, pdf_name)

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF was not created")

    if os.path.getsize(pdf_path) == 0:
        raise RuntimeError("PDF was generated but is empty")

    return pdf_path