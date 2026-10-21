"""Construct every desktop window for both roles with network and writes mocked."""
import importlib
import inspect
import json
from pathlib import Path
import sys
import traceback
import os
import argparse
import requests
from contextlib import ExitStack
from unittest.mock import MagicMock, patch
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
os.environ['LOCALAPPDATA'] = str(ROOT / 'tmp/desktop-audit/local-app-data')
sys.path.insert(0, str(ROOT))
from audit_desktop_contracts import inventory
from session_context import set_user_context


class Response:
    status_code = 200
    ok = True
    text = '[]'
    content = b''
    headers = {'Content-Type': 'application/json'}

    def __init__(self, url):
        self.url = str(url)

    def raise_for_status(self):
        pass

    def json(self):
        url = self.url.lower().rstrip('/')
        if url.endswith(('/servicios', '/surveyores', '/logra-reports', '/noticias/latest', '/clientes', '/comercial/precios', '/comercial/precios/meta')):
            return {'data': [], 'rows': [], 'total': 0}
        if any(x in url for x in ('filtros', 'filters', 'kpis', 'resumen', 'disponibles', 'summary', 'next', 'ultimo', 'siguiente')):
            return {'data': [], 'rows': [], 'status': [], 'year': [], 'total': 0,
                    'dias_disponibles': 10, 'dias_generados': 10, 'dias_solicitados': 0,
                    'next_number': 'TEST-001', 'numero': 'TEST-001'}
        if url.endswith('/1'):
            return {'id': 1, 'consec': 1, 'estado': 'Confirmado', 'tipo': 'Buque',
                    'num_informe': 'TEST-001', 'buque_contenedor': 'TEST VESSEL',
                    'cliente': 'TEST CLIENT', 'payload': {}, 'general': {}, 'draft': {},
                    'data': {}, 'success': True, 'fecha_inicio': '2026-10-17',
                    'hora_inicio': '08:00', 'fecha_fin': '2026-10-17', 'hora_fin': '09:00',
                    'honorarios': 100, 'costo_operativo': 10}
        return []


def run(network_failure=False):
    results = []
    with ExitStack() as stack:
        def effect(self, method=None, url=None, **kw):
            if network_failure:
                raise requests.ConnectionError('Audit: server unavailable')
            return Response(url or method)
        stack.enter_context(patch('requests.sessions.Session.request', side_effect=effect, autospec=True))
        stack.enter_context(patch('psycopg2.connect', side_effect=RuntimeError('Offline audit')))
        stack.enter_context(patch('backend_api.database.connect', side_effect=RuntimeError('Offline audit')))
        for name in ('wait_window', 'wait_visibility', 'grab_set', 'focus_force'):
            stack.enter_context(patch.object(tk.Misc, name, return_value=None))
        for name in ('showerror', 'showwarning', 'showinfo', 'askyesno', 'askokcancel'):
            stack.enter_context(patch('tkinter.messagebox.' + name, return_value=False))
        modules = inventory()
        app = tk.Tk()
        app.withdraw()
        for role in ('user', 'admin'):
            user = 'surveyor01' if role == 'user' else 'admin'
            set_user_context(user, role, company_code='MCI-CR')
            for item in modules:
                for desc in item['classes']:
                    root = tk.Toplevel(app)
                    root.withdraw()
                    root.usuario = user
                    root.rol = role
                    errors = []
                    app.report_callback_exception = lambda exc, value, tb: errors.append(''.join(traceback.format_exception(exc, value, tb)))
                    record = {'file': item['file'], 'class': desc['name'], 'role': role, 'errors': errors}
                    try:
                        module = importlib.import_module('.'.join(Path(item['file']).with_suffix('').parts))
                        cls = getattr(module, desc['name'])
                        if not issubclass(cls, tk.BaseWidget):
                            continue
                        kwargs = {}
                        for name, parameter in inspect.signature(cls).parameters.items():
                            if name == 'parent':
                                kwargs[name] = root
                            elif name in ('usuario', 'usuario_actual'):
                                kwargs[name] = user
                            elif name in ('rol', 'rol_usuario'):
                                kwargs[name] = role
                            elif parameter.default is not inspect.Parameter.empty:
                                continue
                            elif name == 'data' and desc['name'] == 'PopupCostosSurveyor':
                                kwargs[name] = []
                            elif name in ('data', 'record', 'report', 'precio_data', 'empleado_row', 'evento'):
                                kwargs[name] = Response('/1').json()
                            elif name in ('callbacks', 'filtros'):
                                kwargs[name] = {}
                            elif name in ('columnas', 'valores'):
                                kwargs[name] = ['id', 'test'] if name == 'columnas' else [1] * 30
                            elif name in ('consec', 'record_id', 'report_id', 'container_report_id', 'empleado_id', 'row_id'):
                                kwargs[name] = 1
                            elif name == 'entry_widget':
                                kwargs[name] = tk.Entry(root)
                            elif name in ('form_instance', 'agenda_popup'):
                                kwargs[name] = MagicMock()
                            elif name.startswith('on_') or name in ('callback', 'remove_callback'):
                                kwargs[name] = lambda *a, **k: None
                            else:
                                kwargs[name] = 'TEST'
                        window = cls(**kwargs)
                        if isinstance(window, tk.Toplevel) and window.winfo_exists():
                            window.withdraw()
                        root.update()
                        record['result'] = 'PASS' if not errors else 'FAIL'
                    except Exception:
                        errors.append(traceback.format_exc())
                        record['result'] = 'FAIL'
                    finally:
                        for timer in root.tk.splitlist(root.tk.call('after', 'info')):
                            root.tk.call('after', 'cancel', timer)
                        root.destroy()
                    results.append(record)
                    print(role, desc['name'], record['result'], flush=True)
        app.destroy()
    folder = ROOT / 'tmp/desktop-audit'
    folder.mkdir(parents=True, exist_ok=True)
    filename = 'windows-network-error.json' if network_failure else 'windows.json'
    (folder / filename).write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('TOTAL', len(results), 'FAIL', sum(r['result'] == 'FAIL' for r in results))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--network-failure', action='store_true')
    run(parser.parse_args().network_failure)
