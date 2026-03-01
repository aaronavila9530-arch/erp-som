import os
import tempfile
from pathlib import Path
import win32com.client


class VesselBunkerExcelPdfService:
    """
    Genera PDF usando Excel real (NO LibreOffice)
    Respeta print_area, márgenes, fórmulas y layout exacto.
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

        output_dir = tempfile.mkdtemp(prefix="bunker_pdf_")
        pdf_path = os.path.join(
            output_dir,
            f"{Path(excel_path).stem}.pdf"
        )

        excel = None
        workbook = None

        try:
            excel = win32com.client.Dispatch("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False

            workbook = excel.Workbooks.Open(os.path.abspath(excel_path))

            # 🔥 FORZAR RECALCULO COMPLETO
            excel.CalculateFull()
            workbook.RefreshAll()

            # 🔥 SOLO EXPORTAR LAS 3 HOJAS
            sheets = workbook.Sheets

            sheet_indexes = []

            for i in range(1, sheets.Count + 1):
                name = sheets(i).Name
                if name in self.REQUIRED_SHEETS_ORDER:
                    sheet_indexes.append(i)

            if not sheet_indexes:
                raise ValueError("Required sheets not found in workbook.")

            workbook.WorkSheets(sheet_indexes).Select()

            # 🔥 EXPORTAR COMO PDF USANDO MOTOR EXCEL
            workbook.ActiveSheet.ExportAsFixedFormat(
                0,  # 0 = PDF
                pdf_path,
                Quality=0,
                IncludeDocProperties=True,
                IgnorePrintAreas=False,
                OpenAfterPublish=False
            )

        except Exception as e:
            raise RuntimeError(f"Excel PDF export failed: {str(e)}")

        finally:
            if workbook:
                workbook.Close(False)
            if excel:
                excel.Quit()

        if not os.path.exists(pdf_path):
            raise RuntimeError("PDF file was not created.")

        return pdf_path