import os
import tempfile
import subprocess
from docx import Document


# =====================================================
# TEMPLATE PATH (ABSOLUTO Y REAL)
# =====================================================
TEMPLATE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "templates",
        "presentation_containers.docx"
    )
)


# =====================================================
# INTERNAL — SAFE REPLACE (PRESERVA ESTILOS)
# =====================================================
def _replace_in_paragraphs(paragraphs, placeholders: dict):
    for p in paragraphs:
        if not p.runs:
            continue

        # Texto completo (Word puede fragmentarlo en runs)
        full_text = "".join(run.text for run in p.runs)

        replaced = False
        for key, value in placeholders.items():
            if key in full_text:
                full_text = full_text.replace(key, value)
                replaced = True

        if replaced:
            base_run = p.runs[0]

            # Guardar estilo base
            style = {
                "bold": base_run.bold,
                "italic": base_run.italic,
                "underline": base_run.underline,
                "font_name": base_run.font.name,
                "font_size": base_run.font.size,
                "font_color": (
                    base_run.font.color.rgb
                    if base_run.font.color and base_run.font.color.rgb
                    else None
                ),
            }

            # Limpiar runs
            for run in p.runs:
                run.text = ""

            # Nuevo run con texto final
            new_run = p.add_run(full_text)

            # Restaurar estilo
            new_run.bold = style["bold"]
            new_run.italic = style["italic"]
            new_run.underline = style["underline"]
            new_run.font.name = style["font_name"]
            new_run.font.size = style["font_size"]
            if style["font_color"]:
                new_run.font.color.rgb = style["font_color"]


# =====================================================
# INTERNAL — TABLES
# =====================================================
def _replace_in_tables(tables, placeholders):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, placeholders)
                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)


# =====================================================
# MAIN — GENERATE PRESENTATION PDF
# =====================================================
def generate_presentation_pdf(data: dict) -> str:
    """
    Genera PDF desde presentation_containers.docx
    Reemplaza placeholders respetando estilos
    """

    # -----------------------------
    # VALIDATIONS
    # -----------------------------
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(
            f"Presentation template not found: {TEMPLATE_PATH}"
        )

    if not isinstance(data, dict):
        raise ValueError("Invalid data payload — expected dict")

    # -----------------------------
    # LOAD TEMPLATE
    # -----------------------------
    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{{CERT_NO}}": str(data.get("cert_no") or ""),
        "{{CONTAINER}}": str(data.get("container") or ""),
        "{{TO}}": str(data.get("to") or ""),
        "{{PLACE}}": str(data.get("place") or ""),
        "{{DATE}}": str(data.get("date") or "")
    }

    # -----------------------------
    # BODY
    # -----------------------------
    _replace_in_paragraphs(doc.paragraphs, placeholders)
    _replace_in_tables(doc.tables, placeholders)

    # -----------------------------
    # HEADERS / FOOTERS
    # -----------------------------
    for section in doc.sections:
        _replace_in_paragraphs(section.header.paragraphs, placeholders)
        _replace_in_tables(section.header.tables, placeholders)

        _replace_in_paragraphs(section.footer.paragraphs, placeholders)
        _replace_in_tables(section.footer.tables, placeholders)

    # -----------------------------
    # SAVE TEMP DOCX
    # -----------------------------
    fd, docx_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(docx_path)

    output_dir = tempfile.mkdtemp()

    # -----------------------------
    # CONVERT TO PDF (LibreOffice)
    # -----------------------------
    try:
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--nologo",
                "--nolockcheck",
                "--convert-to",
                "pdf",
                "--outdir",
                output_dir,
                docx_path
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE
        )

    except FileNotFoundError:
        raise RuntimeError(
            "LibreOffice (soffice) is not installed or not available in PATH"
        )

    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Error converting DOCX to PDF: {e.stderr.decode(errors='ignore')}"
        )

    # -----------------------------
    # VALIDATE OUTPUT
    # -----------------------------
    pdf_path = os.path.join(
        output_dir,
        os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    )

    if not os.path.exists(pdf_path):
        raise RuntimeError("PDF generation failed — output file not found")

    return pdf_path
