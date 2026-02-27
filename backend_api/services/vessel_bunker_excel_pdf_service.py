import os
import tempfile
import subprocess
from pathlib import Path
from openpyxl import load_workbook


class VesselBunkerExcelPdfService:
    """
    Genera PDF final del Vessel Bunker Report
    combinando 3 hojas del Excel en este orden:

    1. CERTIFICATE
    2. CALCULATIONS
    3. LOG BOOK FIGURES
    """

    REQUIRED_SHEETS_ORDER = [
        "CERTIFICATE",
        "CALCULATIONS",
        "LOG BOOK FIGURES"
    ]

    # =========================================================
    # MAIN ENTRY
    # =========================================================
    def generate_pdf_from_excel(self, excel_path: str) -> str:

        if not excel_path or not os.path.exists(excel_path):
            raise FileNotFoundError("Excel file not found.")

        # 1️⃣ Reordenar hojas correctamente
        self._reorder_sheets(excel_path)

        # 2️⃣ Convertir Excel a PDF usando LibreOffice
        pdf_path = self._convert_excel_to_pdf(excel_path)

        if not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF conversion failed.")

        return pdf_path

    # =========================================================
    # REORDER SHEETS
    # =========================================================
    def _reorder_sheets(self, excel_path: str):

        wb = load_workbook(excel_path)

        # Validar que existan las hojas requeridas
        for sheet_name in self.REQUIRED_SHEETS_ORDER:
            if sheet_name not in wb.sheetnames:
                raise ValueError(f"Sheet '{sheet_name}' not found in workbook.")

        # Reordenar
        new_order = []
        for sheet_name in self.REQUIRED_SHEETS_ORDER:
            new_order.append(wb[sheet_name])

        # Reasignar orden interno
        wb._sheets = new_order

        wb.save(excel_path)

    # =========================================================
    # EXCEL → PDF
    # =========================================================
    def _convert_excel_to_pdf(self, excel_path: str) -> str:

        output_dir = tempfile.mkdtemp()

        command = [
            "soffice",
            "--headless",
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
                f"LibreOffice conversion failed: {e.stderr.decode()}"
            )

        base_name = Path(excel_path).stem
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        return pdf_path