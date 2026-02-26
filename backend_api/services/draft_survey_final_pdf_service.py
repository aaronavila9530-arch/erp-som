import os
import tempfile
from pathlib import Path

from psycopg2.extras import RealDictCursor

from services.draft_survey_excel_pdf_service import DraftSurveyExcelPdfService
from services.draft_survey_word_pdf_service import generate_draft_survey_word_pdf


class DraftSurveyFinalPdfService:
    """
    Genera:
      1) Word PDF (desde draft_survey_word_report)
      2) Excel PDF (desde template + 5 sheets)
      3) Merge -> 1 PDF final
    """

    # =========================================================
    # DB: WORD DATA
    # =========================================================
    def _get_word_data_by_report_number(self, conn, draft_report_number: str) -> dict:

        draft_report_number = str(draft_report_number or "").strip()
        if not draft_report_number:
            raise ValueError("draft_report_number is required")

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cur.execute("""
                SELECT *
                FROM draft_survey_word_report
                WHERE draft_report_number = %s
                LIMIT 1
            """, (draft_report_number,))

            return cur.fetchone() or {}

        finally:
            try:
                cur.close()
            except Exception:
                pass

    # =========================================================
    # PDF MERGE (ULTRA COMPATIBLE)
    # =========================================================
    def _merge_pdfs(self, pdf_paths: list[str], out_path: str) -> str:

        if not pdf_paths or len(pdf_paths) < 2:
            raise RuntimeError("At least 2 PDFs are required to merge")

        for p in pdf_paths:
            if not p or not os.path.exists(p) or os.path.getsize(p) == 0:
                raise RuntimeError(f"Invalid PDF for merge: {p}")

        # -----------------------------------------------------
        # INTENTAR pypdf moderno
        # -----------------------------------------------------
        try:
            from pypdf import PdfWriter, PdfReader

            writer = PdfWriter()

            for path in pdf_paths:
                reader = PdfReader(path)
                for page in reader.pages:
                    writer.add_page(page)

            with open(out_path, "wb") as f:
                writer.write(f)

        # -----------------------------------------------------
        # FALLBACK PyPDF2
        # -----------------------------------------------------
        except Exception:

            try:
                from PyPDF2 import PdfWriter, PdfReader

                writer = PdfWriter()

                for path in pdf_paths:
                    reader = PdfReader(path)
                    for page in reader.pages:
                        writer.add_page(page)

                with open(out_path, "wb") as f:
                    writer.write(f)

            except Exception as e:
                raise RuntimeError(
                    "No compatible PDF merge library installed "
                    "(install pypdf>=3.x or PyPDF2)"
                )

        if not os.path.exists(out_path):
            raise RuntimeError("Merged PDF was not created")

        if os.path.getsize(out_path) == 0:
            raise RuntimeError("Merged PDF is empty")

        return out_path

    # =========================================================
    # PUBLIC: GENERATE FINAL PDF
    # =========================================================
    def generate_final_pdf_by_report_number(self, conn, draft_report_number: str) -> str:

        draft_report_number = str(draft_report_number or "").strip()
        if not draft_report_number:
            raise ValueError("draft_report_number is required")

        # 1) Excel PDF
        excel_service = DraftSurveyExcelPdfService()
        excel_pdf_path = excel_service.generate_pdf_by_report_number(
            conn,
            draft_report_number
        )

        # 2) Word PDF
        word_data = self._get_word_data_by_report_number(conn, draft_report_number)

        if not word_data:
            raise RuntimeError("Word report row not found (draft_survey_word_report)")

        word_pdf_path = generate_draft_survey_word_pdf(word_data)

        # 3) Merge (orden: Excel primero, Word después) — cámbialo si quieres al revés
        out_dir = tempfile.mkdtemp(prefix="draft_final_pdf_")
        out_path = os.path.join(out_dir, f"{draft_report_number}_FINAL.pdf")

        return self._merge_pdfs(
            pdf_paths=[excel_pdf_path, word_pdf_path],
            out_path=out_path
        )