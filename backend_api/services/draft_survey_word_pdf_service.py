import os
import tempfile
from docx import Document

try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    docx2pdf_convert = None


# ============================================================
# GENERATE DRAFT SURVEY WORD PDF (NO DB)
# ============================================================

def generate_draft_survey_word_pdf(data: dict) -> str:

    # ========================================================
    # LOAD TEMPLATE (RELATIVE PATH - IGUAL QUE ADJUNTO)
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
        raise Exception(f"Template not found at: {template_path}")

    doc = Document(template_path)

    # ========================================================
    # SAFE VALUE
    # ========================================================

    def safe(value):
        return "" if value is None else str(value)

    # ========================================================
    # SAFE REPLACEMENT (MISMA LÓGICA QUE TRUCK)
    # ========================================================

    def replace_in_paragraph(paragraph):

        if not paragraph.runs:
            return

        full_text = "".join(run.text for run in paragraph.runs)

        for key, value in data.items():
            placeholder = f"{{{key}}}"
            if placeholder in full_text:
                full_text = full_text.replace(
                    placeholder,
                    safe(value)
                )

        index = 0

        for run in paragraph.runs:
            length = len(run.text)
            if length == 0:
                continue

            run.text = full_text[index:index + length]
            index += length

        if index < len(full_text):
            paragraph.runs[-1].text += full_text[index:]

    # ========================================================
    # BODY
    # ========================================================

    for paragraph in doc.paragraphs:
        replace_in_paragraph(paragraph)

    # ========================================================
    # TABLES
    # ========================================================

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    replace_in_paragraph(paragraph)

    # ========================================================
    # HEADERS & FOOTERS
    # ========================================================

    for section in doc.sections:

        header = section.header
        for paragraph in header.paragraphs:
            replace_in_paragraph(paragraph)

        for table in header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph)

        footer = section.footer
        for paragraph in footer.paragraphs:
            replace_in_paragraph(paragraph)

        for table in footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph)

    # ========================================================
    # SAVE TEMP DOCX
    # ========================================================

    tmp_docx = os.path.join(
        tempfile.gettempdir(),
        f"{data.get('draft_report_number', 'draft_survey')}.docx"
    )

    doc.save(tmp_docx)

    # ========================================================
    # CONVERT TO PDF
    # ========================================================

    if not docx2pdf_convert:
        raise Exception(
            "docx2pdf not available. Install it and ensure Microsoft Word is installed."
        )

    docx2pdf_convert(tmp_docx, tempfile.gettempdir())

    tmp_pdf = tmp_docx.replace(".docx", ".pdf")

    if not os.path.exists(tmp_pdf):
        raise Exception("PDF was not created.")

    return tmp_pdf