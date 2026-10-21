import hashlib
import os
from pathlib import Path
import subprocess
import requests

root = Path(__file__).resolve().parents[1]
api = 'https://api.github.com/repos/aaronavila9530-arch/erp-som'
result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                        text=True, capture_output=True, check=True, cwd=root,
                        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
credentials = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
session = requests.Session()
session.headers.update({'Authorization': 'Bearer ' + credentials['password'], 'Accept': 'application/vnd.github+json'})

def call(method, url, **kwargs):
    response = session.request(method, url, timeout=300, **kwargs)
    response.raise_for_status()
    return response.json()

tag = 'v1.7.45'
asset = root / 'installer/ERP-SOM-Setup-1.7.45.exe'
digest = hashlib.sha256(asset.read_bytes()).hexdigest()
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
releases = call('GET', api + '/releases', params={'per_page': 10})
release = next((r for r in releases if r['tag_name'] == tag), None)
if not release:
    release = call('POST', api + '/releases', json={
        'tag_name': tag, 'target_commitish': sha, 'name': 'ERP-SOM 1.7.45', 'draft': True,
        'body': 'Correcciones de HHRR y Comercial:\n\n'
                '- Pizarra carga los servicios al abrirse y muestra la empresa y el resultado de los filtros.\n'
                '- Conserva la separacion de servicios por empresa y los permisos existentes.\n'
                '- Solicitudes HHRR muestran el detalle del error del servidor.\n'
                '- Correccion de servidor asociada: lectura de claves PEM y aislamiento de fallos de notificaciones push para no cancelar solicitudes.\n\n'
                'SHA-256 del instalador: `' + digest + '`'})
assert release['draft'], 'Already published; do not replace'
existing = next((a for a in release['assets'] if a['name'] == asset.name), None)
if not existing:
    with asset.open('rb') as stream:
        existing = call('POST', release['upload_url'].split('{')[0], params={'name': asset.name},
                        headers={'Content-Type': 'application/octet-stream'}, data=stream)
assert existing['size'] == asset.stat().st_size
assert existing.get('digest') == 'sha256:' + digest
published = call('PATCH', release['url'], json={'draft': False, 'make_latest': 'true'})
assert call('GET', api + '/releases/latest')['tag_name'] == tag
print(published['html_url'])
print(existing['browser_download_url'])
print('SHA256', digest)
