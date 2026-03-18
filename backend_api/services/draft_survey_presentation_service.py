import os
import tempfile
import subprocess
from typing import Dict
from docx import Document
from datetime import datetime


# =====================================================
# TEMPLATE PATH
# =====================================================
TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_draft_survey.docx"
    )
)


# =====================================================
# FORMAT DATE — LONG ENGLISH (NO TIME)
# =====================================================
def _format_date_long_en(value):

    if not value:
        return ""

    try:
        # Si viene como datetime
        if isinstance(value, datetime):
            dt = value

        else:
            value = str(value)

            # ISO con hora → cortar
            if "T" in value:
                value = value.split("T")[0]

            # Intentar parsear YYYY-MM-DD
            try:
                dt = datetime.strptime(value[:10], "%Y-%m-%d")
            except Exception:
                return value  # fallback

        return dt.strftime("%B %d, %Y")  # March 18, 2026

    except Exception:
        return str(value)


# =====================================================
# INTERNAL — SAFE REPLACE (CROSS-RUN SAFE)
# =====================================================
def _replace_in_paragraph(paragraph, placeholder: str, value: str):

    if not paragraph.runs:
        return

    full_text = "".join(run.text for run in paragraph.runs)

    if placeholder not in full_text:
        return

    start = full_text.index(placeholder)
    end = start + len(placeholder)

    current_pos = 0
    first_replacement_done = False

    for run in paragraph.runs:

        run_text = run.text
        run_len = len(run_text)

        run_start = current_pos
        run_end = current_pos + run_len

        if run_end > start and run_start < end:

            prefix_len = max(0, start - run_start)
            suffix_len = max(0, run_end - end)

            prefix = run_text[:prefix_len]
            suffix = run_text[run_len - suffix_len:] if suffix_len > 0 else ""

            if not first_replacement_done:
                run.text = prefix + value + suffix
                first_replacement_done = True
            else:
                run.text = ""

        current_pos += run_len


def _replace_in_paragraphs(paragraphs, placeholders: Dict[str, str]):
    for p in paragraphs:
        for key, value in placeholders.items():
            _replace_in_paragraph(p, key, value)


def _replace_in_tables(tables, placeholders: Dict[str, str]):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, placeholders)
                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


# =====================================================
# MAIN — GENERATE PRESENTATION PDF
# =====================================================
def generate_draft_survey_presentation_pdf(data: dict) -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Draft Survey presentation template not found: {TEMPLATE_PATH}"
        )

    # 🔥 FORMATEO DE FECHA (SIN HORA + LONG ENGLISH)
    formatted_date = _format_date_long_en(
        data.get("word_commenced")
    )

    placeholders = {
        "{draft_report_number}": str(data.get("draft_report_number") or ""),
        "{word_vessel}": str(data.get("word_vessel") or ""),
        "{word_grt}": str(data.get("word_grt") or ""),
        "{word_nrt}": str(data.get("word_nrt") or ""),
        "{word_survey_requested_by}": str(data.get("word_survey_requested_by") or ""),
        "{word_port}": str(data.get("word_port") or ""),
        "{word_country}": str(data.get("word_country") or ""),
        "{word_commenced}": formatted_date,  # 👈 AQUÍ APLICADO
    }

    doc = Document(TEMPLATE_PATH)

    # BODY
    _replace_in_paragraphs(doc.paragraphs, placeholders)
    _replace_in_tables(doc.tables, placeholders)

    # HEADERS / FOOTERS
    for section in doc.sections:
        _replace_in_paragraphs(section.header.paragraphs, placeholders)
        _replace_in_tables(section.header.tables, placeholders)
        _replace_in_paragraphs(section.footer.paragraphs, placeholders)
        _replace_in_tables(section.footer.tables, placeholders)

    fd, temp_docx = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(temp_docx)

    output_dir = tempfile.mkdtemp()

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            temp_docx
        ],
        check=True
    )

    pdf_path = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(temp_docx))[0] + ".pdf"
    )

    if not os.path.exists(pdf_path):
        raise RuntimeError("Presentation PDF generation failed")

    return pdf_path