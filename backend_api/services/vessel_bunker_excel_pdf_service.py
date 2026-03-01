import os
import tempfile
import subprocess
from pathlib import Path
from psycopg2.extras import RealDictCursor
from openpyxl import load_workbook
from openpyxl.worksheet.page import PageMargins

from services.vessel_bunker_excel_service import VesselBunkerExcelGenerator


class VesselBunkerExcelPdfService:

    REQUIRED_SHEETS_ORDER = [
        "CERTIFICATE",
        "CALCULATIONS",
        "LOG BOOK FIGURES"
    ]

    SCALE_MAP = {
        "CERTIFICATE": 70,
        "CALCULATIONS": 80,
        "LOG BOOK FIGURES": 80
    }

    # =========================================================
    # MAIN ENTRY — BUILD EXCEL FIRST
    # =========================================================
    def generate_pdf_by_report_id(self, conn, report_id: int) -> str:

        if not report_id:
            raise ValueError("report_id is required")

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            # -------------------------------------------------
            # 1️⃣ OBTENER DATOS
            # -------------------------------------------------
            cur.execute(
                "SELECT * FROM vessel_bunker_reports WHERE id=%s",
                (report_id,)
            )
            row = cur.fetchone()

            if not row:
                raise Exception("Vessel bunker report not found")

            payload = dict(row)

            # -------------------------------------------------
            # 2️⃣ GENERAR EXCEL COMPLETO
            # -------------------------------------------------
            generator = VesselBunkerExcelGenerator()
            excel_path = generator.generate(payload)

            if not excel_path or not os.path.exists(excel_path):
                raise Exception("Excel generation failed")

            # -------------------------------------------------
            # 3️⃣ PREPARAR IMPRESIÓN
            # -------------------------------------------------
            self._prepare_print(excel_path)

            # -------------------------------------------------
            # 4️⃣ CONVERTIR A PDF
            # -------------------------------------------------
            return self._convert_excel_to_pdf(excel_path)

        finally:
            cur.close()

    # =========================================================
    # PREPARE PRINT (NO ELIMINA DATA FROM DB)
    # =========================================================
    def _prepare_print(self, excel_path: str):

        if not os.path.exists(excel_path):
            raise FileNotFoundError("Excel file not found for print preparation")

        wb = load_workbook(excel_path)

        try:
            # -------------------------------------------------
            # VALIDAR QUE EXISTAN LAS HOJAS REQUERIDAS
            # -------------------------------------------------
            for sheet_name in self.REQUIRED_SHEETS_ORDER:
                if sheet_name not in wb.sheetnames:
                    raise Exception(f"Required sheet '{sheet_name}' not found in workbook")

            # -------------------------------------------------
            # OCULTAR SOLO LAS NO REQUERIDAS (NO BORRAR)
            # -------------------------------------------------
            for ws in wb.worksheets:
                if ws.title not in self.REQUIRED_SHEETS_ORDER:
                    ws.sheet_state = "hidden"
                else:
                    ws.sheet_state = "visible"

            # -------------------------------------------------
            # REORDENAR: visibles primero
            # -------------------------------------------------
            visible = [wb[s] for s in self.REQUIRED_SHEETS_ORDER]
            hidden = [wb[s] for s in wb.sheetnames if s not in self.REQUIRED_SHEETS_ORDER]
            wb._sheets = visible + hidden

            # -------------------------------------------------
            # CONFIGURAR IMPRESIÓN
            # -------------------------------------------------
            for ws in visible:

                max_row = max(ws.max_row, 1)
                max_col = max(ws.max_column, 1)
                last_cell = ws.cell(row=max_row, column=max_col).coordinate

                ws.print_area = f"A1:{last_cell}"

                ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
                ws.page_setup.fitToWidth = 1
                ws.page_setup.fitToHeight = 1

                ws.page_setup.scale = self.SCALE_MAP.get(ws.title, 80)

                ws.page_margins = PageMargins(
                    left=0.15,
                    right=0.15,
                    top=0.25,
                    bottom=0.25,
                    header=0.1,
                    footer=0.1
                )

                ws.page_setup.horizontalCentered = False
                ws.page_setup.verticalCentered = False

            wb.save(excel_path)

        finally:
            wb.close()

    # =========================================================
    # CONVERT
    # =========================================================
    def _convert_excel_to_pdf(self, excel_path: str) -> str:

        if not os.path.exists(excel_path):
            raise FileNotFoundError("Excel file not found for conversion")

        output_dir = tempfile.mkdtemp(prefix="bunker_pdf_")

        command = [
            "soffice",
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--nofirststartwizard",
            "--norestore",
            "--convert-to",
            "pdf",
            excel_path,
            "--outdir",
            output_dir
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"LibreOffice conversion failed:\n{result.stderr}")

        pdf_files = list(Path(output_dir).glob("*.pdf"))

        if not pdf_files:
            raise RuntimeError("PDF was not created by LibreOffice")

        return str(pdf_files[0])