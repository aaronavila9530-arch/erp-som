from pathlib import Path
import sys
import json
from urllib.request import Request, urlopen
import pypdfium2
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend_api'))
from services.pdf import factura_manual_pdf

request = Request(
    'https://api-som-fastapi-production-e66d.up.railway.app/billing/2209',
    headers={'X-Company-Code': 'MSL-CR'},
)
with urlopen(request, timeout=30) as response:
    row = json.load(response)
assert row['company_code'] == 'MSL-CR'
assert row['nombre_cliente'] == 'NORDEN'
assert row['numero_documento'] == '2209'
assert row['moneda'] == 'USD' and float(row['total']) == 25000
output = ROOT / 'output' / 'pdf'
output.mkdir(parents=True, exist_ok=True)
factura_manual_pdf.BASE_DIR = str(output)
payload = {
    'numero_documento': row['numero_documento'],
    'fecha_emision': row['fecha_emision'],
    'cliente': row['nombre_cliente'],
    'place': row.get('place') or row.get('lugar'),
    'buque': row['buque_contenedor'],
    'operacion': row['operacion'],
    'survey': row['operacion'],
    'num_informe': row['num_informe'],
    'periodo': row['periodo_operacion'],
    'descripcion': row['descripcion_servicio'],
    'moneda': row['moneda'],
    'termino_pago': 0,
    'payment_terms': 0,
    'total': row['total'],
}
path = Path(factura_manual_pdf.generar_factura_manual_pdf(payload))
document = pypdfium2.PdfDocument(str(path))
text = '\n'.join(page.extract_text() for page in PdfReader(path).pages)
assert 'CREDIT 0 DAYS' in text and 'CREDIT 30 DAYS' not in text
assert '25,000.00' in text and '2209' in text and 'NORDEN' in text
for i, page in enumerate(document):
    page.render(scale=1.5).to_pil().save(str(ROOT / 'tmp' / f'invoice_2209_check_{i+1}.png'))
print(path)
print(text)
