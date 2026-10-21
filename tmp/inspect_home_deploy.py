import os
import subprocess
import requests

result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n',
    text=True, capture_output=True, check=True, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
credential = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
session = requests.Session()
session.headers.update({'Authorization': 'Bearer ' + credential['password'], 'Accept': 'application/vnd.github+json'})
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
base = 'https://api.github.com/repos/aaronavila9530-arch/erp-som'
for suffix in ('/commits/' + sha + '/status', '/commits/' + sha + '/check-runs'):
    response = session.get(base + suffix, timeout=30)
    response.raise_for_status()
    data = response.json()
    for item in data.get('statuses', data.get('check_runs', [])):
        print({key: item.get(key) for key in ('context','name','state','status','conclusion','description') if item.get(key) is not None})
