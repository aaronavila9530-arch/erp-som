import os
import tempfile
from pathlib import Path
from typing import Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from docx import Document

try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    docx2pdf_convert = None


# =========================================================
# TEMPLATE PATH (RELATIVE TO PROJECT ROOT)
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = BASE_DIR / "templates" / "draft_word_template.docx"


# =========================================================
# SERVICE
# =========================================================
class DraftSurveyWordPdfService:

    # =====================================================
    # PUBLIC ENTRY
    # =====================================================
    def generate_pdf_by_report_number(self, draft_report_number: str) -> str:

        draft_report_number = (draft_report_number or "").strip()

        if not draft_report_number:
            raise ValueError("draft_report_number is required")

        data = self._fetch_data(draft_report_number)

        if not data:
            raise ValueError(
                f"No record found for draft_report_number: {draft_report_number}"
            )

        return self._generate_pdf_from_data(data)

    # =====================================================
    # DATABASE CONNECTION (ENVIRONMENT SAFE)
    # =====================================================
    def _get_connection(self):
        try:
            return psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
            )
        except Exception as e:
            raise RuntimeError(f"Database connection error: {str(e)}")

    # =====================================================
    # FETCH DATA
    # =====================================================
    def _fetch_data(self, draft_report_number: str) -> Optional[Dict]:

        conn = self._get_connection()

        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM draft_survey_word_report
                    WHERE draft_report_number = %s
                    LIMIT 1
                """, (draft_report_number,))

                row = cur.fetchone()
                return dict(row) if row else None

        finally:
            conn.close()

    # =====================================================
    # GENERATE PDF
    # =====================================================
    def _generate_pdf_from_data(self, data: Dict) -> str:

        if not TEMPLATE_PATH.exists():
            raise FileNotFoundError(
                f"Word template not found at {TEMPLATE_PATH}"
            )

        tmp_dir = Path(tempfile.mkdtemp(prefix="draft_word_"))
        tmp_docx = tmp_dir / "filled.docx"
        tmp_pdf = tmp_dir / "filled.pdf"

        doc = Document(str(TEMPLATE_PATH))

        replacements = {
            "{" + str(k) + "}": "" if v is None else str(v)
            for k, v in data.items()
        }

        self._replace_placeholders(doc, replacements)

        doc.save(str(tmp_docx))

        self._convert_to_pdf(tmp_docx, tmp_pdf)

        if not tmp_pdf.exists():
            raise RuntimeError("PDF was not created")

        return str(tmp_pdf)

    # =====================================================
    # PLACEHOLDER REPLACEMENT
    # =====================================================
    def _replace_placeholders(self, doc: Document, replacements: Dict):

        # Paragraphs
        for paragraph in doc.paragraphs:
            self._replace_in_paragraph(paragraph, replacements)

        # Tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._replace_in_paragraph(paragraph, replacements)

    def _replace_in_paragraph(self, paragraph, replacements: Dict):

        full_text = "".join(run.text for run in paragraph.runs)

        if "{" not in full_text:
            return

        for key, value in replacements.items():
            if key in full_text:
                full_text = full_text.replace(key, value)

        # Reset runs safely
        if paragraph.runs:
            paragraph.runs[0].text = full_text
            for run in paragraph.runs[1:]:
                run.text = ""

    # =====================================================
    # DOCX → PDF
    # =====================================================
    def _convert_to_pdf(self, docx_path: Path, pdf_path: Path):

        if not docx2pdf_convert:
            raise RuntimeError(
                "docx2pdf not available. Install it and ensure Microsoft Word is installed."
            )

        try:
            docx2pdf_convert(str(docx_path), str(pdf_path.parent))
        except Exception as e:
            raise RuntimeError(f"Error converting to PDF: {str(e)}")