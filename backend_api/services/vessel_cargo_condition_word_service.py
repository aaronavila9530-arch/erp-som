import os
import tempfile
from datetime import datetime, date
from docx import Document


class VesselCargoConditionWordService:

    TEMPLATE_NAME = "cargo_condition_template.docx"

    # =========================================================
    # MAIN
    # =========================================================
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

        # REMOVE NULL BULLET LINES FIRST
        self._remove_null_paragraphs(doc, data)

        # REPLACE PLACEHOLDERS EVERYWHERE
        self._replace_placeholders_everywhere(doc, data)

        output_path = self._build_output_path(data)

        doc.save(output_path)

        return output_path

    # =========================================================
    # FETCH DATA
    # =========================================================
    def _get_data(self, conn, record_id: int):

        cur = conn.cursor()

        cur.execute("""
            SELECT *
            FROM vessel_cargo_condition_surveys
            WHERE id = %s
        """, (record_id,))

        row = cur.fetchone()

        if not row:
            return None

        columns = [desc[0] for desc in cur.description]

        return dict(zip(columns, row))

    # =========================================================
    # TEMPLATE PATH
    # =========================================================
    def _get_template_path(self):

        base_dir = os.path.dirname(os.path.abspath(__file__))

        return os.path.abspath(
            os.path.join(
                base_dir,
                "..",
                "templates",
                self.TEMPLATE_NAME
            )
        )

    # =========================================================
    # SAFE VALUE (DATE FORMAT LONG ENGLISH)
    # =========================================================
    def _safe(self, value):

        if value is None:
            return ""

        if isinstance(value, (datetime, date)):
            return value.strftime("%B %d %Y")

        if isinstance(value, str):
            value = value.strip()
            try:
                dt = datetime.strptime(value[:10], "%Y-%m-%d")
                return dt.strftime("%B %d %Y")
            except Exception:
                pass

        return str(value)

    # =========================================================
    # REPLACE EVERYWHERE
    # =========================================================
    def _replace_placeholders_everywhere(self, doc: Document, data: dict):

        placeholders = {
            f"{{{key}}}": self._safe(value)
            for key, value in data.items()
        }

        # BODY
        for paragraph in doc.paragraphs:
            self._replace_in_paragraph_safe(paragraph, placeholders)

        # TABLES
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._replace_in_paragraph_safe(paragraph, placeholders)

        # HEADERS & FOOTERS
        for section in doc.sections:

            for paragraph in section.header.paragraphs:
                self._replace_in_paragraph_safe(paragraph, placeholders)

            for table in section.header.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            self._replace_in_paragraph_safe(paragraph, placeholders)

            for paragraph in section.footer.paragraphs:
                self._replace_in_paragraph_safe(paragraph, placeholders)

            for table in section.footer.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            self._replace_in_paragraph_safe(paragraph, placeholders)

    # =========================================================
    # SAFE MULTI-RUN REPLACEMENT (NO FORMAT LOSS)
    # =========================================================
    def _replace_in_paragraph_safe(self, paragraph, placeholders: dict):

        if not paragraph.runs:
            return

        full_text = "".join(run.text for run in paragraph.runs)

        for placeholder, value in placeholders.items():

            if placeholder not in full_text:
                continue

            # Replace in full string
            new_text = full_text.replace(placeholder, value)

            # Now rebuild WITHOUT destroying first run format
            first_run = paragraph.runs[0]
            first_run.text = new_text

            # Clear remaining runs
            for run in paragraph.runs[1:]:
                run.text = ""

            # Update full_text reference
            full_text = new_text

    # =========================================================
    # REMOVE NULL BULLET LINES
    # =========================================================
    def _remove_null_paragraphs(self, doc: Document, data: dict):

        bullet_prefixes = (
            "narrative_",
            "findings_",
            "remarks_",
            "conclusion_"
        )

        null_placeholders = {
            f"{{{key}}}"
            for key, value in data.items()
            if value is None and key.startswith(bullet_prefixes)
        }

        for paragraph in list(doc.paragraphs):
            self._remove_if_contains_null(paragraph, null_placeholders)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in list(cell.paragraphs):
                        self._remove_if_contains_null(paragraph, null_placeholders)

    # =========================================================
    # REMOVE IF CONTAINS NULL PLACEHOLDER
    # =========================================================
    def _remove_if_contains_null(self, paragraph, null_placeholders):

        if not paragraph.text:
            return

        for placeholder in null_placeholders:
            if placeholder in paragraph.text:
                self._delete_paragraph(paragraph)
                return

    # =========================================================
    # SAFE DELETE
    # =========================================================
    def _delete_paragraph(self, paragraph):

        p = paragraph._element
        p.getparent().remove(p)
        paragraph._p = paragraph._element = None

    # =========================================================
    # OUTPUT PATH
    # =========================================================
    def _build_output_path(self, data: dict):

        report_number = data.get("report_number") or "CARGO_CONDITION"

        safe_name = report_number.replace("/", "_").replace("\\", "_")

        temp_dir = tempfile.gettempdir()

        return os.path.join(
            temp_dir,
            f"{safe_name}_CARGO_CONDITION.docx"
        )