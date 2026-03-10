import os
import tempfile
import subprocess
from datetime import datetime, date
from docx import Document


class VesselCraneInspectionPresentationWordService:

    TEMPLATE_NAME = "presentation_crane_inspection.docx"

    # =========================================================
    # MAIN
    # =========================================================

    def generate_pdf_by_id(self, conn, record_id: int) -> str:

        data = self._get_data(conn, record_id)

        if not data:
            raise ValueError("Record not found")

        template_path = self._get_template_path()

        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"Template not found: {template_path}"
            )

        doc = Document(template_path)

        # -----------------------------------------------------
        # FORMAT DATA (DATES → LONG ENGLISH)
        # -----------------------------------------------------

        data = self._format_dates(data)

        # -----------------------------------------------------
        # REPLACE PLACEHOLDERS (FORMAT SAFE)
        # -----------------------------------------------------

        self._replace_all(doc, data)

        # -----------------------------------------------------
        # SAVE TEMP WORD
        # -----------------------------------------------------

        tmp_dir = tempfile.gettempdir()

        word_path = os.path.join(
            tmp_dir,
            f"crane_inspection_{record_id}.docx"
        )

        pdf_path = word_path.replace(".docx", ".pdf")

        doc.save(word_path)

        # -----------------------------------------------------
        # CONVERT TO PDF (WINDOWS WORD)
        # -----------------------------------------------------

        subprocess.run([
            "powershell",
            "-Command",
            f"""
            $word = New-Object -ComObject Word.Application
            $word.Visible = $false
            $doc = $word.Documents.Open('{word_path}')
            $doc.SaveAs([ref] '{pdf_path}', [ref] 17)
            $doc.Close()
            $word.Quit()
            """
        ])

        return pdf_path

    # =========================================================
    # TEMPLATE PATH
    # =========================================================
    def _get_template_path(self):

        base_dir = os.path.dirname(os.path.abspath(__file__))

        template_path = os.path.abspath(
            os.path.join(
                base_dir,
                "..",
                "templates",
                self.TEMPLATE_NAME
            )
        )

        return template_path

    # =========================================================
    # GET DATA
    # =========================================================

    def _get_data(self, conn, record_id):

        cur = conn.cursor()

        cur.execute(
            """
            SELECT *
            FROM vessel_crane_inspection_reports
            WHERE id = %s
            """,
            (record_id,)
        )

        row = cur.fetchone()

        if not row:
            return None

        columns = [desc[0] for desc in cur.description]

        return dict(zip(columns, row))

    # =========================================================
    # FORMAT DATES → LONG ENGLISH
    # =========================================================

    def _format_dates(self, data):

        formatted = {}

        for k, v in data.items():

            if isinstance(v, (datetime, date)):

                formatted[k] = v.strftime("%B %d, %Y")

            else:

                formatted[k] = v

        return formatted

    # =========================================================
    # REPLACE EVERYWHERE
    # =========================================================

    def _replace_all(self, doc, data):

        # Paragraphs
        for p in doc.paragraphs:
            self._replace_runs(p, data)

        # Tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        self._replace_runs(p, data)

        # Headers
        for section in doc.sections:
            for p in section.header.paragraphs:
                self._replace_runs(p, data)

        # Footers
        for section in doc.sections:
            for p in section.footer.paragraphs:
                self._replace_runs(p, data)

    # =========================================================
    # SAFE RUN REPLACEMENT (NO FORMAT LOSS)
    # =========================================================

    def _replace_runs(self, paragraph, data):

        if not paragraph.runs:
            return

        for run in paragraph.runs:

            text = run.text

            for key, value in data.items():

                placeholder = "{{" + key + "}}"

                if placeholder in text:

                    text = text.replace(
                        placeholder,
                        "" if value is None else str(value)
                    )

            run.text = text