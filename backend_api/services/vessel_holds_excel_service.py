import os
from pathlib import Path
from openpyxl import load_workbook
from reportlab.pdfgen import canvas


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
    # GENERATE EXCEL
    # =========================================================

    def generate_excel(self, data: dict):

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

        output_path = Path.cwd() / f"holds_inspection_certificate_{data.get('id')}.xlsx"

        wb.save(output_path)

        return str(output_path)


    # =========================================================
    # GENERATE PDF (FROM DATA)
    # =========================================================

    def generate_pdf(self, data: dict):

        pdf_path = Path.cwd() / f"holds_inspection_certificate_{data.get('id')}.pdf"

        c = canvas.Canvas(str(pdf_path))

        y = 800

        c.setFont("Helvetica", 11)

        for key, value in data.items():

            line = f"{key}: {value}"

            c.drawString(50, y, line)

            y -= 20

            if y < 50:
                c.showPage()
                y = 800

        c.save()

        return str(pdf_path)