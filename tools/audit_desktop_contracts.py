"""Offline desktop import/call-contract inventory. Never connects to production."""
import ast
import importlib
import inspect
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULES = ('Informes', 'Comercial', 'Servicios', 'HHRR')


def inventory():
    results = []
    for area in MODULES:
        for path in sorted((ROOT / 'Modulos' / area).rglob('*.py')):
            record = {'file': str(path.relative_to(ROOT)), 'area': area, 'errors': [], 'classes': [], 'api_functions': []}
            try:
                source = path.read_text(encoding='utf-8-sig')
                tree = ast.parse(source)
                name = '.'.join(path.relative_to(ROOT).with_suffix('').parts)
                module = importlib.import_module(name)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        cls = getattr(module, node.name)
                        record['classes'].append({'name': node.name, 'signature': str(inspect.signature(cls))})
                imported = {}
                api_aliases = {alias.asname or alias.name for node in ast.walk(tree)
                               if isinstance(node, ast.Import) for alias in node.names if alias.name == 'api_client'}
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module == 'api_client':
                        api = importlib.import_module('api_client')
                        for alias in node.names:
                            function = getattr(api, alias.name)
                            imported[alias.asname or alias.name] = function
                            record['api_functions'].append(alias.name)
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id in api_aliases:
                        function_name = node.func.attr
                        function = getattr(importlib.import_module('api_client'), function_name)
                        record['api_functions'].append(function_name)
                    elif isinstance(node.func, ast.Name) and node.func.id in imported:
                        function_name, function = node.func.id, imported[node.func.id]
                    elif isinstance(node.func, ast.Name) and inspect.isclass(getattr(module, node.func.id, None)) and getattr(getattr(module, node.func.id), '__module__', '').startswith('Modulos.'):
                        function_name, function = node.func.id, getattr(module, node.func.id)
                    else:
                        continue
                    if any(isinstance(arg, ast.Starred) for arg in node.args) or any(kw.arg is None for kw in node.keywords):
                        continue
                    try:
                        inspect.signature(function).bind(*[None for _ in node.args], **{kw.arg: None for kw in node.keywords})
                    except TypeError as exc:
                        record['errors'].append(f'line {node.lineno}: {function_name}: {exc}')
            except Exception as exc:
                record['errors'].append(f'{type(exc).__name__}: {exc}')
            results.append(record)
    return results


if __name__ == '__main__':
    with patch('requests.sessions.Session.request', side_effect=RuntimeError('OFFLINE AUDIT: network disabled')), patch('psycopg2.connect', side_effect=RuntimeError('OFFLINE AUDIT: database disabled')):
        results = inventory()
    output = ROOT / 'tmp/desktop-audit'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'inventory.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
    print('Files:', len(results), 'Classes:', sum(len(r['classes']) for r in results))
    for row in results:
        if row['errors']:
            print(row['file'], row['errors'])
    print('Files with findings:', sum(bool(r['errors']) for r in results))
