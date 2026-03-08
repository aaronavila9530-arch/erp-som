import os
import tempfile
from docx import Document
from datetime import datetime


class VesselCraneInspectionWordService:

    TEMPLATE_NAME = "crane_inspection_template.docx"

    # =====================================================
    # MAIN
    # =====================================================

    def generate_word_by_id(self, conn, record_id: int) -> str:

        data = self._get_data(conn, record_id)

        if not data:
            raise ValueError("Record not found")

        template_path = self._get_template_path()

        if not os.path.exists(template_path):
            raise FileNotFoundError(
                f"Template not found: {template_path}"
            )

        doc = Document(template_path)

        # remove empty placeholders
        self._remove_null_paragraphs(doc, data)

        # replace placeholders
        self._replace_placeholders(doc, data)

        output = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".docx"
        )

        doc.save(output.name)

        return output.name


    # =====================================================
    # GET DATA
    # =====================================================

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

        data = dict(zip(columns, row))

        # format dates
        for k, v in data.items():

            if isinstance(v, datetime):
                data[k] = v.strftime("%B %d, %Y")

        return data


    # =====================================================
    # TEMPLATE PATH
    # =====================================================

    def _get_template_path(self):

        base_dir = os.path.dirname(
            os.path.dirname(__file__)
        )

        return os.path.join(
            base_dir,
            "templates",
            self.TEMPLATE_NAME
        )


    # =====================================================
    # REMOVE NULL PARAGRAPHS
    # =====================================================

    def _remove_null_paragraphs(self, doc, data):

        for paragraph in doc.paragraphs:

            text = paragraph.text

            for key, value in data.items():

                placeholder = f"{{{{{key}}}}}"

                if placeholder in text:

                    if value in [None, "", "null"]:

                        paragraph.text = ""


    # =====================================================
    # REPLACE PLACEHOLDERS
    # =====================================================

    def _replace_placeholders(self, doc, data):

        for paragraph in doc.paragraphs:

            for key, value in data.items():

                placeholder = f"{{{{{key}}}}}"

                if placeholder in paragraph.text:

                    paragraph.text = paragraph.text.replace(
                        placeholder,
                        "" if value is None else str(value)
                    )

        # tables
        for table in doc.tables:

            for row in table.rows:

                for cell in row.cells:

                    for key, value in data.items():

                        placeholder = f"{{{{{key}}}}}"

                        if placeholder in cell.text:

                            cell.text = cell.text.replace(
                                placeholder,
                                "" if value is None else str(value)
                            )

        # header footer
        for section in doc.sections:

            header = section.header
            footer = section.footer

            for paragraph in header.paragraphs:

                for key, value in data.items():

                    placeholder = f"{{{{{key}}}}}"

                    if placeholder in paragraph.text:

                        paragraph.text = paragraph.text.replace(
                            placeholder,
                            "" if value is None else str(value)
                        )

            for paragraph in footer.paragraphs:

                for key, value in data.items():

                    placeholder = f"{{{{{key}}}}}"

                    if placeholder in paragraph.text:

                        paragraph.text = paragraph.text.replace(
                            placeholder,
                            "" if value is None else str(value)
                        )