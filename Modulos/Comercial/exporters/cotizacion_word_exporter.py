from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from datetime import date
import os
import tempfile

from branding import footer_text, is_mci_context, logo_asset
from resource_utils import resource_path
from Modulos.Comercial.date_utils import to_long_english_date


def _is_mci(data: dict) -> bool:
    return is_mci_context(data)


def _logo_width_inches(data: dict) -> float:
    return 0.78 if _is_mci(data) else 2.5


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
# EXPORT COTIZACIÓN WORD
# ============================================================
def export_cotizacion_word(data: dict, output_path: str):
    """
    Genera cotización en formato Word (.docx)

    Data esperado:
    {
        quotation_number: str,
        cliente: str,
        servicio: str,
        idioma: 'ES' | 'EN',
        texto: str
    }
    """

    ASSETS_PATH = get_assets_path()

    doc = Document()

    # ==================================================
    # HEADER (LOGO)
    # ==================================================
    section = doc.sections[0]
    if _is_mci(data):
        section.top_margin = Inches(1.15)
        section.header_distance = Inches(0.2)

    header = section.header

    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    hr = hp.add_run()

    header_img_path = logo_asset(data) or os.path.join(ASSETS_PATH, "header.png")
    if os.path.isfile(header_img_path):
        hr.add_picture(
            header_img_path,
            width=Inches(_logo_width_inches(data))
        )
    temp_watermark = None
    if _is_mci(data):
        watermark_img = logo_asset(data) or header_img_path
        if watermark_img and os.path.isfile(watermark_img):
            temp_watermark = _add_docx_watermark(header, watermark_img)

    # ==================================================
    # BODY
    # ==================================================
    body = doc.add_paragraph()
    body.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # --------------------------------------------------
    # QUOTATION NUMBER
    # --------------------------------------------------
    quotation_number = data.get("quotation_number")
    if quotation_number:
        body.add_run(f"{quotation_number}\n").bold = True

    # --------------------------------------------------
    # FECHA / CIUDAD
    # --------------------------------------------------
    body.add_run(
        f"Alajuela, Costa Rica\n{to_long_english_date(date.today())}\n\n"
    )

    # --------------------------------------------------
    # SUBJECT / ASUNTO
    # --------------------------------------------------
    idioma = data.get("idioma", "ES")

    if idioma == "EN":
        subject = f"Quotation – {data.get('servicio', '')}"
        body.add_run(f"Subject: {subject}\n\n").bold = True
    else:
        subject = f"Cotización – {data.get('servicio', '')}"
        body.add_run(f"Asunto: {subject}\n\n").bold = True

    # --------------------------------------------------
    # TEXTO PRINCIPAL
    # --------------------------------------------------
    body.add_run(data.get("texto", ""))

    # ==================================================
    # SIGNATURE
    # ==================================================
    doc.add_paragraph("\n")

    sig = doc.add_paragraph()
    sig.alignment = WD_ALIGN_PARAGRAPH.LEFT

    if idioma == "EN":
        sig.add_run("Sincerely,\n\n")
    else:
        sig.add_run("Atentamente,\n\n")

    signature_path = os.path.join(ASSETS_PATH, "FIRMA DIANA.png")
    if os.path.isfile(signature_path):
        sig.add_run().add_picture(
            signature_path,
            width=Inches(1.8)
        )

    if _is_mci(data):
        sig.add_run("\nMsc. Diana Quiros Benambourg\n")
        sig.add_run("Business Manager\n").bold = True
        sig.add_run("MSL 2.0\n").bold = True
        sig.add_run("MARINE CLAIMS & RISK INTELLIGENCE").bold = True
    else:
        sig.add_run("\nDiana Quirós Benambourg\n")
        sig.add_run("Business Manager\n")
        sig.add_run("Marine Surveyors & Logistics Group SRL")

    # ==================================================
    # FOOTER
    # ==================================================
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.text = footer_text(data)

    # ==================================================
    # SAVE
    # ==================================================
    doc.save(output_path)
    if temp_watermark:
        try:
            os.unlink(temp_watermark)
        except Exception:
            pass
