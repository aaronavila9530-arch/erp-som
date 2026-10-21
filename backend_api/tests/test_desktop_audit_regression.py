"""Desktop contracts and error paths, without production writes."""
import ast
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import api_client
from session_context import set_user_context


def methods(path, names, namespace):
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8-sig'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
    nodes = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), namespace)
    return namespace


class DesktopAuditTests(unittest.TestCase):
    def setUp(self):
        set_user_context('surveyor01', 'user', company_code='MCI-CR')

    def test_draft_status_uses_dedicated_action_without_overwriting_report(self):
        for status, action in [('Approved', 'approve'), ('Rejected', 'reject')]:
            with self.subTest(status=status), patch.object(api_client, 'api_request') as request:
                request.return_value.json.return_value = {'success': True}
                result = api_client.update_draft_survey_status_api('2246-1310-2026', status)
                self.assertTrue(result['success'])
                self.assertEqual(request.call_args.args, ('PUT', '/draft-survey/2246-1310-2026/' + action))
                self.assertNotIn('json', request.call_args.kwargs)

    def test_invalid_draft_status_does_not_send_request(self):
        with patch.object(api_client, 'api_request') as request:
            with self.assertRaises(ValueError):
                api_client.update_draft_survey_status_api('1', 'Unknown')
            request.assert_not_called()

    def test_hr_legacy_filters_and_explicit_identity_are_supported(self):
        with patch.object(api_client, 'api_request') as request:
            api_client.listar_eventos_hr(event_type='LIQUIDATION', empleado_id=7)
            self.assertEqual(request.call_args.kwargs['headers']['X-User'], 'surveyor01')
            self.assertEqual(request.call_args.kwargs['params'], {'event_type': 'LIQUIDATION', 'empleado_id': 7})
            api_client.listar_eventos_hr('admin', 'admin')
            self.assertEqual(request.call_args.kwargs['headers']['X-Role'], 'admin')

    def test_services_client_selector_normalizes_paginated_catalog(self):
        ns = methods('Modulos/Servicios/ui_servicios.py', {'load_clientes'}, {
            'get_clientes_api': lambda: {'data': [{'nombrecomercial': 'Client A'}, {'nombrejuridico': 'Client B'}]}
        })
        ui = MagicMock()
        ns['load_clientes'](ui)
        loader = ui._load_combo.call_args.args[2]
        self.assertEqual(loader(), ['Client A', 'Client B'])

    def test_failed_filter_can_be_retried(self):
        ns = methods('Modulos/Servicios/ui_servicios.py', {'_load_combo'}, {'messagebox': MagicMock()})
        ui = type('View', (), {})()
        combo = MagicMock()
        ns['_load_combo'](ui, '_loaded', combo, MagicMock(side_effect=ConnectionError('offline')))
        self.assertFalse(hasattr(ui, '_loaded'))
        ns['_load_combo'](ui, '_loaded', combo, lambda: ['Confirmado'])
        self.assertTrue(ui._loaded)
        combo.config.assert_called_once_with(values=['Confirmado'])

    def test_service_query_error_is_reported_without_escaping(self):
        ns = methods('Modulos/Servicios/vista_servicios.py', {'load_data'}, {
            'api_request': MagicMock(side_effect=ConnectionError('offline')),
            'BASE_URL': 'https://invalid.test', 'messagebox': MagicMock(),
            'queue': __import__('queue'),
            'threading': type('Threads', (), {
                'Thread': lambda **kw: type('Worker', (), {'start': lambda self: kw['target']()})()
            }),
        })
        ui = MagicMock()
        ui.filtros = {}
        ns['load_data'](ui)
        ui.after.call_args.args[1]()
        ns['messagebox'].showerror.assert_called_once()


if __name__ == '__main__':
    unittest.main()
