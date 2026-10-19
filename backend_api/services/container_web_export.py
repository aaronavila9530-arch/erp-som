"""Web exports reuse desktop templates, with isolated conversion and cleanup."""
from datetime import datetime
from copy import copy
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


def restore_template_layout(source):
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment
    from services.container_report_excel_service import TEMPLATE_PATH
    book, template = load_workbook(source), load_workbook(TEMPLATE_PATH)
    sheet, original = book.active, template.active
    # The shared autofitter materializes missing column widths as 13 even though
    # this fixed-format template defaults to 4. Restore only this web copy.
    sheet.column_dimensions.clear()
    for key, dimension in original.column_dimensions.items():
        sheet.column_dimensions[key] = copy(dimension)
    for row in original:
        for cell in row:
            target = sheet[cell.coordinate]
            if target.__class__.__name__ != 'MergedCell':
                target.alignment = copy(cell.alignment)
                target.font = copy(cell.font)
    for key, dimension in original.row_dimensions.items():
        sheet.row_dimensions[key].height = dimension.height
    # The desktop mapping writes appointment immediately before its merged box.
    sheet['D8'] = sheet['C8'].value
    sheet['C8'] = None
    sheet['D8'].alignment = Alignment(wrap_text=True, vertical='top')
    sheet.merge_cells('AD3:AJ3')
    sheet['AD3'].alignment = Alignment(horizontal='center')
    link = sheet['B42'].hyperlink
    value = sheet['B42'].value
    sheet['B42'] = None
    sheet.merge_cells('A42:AJ42')
    sheet['A42'] = value
    if link:
        sheet['A42'].hyperlink = link.target
    sheet['A42'].alignment = Alignment(wrap_text=True, vertical='top')
    # Scope text belongs in the answer box, not the one-column checkmark cell.
    sheet['AF53'] = sheet['AB53'].value
    sheet['AB53'] = None
    for region in ('AF53:AH53', 'D9:H9'):
        sheet.unmerge_cells(region)
    sheet.merge_cells('AF53:AJ53')
    sheet.merge_cells('D9:R9')
    _fit_web_values(sheet, original)
    sheet.print_area = 'A1:AJ60'
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    book.save(source)
    book.close()
    template.close()


def _fit_web_values(sheet, original):
    from openpyxl.styles import Alignment
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.lib.utils import simpleSplit
    from openpyxl.utils import get_column_letter
    for row in sheet:
        for cell in row:
            if cell.__class__.__name__ == 'MergedCell' or cell.value in (None, '', '\u2714'):
                continue
            if cell.value == original[cell.coordinate].value:
                continue
            region = next((r for r in sheet.merged_cells.ranges if cell.coordinate in r), None)
            c1, c2 = (region.min_col, region.max_col) if region else (cell.column, cell.column)
            r1, r2 = (region.min_row, region.max_row) if region else (cell.row, cell.row)
            width = 0
            for col in range(c1, c2 + 1):
                dim = sheet.column_dimensions.get(get_column_letter(col))
                width += ((dim.width if dim else sheet.sheet_format.defaultColWidth or 4) * 7 + 5) * .75
            width = max(12, width - 8)
            size = float(cell.font.sz or 10)
            font = 'Helvetica-Bold' if cell.font.bold else 'Helvetica'
            value = cell.value.strftime('%d-%m-%Y %H:%M') if isinstance(cell.value, datetime) else str(cell.value)
            lines = simpleSplit(value, font, size, width)
            # Account for URLs and other tokens without word boundaries.
            count = sum(max(1, int(stringWidth(line, font, size) / width + .999)) for line in lines)
            needed = max(1, count) * size * 1.3 + 6
            available = sum(sheet.row_dimensions[r].height or sheet.sheet_format.defaultRowHeight for r in range(r1, r2 + 1))
            if needed > available:
                sheet.row_dimensions[r2].height = (sheet.row_dimensions[r2].height or sheet.sheet_format.defaultRowHeight) + needed - available
            cell.alignment = Alignment(horizontal='left', vertical='top', wrap_text=True)


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
            restore_template_layout(source)
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
