import os
import tempfile
from typing import Dict, List, Tuple

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
# INTERNAL — MAP TEXT POS -> RUN INDEX
# =====================================================
def _build_run_index(paragraph) -> Tuple[str, List[Tuple[int, int]]]:
    """
    Devuelve:
      - full_text concatenado de runs
      - spans: lista (start,end) por run sobre full_text
    """
    spans: List[Tuple[int, int]] = []
    parts: List[str] = []
    pos = 0

    for r in paragraph.runs:
        t = r.text or ""
        parts.append(t)
        start = pos
        pos += len(t)
        end = pos
        spans.append((start, end))

    return "".join(parts), spans


def _find_run_at_pos(spans: List[Tuple[int, int]], pos: int) -> int:
    """
    Dado un índice pos en full_text, devuelve el índice del run que lo contiene.
    """
    for i, (s, e) in enumerate(spans):
        if s <= pos < e:
            return i
    return max(0, len(spans) - 1)


# =====================================================
# INTERNAL — SAFE REPLACE (CROSS-RUN SIN CREAR RUNS)
# =====================================================
def _replace_placeholder_in_paragraph(paragraph, placeholder: str, value: str) -> bool:
    """
    Reemplaza placeholder incluso si está partido entre runs, SIN:
    - crear runs nuevos
    - mover nodos
    - reconstruir párrafo

    Preserva 100% el formato de:
    - texto a la par del placeholder
    - runs anteriores/siguientes (ej. "CERT N°" azul)
    - el formato del run objetivo (el que ya tenía el estilo del placeholder)
    """
    if not paragraph.runs:
        return False

    replaced_any = False

    while True:
        full_text, spans = _build_run_index(paragraph)
        idx = full_text.find(placeholder)
        if idx == -1:
            break

        start_pos = idx
        end_pos = idx + len(placeholder)  # exclusivo

        start_run_idx = _find_run_at_pos(spans, start_pos)
        end_run_idx = _find_run_at_pos(spans, max(start_pos, end_pos - 1))

        start_run = paragraph.runs[start_run_idx]
        end_run = paragraph.runs[end_run_idx]

        start_run_start, _ = spans[start_run_idx]
        end_run_start, _ = spans[end_run_idx]

        start_off = start_pos - start_run_start
        end_off_exclusive = end_pos - end_run_start

        start_text = start_run.text or ""
        end_text = end_run.text or ""

        prefix = start_text[:start_off]
        suffix = end_text[end_off_exclusive:] if end_off_exclusive <= len(end_text) else ""

        # Caso 1: todo en el mismo run
        if start_run_idx == end_run_idx:
            start_run.text = start_text[:start_off] + value + start_text[start_off + len(placeholder):]
            replaced_any = True
            continue

        # Caso 2: cruza varios runs
        # 1) preserva prefijo en start_run y sufijo en end_run
        start_run.text = prefix
        end_run.text = suffix

        # 2) seleccionar run objetivo para el VALOR sin cambiar formato:
        #    preferimos un run intermedio "real" (ej: 'cert_no', 'vessel_name') si existe.
        target_idx = None
        for i in range(start_run_idx + 1, end_run_idx):
            t = paragraph.runs[i].text or ""
            if t.strip():  # suele ser 'cert_no' sin llaves
                target_idx = i
                break

        # fallback: si no hay intermedio, usamos start o end según convenga
        if target_idx is None:
            # Si start_run solo era '{' normalmente prefix queda vacío -> OK usar start_run
            # Si no, usar end_run para no mezclar con prefix
            target_idx = start_run_idx if prefix == "" else end_run_idx

        # 3) vaciar runs internos excepto el objetivo
        for i in range(start_run_idx + 1, end_run_idx):
            if i == target_idx:
                continue
            paragraph.runs[i].text = ""

        # 4) escribir el valor en el run objetivo SIN tocar estilos
        target_run = paragraph.runs[target_idx]
        target_run.text = value

        replaced_any = True

    return replaced_any


def _replace_in_paragraphs(paragraphs, placeholders: Dict[str, str]) -> None:
    for p in paragraphs:
        for key, val in placeholders.items():
            _replace_placeholder_in_paragraph(p, key, val)


def _replace_in_tables(tables, placeholders: Dict[str, str]) -> None:
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, placeholders)
                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


# =====================================================
# MAIN
# =====================================================
def generate_vessel_presentation_doc(data: dict) -> str:
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Presentation template not found: {TEMPLATE_PATH}")

    if not isinstance(data, dict):
        raise ValueError("Invalid data payload — expected dict")

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

    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(output_path)
    return output_path
