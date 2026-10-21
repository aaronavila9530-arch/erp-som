from datetime import date
from pathlib import Path
import tempfile

from docx import Document
try:
    from services.template_autofit import apply_docx_autofit
except ModuleNotFoundError:
    from backend_api.services.template_autofit import apply_docx_autofit
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from docx.shared import Inches
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

try:
    from branding import footer_text, is_mci_context, logo_asset, watermark_asset
except ModuleNotFoundError:
    from backend_api.branding import footer_text, is_mci_context, logo_asset, watermark_asset


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


def _is_mci(data: dict) -> bool:
    return is_mci_context(data)


def _logo_width_inches(data: dict) -> float:
    return 0.78 if _is_mci(data) else 2.5


def _pdf_logo_width(data: dict, inch_unit: float) -> float:
    return (0.72 if _is_mci(data) else 3.6) * inch_unit


def _make_faded_watermark(image_path: str) -> str | None:
    try:
        from PIL import Image
    except Exception:
        return None

    try:
        image = Image.open(image_path).convert("RGBA")
        alpha = image.getchannel("A").point(lambda value: int(value * 0.13))
        image.putalpha(alpha)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp.close()
        image.save(temp.name)
        return temp.name
    except Exception:
        return None


def _add_docx_watermark(header, image_path: str) -> str | None:
    faded_path = _make_faded_watermark(image_path)
    source_path = faded_path or image_path
    rel_id, _image = header.part.get_or_add_image(source_path)
    paragraph = header.add_paragraph()
    paragraph._p.append(parse_xml(
        f"""
        <w:r {nsdecls('w', 'r')} xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
          <w:pict>
            <v:shape id="MCIWatermark"
              o:spid="_x0000_s1025"
              type="#_x0000_t75"
              style="position:absolute;margin-left:205pt;margin-top:185pt;width:185pt;height:231pt;z-index:-251654144;mso-position-horizontal:absolute;mso-position-vertical:absolute"
              o:allowincell="f">
              <v:imagedata r:id="{rel_id}" o:title="MCI watermark"/>
            </v:shape>
          </w:pict>
        </w:r>
        """
    ))
    return faded_path


def export_cotizacion_word(data: dict, output_path: str):
    doc = Document()
    section = doc.sections[0]
    if _is_mci(data):
        section.top_margin = Inches(1.2)
        section.header_distance = Inches(0.2)

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.LEFT
    header_img = logo_asset(data) or _asset("header.png")
    if header_img:
        header.add_run().add_picture(header_img, width=Inches(_logo_width_inches(data)))
    temp_watermark = None
    if _is_mci(data):
        watermark_img = watermark_asset(data) or header_img
        if watermark_img:
            temp_watermark = _add_docx_watermark(section.header, watermark_img)

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

    if _is_mci(data):
        sig.add_run("\nMsc. Diana Quiros Benambourg\n")
        sig.add_run("Business Manager\n").bold = True
        sig.add_run("MSL 2.0\n").bold = True
        sig.add_run("MARINE CLAIMS & RISK INTELLIGENCE").bold = True
    else:
        sig.add_run("\nDiana Quiros Benambourg\n")
        sig.add_run("Business Manager\n")
        sig.add_run("Marine Surveyors & Logistics Group SRL")

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.text = footer_text(data)

    apply_docx_autofit(doc)
    doc.save(output_path)
    if temp_watermark:
        try:
            Path(temp_watermark).unlink(missing_ok=True)
        except Exception:
            pass


