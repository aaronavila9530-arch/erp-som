import os
from pathlib import Path
from openpyxl import load_workbook
import win32com.client


class VesselHoldsInspectionExcelService:

    # =========================================================
    # TEMPLATE PATH (RELATIVE SAFE)
    # =========================================================
    def _get_template_path(self):

        base_dir = Path(__file__).resolve().parent.parent

        template_path = base_dir / "templates" / "holds_inspection_certificate.xlsx"

        if not template_path.exists():
            raise Exception("Excel template not found.")

        return template_path


    # =========================================================
    # BUILD EXCEL (INSERT DATA)
    # =========================================================
    def _build_excel(self, data: dict):

        template_path = self._get_template_path()

        wb = load_workbook(template_path)

        if "data" not in wb.sheetnames:
            raise Exception("Sheet 'data' not found in template.")

        ws = wb["data"]

        ordered_values = [

            data.get("id"),
            data.get("report_number"),
            data.get("port"),
            data.get("country"),
            data.get("vessel"),
            data.get("voyage"),
            data.get("load_port"),
            data.get("place"),
            data.get("installation"),
            data.get("product"),
            data.get("date"),
            data.get("inspection_time"),
            data.get("vessel_holds"),
            data.get("vessel_holds_status"),
            data.get("cargo_holds"),
            data.get("accepted_time"),
            data.get("place_location"),
            data.get("place_date"),
            data.get("hose_test_start"),
            data.get("hose_test_end"),
            data.get("remarks"),
            data.get("created_at"),
            data.get("updated_at"),
            data.get("status"),
            data.get("master_chief_officer")

        ]

        for idx, value in enumerate(ordered_values, start=1):
            ws.cell(row=idx, column=2, value=value)

        excel_path = Path.cwd() / f"holds_inspection_certificate_{data.get('id')}.xlsx"

        wb.save(excel_path)

        return excel_path


    # =========================================================
    # EXCEL → PDF (ONLY CERTIFICATE SHEET)
    # =========================================================
    def _excel_to_pdf(self, excel_path):

        pdf_path = str(excel_path).replace(".xlsx", ".pdf")

        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False

        wb = excel.Workbooks.Open(str(excel_path))

        try:

            sheet = wb.Worksheets("VESSEL HOLDS INSPECTION CERTIFI")

        except Exception:
            wb.Close(False)
            excel.Quit()
            raise Exception("Sheet 'VESSEL HOLDS INSPECTION CERTIFI' not found.")

        sheet.ExportAsFixedFormat(
            0,  # PDF
            pdf_path
        )

        wb.Close(False)
        excel.Quit()

        return pdf_path


    # =========================================================
    # PUBLIC METHOD
    # =========================================================
    def generate_pdf(self, data: dict):

        # 1) build excel
        excel_file = self._build_excel(data)

        # 2) convert to pdf (certificate sheet only)
        pdf_file = self._excel_to_pdf(excel_file)

        return pdf_file