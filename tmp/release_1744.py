import hashlib
import os
from pathlib import Path
import subprocess
import sys
import requests

ROOT = Path(__file__).resolve().parents[1]
REPO = 'aaronavila9530-arch/erp-som'
API = 'https://api.github.com/repos/' + REPO
result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
                        text=True, capture_output=True, check=True, cwd=ROOT,
                        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
credential = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
session = requests.Session()
session.headers.update({'Authorization': 'Bearer ' + credential['password'],
                        'Accept': 'application/vnd.github+json'})


def call(method, url, **kwargs):
    response = session.request(method, url, timeout=300, **kwargs)
    if not response.ok:
        raise RuntimeError(f'GitHub request failed: {response.status_code} {response.text[:250]}')
    return response.json()


releases = call('GET', API + '/releases', params={'per_page': 10})
if len(sys.argv) < 2 or sys.argv[1] == 'inspect':
    print([{'tag': r['tag_name'], 'draft': r['draft'], 'assets': [a['name'] for a in r['assets']]} for r in releases])
    raise SystemExit()

tag = 'v1.7.44'
asset = ROOT / 'installer' / 'ERP-SOM-Setup-1.7.44.exe'
digest = hashlib.sha256(asset.read_bytes()).hexdigest()
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
release = next((r for r in releases if r['tag_name'] == tag), None)
if not release:
    release = call('POST', API + '/releases', json={
        'tag_name': tag, 'target_commitish': sha, 'name': 'ERP-SOM 1.7.44', 'draft': True,
        'body': 'Correcciones de Master Data para escritorio:\n\n'
                '- Lectura compartida de formularios Excel y Word en OneDrive.\n'
                '- Reintentos ante bloqueos temporales y errores por archivo.\n'
                '- Lectura de encabezados bilingues por tipo de formulario, conservando correos, telefonos y datos bancarios.\n'
                '- Reconocimiento de encabezados parcialmente editados cuando la otra etiqueta identifica el campo.\n\n'
                'No cambia permisos de Windows ni omite bloqueos exclusivos.\n\n'
                'SHA-256 del instalador: `' + digest + '`'})
assert release['draft'], 'Release already published; do not replace'
existing = next((a for a in release['assets'] if a['name'] == asset.name), None)
if existing:
    assert existing.get('digest') == 'sha256:' + digest, 'Existing asset differs'
else:
    with asset.open('rb') as stream:
        existing = call('POST', release['upload_url'].split('{')[0], params={'name': asset.name},
                        headers={'Content-Type': 'application/octet-stream'}, data=stream)
assert existing['size'] == asset.stat().st_size
assert existing.get('digest') == 'sha256:' + digest
published = call('PATCH', release['url'], json={'draft': False, 'make_latest': 'true'})
latest = call('GET', API + '/releases/latest')
assert latest['tag_name'] == tag
print(published['html_url'])
print(existing['browser_download_url'])
print('SHA256', digest)
