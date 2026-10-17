import ast
from pathlib import Path
import unittest
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[2]


class DesktopCommercialTests(unittest.TestCase):
    def methods(self):
        tree = ast.parse((ROOT / 'Modulos/Comercial/comercial_home_ui.py').read_text(encoding='utf-8-sig'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('_search', '_initial_search')]
        namespace = {'get_company_code': lambda: 'MCI-CR', 'get_comercial_board_api': MagicMock(), 'messagebox': MagicMock()}
        exec(compile(ast.Module(body=methods, type_ignores=[]), '<methods>', 'exec'), namespace)
        return namespace

    def test_initial_search_only_for_live_view(self):
        ns = self.methods()
        ui = MagicMock()
        ui.winfo_exists.return_value = False
        ns['_initial_search'](ui)
        ui._search.assert_not_called()
        ui.winfo_exists.return_value = True
        ns['_initial_search'](ui)
        ui._search.assert_called_once()

    def test_search_reports_company_and_sorts_results(self):
        ns = self.methods()
        ui = MagicMock()
        ui._build_filters.return_value = {'estados': ['Confirmado']}
        ns['get_comercial_board_api'].return_value = [{'consec': 1}, {'consec': 519}]
        ns['_search'](ui)
        self.assertEqual(ui._data_all[0]['consec'], 519)
        self.assertIn('MCI-CR | 2', ui.result_status.config.call_args.kwargs['text'])
        ns['get_comercial_board_api'].return_value = []
        ns['_search'](ui)
        self.assertIn('Sin servicios', ui.result_status.config.call_args.kwargs['text'])

    def test_failure_keeps_previous_results_and_warns(self):
        ns = self.methods()
        ui = MagicMock()
        ui._build_filters.return_value = {}
        ui._data_all = [{'consec': 519}]
        ns['get_comercial_board_api'].side_effect = RuntimeError('network')
        ns['_search'](ui)
        self.assertEqual(ui._data_all, [{'consec': 519}])
        ns['messagebox'].showerror.assert_called_once()


if __name__ == '__main__':
    unittest.main()
