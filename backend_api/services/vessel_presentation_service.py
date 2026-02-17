import os
import tempfile
from typing import Dict
from docx import Document


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_grain_vessel.docx"
    )
)


# =====================================================
# INTERNAL — SAFE REPLACE (RUN-LEVEL, 1 PASADA)
# =====================================================
def _replace_in_paragraphs(paragraphs, placeholders: Dict[str, str]):
    """
    Reemplaza placeholders SOLO dentro del run donde existen.
    No reconstruye párrafo.
    No crea nuevos runs.
    No altera formato.
    No afecta texto adyacente.
    """
    for p in paragraphs:
        for run in p.runs:
            if not run.text:
                continue

            for key, value in placeholders.items():
                if key in run.text:
                    run.text = run.text.replace(key, value)
                    break  # 🔒 CRÍTICO: no tocar el run más de una vez


# =====================================================
# INTERNAL — TABLES (RECURSIVO SEGURO)
# =====================================================
def _replace_in_tables(tables, placeholders: Dict[str, str]):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, placeholders)

                # Si hay tablas anidadas
                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


# =====================================================
# MAIN
# =====================================================
def generate_vessel_presentation_doc(data: dict) -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Presentation template not found: {TEMPLATE_PATH}"
        )

    if not isinstance(data, dict):
        raise ValueError("Invalid data payload — expected dict")

    # ----------------------------------------
    # Normalizar fecha (solo YYYY-MM-DD)
    # ----------------------------------------
    raw_dt = data.get("sampling_start_time") or ""
    sampling_date = str(raw_dt).split(" ")[0] if raw_dt else ""

    placeholders = {
        "{cert_no}": str(data.get("cert_no") or ""),
        "{vessel_name}": str(data.get("vessel_name") or ""),
        "{ship_grt}": str(data.get("ship_grt") or ""),
        "{ship_nrt}": str(data.get("ship_nrt") or ""),
        "{requested_by}": str(data.get("requested_by") or ""),
        "{sampling_start_time}": sampling_date,
    }

    # ----------------------------------------
    # Cargar template
    # ----------------------------------------
    doc = Document(TEMPLATE_PATH)

    # BODY
    _replace_in_paragraphs(doc.paragraphs, placeholders)
    _replace_in_tables(doc.tables, placeholders)

    # HEADERS / FOOTERS
    for section in doc.sections:
        _replace_in_paragraphs(section.header.paragraphs, placeholders)
        _replace_in_tables(section.header.tables, placeholders)

        _replace_in_paragraphs(section.footer.paragraphs, placeholders)
        _replace_in_tables(section.footer.tables, placeholders)

    # ----------------------------------------
    # Guardar temporal
    # ----------------------------------------
    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(output_path)

    return output_path
