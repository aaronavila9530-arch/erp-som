import os
import tempfile
import subprocess
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.worksheet.page import PageMargins


class VesselBunkerExcelPdfService:

    REQUIRED_SHEETS_ORDER = [
        "CERTIFICATE",
        "CALCULATIONS",
        "LOG BOOK FIGURES"
    ]

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def generate_pdf_from_excel(self, excel_path: str) -> str:

        if not excel_path:
            raise ValueError("Excel path is empty.")

        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        # 🔥 PASO 1 — PREPARAR EXCEL COMPLETAMENTE
        self._prepare_excel_for_pdf(excel_path)

        # 🔥 PASO 2 — CONVERTIR A PDF
        pdf_path = self._convert_excel_to_pdf(excel_path)

        if not pdf_path or not os.path.exists(pdf_path):
            raise RuntimeError("PDF conversion failed.")

        return pdf_path

    # =========================================================
    # PREPARE EXCEL
    # =========================================================
    def _prepare_excel_for_pdf(self, excel_path: str):

        wb = load_workbook(excel_path)

        # 🔥 FORZAR RECÁLCULO AL ABRIR
        wb.calculation.fullCalcOnLoad = True
        wb.calculation.forceFullCalc = True

        # 🔥 ELIMINAR HOJAS NO REQUERIDAS
        for sheet in list(wb.sheetnames):
            if sheet not in self.REQUIRED_SHEETS_ORDER:
                wb.remove(wb[sheet])

        # 🔥 REORDENAR
        for i, name in enumerate(self.REQUIRED_SHEETS_ORDER):
            if name in wb.sheetnames:
                wb._sheets.insert(i, wb._sheets.pop(wb.sheetnames.index(name)))

        # 🔥 CONFIGURAR CADA HOJA
        for sheet_name in self.REQUIRED_SHEETS_ORDER:

            ws = wb[sheet_name]

            # --------------------------------------------------
            # CONSTRUIR PRINT AREA DESDE A1 HASTA ÚLTIMA CELDA
            # --------------------------------------------------
            max_row = ws.max_row
            max_col = ws.max_column

            if max_row < 1:
                max_row = 1
            if max_col < 1:
                max_col = 1

            last_cell = ws.cell(row=max_row, column=max_col).coordinate
            ws.print_area = f"A1:{last_cell}"

            # --------------------------------------------------
            # ORIENTACIÓN VERTICAL
            # --------------------------------------------------
            ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT

            # --------------------------------------------------
            # 🔥 FORZAR A 1 SOLA PÁGINA
            # --------------------------------------------------
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 1

            # 🔥 ESCALA REDUCIDA LIGERAMENTE
            ws.page_setup.scale = 85  # puedes probar 80 si aún divide

            # --------------------------------------------------
            # MÁRGENES MÍNIMOS
            # --------------------------------------------------
            ws.page_margins = PageMargins(
                left=0.15,
                right=0.15,
                top=0.25,
                bottom=0.25,
                header=0.1,
                footer=0.1
            )

            # NO centrar horizontalmente
            ws.page_setup.horizontalCentered = False
            ws.page_setup.verticalCentered = False

        wb.save(excel_path)
        wb.close()

    # =========================================================
    # CONVERT
    # =========================================================
    def _convert_excel_to_pdf(self, excel_path: str) -> str:

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
            raise RuntimeError(
                f"LibreOffice conversion failed:\n{result.stderr}"
            )

        pdf_files = list(Path(output_dir).glob("*.pdf"))

        if not pdf_files:
            raise RuntimeError("PDF was not created.")

        return str(pdf_files[0])