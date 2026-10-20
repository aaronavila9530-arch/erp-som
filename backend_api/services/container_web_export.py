"""Web exports reuse desktop templates, with isolated conversion and cleanup."""
from datetime import datetime
from io import BytesIO
from pathlib import Path
import shutil
import subprocess
import tempfile


def convert(source, folder):
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise RuntimeError("LibreOffice unavailable")
    profile = folder / (source.stem + "-profile")
    subprocess.run([binary, "-env:UserInstallation=" + profile.as_uri(), "--headless", "--nologo",
                    "--convert-to", "pdf", "--outdir", str(folder), str(source)],
                   check=True, timeout=75, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    result = folder / (source.stem + ".pdf")
    if not result.is_file():
        raise RuntimeError("PDF conversion produced no file")
    return result


def presentation(report, customer, folder):
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.utils import ImageReader
    from branding import logo_asset
    raw = report.get("init_inspection_datetime")
    try:
        date = (raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw))).strftime("%d-%m-%Y")
    except (ValueError, TypeError):
        date = str(raw or "")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=25, leading=31, textColor=colors.HexColor('#173f50'), spaceAfter=18))
    styles.add(ParagraphStyle('CoverValue', fontName='Helvetica', fontSize=12, leading=18))
    def paragraph(value):
        return Paragraph(escape(str(value or '-')).replace('\n','<br/>'), styles['CoverValue'])
    story = []
    logo = logo_asset(report)
    if logo:
        width, height = ImageReader(logo).getSize()
        image = Image(str(logo), width=130, height=130*height/width)
        image.hAlign = 'LEFT'
        story.extend([image, Spacer(1,36)])
    story.extend([Paragraph('CONTAINER INSPECTION<br/>REPORT', styles['CoverTitle']),
                  paragraph(report.get('company_code')), Spacer(1,30)])
    rows = [[paragraph(label), paragraph(value)] for label,value in (
        ('Report No.',report.get('linked_report_number')),('Reference',report.get('report_no')),
        ('Vessel',report.get('vessel')),('To',customer),('On behalf of',report.get('on_behalf_of')),
        ('Inspection place',report.get('inspection_place')),('Inspection date',date),('Status',report.get('status')))]
    table = Table(rows,colWidths=[125,350],hAlign='LEFT')
    table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),12),('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#d5e0e4'))]))
    story.append(table)
    result = folder / 'presentation.pdf'
    SimpleDocTemplate(str(result),pagesize=A4,leftMargin=60,rightMargin=60,topMargin=50,bottomMargin=45).build(story)
    return result


def build(report, customer, kind):
    from services.container_report_excel_service import generate_container_report_excel
    # Treat user-entered narrative as text, never as an executable Excel formula.
    safe = {key: "'" + value if isinstance(value, str) and value.startswith("=") else value
            for key, value in report.items()}
    with tempfile.TemporaryDirectory(prefix="som_container_web_") as directory:
        folder = Path(directory)
        report_pdf = None
        if kind in ("excel", "pdf", "unified"):
            generated = Path(generate_container_report_excel(safe))
            try:
                source = folder / "report.xlsx"
                shutil.copyfile(generated, source)
            finally:
                generated.unlink(missing_ok=True)
            if kind == "excel":
                return source.read_bytes()
            report_pdf = convert(source, folder)
            if kind == "pdf":
                return report_pdf.read_bytes()
        cover = presentation(report, customer, folder)
        if kind == "presentation":
            return cover.read_bytes()
        from pypdf import PdfWriter
        output = BytesIO()
        with PdfWriter() as writer:
            writer.append(str(cover))
            writer.append(str(report_pdf))
            writer.write(output)
        return output.getvalue()