def export_cotizacion_pdf(data: dict, output_path: str):
    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER
    left = 0.75 * inch
    right = 0.75 * inch
    body_width = width - left - right
    mci_branding = _is_mci(data)
    header_y = height - (1.28 * inch if mci_branding else 1.9 * inch)
    top_y = height - (1.85 * inch if mci_branding else 2.4 * inch)
    footer_y = 0.7 * inch
    signature_block_height = 1.55 * inch
    body_min_y = footer_y + 0.35 * inch

    watermark = watermark_asset(data) or _asset("watermark.png")
    header = logo_asset(data) or _asset("header.png")
    signature = _asset("FIRMA DIANA.png")

    def wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
        text = str(text or "")
        if not text:
            return [""]
        wrapped = []
        for raw_line in text.splitlines() or [""]:
            line = raw_line.strip()
            if not line:
                wrapped.append("")
                continue
            words = line.split(" ")
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if stringWidth(candidate, font_name, font_size) <= max_width:
                    current = candidate
                    continue
                if current:
                    wrapped.append(current)
                    current = word
                else:
                    piece = ""
                    for ch in word:
                        candidate_piece = piece + ch
                        if stringWidth(candidate_piece, font_name, font_size) <= max_width:
                            piece = candidate_piece
                        else:
                            if piece:
                                wrapped.append(piece)
                            piece = ch
                    current = piece
            wrapped.append(current)
        return wrapped

    def draw_footer():
        c.setFont("Helvetica", 8)
        c.drawCentredString(
            width / 2,
            footer_y,
            " - ".join(footer_text(data).splitlines()),
        )

    def draw_image_aspect(path: str, x: float, y: float, target_width: float, alpha: float | None = None):
        image = ImageReader(path)
        image_width, image_height = image.getSize()
        target_height = target_width * (image_height / image_width)
        if alpha is not None:
            c.saveState()
            c.setFillAlpha(alpha)
            c.drawImage(image, x, y, width=target_width, height=target_height, mask="auto")
            c.restoreState()
            return target_height
        c.drawImage(image, x, y, width=target_width, height=target_height, mask="auto")
        return target_height

    def draw_static():
        if watermark:
            wm_width = (2.6 if mci_branding else 4.5) * inch
            wm_x = (width - wm_width) / 2
            image = ImageReader(watermark)
            image_width, image_height = image.getSize()
            wm_height = wm_width * (image_height / image_width)
            wm_y = (height - wm_height) / 2
            draw_image_aspect(watermark, wm_x, wm_y, wm_width, alpha=0.11 if mci_branding else 0.08)
        if header:
            header_width = _pdf_logo_width(data, inch)
            if mci_branding:
                image = ImageReader(header)
                image_width, image_height = image.getSize()
                header_height = header_width * (image_height / image_width)
                c.drawImage(
                    image,
                    left,
                    height - 0.35 * inch - header_height,
                    width=header_width,
                    height=header_height,
                    mask="auto",
                )
            else:
                draw_image_aspect(header, left, header_y, header_width)
        draw_footer()

    def new_page():
        c.showPage()
        draw_static()
        c.setFont("Helvetica", 10)
        return top_y

    def draw_wrapped_line(text: str, font_name: str, font_size: int, y_pos: float, min_y: float) -> float:
        c.setFont(font_name, font_size)
        for wrapped_line in wrap_text(text, font_name, font_size, body_width):
            if y_pos < min_y:
                y_pos = new_page()
                c.setFont(font_name, font_size)
            c.drawString(left, y_pos, wrapped_line)
            y_pos -= 14 if font_size <= 10 else 16
        return y_pos

    draw_static()
    y = top_y

    quotation_number = data.get("quotation_number") or ""
    if quotation_number:
        y = draw_wrapped_line(quotation_number, "Helvetica-Bold", 11, y, body_min_y)
        y -= 8

    y = draw_wrapped_line("Alajuela, Costa Rica", "Helvetica-Bold", 10, y, body_min_y)
    y = draw_wrapped_line(str(date.today()), "Helvetica-Bold", 10, y, body_min_y)
    y -= 12

    idioma = data.get("idioma") or "ES"
    servicio = data.get("servicio") or ""
    subject = f"Quotation - {servicio}" if idioma == "EN" else f"Cotizacion - {servicio}"
    y = draw_wrapped_line(subject, "Helvetica-Bold", 11, y, body_min_y)
    y -= 8

    for line in (data.get("texto") or "").split("\n"):
        y = draw_wrapped_line(line, "Helvetica", 10, y, body_min_y)

    title_y = footer_y + 0.55 * inch
    name_y = title_y + 14
    signature_y = name_y + 18

    if y < footer_y + signature_block_height:
        y = new_page()

    if signature:
        c.drawImage(signature, left, signature_y, width=1.8 * inch, height=0.6 * inch, preserveAspectRatio=True, mask="auto")

    if _is_mci(data):
        c.setFont("Helvetica", 10)
        c.drawString(left, name_y, "Msc. Diana Quiros Benambourg")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, title_y, "Business Manager")
        c.drawString(left, title_y - 12, "MSL 2.0")
        c.drawString(left, title_y - 24, "MARINE CLAIMS & RISK INTELLIGENCE")
    else:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, name_y, "Diana Quiros Benambourg")
        c.setFont("Helvetica", 10)
        c.drawString(left, title_y, "Business Manager")
        c.drawString(left, title_y - 12, "MSL MARINE SURVEYORS & LOGISTICS GROUP SRL")

    c.save()
