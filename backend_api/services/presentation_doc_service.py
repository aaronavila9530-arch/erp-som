# =====================================================
# TEMPLATE PATH
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

        full_text = "".join(run.text for run in p.runs)

        replaced = False
        for key, value in placeholders.items():
            if key in full_text:
                full_text = full_text.replace(key, value)
                replaced = True

        if replaced:
            base_run = p.runs[0]

            style = {
                "bold": base_run.bold,
                "italic": base_run.italic,
                "underline": base_run.underline,
                "font_name": base_run.font.name,
                "font_size": base_run.font.size,
                "font_color": base_run.font.color.rgb if base_run.font.color else None,
            }

            for run in p.runs:
                run.text = ""

            new_run = p.add_run(full_text)

            new_run.bold = style["bold"]
            new_run.italic = style["italic"]
            new_run.underline = style["underline"]
            new_run.font.name = style["font_name"]
            new_run.font.size = style["font_size"]
            if style["font_color"]:
                new_run.font.color.rgb = style["font_color"]

# =====================================================
# TABLES
# =====================================================
def _replace_in_tables(tables, placeholders):
    for table in tables:
        for row in table.rows:
            for cell in row.cells:
                _replace_in_paragraphs(cell.paragraphs, placeholders)
                if cell.tables:
                    _replace_in_tables(cell.tables, placeholders)

# =====================================================
# MAIN
# =====================================================
def generate_presentation_pdf(data: dict) -> str:
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH}")

    doc = Document(TEMPLATE_PATH)

    placeholders = {
        "{{CERT_NO}}": str(data.get("cert_no") or ""),
        "{{CONTAINER}}": str(data.get("container") or ""),
        "{{TO}}": str(data.get("to") or ""),
        "{{PLACE}}": str(data.get("place") or ""),
        "{{DATE}}": str(data.get("date") or "")
    }

    _replace_in_paragraphs(doc.paragraphs, placeholders)
    _replace_in_tables(doc.tables, placeholders)

    for section in doc.sections:
        _replace_in_paragraphs(section.header.paragraphs, placeholders)
        _replace_in_tables(section.header.tables, placeholders)
        _replace_in_paragraphs(section.footer.paragraphs, placeholders)
        _replace_in_tables(section.footer.tables, placeholders)

    fd, docx_path = tempfile.mkstemp(suffix=".docx")
    os.close(fd)
    doc.save(docx_path)

    out_dir = tempfile.mkdtemp()

    subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            out_dir,
            docx_path
        ],
        check=True
    )

    pdf_path = os.path.join(
        out_dir,
        os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
    )

    return pdf_path
