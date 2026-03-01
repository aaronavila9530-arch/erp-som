import os
import tempfile
import subprocess
from pathlib import Path
from openpyxl import load_workbook


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

        # 1️⃣ Reemplazar fórmulas por valores
        self._freeze_formulas_to_values(excel_path)

        # 2️⃣ Convertir a PDF
        pdf_path = self._convert_excel_to_pdf(excel_path)

        if not pdf_path or not os.path.exists(pdf_path):
            raise RuntimeError("PDF conversion failed.")

        return pdf_path

    # =========================================================
    # FREEZE FORMULAS
    # =========================================================
    def _freeze_formulas_to_values(self, excel_path: str):

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
                        value = ws_values[cell.coordinate].value
                        cell.value = value

        wb_formulas.save(excel_path)
        wb_formulas.close()
        wb_values.close()

    # =========================================================
    # CONVERT USING LIBREOFFICE
    # =========================================================
    def _convert_excel_to_pdf(self, excel_path: str) -> str:

        output_dir = tempfile.mkdtemp(prefix="bunker_pdf_")

        command = [
            "soffice",
            "--headless",
            "--nologo",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            excel_path,
            "--outdir",
            output_dir
        ]

        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"LibreOffice conversion failed:\n{e.stderr.decode(errors='ignore')}"
            )

        pdf_path = os.path.join(
            output_dir,
            f"{Path(excel_path).stem}.pdf"
        )

        return pdf_path