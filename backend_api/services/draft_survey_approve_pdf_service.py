import os
import shutil
import tempfile
from pathlib import Path

from docx import Document

# Word->PDF (Windows: Word via docx2pdf)
try:
    from docx2pdf import convert as docx2pdf_convert
except Exception:
    docx2pdf_convert = None

# Excel->PDF (Windows: Excel COM)
try:
    import pythoncom
    import win32com.client
except Exception:
    pythoncom = None
    win32com = None

from services.draft_survey_excel_service import generate_draft_survey_excel
from services.pdf_merge_service import merge_pdf_list


TEMPLATE_WORD_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "draft_word_template.docx"
    )
)

# Nombres EXACTOS de las hojas a poner en Landscape
LANDSCAPE_SHEETS = {
    "ECE DRAUGHT SURVEY CODE   Draught survey report",
    "ECE DRAUGHT SURVEY CODE D2",
}


class DraftSurveyApprovePdfService:
    """
    Approve -> Genera:
      1) Word Report (solo draft_survey_word_report) -> PDF
      2) Excel (template) -> PDF por hoja (solo página 1 por hoja)
      3) Merge total -> PDF final
    """

    # =========================================================
    # PUBLIC
    # =========================================================
    def generate_final_pdf(self, word_payload: dict, excel_payload: dict) -> str:
        """
        word_payload: SOLO campos de draft_survey_word_report (word_* + metadata)
        excel_payload: payload completo para llenar excel template
        return: path del PDF final merged (temporal)
        """

        # 1) WORD -> PDF
        word_pdf = self._generate_word_pdf_from_template(word_payload)

        # 2) EXCEL -> PDFs por hoja
        excel_pdfs = self._generate_excel_sheet_pdfs(excel_payload)

        # 3) MERGE
        all_pdfs = [word_pdf] + excel_pdfs
        final_pdf = merge_pdf_list(all_pdfs)

        return final_pdf

    # =========================================================
    # WORD PIPELINE
    # =========================================================
    def _generate_word_pdf_from_template(self, payload: dict) -> str:
        if not os.path.exists(TEMPLATE_WORD_PATH):
            raise FileNotFoundError(f"Word template not found: {TEMPLATE_WORD_PATH}")

        # Crear DOCX temporal
        out_dir = tempfile.mkdtemp(prefix="draft_word_")
        tmp_docx = os.path.join(out_dir, "draft_word_filled.docx")

        # Cargar y reemplazar
        doc = Document(TEMPLATE_WORD_PATH)
        repl = self._build_replacements(payload)

        # Body
        self._replace_in_document(doc, repl)

        # Headers/Footers
        for section in doc.sections:
            self._replace_in_header_footer(section.header, repl)
            self._replace_in_header_footer(section.footer, repl)

        doc.save(tmp_docx)

        # Convertir DOCX -> PDF (Windows preferido: docx2pdf)
        tmp_pdf = os.path.join(out_dir, "draft_word_filled.pdf")
        self._convert_docx_to_pdf(tmp_docx, tmp_pdf)

        if not os.path.exists(tmp_pdf):
            raise RuntimeError("Word PDF was not created")

        return tmp_pdf

    def _build_replacements(self, payload: dict) -> dict:
        """
        Convierte {field} -> value (si None, reemplaza por "")
        OJO: Aquí solo se usa draft_survey_word_report.
        """
        repl = {}
        for k, v in (payload or {}).items():
            key = "{" + str(k) + "}"
            repl[key] = "" if v is None else str(v)
        return repl

    def _replace_in_document(self, doc: Document, repl: dict) -> None:
        # Paragraphs
        for p in doc.paragraphs:
            self._replace_in_paragraph_runs(p, repl)

        # Tables
        for t in doc.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        self._replace_in_paragraph_runs(p, repl)

    def _replace_in_header_footer(self, hf, repl: dict) -> None:
        for p in hf.paragraphs:
            self._replace_in_paragraph_runs(p, repl)
        for t in hf.tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        self._replace_in_paragraph_runs(p, repl)

    def _replace_in_paragraph_runs(self, paragraph, repl: dict) -> None:
        """
        Reemplazo “run-safe”:
        - Mantiene formato porque no recrea estilos; solo cambia texto en runs.
        - Maneja placeholders partidos en varios runs.
        """
        if not paragraph.runs:
            return

        full = "".join(r.text for r in paragraph.runs)
        if "{" not in full or "}" not in full:
            return

        changed = False
        for ph, val in repl.items():
            if ph in full:
                full = full.replace(ph, val)
                changed = True

        if not changed:
            return

        # Re-aplicar a runs preservando estilo del primer run
        # Estrategia: escribir todo en el primer run y vaciar los demás.
        paragraph.runs[0].text = full
        for r in paragraph.runs[1:]:
            r.text = ""

    def _convert_docx_to_pdf(self, docx_path: str, pdf_path: str) -> None:
        # Windows: docx2pdf usa Microsoft Word (respeta formatos)
        if docx2pdf_convert:
            out_dir = os.path.dirname(pdf_path)
            os.makedirs(out_dir, exist_ok=True)
            docx2pdf_convert(docx_path, out_dir)
            # docx2pdf genera pdf con mismo nombre
            generated = str(Path(docx_path).with_suffix(".pdf").name)
            gen_path = os.path.join(out_dir, generated)
            if os.path.exists(gen_path) and gen_path != pdf_path:
                shutil.move(gen_path, pdf_path)
            return

        # Fallback: LibreOffice soffice si existe en PATH (similar a tu servicio)
        import subprocess
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

        gen_path = str(Path(docx_path).with_suffix(".pdf"))
        if os.path.exists(gen_path) and gen_path != pdf_path:
            shutil.move(gen_path, pdf_path)

    # =========================================================
    # EXCEL PIPELINE
    # =========================================================
    def _generate_excel_sheet_pdfs(self, payload: dict) -> list:
        """
        1) Genera Excel usando tu servicio actual
        2) Abre con Excel COM
        3) PageSetup por hoja (landscape/portrait)
        4) ExportAsFixedFormat -> 1 página por hoja
        """
        if pythoncom is None or win32com is None:
            raise RuntimeError("win32com/pythoncom not available. Install pywin32.")

        excel_path = generate_draft_survey_excel(payload)
        if not excel_path or not os.path.exists(excel_path):
            raise RuntimeError("Excel file was not generated")

        out_dir = tempfile.mkdtemp(prefix="draft_excel_pdf_")
        pdfs = []

        pythoncom.CoInitialize()
        excel = win32com.client.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False

        # xlTypePDF = 0
        xlTypePDF = 0

        try:
            wb = excel.Workbooks.Open(excel_path, UpdateLinks=0, ReadOnly=True)

            for ws in wb.Worksheets:
                sheet_name = ws.Name

                # Orientación
                try:
                    if sheet_name in LANDSCAPE_SHEETS:
                        ws.PageSetup.Orientation = 2  # xlLandscape
                    else:
                        ws.PageSetup.Orientation = 1  # xlPortrait
                except Exception:
                    pass

                # Ajustes recomendados para que quepa “bonito”
                try:
                    ws.PageSetup.Zoom = False
                    ws.PageSetup.FitToPagesWide = 1
                    ws.PageSetup.FitToPagesTall = False
                except Exception:
                    pass

                # Exportar SOLO página 1
                pdf_path = os.path.join(out_dir, f"{self._safe_filename(sheet_name)}.pdf")

                ws.ExportAsFixedFormat(
                    Type=xlTypePDF,
                    Filename=pdf_path,
                    Quality=0,
                    IncludeDocProperties=True,
                    IgnorePrintAreas=False,
                    From=1,
                    To=1,
                    OpenAfterPublish=False
                )

                if os.path.exists(pdf_path):
                    pdfs.append(pdf_path)

        finally:
            try:
                wb.Close(False)
            except Exception:
                pass
            try:
                excel.Quit()
            except Exception:
                pass
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

        if not pdfs:
            raise RuntimeError("No sheet PDFs were created from Excel")

        return pdfs

    def _safe_filename(self, name: str) -> str:
        bad = '<>:"/\\|?*'
        for ch in bad:
            name = name.replace(ch, "_")
        return name.strip()[:120]