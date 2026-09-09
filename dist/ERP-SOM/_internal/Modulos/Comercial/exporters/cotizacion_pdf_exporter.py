from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import date
import os

from branding import footer_text, is_mci_context, logo_asset, watermark_asset
from resource_utils import resource_path
from Modulos.Comercial.date_utils import to_long_english_date


def _is_mci(data: dict) -> bool:
    return is_mci_context(data)


def _pdf_logo_width(data: dict) -> float:
    return (0.72 if _is_mci(data) else 3.6) * inch


# ============================================================
# ASSETS PATH — BLINDADO TOTAL (DEV / EXE / PROGRAM FILES)
# ============================================================
def get_assets_path() -> str:
    """
    Devuelve la ruta correcta a /assets usando resource_path.
    Funciona en:
    - Desarrollo
    - PyInstaller ONEDIR
    - Instalado en Program Files
    """

    assets_path = resource_path("assets")

    if not os.path.isdir(assets_path):
        raise RuntimeError(
            f"Assets folder not found via resource_path: {assets_path}"
        )

    return assets_path


# ============================================================
# EXPORT COTIZACIÓN PDF
# ============================================================
def export_cotizacion_pdf(data: dict, output_path: str):
    """
    Genera cotización en PDF:
    - Header corporativo
    - Watermark
    - Firma
    - TOTALMENTE independiente de rutas locales
    """

    ASSETS_PATH = get_assets_path()

    c = canvas.Canvas(output_path, pagesize=LETTER)
    width, height = LETTER

    LEFT_MARGIN = 0.75 * inch
    RIGHT_MARGIN = 0.75 * inch
    BODY_WIDTH = width - LEFT_MARGIN - RIGHT_MARGIN

    mci_branding = _is_mci(data)
    HEADER_Y = height - (1.28 * inch if mci_branding else 1.9 * inch)
    TOP_MARGIN = height - (1.85 * inch if mci_branding else 2.4 * inch)

    FOOTER_Y = 0.7 * inch

    SIGNATURE_BLOCK_HEIGHT = 1.55 * inch
    BODY_MIN_Y = FOOTER_Y + 0.35 * inch

    def _wrap_text(text: str, font_name: str, font_size: int, max_width: float) -> list[str]:
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

    def _draw_footer():
        c.setFont("Helvetica", 8)
        footer = " - ".join(footer_text(data).splitlines())
        c.drawCentredString(width / 2, FOOTER_Y, footer)

    def _draw_image_aspect(path: str, x: float, y: float, target_width: float, alpha: float | None = None):
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

    def _draw_static():
        # =========================================================
        # WATERMARK
        # =========================================================
        watermark_path = watermark_asset(data) or os.path.join(ASSETS_PATH, "watermark.png")
        if os.path.isfile(watermark_path):
            wm_width = (2.6 if mci_branding else 4.5) * inch
            image = ImageReader(watermark_path)
            image_width, image_height = image.getSize()
            wm_height = wm_width * (image_height / image_width)
            wm_x = (width - wm_width) / 2
            wm_y = (height - wm_height) / 2
            _draw_image_aspect(watermark_path, wm_x, wm_y, wm_width, alpha=0.11 if mci_branding else 0.08)

        # =========================================================
        # HEADER
        # =========================================================
        header_path = logo_asset(data) or os.path.join(ASSETS_PATH, "header.png")
        if os.path.isfile(header_path):
            header_width = _pdf_logo_width(data)
            if mci_branding:
                image = ImageReader(header_path)
                image_width, image_height = image.getSize()
                header_height = header_width * (image_height / image_width)
                c.drawImage(
                    image,
                    LEFT_MARGIN,
                    height - 0.35 * inch - header_height,
                    width=header_width,
                    height=header_height,
                    mask="auto",
                )
            else:
                _draw_image_aspect(header_path, LEFT_MARGIN, HEADER_Y, header_width)

        _draw_footer()

    def _new_page():
        c.showPage()
        _draw_static()
        c.setFont("Helvetica", 10)
        return TOP_MARGIN

    def _draw_wrapped_line(text: str, font_name: str, font_size: int, y_pos: float, min_y: float) -> float:
        c.setFont(font_name, font_size)
        for wrapped_line in _wrap_text(text, font_name, font_size, BODY_WIDTH):
            if y_pos < min_y:
                y_pos = _new_page()
                c.setFont(font_name, font_size)
            c.drawString(LEFT_MARGIN, y_pos, wrapped_line)
            y_pos -= 14 if font_size <= 10 else 16
        return y_pos

    _draw_static()

    y = TOP_MARGIN

    # =========================================================
    # QUOTATION NUMBER
    # =========================================================
    quotation_number = data.get("quotation_number")
    if quotation_number:
        y = _draw_wrapped_line(quotation_number, "Helvetica-Bold", 11, y, BODY_MIN_Y)
        y -= 8

    # =========================================================
    # FECHA / LUGAR
    # =========================================================
    y = _draw_wrapped_line("Alajuela, Costa Rica", "Helvetica-Bold", 10, y, BODY_MIN_Y)
    y = _draw_wrapped_line(to_long_english_date(date.today()), "Helvetica-Bold", 10, y, BODY_MIN_Y)
    y -= 12

    # =========================================================
    # ASUNTO
    # =========================================================
    idioma = data.get("idioma", "ES")

    asunto = (
        f"Quotation – {data.get('servicio', '')}"
        if idioma == "EN"
        else f"Cotización – {data.get('servicio', '')}"
    )

    y = _draw_wrapped_line(asunto, "Helvetica-Bold", 11, y, BODY_MIN_Y)
    y -= 8

    # =========================================================
    # BODY
    # =========================================================
    for line in data.get("texto", "").split("\n"):
        y = _draw_wrapped_line(line, "Helvetica", 10, y, BODY_MIN_Y)

    # =========================================================
    # FIRMA
    # =========================================================
    signature_path = os.path.join(ASSETS_PATH, "FIRMA DIANA.png")

    SIGNATURE_IMAGE_HEIGHT = 0.6 * inch
    GAP_ABOVE_FOOTER = 0.55 * inch

    title_y = FOOTER_Y + GAP_ABOVE_FOOTER
    name_y = title_y + 14
    signature_img_y = name_y + 18

    if y < FOOTER_Y + SIGNATURE_BLOCK_HEIGHT:
        y = _new_page()

    if os.path.isfile(signature_path):
        c.drawImage(
            signature_path,
            LEFT_MARGIN,
            signature_img_y,
            width=1.8 * inch,
            height=SIGNATURE_IMAGE_HEIGHT,
            preserveAspectRatio=True,
            mask="auto"
        )

    if _is_mci(data):
        c.setFont("Helvetica", 10)
        c.drawString(LEFT_MARGIN, name_y, "Msc. Diana Quiros Benambourg")
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, title_y, "Business Manager")
        c.drawString(LEFT_MARGIN, title_y - 12, "MSL 2.0")
        c.drawString(LEFT_MARGIN, title_y - 24, "MARINE CLAIMS & RISK INTELLIGENCE")
    else:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, name_y, "Diana Quirós Benambourg")

        c.setFont("Helvetica", 10)
        c.drawString(LEFT_MARGIN, title_y, "Business Manager")
        c.drawString(
            LEFT_MARGIN,
            title_y - 12,
            "MSL MARINE SURVEYORS & LOGISTICS GROUP SRL"
        )

    c.save()
