import os
import tempfile
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

        # 🔥 1️⃣ REMOVE NULL BULLET LINES FIRST
        self._remove_null_paragraphs(doc, data)

        # 🔥 2️⃣ THEN REPLACE VALUES
        self._replace_placeholders(doc, data)

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
    # SAFE VALUE
    # =========================================================
    def _safe(self, value):

        if value is None:
            return ""

        return str(value)

    # =========================================================
    # CORE REPLACEMENT ENGINE (FORMAT SAFE)
    # =========================================================
    def _replace_placeholders(self, doc: Document, data: dict):

        placeholders = {
            f"{{{key}}}": self._safe(value)
            for key, value in data.items()
        }

        # Replace in paragraphs
        for paragraph in doc.paragraphs:
            self._replace_in_paragraph(paragraph, placeholders)

        # Replace in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        self._replace_in_paragraph(paragraph, placeholders)

    # =========================================================
    # RUN-LEVEL SAFE REPLACEMENT
    # =========================================================
    def _replace_in_paragraph(self, paragraph, placeholders: dict):

        for run in paragraph.runs:
            if not run.text:
                continue

            original_text = run.text

            for placeholder, value in placeholders.items():
                if placeholder in original_text:
                    original_text = original_text.replace(
                        placeholder,
                        value
                    )

            run.text = original_text

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


    # =========================================================
    # REMOVE PARAGRAPHS IF PLACEHOLDER VALUE IS NULL
    # =========================================================
    # =========================================================
    # REMOVE PARAGRAPHS IF BULLET PLACEHOLDER IS NULL
    # =========================================================
    def _remove_null_paragraphs(self, doc: Document, data: dict):

        # Solo afectar secciones dinámicas
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

        # Remove from normal paragraphs
        for paragraph in list(doc.paragraphs):
            self._remove_if_contains_null(paragraph, null_placeholders)

        # Remove from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in list(cell.paragraphs):
                        self._remove_if_contains_null(
                            paragraph,
                            null_placeholders
                        )


    def _remove_if_contains_null(self, paragraph, null_placeholders):

        if not paragraph.text:
            return

        for placeholder in null_placeholders:
            if placeholder in paragraph.text:
                self._delete_paragraph(paragraph)
                return


    def _delete_paragraph(self, paragraph):

        p = paragraph._element
        p.getparent().remove(p)
        paragraph._p = paragraph._element = None


