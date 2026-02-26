import os
import tempfile
from pathlib import Path
from docx import Document
from psycopg2.extras import RealDictCursor
from database import get_db

try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    docx2pdf_convert = None


TEMPLATE_PATH = r"C:\Users\Aaron Avila\Documents\ERP-SOM\backend_api\templates\draft_word_template.docx"


class DraftSurveyWordPdfService:

    # =====================================================
    # PUBLIC ENTRY
    # =====================================================
    def generate_pdf_by_report_number(self, draft_report_number: str) -> str:

        if not draft_report_number:
            raise ValueError("draft_report_number is required")

        data = self._fetch_data(draft_report_number)

        if not data:
            raise ValueError(
                f"No record found for draft_report_number: {draft_report_number}"
            )

        return self._generate_pdf_from_data(data)

    # =====================================================
    # FETCH DATA
    # =====================================================
    def _fetch_data(self, draft_report_number: str) -> dict:

        conn = get_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT *
            FROM draft_survey_word_report
            WHERE draft_report_number = %s
            LIMIT 1
        """, (draft_report_number,))

        row = cur.fetchone()

        cur.close()
        conn.close()

        return dict(row) if row else None

    # =====================================================
    # GENERATE PDF
    # =====================================================
    def _generate_pdf_from_data(self, data: dict) -> str:

        if not os.path.exists(TEMPLATE_PATH):
            raise FileNotFoundError("Word template not found")

        tmp_dir = tempfile.mkdtemp(prefix="draft_word_only_")
        tmp_docx = os.path.join(tmp_dir, "filled.docx")
        tmp_pdf = os.path.join(tmp_dir, "filled.pdf")

        doc = Document(TEMPLATE_PATH)

        replacements = {
            "{" + k + "}": "" if v is None else str(v)
            for k, v in data.items()
        }

        self._replace_placeholders(doc, replacements)

        doc.save(tmp_docx)

        self._convert_to_pdf(tmp_docx, tmp_pdf)

        if not os.path.exists(tmp_pdf):
            raise RuntimeError("PDF was not created")

        return tmp_pdf

    # =====================================================
    # PLACEHOLDER REPLACEMENT
    # =====================================================
    def _replace_placeholders(self, doc: Document, replacements: dict):

        for paragraph in doc.paragraphs:
            self._replace_in_paragraph(paragraph, replacements)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._replace_in_paragraph(paragraph, replacements)

    def _replace_in_paragraph(self, paragraph, replacements: dict):

        full_text = "".join(run.text for run in paragraph.runs)

        if "{" not in full_text:
            return

        for key, value in replacements.items():
            if key in full_text:
                full_text = full_text.replace(key, value)

        for i, run in enumerate(paragraph.runs):
            if i == 0:
                run.text = full_text
            else:
                run.text = ""

    # =====================================================
    # DOCX → PDF
    # =====================================================
    def _convert_to_pdf(self, docx_path: str, pdf_path: str):

        if docx2pdf_convert:
            docx2pdf_convert(docx_path, os.path.dirname(pdf_path))
            return

        raise RuntimeError(
            "docx2pdf not available. Install it or ensure Word is installed."
        )