import os
import tempfile
from typing import Dict, Optional, Tuple, List

from docx import Document
from docx.text.run import Run


TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_grain_vessel.docx"
    )
)


# =====================================================
# INTERNAL — RUN INSERT (mantiene formato del run base)
# =====================================================
def _clone_run_format(src: Run, dst: Run) -> None:
    """
    Copia formato del run (bold/italic/underline/color/size/font/etc.)
    sin tocar el texto.
    """
    # Fuente y estilos directos
    dst.bold = src.bold
    dst.italic = src.italic
    dst.underline = src.underline
    dst.style = src.style

    # Font
    dst.font.name = src.font.name
    dst.font.size = src.font.size
    dst.font.color.rgb = src.font.color.rgb if src.font.color is not None else None
    dst.font.highlight_color = src.font.highlight_color
    dst.font.all_caps = src.font.all_caps
    dst.font.small_caps = src.font.small_caps
    dst.font.strike = src.font.strike
    dst.font.double_strike = src.font.double_strike
    dst.font.subscript = src.font.subscript
    dst.font.superscript = src.font.superscript
    dst.font.shadow = src.font.shadow
    dst.font.outline = src.font.outline
    dst.font.rtl = src.font.rtl
    dst.font.cs = src.font.cs


def _insert_run_after(run: Run, text: str, format_from: Run) -> Run:
    """
    Inserta un nuevo run inmediatamente después de `run` preservando el formato.
    """
    paragraph = run._parent
    new_run = paragraph.add_run("")  # se crea al final; luego lo movemos
    _clone_run_format(format_from, new_run)
    new_run.text = text

    # mover new_run justo después de run
    run._r.addnext(new_run._r)
    return new_run


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
# INTERNAL — REPLACE (cross-run sin romper estilos)
# =====================================================
def _replace_placeholder_in_paragraph(paragraph, placeholder: str, value: str) -> bool:
    """
    Reemplaza UN placeholder en un paragraph, incluso si está partido entre runs,
    sin reconstruir el párrafo completo (preserva estilos).

    Retorna True si reemplazó algo.
    """
    if not paragraph.runs:
        return False

    full_text, spans = _build_run_index(paragraph)
    if not full_text or placeholder not in full_text:
        return False

    # Reemplazamos TODAS las ocurrencias del placeholder en este paragraph
    replaced_any = False
    while True:
        full_text, spans = _build_run_index(paragraph)
        idx = full_text.find(placeholder)
        if idx == -1:
            break

        start_pos = idx
        end_pos = idx + len(placeholder)

        start_run_idx = _find_run_at_pos(spans, start_pos)
        # end_pos-1 porque end_pos es exclusivo
        end_run_idx = _find_run_at_pos(spans, max(start_pos, end_pos - 1))

        start_run = paragraph.runs[start_run_idx]
        end_run = paragraph.runs[end_run_idx]

        start_run_start, _ = spans[start_run_idx]
        end_run_start, end_run_end = spans[end_run_idx]

        # offsets dentro de los runs
        start_off = start_pos - start_run_start
        end_off_exclusive = end_pos - end_run_start  # exclusivo en end_run

        # Texto antes/después del placeholder
        start_text = start_run.text or ""
        end_text = end_run.text or ""

        prefix = start_text[:start_off]
        suffix = end_text[end_off_exclusive:] if end_off_exclusive <= len(end_text) else ""

        # Caso 1: placeholder está dentro del mismo run
        if start_run_idx == end_run_idx:
            start_run.text = start_text.replace(placeholder, value, 1)
            replaced_any = True
            continue

        # Caso 2: placeholder cruza varios runs
        # 1) dejamos prefix en start_run
        start_run.text = prefix

        # Elegimos el formato del placeholder: normalmente el run donde empieza (o el siguiente si prefix ocupa algo)
        fmt_run = start_run
        if start_off == len(start_text) and start_run_idx + 1 < len(paragraph.runs):
            fmt_run = paragraph.runs[start_run_idx + 1]

        # 2) limpiamos runs intermedios (incluyendo end_run por ahora)
        for i in range(start_run_idx + 1, end_run_idx + 1):
            paragraph.runs[i].text = ""

        # 3) insertamos run con el valor, con formato del placeholder
        value_run = _insert_run_after(start_run, value, fmt_run)

        # 4) si hay suffix, lo insertamos preservando formato del end_run
        if suffix:
            _insert_run_after(value_run, suffix, end_run)

        replaced_any = True

    return replaced_any


def _replace_in_paragraphs(paragraphs, placeholders: Dict[str, str]) -> None:
    for p in paragraphs:
        # Reemplazar cada placeholder; si el template tiene runs partidos, esto lo resuelve.
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

    # Normaliza fecha (si viene datetime o string con hora)
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

    # HEADERS / FOOTERS (por si el template los usa)
    for section in doc.sections:
        _replace_in_paragraphs(section.header.paragraphs, placeholders)
        _replace_in_tables(section.header.tables, placeholders)

        _replace_in_paragraphs(section.footer.paragraphs, placeholders)
        _replace_in_tables(section.footer.tables, placeholders)

    fd, output_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(output_path)
    return output_path
