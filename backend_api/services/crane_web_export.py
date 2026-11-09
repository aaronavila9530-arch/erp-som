"""Request-local Crane exports using the unmodified MSL desktop templates."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import re
import tempfile

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.text.paragraph import Paragraph
from services.crane_web_fields import SPEC, POINTS, SUFFIXES
from services.draft_survey_report_formatting import replace_placeholders
from services.port_captancy_web_export import date_text
from services.container_web_export import convert
from services.template_autofit import apply_docx_autofit

TEMPLATES=Path(__file__).resolve().parents[1]/'templates'


def set_paragraph_text(p,text):
    if p.runs:
        p.runs[0].text=text
        for run in p.runs[1:]:run.text=''
    else:p.add_run(text)


def word(data,target,presentation=False):
    if data.get('company_code')!='MSL-CR':
        raise ValueError('Original Crane template requires MSL context')
    doc=Document(TEMPLATES/('presentation_crane_inspection.docx' if presentation else 'crane_inspection_template.docx'))
    values={k:date_text(data.get(k)) if f['type']=='date' else str(data.get(k) or '') for k,f in SPEC['fields'].items()}
    replacements={'{'+k+'}':v for k,v in values.items()}
    replacements.update({'{{'+k+'}}':v for k,v in values.items()})
    # The original has an omitted fourth status and two copy/paste field errors.
    # Correct only the in-memory output; the desktop templates remain untouched.
    seen_remark7=False
    for p in doc.paragraphs:
        original=p.text
        if '{crane3_remark_7}' in original:
            if seen_remark7:replace_placeholders(p,{'{crane3_remark_7}':'{crane3_remark_9}'})
            seen_remark7=True
        point=next((key for key in POINTS if '{'+key+'_status}' in original),None)
        if point:
            statuses=[values[point+'_'+suffix] for suffix in SUFFIXES if values[point+'_'+suffix]]
            if statuses or data.get(point+'_done'):
                text=POINTS[point]+': '+(', '.join(statuses) if statuses else 'Inspection performed; status not specified')+'.'
                set_paragraph_text(p,text)
            else:p._p.getparent().remove(p._p)
        elif original.startswith('On {intro_inspection_date}') and data.get('intro_text'):
            set_paragraph_text(p,str(data['intro_text']))

    def fill(part):
        # Includes text boxes and nested tables without flattening their drawings.
        for element in list(part._element.xpath('.//w:p')):
            p=Paragraph(element,part)
            keys=re.findall(r'\{([a-z0-9_]+)\}',p.text)
            if keys and all(k.startswith(('crane1_remark_','crane2_remark_','crane3_remark_',
                    'crane4_remark_','recommendation_','grabs_condition_','conclusion_','gear_'))
                    and not values.get(k) for k in keys):
                if not element.xpath('.//w:drawing|.//w:pict'):
                    element.getparent().remove(element)
                    continue
            replace_placeholders(p,replacements)
    fill(doc)
    seen=set()
    for section in doc.sections:
        for part in (section.header,section.footer,section.first_page_header,section.first_page_footer,
                     section.even_page_header,section.even_page_footer):
            if part.part.partname not in seen:
                fill(part);seen.add(part.part.partname)
    apply_docx_autofit(doc)
    doc.settings.odd_and_even_pages_header_footer=False
    for section in doc.sections:section.different_first_page_header_footer=False
    for p in doc.paragraphs:
        if p.text.strip() in ('CRANES GEAR SURVEY','Crane Inspection','REMARKS BY CRANE','RECOMENDATIONS',
                             'GRABS CONDITION SURVEY','CONCLUSION','ENCLOSURE') or p.text.strip().startswith('CRANE #'):
            p.paragraph_format.keep_with_next=True
    if not presentation:
        paragraphs=doc.paragraphs
        signature=next((i for i,p in enumerate(paragraphs) if p.text.strip().startswith('Surveyor.')),None)
        if signature is not None:
            start=signature
            while start and not paragraphs[start-1].text.strip():start-=1
            for p in paragraphs[start:]:
                p.paragraph_format.keep_with_next=True
            paragraphs[-1].paragraph_format.keep_with_next=False
        for section in doc.sections:
            for p in section.footer.paragraphs:
                if not p._p.xpath('.//w:instrText[contains(text(),"PAGE")]'):continue
                # Long identities may wrap, but the page counter must remain intact.
                for run in list(p.runs):run._r.getparent().remove(run._r)
                p.paragraph_format.left_indent=p.paragraph_format.right_indent=Pt(0)
                p.paragraph_format.first_line_indent=Pt(0)
                p.paragraph_format.tab_stops.clear_all()
                p.alignment=WD_ALIGN_PARAGRAPH.LEFT
                p.add_run(f"{values['report_number']}  {values['vessel']} CRANE INSPECTION - {values['port']} - {values['country']}\nPage ")
                for code,tail in (('PAGE',' of '),('NUMPAGES','')):
                    field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),' '+code+' ')
                    p._p.append(field)
                    if tail:p.add_run(tail)
                for run in p.runs:run.font.size=Pt(8)
    else:
        for p in doc.paragraphs:
            text=p.text.strip()
            if text.startswith('PUERTO') or text==values['vessel'] or text.startswith('TO:'):
                p.paragraph_format.right_indent=Pt(95)
                for run in p.runs:
                    if run.font.size and run.font.size>Pt(16):run.font.size=Pt(16)
    # Use the original default artwork consistently on every page.
    for section in doc.sections:
        for tag in ('headerReference','footerReference'):
            refs=list(section._sectPr.findall(qn('w:'+tag)))
            default=next((r for r in refs if r.get(qn('w:type'))=='default'),None)
            if default is None:continue
            for old in refs:
                if old.get(qn('w:type')) in ('first','even'):section._sectPr.remove(old)
            for typ in ('first','even'):
                ref=deepcopy(default);ref.set(qn('w:type'),typ);default.addnext(ref)
    setting=OxmlElement('w:updateFields');setting.set(qn('w:val'),'true');doc.settings.element.append(setting)
    doc.save(target)


def build(data,format):
    if format not in ('word','pdf','presentation','complete'):raise ValueError('Unsupported format')
    with tempfile.TemporaryDirectory(prefix='som_crane_') as tmp:
        folder=Path(tmp)
        if format in ('presentation','complete'):
            cover=folder/'presentation.docx';word(data,cover,True)
            cover_pdf=convert(cover,folder)
            if format=='presentation':return cover_pdf.read_bytes()
        report=folder/'report.docx';word(data,report)
        if format=='word':return report.read_bytes()
        report_pdf=convert(report,folder)
        if format=='pdf':return report_pdf.read_bytes()
        from pypdf import PdfWriter
        with PdfWriter() as writer:
            writer.append(cover_pdf);writer.append(report_pdf)
            out=BytesIO();writer.write(out);return out.getvalue()
