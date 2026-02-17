import os
import tempfile
from typing import Dict
from docx import Document
from docx2pdf import convert


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_grain_vessel.docx"
    )
)


# =====================================================
# INTERNAL — SAFE REPLACE (CROSS-RUN SIN RECONSTRUIR)
# =====================================================
def _replace_in_paragraphs(paragraphs, placeholders: Dict[str, str]):
    """
    Reemplaza placeholders aunque estén fragmentados en múltiples runs.
    NO reconstruye el párrafo completo.
    NO altera texto contiguo.
    """
    for p in paragraphs:
        for key, value in placeholders.items():

            full_text = "".join(run.text for run in p.runs)

            if key not in full_text:
                continue

            start = full_text.find(key)
            end = start + len(key)

            current_pos = 0

            for run in p.runs:
                run_text = run.text
                run_len = len(run_text)

                run_start = current_pos
                run_end = current_pos + run_len

                if run_end > start and run_start < end:

                    prefix_len = max(0, start - run_start)
                    suffix_len = max(0, run_end - end)

                    prefix = run_text[:prefix_len]
                    suffix = run_text[run_len - suffix_len:] if suffix_len > 0 else ""

                    if run_start <= start < run_end:
                        run.text = prefix + value + suffix
                    else:
                        run.text = ""

                current_pos += run_len


def _replace_in_tables(tables, placeholders: Dict[str, str]):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, placeholders)
                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


# =====================================================
# MAIN — GENERATE PDF WITH WORD (docx2pdf)
# =====================================================
def generate_vessel_presentation_pdf(data: dict) -> str:

    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Presentation template not found: {TEMPLATE_PATH}"
        )

    if not isinstance(data, dict):
        raise ValueError("Invalid data payload — expected dict")

    # Normalizar fecha
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

    # Cargar template
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

    # Guardar DOCX temporal
    fd, temp_docx = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(temp_docx)

    # Crear ruta PDF final
    temp_pdf = temp_docx.replace(".docx", ".pdf")

    # Convertir usando Microsoft Word real
    convert(temp_docx, temp_pdf)

    if not os.path.exists(temp_pdf):
        raise RuntimeError("PDF conversion failed")

    return temp_pdf
