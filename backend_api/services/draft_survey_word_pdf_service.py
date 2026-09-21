import os
import re
import tempfile
import subprocess
from datetime import date, datetime
from pathlib import Path
from docx import Document
from docx.enum.text import WD_TAB_ALIGNMENT
from docx.shared import Inches
try:
    from services.template_autofit import apply_docx_autofit
    from services.document_branding import apply_mci_docx_branding
except ModuleNotFoundError:
    from backend_api.services.template_autofit import apply_docx_autofit
    from backend_api.services.document_branding import apply_mci_docx_branding


# ============================================================
# GENERATE DRAFT SURVEY WORD PDF (ERP VERSION - BLINDADO)
# ============================================================

def generate_draft_survey_word_pdf(data: dict) -> str:
    data = dict(data or {})

    def _format_report_date(value):
        if value in (None, ""):
            return ""
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return value.strftime("%b %d %Y")
        text = str(value or "").strip()
        if not text:
            return ""
        for fmt in (
            "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y",
            "%m-%d-%Y", "%m/%d/%Y", "%b %d %Y", "%B %d %Y",
            "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S",
        ):
            try:
                return datetime.strptime(text.replace(",", " "), fmt).strftime("%b %d %Y")
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text[:19].replace(" ", "T")).strftime("%b %d %Y")
        except Exception:
            return text

    def _combine_date_time(prefix):
        current = str(data.get(prefix) or "").strip()
        if current and not current.startswith("{"):
            return current
        date_text = _format_report_date(data.get(f"{prefix}_date"))
        time_text = str(data.get(f"{prefix}_time") or "").strip()
        if not date_text:
            return ""
        if time_text and time_text not in {"00:00", "00:00:00"}:
            return f"{date_text} {time_text[:5]}"
        return date_text

    for _key in (
        "word_arrived_buoy",
        "word_nor_tendered",
        "word_all_fast",
        "word_initial_draft",
        "word_commenced",
        "word_completed",
        "word_final_draft",
    ):
        data[_key] = _combine_date_time(_key)

    # ========================================================
    # VALIDACIÓN
    # ========================================================

    if not isinstance(data, dict):
        raise ValueError("Invalid payload. Expected dict.")

    draft_report_number = str(
        data.get("draft_report_number") or ""
    ).strip()

    if not draft_report_number:
        raise ValueError("draft_report_number is required")

    # ========================================================
    # TEMPLATE PATH
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

    doc = Document(template_path)

    # ========================================================
    # SAFE VALUE
    # ========================================================

    def safe(value):
        return "" if value is None else str(value)

    # ========================================================
    # PLACEHOLDER MAP
    # ========================================================

    placeholder_map = {
        f"{{{key}}}": safe(value)
        for key, value in data.items()
    }

    time_sheet_labels = {
        "word_arrived_buoy": "Vessel Arrived at Sea buoy",
        "word_nor_tendered": "N.O.R Tendered",
        "word_all_fast": "All Fast",
        "word_initial_draft": "Initial Draft Survey",
        "word_commenced": "Commenced Discharge",
        "word_completed": "Completed Discharge",
        "word_final_draft": "Final Draft Survey",
    }
    quantity_labels = {
        "word_draft_figures": ("Draft Survey Figure", "MT."),
        "word_bl_figures": ("B/L Figures", "MT."),
        "word_difference": ("Difference", "MT"),
        "word_percentage": ("Percentage", "%"),
        "word_shore_scale": ("Shore Scale Figures", "MT."),
        "word_shore_bl": ("B/L Figures", "MT."),
        "word_shore_difference": ("Difference", "MT"),
        "word_shore_percentage": ("Percentage", "%"),
    }

    def set_paragraph_text(paragraph, text):
        if paragraph.runs:
            paragraph.runs[0].text = text
            for run in paragraph.runs[1:]:
                run.text = ""
        else:
            paragraph.add_run(text)

    def align_time_sheet_paragraph(paragraph):
        text = paragraph.text or ""
        for key, label in time_sheet_labels.items():
            placeholder = f"{{{key}}}"
            if placeholder not in text:
                continue
            value = safe(data.get(key))
            try:
                paragraph.paragraph_format.tab_stops.clear_all()
                paragraph.paragraph_format.tab_stops.add_tab_stop(
                    Inches(3.65),
                    WD_TAB_ALIGNMENT.LEFT,
                )
            except Exception:
                pass
            set_paragraph_text(paragraph, f"{label}\t{value} LT.")
            return True
        return False

    def align_quantity_paragraph(paragraph):
        text = paragraph.text or ""
        for key, (label, unit) in quantity_labels.items():
            placeholder = f"{{{key}}}"
            if placeholder not in text:
                continue
            value = safe(data.get(key))
            try:
                paragraph.paragraph_format.tab_stops.clear_all()
                paragraph.paragraph_format.tab_stops.add_tab_stop(
                    Inches(2.95),
                    WD_TAB_ALIGNMENT.LEFT,
                )
                paragraph.paragraph_format.tab_stops.add_tab_stop(
                    Inches(4.25),
                    WD_TAB_ALIGNMENT.LEFT,
                )
            except Exception:
                pass
            suffix = f" {unit}" if unit else ""
            set_paragraph_text(paragraph, f"{label}\t{value}\t{suffix}".rstrip())
            return True
        return False

    # ========================================================
    # REPLACEMENT ENGINE (ANTI-RUN SPLIT + PRESERVE FORMAT)
    # ========================================================

    def replace_in_paragraph(paragraph):

        if not paragraph or not paragraph.runs:
            return

        try:
            if align_time_sheet_paragraph(paragraph):
                return
            if align_quantity_paragraph(paragraph):
                return

            full_text = "".join(run.text for run in paragraph.runs)

            if not full_text:
                return

            updated_text = full_text

            for placeholder, value in placeholder_map.items():
                if placeholder in updated_text:
                    updated_text = updated_text.replace(
                        placeholder,
                        value
                    )

            updated_text = re.sub(r"\{[^{}]+\}", "", updated_text)

            if updated_text == full_text:
                return

            index = 0

            for run in paragraph.runs:
                original_length = len(run.text)

                if original_length == 0:
                    continue

                run.text = updated_text[index:index + original_length]
                index += original_length

            if index < len(updated_text):
                paragraph.runs[-1].text += updated_text[index:]

        except Exception:
            # Nunca permitir que el reemplazo rompa el proceso
            return

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

        # Header paragraphs
        for paragraph in section.header.paragraphs:
            replace_in_paragraph(paragraph)

        # Header tables
        for table in section.header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph)

        # Footer paragraphs
        for paragraph in section.footer.paragraphs:
            replace_in_paragraph(paragraph)

        # Footer tables
        for table in section.footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_in_paragraph(paragraph)

    # ========================================================
    # SAVE TEMP DOCX
    # ========================================================

    temp_docx = os.path.join(
        tempfile.gettempdir(),
        f"{draft_report_number}.docx"
    )

    apply_mci_docx_branding(doc, data)
    apply_docx_autofit(doc)
    doc.save(temp_docx)

    # ========================================================
    # LIBREOFFICE CONVERSION
    # ========================================================

    soffice_path = os.getenv("LIBREOFFICE_PATH", "soffice")

    output_dir = tempfile.mkdtemp(prefix="draft_word_pdf_")
    libre_profile = tempfile.mkdtemp(prefix="lo_profile_")

    cmd = [
        soffice_path,
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

    pdf_path = os.path.join(
        output_dir,
        f"{draft_report_number}.pdf"
    )

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF was not created")

    if os.path.getsize(pdf_path) == 0:
        raise RuntimeError("PDF was generated but is empty")

    return pdf_path
