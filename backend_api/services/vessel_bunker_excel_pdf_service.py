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

        # 🔥 PASO 1 — CONGELAR FÓRMULAS CON VALORES CACHEADOS
        self._freeze_formulas_with_cached_values(excel_path)

        # 🔥 PASO 2 — PREPARAR IMPRESIÓN
        self._prepare_print(excel_path)

        # 🔥 PASO 3 — CONVERTIR
        return self._convert_excel_to_pdf(excel_path)

    # =========================================================
    # FREEZE FORMULAS
    # =========================================================
    def _freeze_formulas_with_cached_values(self, excel_path: str):

        wb_values = load_workbook(excel_path, data_only=True)
        wb_formulas = load_workbook(excel_path)

        for sheet_name in self.REQUIRED_SHEETS_ORDER:

            if sheet_name not in wb_formulas.sheetnames:
                continue

            ws_values = wb_values[sheet_name]
            ws_formulas = wb_formulas[sheet_name]

            for row in ws_formulas.iter_rows():
                for cell in row:
                    if cell.data_type == "f":
                        cached_value = ws_values[cell.coordinate].value

                        # 🔥 FORZAR VALOR SI EXISTE
                        if cached_value is not None:
                            cell.value = cached_value
                        else:
                            # si no hay valor cacheado, dejar 0 en vez de #NAME?
                            cell.value = 0

        wb_formulas.save(excel_path)
        wb_formulas.close()
        wb_values.close()

    # =========================================================
    # PREPARE PRINT
    # =========================================================
    def _prepare_print(self, excel_path: str):

        wb = load_workbook(excel_path)

        # eliminar hojas no necesarias
        for sheet in list(wb.sheetnames):
            if sheet not in self.REQUIRED_SHEETS_ORDER:
                wb.remove(wb[sheet])

        for ws in wb.worksheets:

            max_row = ws.max_row
            max_col = ws.max_column

            last_cell = ws.cell(row=max_row, column=max_col).coordinate
            ws.print_area = f"A1:{last_cell}"

            ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 1
            ws.page_setup.scale = 70

            ws.page_margins = PageMargins(
                left=0.15,
                right=0.15,
                top=0.25,
                bottom=0.25,
                header=0.1,
                footer=0.1
            )

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