import os
import shutil
import tempfile
import subprocess
from pathlib import Path
from docx import Document

try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    docx2pdf_convert = None

from services.draft_survey_excel_service import DraftSurveyExcelGenerator
from services.pdf_merge_service import merge_pdf_list


TEMPLATE_WORD_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "draft_word_template.docx"
    )
)


class DraftSurveyApprovePdfService:

    # =========================================================
    # PUBLIC
    # =========================================================
    def generate_final_pdf(self, word_payload: dict, excel_payload: dict) -> str:

        word_pdf = self._generate_word_pdf_from_template(word_payload)
        excel_pdf = self._generate_excel_pdf_from_template(excel_payload)

        final_pdf = merge_pdf_list([word_pdf, excel_pdf])
        return final_pdf

    # =========================================================
    # WORD PIPELINE (FORMATO 100% RESPETADO)
    # =========================================================
    def _generate_word_pdf_from_template(self, payload: dict) -> str:

        if not os.path.exists(TEMPLATE_WORD_PATH):
            raise FileNotFoundError(f"Word template not found: {TEMPLATE_WORD_PATH}")

        out_dir = tempfile.mkdtemp(prefix="draft_word_")
        tmp_docx = os.path.join(out_dir, "draft_word_filled.docx")

        doc = Document(TEMPLATE_WORD_PATH)
        replacements = self._build_replacements(payload)

        self._replace_in_document(doc, replacements)

        for section in doc.sections:
            self._replace_in_container(section.header, replacements)
            self._replace_in_container(section.footer, replacements)

        doc.save(tmp_docx)

        tmp_pdf = os.path.join(out_dir, "draft_word_filled.pdf")
        self._convert_docx_to_pdf(tmp_docx, tmp_pdf)

        if not os.path.exists(tmp_pdf):
            raise RuntimeError("Word PDF was not created")

        return tmp_pdf

    def _build_replacements(self, payload: dict) -> dict:
        repl = {}
        for k, v in (payload or {}).items():
            repl["{" + str(k) + "}"] = "" if v is None else str(v)
        return repl

    def _replace_in_document(self, doc: Document, repl: dict):
        for p in doc.paragraphs:
            self._replace_in_paragraph_safe(p, repl)

        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        self._replace_in_paragraph_safe(p, repl)

    def _replace_in_container(self, container, repl: dict):
        for p in container.paragraphs:
            self._replace_in_paragraph_safe(p, repl)

        for t in container.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        self._replace_in_paragraph_safe(p, repl)

    def _replace_in_paragraph_safe(self, paragraph, repl: dict):
        if not paragraph.runs:
            return

        full_text = "".join(run.text for run in paragraph.runs)

        if "{" not in full_text:
            return

        changed = False
        for ph, val in repl.items():
            if ph in full_text:
                full_text = full_text.replace(ph, val)
                changed = True

        if not changed:
            return

        idx = 0
        for run in paragraph.runs:
            length = len(run.text)
            run.text = full_text[idx: idx + length]
            idx += length

        if idx < len(full_text):
            paragraph.runs[-1].text += full_text[idx:]

    def _convert_docx_to_pdf(self, docx_path: str, pdf_path: str):

        if docx2pdf_convert:
            out_dir = os.path.dirname(pdf_path)
            os.makedirs(out_dir, exist_ok=True)
            docx2pdf_convert(docx_path, out_dir)

            generated = Path(docx_path).with_suffix(".pdf").name
            gen_path = os.path.join(out_dir, generated)

            if os.path.exists(gen_path) and gen_path != pdf_path:
                shutil.move(gen_path, pdf_path)
            return

        out_dir = os.path.dirname(pdf_path)
        os.makedirs(out_dir, exist_ok=True)

        cmd = [
            "soffice",
            "--headless",
            "--nologo",
            "--nolockcheck",
            "--convert-to", "pdf",
            "--outdir", out_dir,
            docx_path
        ]

        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if r.returncode != 0:
            raise RuntimeError(f"DOCX->PDF conversion failed:\n{r.stderr}")

    # =========================================================
    # EXCEL -> PDF (VERSIÓN DEFINITIVA ESTABLE WINDOWS)
    # =========================================================
    def _generate_excel_pdf_from_template(self, payload: dict) -> str:

        try:
            import pythoncom
            import win32com.client
            import time
        except Exception:
            raise RuntimeError(
                "Microsoft Excel COM (pywin32) no está disponible."
            )

        generator = DraftSurveyExcelGenerator()
        excel_path = generator.generate(payload)

        if not excel_path or not os.path.exists(excel_path):
            raise RuntimeError("Excel file was not generated")

        # 🔥 GUARDAR EL PDF EN EL MISMO DIRECTORIO DEL EXCEL
        output_dir = os.path.dirname(excel_path)
        pdf_path = os.path.join(output_dir, "draft_survey.pdf")

        pythoncom.CoInitialize()

        excel = None
        workbook = None

        try:
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            excel.EnableEvents = False

            workbook = excel.Workbooks.Open(
                os.path.abspath(excel_path),
                UpdateLinks=0,
                ReadOnly=False
            )

            # Esperar a que cargue completamente
            time.sleep(1)

            workbook.Activate()

            # Recalcular completamente
            try:
                excel.CalculateFullRebuild()
            except Exception:
                pass

            time.sleep(0.5)

            # 🔥 Export directo desde el workbook (más estable)
            workbook.ExportAsFixedFormat(
                Type=0,  # xlTypePDF
                Filename=os.path.abspath(pdf_path),
                Quality=0,
                IncludeDocProperties=True,
                IgnorePrintAreas=False,
                OpenAfterPublish=False
            )

        except Exception as e:
            raise RuntimeError(f"Excel COM PDF export failed:\n{e}")

        finally:
            try:
                if workbook:
                    workbook.Close(False)
            except Exception:
                pass

            try:
                if excel:
                    excel.Quit()
            except Exception:
                pass

            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        if not os.path.exists(pdf_path):
            raise RuntimeError("Excel PDF was not created")

        return pdf_path

