from pathlib import Path
import sys
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend_api'))
from routers.masterdata_forms import _import_masterdata_files, _validate_upload_record

BASE = 'https://api-som-fastapi-production-e66d.up.railway.app'
session = requests.Session()
session.headers['X-Company-Code'] = 'MCI-CR'


def call(method, path, **kwargs):
    response = session.request(method, BASE + path, timeout=40, **kwargs)
    if not response.ok:
        raise RuntimeError(f'{method} {path}: {response.status_code} {response.text[:500]}')
    return response.json()


source = Path(r'C:\Users\aaron\Downloads\081026 PABEL Formulario_MasterData_Cliente TECH MARINE.xlsx')
records = _import_masterdata_files([source])
assert len(records) == 1 and records[0]['entity'] == 'cliente' and not records[0]['error']
data = records[0]['data']
assert data['CedulaJuridicaVAT'] == '10199523000162'
assert not _validate_upload_record('cliente', data)
data['FechaDePago'] = None
data['company_code'] = 'MCI-CR'
assert data['Prefijo'] == data['Telefono'] == '55.13.99753-7520'
data['Prefijo'] = '55'
rows = []
page = 1
while True:
    result = call('GET', '/clientes', params={'page': page, 'page_size': 100})
    rows.extend(result['data'])
    if len(rows) >= result['total']:
        break
    assert result['data'], 'Incomplete client listing'
    page += 1
matches = [row for row in rows if str(row.get('cedulajuridicavat')) == data['CedulaJuridicaVAT']
           or str(row.get('nombrejuridico', '')).casefold() == data['NombreJuridico'].casefold()]
assert len(matches) <= 1, 'Multiple matching clients; manual review needed'
if matches:
    code = matches[0]['codigo']
    print('Existing client, no duplicate created:', code)
else:
    last = call('GET', '/clientes/ultimo')['ultimo']
    code = f'MCI-{int(last) + 1:04d}-C'
    data['Codigo'] = code
    call('POST', '/clientes/add', json=data)
    print('Created:', code)
credit = call('GET', '/cliente-credito/' + code)
if credit.get('exists'):
    call('PUT', '/cliente-credito/' + code, json={'termino_pago': 15})
else:
    # Keep the application's default zero credit limit; only set the requested term.
    call('POST', '/cliente-credito/', json={'codigo_cliente': code, 'termino_pago': 15})
client = call('GET', '/clientes/' + code)
credit = call('GET', '/cliente-credito/' + code)
print('CLIENT_VERIFICATION', client)
assert credit['data']['termino_pago'] == 15
print('PAYMENT_TERM_VERIFIED', credit['data']['termino_pago'])
