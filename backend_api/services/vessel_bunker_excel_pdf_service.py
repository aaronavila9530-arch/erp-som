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

        if not excel_path:
            raise ValueError("Excel path is empty.")

        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        # 1️⃣ Validar que el Excel tenga datos reales
        self._validate_workbook_not_empty(excel_path)

        # 2️⃣ Reordenar hojas SIN perder datos
        self._reorder_sheets(excel_path)

        # 3️⃣ Convertir Excel a PDF usando LibreOffice
        pdf_path = self._convert_excel_to_pdf(excel_path)

        if not pdf_path or not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF conversion failed.")

        return pdf_path

    # =========================================================
    # VALIDATE WORKBOOK HAS DATA
    # =========================================================
    def _validate_workbook_not_empty(self, excel_path: str):

        wb = load_workbook(excel_path, data_only=True)

        has_data = False

        for sheet_name in self.REQUIRED_SHEETS_ORDER:
            if sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                for row in ws.iter_rows(values_only=True):
                    if any(cell not in (None, "") for cell in row):
                        has_data = True
                        break
                if has_data:
                    break

        wb.close()

        if not has_data:
            raise ValueError("Workbook appears to have no data before PDF conversion.")

    # =========================================================
    # REORDER SHEETS (SAFE)
    # =========================================================
    def _reorder_sheets(self, excel_path: str):

        wb = load_workbook(excel_path)

        # Validar que existan las hojas requeridas
        for sheet_name in self.REQUIRED_SHEETS_ORDER:
            if sheet_name not in wb.sheetnames:
                wb.close()
                raise ValueError(f"Sheet '{sheet_name}' not found in workbook.")

        # Mantener otras hojas pero mover las 3 requeridas al inicio
        ordered_sheets = []

        # Primero las requeridas en orden correcto
        for sheet_name in self.REQUIRED_SHEETS_ORDER:
            ordered_sheets.append(wb[sheet_name])

        # Luego cualquier otra hoja adicional
        for sheet_name in wb.sheetnames:
            if sheet_name not in self.REQUIRED_SHEETS_ORDER:
                ordered_sheets.append(wb[sheet_name])

        wb._sheets = ordered_sheets

        wb.save(excel_path)
        wb.close()

    # =========================================================
    # EXCEL → PDF (ROBUST)
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
            result = subprocess.run(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"LibreOffice conversion failed:\n{e.stderr.decode(errors='ignore')}"
            )

        base_name = Path(excel_path).stem
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        if not os.path.exists(pdf_path):
            raise RuntimeError(
                "LibreOffice finished but PDF file was not created."
            )

        return pdf_path