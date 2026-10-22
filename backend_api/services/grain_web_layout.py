"""Layout corrections on generated Web copies, never on desktop templates."""
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from services.draft_survey_report_formatting import normalize_draft_layout


def normalize(path, presentation=False, customer=""):
    doc = Document(path)
    normalize_draft_layout(doc, presentation=presentation)
    if not presentation:
        # The sampling diagram is a grouped drawing, not a picture; reserve
        # its full height so the following paragraphs cannot run behind it.
        for anchor in list(doc._element.xpath('.//wp:anchor')):
            inline = OxmlElement('wp:inline')
            for tag in ('wp:extent','wp:effectExtent','wp:docPr','wp:cNvGraphicFramePr','a:graphic'):
                child = anchor.find(qn(tag))
                if child is not None:
                    inline.append(child)
            anchor.getparent().replace(anchor, inline)
    if presentation:
        # The legacy website textbox shares the certificate paragraph anchor.
        # Move only its generated text into the footer, retaining all artwork.
        for paragraph in doc.paragraphs:
            for run in paragraph.runs:
                if run.text.strip().startswith('www.mslogisticsgroup.'):
                    run.text = ''
            if 'CERT N' in paragraph.text:
                paragraph.paragraph_format.right_indent = Pt(70)
                paragraph.paragraph_format.left_indent = Pt(0)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(14)
        footer = doc.sections[-1].footer.add_paragraph('www.mslogisticsgroup.com')
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.paragraph_format.space_before = footer.paragraph_format.space_after = Pt(0)
        for run in footer.runs:
            run.font.size = Pt(10)
    for section in doc.sections:
        number = section._sectPr.find(qn('w:pgNumType'))
        if number is not None:
            number.attrib.pop(qn('w:start'), None)
    for paragraph in doc.paragraphs:
        pf = paragraph.paragraph_format
        if pf.right_indent is not None and pf.right_indent < 0:
            pf.right_indent = Pt(0)
        if presentation and (paragraph.text.strip().startswith('PUERTO') or (customer and paragraph.text.strip() == customer.strip())):
            # Leave room for the original right-side photographs.
            pf.right_indent = Pt(70)
            for run in paragraph.runs:
                if run.font.size and run.font.size > Pt(18):
                    run.font.size = Pt(18)
    doc.save(path)
