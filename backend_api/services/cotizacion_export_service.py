from datetime import date
from pathlib import Path

from docx import Document
from backend_api.services.template_autofit import apply_docx_autofit
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
ASSET_DIRS = (
    BACKEND_DIR / "assets",
    REPO_DIR / "assets",
)


def _asset(name: str) -> str | None:
    for directory in ASSET_DIRS:
        path = directory / name
        if path.is_file():
            return str(path)
    return None


def export_cotizacion_word(data: dict, output_path: str):
    doc = Document()
    section = doc.sections[0]

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header_img = _asset("header.png")
    if header_img:
        header.add_run().add_picture(header_img, width=Inches(2.5))

    body = doc.add_paragraph()
    body.alignment = WD_ALIGN_PARAGRAPH.LEFT

    quotation_number = data.get("quotation_number") or ""
    if quotation_number:
        body.add_run(f"{quotation_number}\n").bold = True

    body.add_run(f"Alajuela, Costa Rica\n{date.today()}\n\n")

    idioma = data.get("idioma") or "ES"
    servicio = data.get("servicio") or ""
    subject = f"Quotation - {servicio}" if idioma == "EN" else f"Cotizacion - {servicio}"
    body.add_run(f"{'Subject' if idioma == 'EN' else 'Asunto'}: {subject}\n\n").bold = True
    body.add_run(data.get("texto") or "")

    doc.add_paragraph("\n")
    sig = doc.add_paragraph()
    sig.alignment = WD_ALIGN_PARAGRAPH.LEFT
    sig.add_run("Sincerely,\n\n" if idioma == "EN" else "Atentamente,\n\n")

    signature = _asset("FIRMA DIANA.png")
    if signature:
        sig.add_run().add_picture(signature, width=Inches(1.8))

    sig.add_run("\nDiana Quiros Benambourg\n")
    sig.add_run("Business Manager\n")
    sig.add_run("Marine Surveyors & Logistics Group SRL")

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.text = (
        "Head Office - Costa Rica, Alajuela, Plaza Aeropuerto G-14\n"
        "Phone (506) 8814-07-84 - (506) 4052-8382"
    )

    apply_docx_autofit(doc)
    doc.save(output_path)


def export_cotizacion_pdf(data: dict, output_path: str):
    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    left = 1 * inch
    header_y = height - 1.9 * inch
    top_y = header_y - 0.5 * inch
    footer_y = 0.7 * inch
    body_min_y = footer_y + 2.1 * inch

    watermark = _asset("watermark.png")
    header = _asset("header.png")
    signature = _asset("FIRMA DIANA.png")

    def draw_static():
        if watermark:
            c.saveState()
            c.setFillAlpha(0.08)
            c.drawImage(watermark, 1.2 * inch, 2.5 * inch, width=4.5 * inch, preserveAspectRatio=True, mask="auto")
            c.restoreState()
        if header:
            c.drawImage(header, left, header_y, width=3.6 * inch, preserveAspectRatio=True, mask="auto")

    draw_static()
    y = top_y

    quotation_number = data.get("quotation_number") or ""
    if quotation_number:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, quotation_number)
        y -= 22

    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Alajuela, Costa Rica")
    y -= 14
    c.drawString(left, y, str(date.today()))
    y -= 26

    idioma = data.get("idioma") or "ES"
    servicio = data.get("servicio") or ""
    subject = f"Quotation - {servicio}" if idioma == "EN" else f"Cotizacion - {servicio}"
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, subject[:105])
    y -= 24

    c.setFont("Helvetica", 10)
    for line in (data.get("texto") or "").split("\n"):
        if y < body_min_y:
            c.showPage()
            draw_static()
            y = top_y
            c.setFont("Helvetica", 10)
        c.drawString(left, y, line[:115])
        y -= 14

    title_y = footer_y + 0.55 * inch
    name_y = title_y + 14
    signature_y = name_y + 18

    if signature:
        c.drawImage(signature, left, signature_y, width=1.8 * inch, height=0.6 * inch, preserveAspectRatio=True, mask="auto")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, name_y, "Diana Quiros Benambourg")
    c.setFont("Helvetica", 10)
    c.drawString(left, title_y, "Business Manager")
    c.drawString(left, title_y - 12, "MSL MARINE SURVEYORS & LOGISTICS GROUP SRL")

    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, footer_y, "Head Office - Costa Rica, Alajuela, Plaza Aeropuerto G-14 - Phone (506) 8814-07-84 - (506) 4052-8382")
    c.save()

