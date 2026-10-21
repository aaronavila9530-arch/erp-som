import os
import json
import re
import shutil
import tempfile
import subprocess
from datetime import datetime, date, time
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet
from psycopg2.extras import RealDictCursor


class DraftSurveyExcelPdfService:
    """
    Genera XLSX desde template + convierte a PDF (solo hojas seleccionadas).
    Fuente de datos: draft_survey + draft_survey_ballast + general_draft_survey
    """

    # =========================================================
    # TEMPLATE PATH (BACKEND)
    # =========================================================
    TEMPLATE_PATH = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "templates",
            "draft_survey_template.xlsx"
        )
    )

    # =========================================================
    # Hojas del template correcto de Draft Survey, en el mismo orden del Excel
    # oficial usado como referencia.
    # =========================================================
    KEEP_SHEETS = [
        "A",
        "B",
        "C",
        "General",
        "Draft",
        "E",
        "D1",
        "D2",
        "Hoja1",
        "D3",
        "Deductions",
        "Note of Protest SHORE SCALE ",
        "Note of Protest DRAFT",
    ]

    # =========================================================
    # MASTER MAPPING (LAZY LOAD PARA NO CRASHEAR STARTUP)
    # =========================================================
    EXCEL_MAPPING = None

    def _merge_preserving_values(self, target: dict, source: dict) -> None:
        for key, value in (source or {}).items():
            current = target.get(key)
            if key in target and current not in (None, "") and value in (None, ""):
                continue
            target[key] = value

    def _get_excel_mapping(self) -> dict:

        if isinstance(self.EXCEL_MAPPING, dict) and self.EXCEL_MAPPING:
            return self.EXCEL_MAPPING

        try:
            from services.draft_survey_excel_service import DraftSurveyExcelGenerator
            mapping = getattr(DraftSurveyExcelGenerator, "EXCEL_MAPPING", None)

            if not isinstance(mapping, dict) or not mapping:
                raise RuntimeError("DraftSurveyExcelGenerator.EXCEL_MAPPING not found or invalid")

            self.EXCEL_MAPPING = mapping
            return self.EXCEL_MAPPING

        except Exception as e:
            raise RuntimeError(f"Failed to load EXCEL_MAPPING: {e}")

    # =========================================================
    # DB: FETCH (3 TABLAS) → PAYLOAD
    # =========================================================
    def _fetch_payload_by_report_number(self, conn, draft_report_number: str) -> dict:

        draft_report_number = str(draft_report_number or "").strip()
        if not draft_report_number:
            raise ValueError("draft_report_number is required")

        if conn is None or not hasattr(conn, "cursor"):
            raise ValueError("Invalid DB connection")

        cur = conn.cursor(cursor_factory=RealDictCursor)

        try:
            cur.execute("""
                SELECT *
                FROM draft_survey
                WHERE draft_report_number = %s
                LIMIT 1
            """, (draft_report_number,))
            draft_row = cur.fetchone() or {}

            cur.execute("""
                SELECT *
                FROM draft_survey_ballast
                WHERE draft_report_number = %s
                LIMIT 1
            """, (draft_report_number,))
            ballast_row = cur.fetchone() or {}

            cur.execute("""
                SELECT *
                FROM general_draft_survey
                WHERE draft_report_number = %s
                LIMIT 1
            """, (draft_report_number,))
            general_row = cur.fetchone() or {}

            cur.execute("""
                SELECT *
                FROM draft_survey_word_report
                WHERE draft_report_number = %s
                LIMIT 1
            """, (draft_report_number,))
            word_row = cur.fetchone() or {}

        finally:
            try:
                cur.close()
            except Exception:
                pass

        if not draft_row and not general_row and not ballast_row:
            return {}

        payload = {}
        self._merge_preserving_values(payload, general_row or {})
        self._merge_preserving_values(payload, draft_row or {})
        self._merge_preserving_values(payload, ballast_row or {})
        self._merge_preserving_values(payload, word_row or {})

        payload["draft_report_number"] = draft_report_number

        ballast_json = payload.get("ballast_json")
        if isinstance(ballast_json, str):
            try:
                ballast_json = json.loads(ballast_json)
            except Exception:
                ballast_json = None
        if isinstance(ballast_json, dict):
            payload["ballast"] = ballast_json.get("ballast") or {}
            payload["fresh_water"] = ballast_json.get("fresh_water") or {}

        if "cargo" not in payload:
            payload["cargo"] = payload.get("init_cargo") or payload.get("final_cargo")

        if "port_from" not in payload:
            payload["port_from"] = payload.get("init_port_from") or payload.get("port_from")

        if "port_to" not in payload:
            payload["port_to"] = payload.get("init_port_to") or payload.get("port_to")

        payload.update(self._build_ballast_aliases(ballast_row or {}))

        return payload

    # =========================================================
    # BALLEST: MAP KEYS DB -> TEMPLATE KEYS (TU MAPPING)
    # =========================================================
    def _build_ballast_aliases(self, row: dict) -> dict:

        out = {}

        def _tank_code_to_template(code: str) -> str:
            return str(code or "").upper()

        def _side_to_template(side: str) -> str:
            return str(side or "").upper()

        for k, v in (row or {}).items():
            if v is None:
                continue

            key = str(k)

            if key.startswith(("init_fpt_", "final_fpt_", "init_apt_", "final_apt_")):
                parts = key.split("_")
                if len(parts) >= 3:
                    prefix = parts[0]
                    tank = parts[1]
                    rest = "_".join(parts[2:])
                    out[f"{prefix}_{_tank_code_to_template(tank)}_{rest}"] = v
                continue

            if key.startswith(("init_slop_tank_", "final_slop_tank_")):
                parts = key.split("_")
                if len(parts) >= 4:
                    prefix = parts[0]
                    rest = "_".join(parts[3:])
                    out[f"{prefix}_SLOP TANK_{rest}"] = v
                continue

            if key.startswith(("init_fw_wash_", "final_fw_wash_")):
                parts = key.split("_")
                if len(parts) >= 4:
                    prefix = parts[0]
                    rest = "_".join(parts[3:])
                    out[f"{prefix}_FW WASH_{rest}"] = v
                continue

            if key.startswith(("init_fw_", "final_fw_")):
                parts = key.split("_")
                if len(parts) >= 4:
                    prefix = parts[0]
                    tank = parts[2]
                    rest = "_".join(parts[3:])
                    out[f"{prefix}_FW {str(tank).upper()}_{rest}"] = v
                continue

            if key.startswith(("init_wbt_", "final_wbt_")):
                parts = key.split("_")
                if len(parts) >= 4:
                    prefix = parts[0]
                    tank = parts[1]
                    numside = parts[2]
                    rest = "_".join(parts[3:])

                    num = "".join(ch for ch in str(numside) if ch.isdigit())
                    side = "".join(ch for ch in str(numside) if ch.isalpha())

                    if num and side:
                        out[f"{prefix}_{_tank_code_to_template(tank)} {num}{_side_to_template(side)}_{rest}"] = v
                continue

        return out

    # =========================================================
    # SAFE SETTERS (MERGE SAFE + NUM SAFE)
    # =========================================================
    def _coerce_excel_value(self, value):
        if value in (None, ""):
            return value

        if isinstance(value, time):
            return value

        if isinstance(value, bool):
            return "YES" if value else "NO"

        if isinstance(value, (int, float)):
            return value

        if not isinstance(value, str):
            return value

        text = value.strip()
        if not text:
            return value
        text = self._strip_excel_text_prefix(text)
        if text.startswith("="):
            return text

        if re.fullmatch(r"\d{1,2}:\d{2}(:\d{2})?", text):
            try:
                return datetime.strptime(text, "%H:%M:%S" if text.count(":") == 2 else "%H:%M").time()
            except Exception:
                return value

        number_text = text.replace("\u00a0", "").replace(" ", "")
        allowed = set("0123456789+-.,")
        if any(ch not in allowed for ch in number_text):
            return value
        if any(sign in number_text[1:] for sign in "+-"):
            return value

        if "," in number_text and "." in number_text:
            if number_text.rfind(",") > number_text.rfind("."):
                number_text = number_text.replace(".", "").replace(",", ".")
            else:
                number_text = number_text.replace(",", "")
        elif "," in number_text:
            parts = number_text.split(",")
            if len(parts) == 2:
                number_text = f"{parts[0]}.{parts[1]}"
            else:
                number_text = number_text.replace(",", "")

        try:
            number = float(number_text)
        except Exception:
            return value

        if number.is_integer() and "." not in number_text:
            return int(number)
        return number

    def _strip_excel_text_prefix(self, text: str) -> str:
        if not isinstance(text, str):
            return text
        cleaned = text.strip()
        quote_chars = ("'", "`", "\u00b4", "\u2018", "\u2019")
        while len(cleaned) > 1 and cleaned[0] in quote_chars:
            next_char = cleaned[1]
            if next_char == "=" or next_char.isdigit() or next_char in "+-.,":
                cleaned = cleaned[1:].strip()
                continue
            break
        return cleaned

    def _safe_set(self, ws: Worksheet, cell: str, value):

        try:
            if value in (None, ""):
                return

            if not isinstance(cell, str) or not cell.strip():
                return

            value = self._coerce_excel_value(value)

            for merged in ws.merged_cells.ranges:
                if cell in merged:
                    ws.cell(row=merged.min_row, column=merged.min_col).value = value
                    return

            ws[cell].value = value

        except Exception:
            return

    def _safe_set_date(self, ws: Worksheet, cell: str, value):

        try:
            if not value:
                return

            if not isinstance(cell, str) or not cell.strip():
                return

            parsed = None

            if isinstance(value, (datetime, date)):
                parsed = value

            elif isinstance(value, str):
                date_part = " ".join(value.strip().replace(",", " ").split())

                date_formats = [
                    "%m-%d-%Y",
                    "%d-%m-%Y",
                    "%Y-%m-%d",
                    "%m/%d/%Y",
                    "%d/%m/%Y",
                    "%Y/%m/%d",
                    "%B %d %Y",
                    "%b %d %Y",
                    "%Y-%m-%d %H:%M",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M",
                    "%Y-%m-%dT%H:%M:%S",
                ]

                for fmt in date_formats:
                    try:
                        parsed = datetime.strptime(date_part, fmt)
                        break
                    except Exception:
                        continue

            if not parsed:
                return

            for merged in ws.merged_cells.ranges:
                if cell in merged:
                    c = ws.cell(row=merged.min_row, column=merged.min_col)
                    c.value = parsed
                    c.number_format = "DD-MM-YYYY"
                    return

            ws[cell].value = parsed
            ws[cell].number_format = "DD-MM-YYYY"

        except Exception:
            return

    # =========================================================
    # VALIDATE TEMPLATE + SHEETS
    # =========================================================
    def _validate_template(self, wb):

        if not wb or not hasattr(wb, "sheetnames"):
            raise RuntimeError("Invalid workbook loaded")

        missing = [s for s in self.KEEP_SHEETS if s not in wb.sheetnames]

        if missing:
            raise RuntimeError(
                "Template is missing required sheets: "
                + ", ".join(missing)
            )

    # =========================================================
    # GENERATE XLSX (SOLO HOJAS KEEP_SHEETS)
    # =========================================================
    def generate_excel_by_report_number(self, conn, draft_report_number: str) -> str:

        if not os.path.exists(self.TEMPLATE_PATH):
            raise FileNotFoundError(
                f"Draft Survey template not found: {self.TEMPLATE_PATH}"
            )

        payload = self._fetch_payload_by_report_number(conn, draft_report_number)

        if not payload:
            raise RuntimeError(
                "Draft Survey record not found for that report number"
            )

        tmp_dir = tempfile.mkdtemp(prefix="draft_excel_")
        out_xlsx = os.path.join(tmp_dir, f"draft_survey_{draft_report_number}.xlsx")

        from services.draft_survey_excel_service import DraftSurveyExcelGenerator

        generated_path = DraftSurveyExcelGenerator().generate(payload)
        shutil.copy2(generated_path, out_xlsx)

        if not os.path.exists(out_xlsx) or os.path.getsize(out_xlsx) == 0:
            raise RuntimeError("Excel was not generated")

        return out_xlsx

    # =========================================================
    # XLSX -> PDF (LIBREOFFICE)
    # =========================================================
    def convert_excel_to_pdf(self, excel_path: str) -> str:

        if not excel_path or not os.path.exists(excel_path):
            raise RuntimeError("Excel path invalid or missing")

        soffice_path = os.getenv("LIBREOFFICE_PATH", "soffice")

        output_dir = tempfile.mkdtemp(prefix="draft_excel_pdf_")
        libre_profile = tempfile.mkdtemp(prefix="lo_profile_")

        cmd = [
            soffice_path,
            "--headless",
            "--nologo",
            "--nodefault",
            "--nolockcheck",
            "--nofirststartwizard",
            "--norestore",
            f"-env:UserInstallation=file://{libre_profile}",
            "--convert-to",
            "pdf",
            "--outdir",
            output_dir,
            excel_path
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except FileNotFoundError:
            raise RuntimeError(
                "LibreOffice 'soffice' not found. Install LibreOffice in the container "
                "or set LIBREOFFICE_PATH."
            )

        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice PDF conversion failed:\n{result.stderr}"
            )

        # Buscar PDF generado (más robusto que asumir nombre exacto)
        pdf_files = sorted(
            [p for p in Path(output_dir).glob("*.pdf")],
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not pdf_files:
            raise RuntimeError("PDF was not created")

        pdf_path = str(pdf_files[0])

        if os.path.getsize(pdf_path) == 0:
            raise RuntimeError("PDF was generated but is empty")

        return pdf_path

    # =========================================================
    # PUBLIC: GENERATE PDF BY REPORT NUMBER
    # =========================================================
    def generate_pdf_by_report_number(self, conn, draft_report_number: str) -> str:
        xlsx_path = self.generate_excel_by_report_number(conn, draft_report_number)
        return self.convert_excel_to_pdf(xlsx_path)
