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
    # MAIN
    # =========================================================
    def generate_pdf_from_excel(self, excel_path: str) -> str:

        if not excel_path:
            raise ValueError("Excel path is empty.")

        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        # 🔥 SOLO PREPARAR IMPRESIÓN (NO TOCAR FÓRMULAS)
        self._prepare_print(excel_path)

        return self._convert_excel_to_pdf(excel_path)

    # =========================================================
    # PREPARE PRINT (SCALE INDIVIDUAL)
    # =========================================================
    def _prepare_print(self, excel_path: str):

        wb = load_workbook(excel_path)

        # 🔥 ELIMINAR HOJAS NO REQUERIDAS
        for sheet in list(wb.sheetnames):
            if sheet not in self.REQUIRED_SHEETS_ORDER:
                wb.remove(wb[sheet])

        # 🔥 REORDENAR
        for i, name in enumerate(self.REQUIRED_SHEETS_ORDER):
            if name in wb.sheetnames:
                wb._sheets.insert(i, wb._sheets.pop(wb.sheetnames.index(name)))

        # 🔥 CONFIGURAR CADA HOJA CON SCALE DIFERENTE
        for ws in wb.worksheets:

            max_row = ws.max_row
            max_col = ws.max_column

            last_cell = ws.cell(row=max_row, column=max_col).coordinate
            ws.print_area = f"A1:{last_cell}"

            ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = False

            # 🔥 SCALE INDIVIDUAL
            if ws.title == "CERTIFICATE":
                ws.page_setup.scale = 70
            else:
                ws.page_setup.scale = 80

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
        wb.close()

    # =========================================================
    # CONVERT
    # =========================================================
    def _convert_excel_to_pdf(self, excel_path: str) -> str:

        output_dir = tempfile.mkdtemp(prefix="bunker_pdf_")

        command = [
            "soffice",
            "--headless",
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
            raise RuntimeError(result.stderr)

        pdf_files = list(Path(output_dir).glob("*.pdf"))

        if not pdf_files:
            raise RuntimeError("PDF not created.")

        return str(pdf_files[0])