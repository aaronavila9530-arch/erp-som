import os
from openpyxl import load_workbook


class VesselHoldsInspectionExcelService:

    TEMPLATE_PATH = r"C:\Users\Aaron Avila\Documents\ERP-SOM\backend_api\templates\holds_inspection_certificate.xlsx"

    # =========================================================
    # GENERATE EXCEL
    # =========================================================
    def generate_excel(self, data: dict):

        if not os.path.exists(self.TEMPLATE_PATH):
            raise Exception("Excel template not found.")

        wb = load_workbook(self.TEMPLATE_PATH)

        if "data" not in wb.sheetnames:
            raise Exception("Sheet 'data' not found in template.")

        ws = wb["data"]

        # =====================================================
        # ORDER (COLUMN A)
        # =====================================================

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

        # =====================================================
        # WRITE COLUMN B (FROM B1 DOWN)
        # =====================================================

        for idx, value in enumerate(ordered_values, start=1):

            ws.cell(row=idx, column=2, value=value)

        # =====================================================
        # SAVE TEMP FILE
        # =====================================================

        output_path = os.path.join(
            os.getcwd(),
            f"holds_inspection_certificate_{data.get('id')}.xlsx"
        )

        wb.save(output_path)

        return output_path