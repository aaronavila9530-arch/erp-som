import hashlib
import os
from pathlib import Path
import subprocess
import requests

root = Path(__file__).resolve().parents[1]
asset = root.parent / 'som-release-1.7.47/installer/ERP-SOM-Setup-1.7.47.exe'
api = 'https://api.github.com/repos/aaronavila9530-arch/erp-som'
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
assert sha.startswith('d758aaa9'), 'Release source changed; revalidate build first'
assert asset.is_file()
digest = hashlib.sha256(asset.read_bytes()).hexdigest()
credential = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
    capture_output=True, text=True, check=True, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
fields = dict(line.split('=', 1) for line in credential.stdout.splitlines() if '=' in line)
session = requests.Session()
session.headers.update({'Authorization': 'Bearer ' + fields['password'], 'Accept': 'application/vnd.github+json'})
def call(method, url, **kwargs):
    result = session.request(method, url, timeout=600, **kwargs)
    result.raise_for_status()
    return result.json()
releases = call('GET', api + '/releases', params={'per_page': 10})
release = next((r for r in releases if r['tag_name'] == 'v1.7.47'), None)
if release is None:
    release = call('POST', api + '/releases', json={
        'tag_name': 'v1.7.47', 'target_commitish': sha, 'name': 'ERP-SOM 1.7.47', 'draft': True,
        'body': 'Servicios en SOM Escritorio:\n\n'
        '- Consulta de credito y guardado en segundo plano para mantener la ventana responsive.\n'
        '- Bloqueo del doble guardado mientras se procesa la solicitud.\n'
        '- Recarga de la lista en segundo plano.\n'
        '- Ante una respuesta incierta, comprobar si el servicio existe antes de reintentar.\n\n'
        'Esta actualizacion requiere instalarse en cada equipo. La correccion del pool del backend se despliega por separado.\n\n'
        'SHA-256: `' + digest + '`'})
assert release['draft'], 'Do not replace a published release'
existing = next((a for a in release['assets'] if a['name'] == asset.name), None)
if existing is None:
    with asset.open('rb') as stream:
        existing = call('POST', release['upload_url'].split('{')[0], params={'name': asset.name},
                        headers={'Content-Type': 'application/octet-stream'}, data=stream)
assert existing['size'] == asset.stat().st_size
assert existing.get('digest') == 'sha256:' + digest
published = call('PATCH', release['url'], json={'draft': False, 'make_latest': 'true'})
assert call('GET', api + '/releases/latest')['tag_name'] == 'v1.7.47'
print(published['html_url'])
print('SHA256', digest)
