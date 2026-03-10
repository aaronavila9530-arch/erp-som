from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import date
import os

from resource_utils import resource_path


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

    LEFT_MARGIN = 1 * inch

    HEADER_Y = height - 1.9 * inch
    TOP_MARGIN = HEADER_Y - 0.5 * inch

    FOOTER_Y = 0.7 * inch

    SIGNATURE_BLOCK_HEIGHT = 2.1 * inch
    BODY_MIN_Y = FOOTER_Y + SIGNATURE_BLOCK_HEIGHT

    # =========================================================
    # WATERMARK
    # =========================================================
    watermark_path = os.path.join(ASSETS_PATH, "watermark.png")
    if os.path.isfile(watermark_path):
        c.saveState()
        c.setFillAlpha(0.08)
        c.drawImage(
            watermark_path,
            1.2 * inch,
            2.5 * inch,
            width=4.5 * inch,
            preserveAspectRatio=True,
            mask="auto"
        )
        c.restoreState()

    # =========================================================
    # HEADER
    # =========================================================
    header_path = os.path.join(ASSETS_PATH, "header.png")
    if os.path.isfile(header_path):
        c.drawImage(
            header_path,
            LEFT_MARGIN,
            HEADER_Y,
            width=3.6 * inch,
            preserveAspectRatio=True,
            mask="auto"
        )

    y = TOP_MARGIN

    # =========================================================
    # QUOTATION NUMBER
    # =========================================================
    quotation_number = data.get("quotation_number")
    if quotation_number:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(LEFT_MARGIN, y, quotation_number)
        y -= 22

    # =========================================================
    # FECHA / LUGAR
    # =========================================================
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT_MARGIN, y, "Alajuela, Costa Rica")
    y -= 14
    c.drawString(LEFT_MARGIN, y, str(date.today()))
    y -= 26

    # =========================================================
    # ASUNTO
    # =========================================================
    idioma = data.get("idioma", "ES")

    asunto = (
        f"Quotation – {data.get('servicio', '')}"
        if idioma == "EN"
        else f"Cotización – {data.get('servicio', '')}"
    )

    c.setFont("Helvetica-Bold", 11)
    c.drawString(LEFT_MARGIN, y, asunto)
    y -= 24

    # =========================================================
    # BODY
    # =========================================================
    c.setFont("Helvetica", 10)

    for line in data.get("texto", "").split("\n"):
        if y < BODY_MIN_Y:
            c.showPage()

            # Watermark repetido
            if os.path.isfile(watermark_path):
                c.saveState()
                c.setFillAlpha(0.08)
                c.drawImage(
                    watermark_path,
                    1.2 * inch,
                    2.5 * inch,
                    width=4.5 * inch,
                    preserveAspectRatio=True,
                    mask="auto"
                )
                c.restoreState()

            # Header repetido
            if os.path.isfile(header_path):
                c.drawImage(
                    header_path,
                    LEFT_MARGIN,
                    HEADER_Y,
                    width=3.6 * inch,
                    preserveAspectRatio=True,
                    mask="auto"
                )

            y = TOP_MARGIN
            c.setFont("Helvetica", 10)

        c.drawString(LEFT_MARGIN, y, line)
        y -= 14

    # =========================================================
    # FIRMA
    # =========================================================
    signature_path = os.path.join(ASSETS_PATH, "FIRMA DIANA.png")

    SIGNATURE_IMAGE_HEIGHT = 0.6 * inch
    GAP_ABOVE_FOOTER = 0.55 * inch

    title_y = FOOTER_Y + GAP_ABOVE_FOOTER
    name_y = title_y + 14
    signature_img_y = name_y + 18

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

    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT_MARGIN, name_y, "Diana Quirós Benambourg")

    c.setFont("Helvetica", 10)
    c.drawString(LEFT_MARGIN, title_y, "Business Manager")
    c.drawString(
        LEFT_MARGIN,
        title_y - 12,
        "MSL MARINE SURVEYORS & LOGISTICS GROUP SRL"
    )

    # =========================================================
    # FOOTER
    # =========================================================
    c.setFont("Helvetica", 8)
    c.drawCentredString(
        width / 2,
        FOOTER_Y,
        "Head Office – Costa Rica, Alajuela, Plaza Aeropuerto G-14 – "
        "Phone (506) 8814-07-84 – (506) 4052-8382"
    )

    c.save()
