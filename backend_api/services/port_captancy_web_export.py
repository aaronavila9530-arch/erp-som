"""Fill original MSL templates in request-local files, never alter desktop sources."""
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
import tempfile
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from services.port_captancy_web_fields import SPEC
from services.port_captancy_presentation_service import PortCaptancyPresentationService
from services.draft_survey_report_formatting import replace_placeholders
from services.template_autofit import apply_docx_autofit
from services.container_web_export import convert

TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'
MONTHS = ('January','February','March','April','May','June','July','August','September','October','November','December')

def date_text(value):
    if not value:
        return ''
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        for fmt in ('%Y-%m-%d', '%B %d, %Y', '%d/%m/%Y'):
            try:
                value = datetime.strptime(str(value), fmt).date()
                break
            except ValueError:
                pass
    return f'{MONTHS[value.month-1]} {value.day:02d}, {value.year}' if isinstance(value, date) else str(value)

def word(data, target, presentation=False):
    if data.get('company_code') != 'MSL-CR':
        raise ValueError('Original Port Captancy template requires MSL context')
    name = PortCaptancyPresentationService()._select_template(data) if presentation else 'port_captancy_template.docx'
    doc = Document(TEMPLATES/name)
    values = {k: date_text(data.get(k)) if f['type']=='date' else str(data.get(k) or '') for k,f in SPEC['fields'].items()}
    replacements = {}
    for k,v in values.items():
        replacements['{{'+k+'}}'] = v
        replacements['{'+k+'}'] = v
    def fill(container):
        for p in list(container.paragraphs):
            blank = [k for k,v in values.items() if not v and k.startswith(('operation_summary_','remarks_','conclusion_'))]
            if any('{'+k+'}' in p.text for k in blank):
                p._p.getparent().remove(p._p)
            else:
                replace_placeholders(p, replacements)
        for table in container.tables:
            for row in table.rows:
                for cell in row.cells:
                    fill(cell)
    fill(doc)
    for section in doc.sections:
        for part in (section.header, section.footer):
            fill(part)
    apply_docx_autofit(doc)
    if not presentation:
        for section in doc.sections:
            for p in section.header.paragraphs:
                if 'CERT' not in p.text:
                    continue
                for run in p.runs:
                    if not run._r.xpath('.//w:drawing|.//w:pict'):
                        run.text=''
                p.add_run('CERT No. '+values['report_number']).font.size=Pt(8)
                p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
                pf=p.paragraph_format
                pf.left_indent=pf.right_indent=pf.first_line_indent=Pt(0)
                pf.tab_stops.clear_all()
        for p in doc.paragraphs:
            if p.text.strip() in ('INTRODUCTIONS','THE VESSEL','EXTRACT TIME SHEET','OPERATION SUMMARY','REMARKS','CONCLUSION','ENCLOSURE'):
                p.paragraph_format.keep_with_next=True
    else:
        # Keep variable cover text left of the original right-hand photo strip.
        for p in doc.paragraphs:
            if p.text.strip().startswith('PUERTO') or p.text.strip() in (values['vessel'],values['requested_by'],'TO: '+values['requested_by']):
                p.paragraph_format.right_indent=Pt(75)
                for run in p.runs:
                    if run.font.size and run.font.size>Pt(16):run.font.size=Pt(16)
    # Explicit references avoid converter-specific first-page-only headers.
    for section in doc.sections:
        for tag in ('headerReference','footerReference'):
            default=next((r for r in section._sectPr.findall(qn('w:'+tag)) if r.get(qn('w:type'))=='default'),None)
            if default is None:continue
            for typ in ('first','even'):
                for old in list(section._sectPr.findall(qn('w:'+tag))):
                    if old.get(qn('w:type'))==typ:section._sectPr.remove(old)
                ref=OxmlElement('w:'+tag);ref.set(qn('w:type'),typ);ref.set(qn('r:id'),default.get(qn('r:id')))
                default.addnext(ref)
    doc.save(target)

def build(data, format):
    with tempfile.TemporaryDirectory(prefix='som_port_captancy_') as folder:
        folder=Path(folder)
        if format in ('presentation','complete'):
            cover=folder/'presentation.docx';word(data,cover,True)
            cover_pdf=convert(cover,folder)
            if format=='presentation':return cover_pdf.read_bytes()
        report=folder/'report.docx';word(data,report)
        if format=='word':return report.read_bytes()
        report_pdf=convert(report,folder)
        if format=='pdf':return report_pdf.read_bytes()
        if format!='complete':raise ValueError('Unsupported format')
        from pypdf import PdfWriter
        with PdfWriter() as writer:
            writer.append(cover_pdf);writer.append(report_pdf)
            output=BytesIO();writer.write(output);return output.getvalue()
