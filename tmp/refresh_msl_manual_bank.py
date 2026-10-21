"""Regenerate the user's MSL manual PDFs, preserving invoice business fields."""
import json
import hashlib
import zipfile
from io import BytesIO
from pathlib import Path

import requests
from pypdf import PdfReader

BASE = 'https://api-som-fastapi-production-e66d.up.railway.app'
OUT = Path('output/pdf/MSL_manual_BCR_layout_2026-10-12')
session = requests.Session()
session.headers['X-Company-Code'] = 'MSL-CR'


def get(path, **params):
    response = session.get(BASE + path, params=params, timeout=90)
    response.raise_for_status()
    return response


def main():
    version = get('/som/web-version').json()['asset_version']
    if version != '20261012-manual-bank-layout-v6':
        raise RuntimeError('Deployment not ready: ' + version)
    listing = get('/billing/search', company_code='MSL-CR', tipo_factura='MANUAL',
                  tipo_documento='FACTURA', page_size=10000).json()
    rows = listing['data']
    if len(rows) != listing['total'] or not rows:
        raise RuntimeError('Incomplete invoice inventory')
    OUT.mkdir(parents=True, exist_ok=True)
    snapshots = []
    # Back up all business fields before regenerating any PDF.
    for row in rows:
        before = get('/billing/' + row['numero_documento'], invoice_id=row['id']).json()
        assert before['id'] == row['id'] and before['company_code'] == 'MSL-CR'
        assert before['tipo_factura'] == 'MANUAL' and before['tipo_documento'] == 'FACTURA'
        snapshots.append(before)
    (OUT / 'before.json').write_text(json.dumps(snapshots, indent=2, ensure_ascii=False), encoding='utf-8')
    manifest = []
    for before in snapshots:
        number, identity = before['numero_documento'], before['id']
        content = get('/billing/pdf/' + number, invoice_id=identity).content
        reader = PdfReader(BytesIO(content))
        text = ' '.join(' '.join(p.extract_text() for p in reader.pages).split())
        for required in ['Banco de Costa Rica', 'MSL MARINE SURVEYORS AND LOGISTICS SOCIEDAD DE RESPONSABILIDAD LIMITADA',
                         'CR90015202001393623379', 'Avenida Central y Segunda, calles 4 y 6 San José, Costa Rica',
                         'BCRICRSJ.', '019339.']:
            assert required in text, (identity, required)
        assert 'CR49015201308000025850' not in text
        assert '308258-5' not in text
        assert str(number) in text
        after = get('/billing/' + number, invoice_id=identity).json()
        assert {k:v for k,v in before.items() if k != 'pdf_path'} == {k:v for k,v in after.items() if k != 'pdf_path'}, identity
        name = f"MSL_{identity}_Factura_{number}.pdf"
        (OUT / name).write_bytes(content)
        manifest.append(dict(id=identity, numero=number, cliente=before['nombre_cliente'],
                             total=before['total'], termino_pago=before.get('termino_pago'),
                             file=name, pages=len(reader.pages), sha256=hashlib.sha256(content).hexdigest()))
        print(json.dumps(manifest[-1], ensure_ascii=True), flush=True)
    (OUT / 'verification.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    archive = OUT.parent / 'MSL_facturas_manuales_BCR_corregidas_2026-10-12.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for row in manifest:
            bundle.write(OUT / row['file'], row['file'])
        bundle.write(OUT / 'verification.json', 'verification.json')
    print(json.dumps({'verified': len(manifest), 'archive': str(archive.resolve())}), flush=True)


if __name__ == '__main__':
    main()
