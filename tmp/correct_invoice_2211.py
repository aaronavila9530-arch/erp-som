from io import BytesIO
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import TextStringObject
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
import pypdfium2 as pdfium

source = Path('C:/Users/aaron/AppData/Local/Temp/MSL_107_Factura_2211.pdf')
output = Path('output/pdf/MSL_107_Factura_2211_corregida.pdf')
reader = PdfReader(source)
writer = PdfWriter(clone_from=reader)
page = writer.pages[0]
content = page.get_contents()
removed = []
for operands, operator in content.operations:
    if operator == b'Tj' and 'ENSENADA' in str(operands[0]):
        removed.append(str(operands[0]))
        operands[0] = TextStringObject('')
assert len(removed) == 1, removed
page.replace_contents(content)
description = 'MV NORD DELTA ENSENADA, M\u00c9XICO \u2013 ON HIRE BUNKER & CONDITION SURVEY 2 PARTIES \u2013 BUNKER'
lines = []
line = ''
for word in description.split():
    candidate = (line + ' ' + word).strip()
    if stringWidth(candidate, 'Times-Roman', 11) > 485:
        lines.append(line)
        line = word
    else:
        line = candidate
lines.append(line)
assert len(lines) == 2
overlay = BytesIO()
c = canvas.Canvas(overlay, pagesize=(float(page.mediabox.width), float(page.mediabox.height)))
c.setFont('Times-Roman', 11)
for i, line in enumerate(lines):
    c.drawString(55.27559, 499.748 - 14 * i, line)
c.save()
page.merge_page(PdfReader(overlay).pages[0])
output.parent.mkdir(parents=True, exist_ok=True)
with output.open('wb') as f:
    writer.write(f)
text = PdfReader(output).pages[0].extract_text()
assert description in ' '.join(text.split())
original_text = PdfReader(source).pages[0].extract_text()
expected = '\n'.join(line for line in original_text.splitlines() if 'ENSENADA' not in line)
actual = text
for line in lines:
    actual = actual.replace(line, '')
assert ' '.join(expected.split()) == ' '.join(actual.split())
doc = pdfium.PdfDocument(str(output))
doc[0].render(scale=1.5).to_pil().save('tmp/pdfs/2211-corrected.png')
print(output.resolve())
print('Verified: description corrected; all other extracted text unchanged.')
