import os
from pathlib import Path
from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class VesselHoldsInspectionExcelService:

    # =========================================================
    # TEMPLATE PATH
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

        temp_excel = Path.cwd() / f"holds_inspection_certificate_{data.get('id')}.xlsx"

        wb.save(temp_excel)

        return temp_excel


    # =========================================================
    # GENERATE PDF FROM CERTIFICATE SHEET
    # =========================================================
    def _excel_layout_to_pdf(self, excel_path):

        wb = load_workbook(excel_path, data_only=True)

        if "VESSEL HOLDS INSPECTION CERTIFI" not in wb.sheetnames:
            raise Exception("Certificate sheet not found.")

        ws = wb["VESSEL HOLDS INSPECTION CERTIFI"]

        pdf_path = str(excel_path).replace(".xlsx", ".pdf")

        c = canvas.Canvas(pdf_path, pagesize=A4)

        y = 800

        for row in ws.iter_rows(values_only=True):

            line = " ".join([str(v) for v in row if v is not None])

            if line.strip():
                c.drawString(50, y, line)
                y -= 18

                if y < 50:
                    c.showPage()
                    y = 800

        c.save()

        return pdf_path



    # =========================================================
    # PUBLIC METHOD
    # =========================================================
    def generate_pdf(self, data: dict):

        excel_file = self._build_excel(data)

        pdf_file = self._excel_layout_to_pdf(excel_file)

        return pdf_file