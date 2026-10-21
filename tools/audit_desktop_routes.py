"""Inventory desktop HTTP contracts; optional GET-only production checks."""
import argparse
import ast
from contextlib import ExitStack, redirect_stdout
import inspect
import io
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import api_client
from session_context import set_user_context


class Captured(Exception):
    pass


def capture_routes():
    inventory = json.loads((ROOT / 'tmp/desktop-audit/inventory.json').read_text(encoding='utf-8'))
    names = sorted({name for row in inventory for name in row['api_functions']})
    records = []
    current = None
    def capture(_session, method, url, **kwargs):
        records.append({'function': current, 'method': method.upper(), 'path': urlparse(url).path,
                        'params': kwargs.get('params') or {}})
        raise Captured('Offline contract capture')
    with patch('requests.sessions.Session.request', autospec=True, side_effect=capture):
        for name in names:
            if name in ('api_request', 'raise_for_status_with_detail'):
                continue
            function = getattr(api_client, name, None)
            if not callable(function):
                continue
            current = name
            kwargs = {}
            for key, param in inspect.signature(function).parameters.items():
                if param.default is not inspect.Parameter.empty or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                    continue
                if key in ('payload', 'data', 'filtros', 'filters', 'report'):
                    kwargs[key] = {}
                elif key in ('usuario', 'user', 'approved_by'):
                    kwargs[key] = 'surveyor01'
                elif key in ('rol', 'role'):
                    kwargs[key] = 'user'
                elif key in ('year', 'anio'):
                    kwargs[key] = 2026
                elif key in ('month', 'mes'):
                    kwargs[key] = 10
                elif 'path' in key:
                    kwargs[key] = str(ROOT / 'tmp/desktop-audit/not-written.tmp')
                elif key in ('event_type', 'status', 'estado'):
                    kwargs[key] = 'PENDING'
                elif key in ('fecha', 'fecha_inicio', 'fecha_fin', 'event_date'):
                    kwargs[key] = '2026-10-17'
                elif key == 'hora':
                    kwargs[key] = '08:00'
                else:
                    kwargs[key] = 1
            try:
                with redirect_stdout(io.StringIO()):
                    function(**kwargs)
            except Exception:
                pass
    return names, records


def run(live=False):
    set_user_context('surveyor01', 'user', company_code='MCI-CR')
    names, records = capture_routes()
    folder = ROOT / 'tmp/desktop-audit'
    (folder / 'routes.json').write_text(json.dumps(records, indent=2, default=str), encoding='utf-8')
    print('Referenced API functions', len(names), 'Captured HTTP contracts', len(records), flush=True)
    if not live:
        return
    session = requests.Session()
    schema = session.get(api_client.BASE_URL + '/openapi.json', timeout=45)
    schema.raise_for_status()
    paths = schema.json()['paths']
    compiled = [(path, re.compile('^' + re.sub(r'\{[^}]+\}', '[^/]+', path.rstrip('/')) + '/?$'), methods) for path, methods in paths.items()]
    findings = []
    for record in records:
        matches = [row for row in compiled if row[1].match(record['path'])]
        if not any(record['method'].lower() in row[2] for row in matches):
            findings.append(record)
    print('Unmatched contracts:', json.dumps(findings, ensure_ascii=False), flush=True)
    results = []
    checked = set()
    for record in records:
        if record['method'] != 'GET' or any(x in record['path'].lower() for x in ('generate', 'approve', 'reject', 'sync', 'download', 'pdf', 'export', 'word', 'excel')):
            continue
        key = (record['path'], json.dumps(record['params'], sort_keys=True, default=str))
        if key in checked:
            continue
        checked.add(key)
        for role, user in (('user', 'surveyor01'), ('admin', 'admin')):
            for company in ('MCI-CR', 'MSL-CR'):
                headers = {'X-User': user, 'X-Role': role, 'X-User-Role': role, 'X-Company-Code': company}
                result = {**record, 'role': role, 'company': company}
                try:
                    response = session.get(api_client.BASE_URL + record['path'], params=record['params'], headers=headers, timeout=35)
                    result['status'] = response.status_code
                    if response.ok:
                        body = response.json()
                        result['shape'] = type(body).__name__
                        result['count'] = len(body) if isinstance(body, list) else len(body.get('data', [])) if isinstance(body, dict) and isinstance(body.get('data'), list) else None
                    elif response.status_code >= 500:
                        result['error'] = response.text[:800]
                except Exception as exc:
                    result['error'] = str(exc)
                results.append(result)
                print(role, company, record['path'], result.get('status', 'ERROR'), flush=True)
                (folder / 'reads.json').write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    (folder / 'unmatched-routes.json').write_text(json.dumps(findings, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    run(parser.parse_args().live)
