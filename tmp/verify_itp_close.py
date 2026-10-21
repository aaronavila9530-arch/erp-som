import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

base = 'https://api-som-fastapi-production-e66d.up.railway.app'
mode = sys.argv[1]
path = Path(__file__).with_name('itp_close_before.json')
data = {}
for company in ('MCI-CR', 'MSL-CR'):
    req = Request(base + '/invoice-to-pay/search?status=ALL', headers={'X-Company-Code': company})
    with urlopen(req, timeout=120) as response:
        data[company] = json.load(response)['data']
if mode == 'before':
    if path.exists():
        raise SystemExit('Before snapshot already exists; refusing to overwrite')
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
before = json.loads(path.read_text(encoding='utf-8'))
for company, rows in data.items():
    targets = [r for r in before[company] if r.get('issue_date') and r['issue_date'][:10] < '2026-10-01' and r.get('status') in ('PENDING', 'PARTIAL') and r.get('record_type', 'OBLIGATION') == 'OBLIGATION']
    print(company, 'target_count', len(targets))
    if mode == 'after':
        lookup = {r['id']: r for r in rows}
        failed = [r['id'] for r in targets if lookup[r['id']]['status'] != 'PAID' or float(lookup[r['id']]['balance']) != 0]
        october = [r for r in before[company] if (r.get('issue_date') or '') >= '2026-10-01']
        changed = [r['id'] for r in october if (r['status'], r['balance']) != (lookup[r['id']]['status'], lookup[r['id']]['balance'])]
        print('failed', failed, 'October changed', changed)
        assert not failed and not changed
