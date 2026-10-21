import hashlib
import os
from pathlib import Path
import subprocess
import requests

root = Path(__file__).resolve().parents[1]
source = root.parent / 'draft-release-1.7.46'
api = 'https://api.github.com/repos/aaronavila9530-arch/erp-som'
tag = 'v1.7.46'
asset = source / 'installer/ERP-SOM-Setup-1.7.46.exe'
assert asset.is_file()
digest = hashlib.sha256(asset.read_bytes()).hexdigest()
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
assert sha.startswith('9d505d9e'), 'Release must target the tested fix'
result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                        text=True, capture_output=True, check=True, cwd=root,
                        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
credentials = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
session = requests.Session()
session.headers.update({'Authorization': 'Bearer ' + credentials['password'], 'Accept': 'application/vnd.github+json'})

def call(method, url, **kwargs):
    response = session.request(method, url, timeout=600, **kwargs)
    response.raise_for_status()
    return response.json()

releases = call('GET', api + '/releases', params={'per_page': 10})
release = next((r for r in releases if r['tag_name'] == tag), None)
if not release:
    release = call('POST', api + '/releases', json={
        'tag_name': tag, 'target_commitish': sha, 'name': 'ERP-SOM 1.7.46', 'draft': True,
        'body': 'Correccion de Draft Survey en SOM Escritorio:\n\n'
                '- Word report: diferencia = Draft Survey Figures - B/L Figures.\n'
                '- Porcentaje con el mismo signo, respecto a B/L.\n'
                '- Ejemplo verificado: 51,444.60 - 51,442.00 = 2.60 MT (0.0051%).\n'
                '- Sin cambios en calculos hidrostaticos ni en Shore Scale.\n'
                '- Para informes guardados anteriormente: abrir, guardar y generar el reporte nuevamente.\n\n'
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
