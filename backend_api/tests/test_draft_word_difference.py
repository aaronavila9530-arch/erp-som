"""Exercise desktop and server calculations without GUI or database side effects."""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


def load_calculations():
    desktop = ast.parse((ROOT / 'Modulos/Informes/Vessel_Draft_Survey/draft_survey_form.py').read_text(encoding='utf-8-sig'))
    cls = next(n for n in desktop.body if isinstance(n, ast.ClassDef) and n.name == 'DraftSurveyForm')
    names = {'_coerce_draft_number', '_fmt_calc_number', '_fmt_calc_percent',
             '_apply_word_report_calculations_to_data'}
    cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
    cls.bases = []
    scope = {}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), '<desktop-calculations>', 'exec'), scope)
    desktop_calculate = scope['DraftSurveyForm']()._apply_word_report_calculations_to_data
    server = ast.parse((ROOT / 'backend_api/routers/draft_survey_extra_router.py').read_text(encoding='utf-8-sig'))
    names = {'_coerce_number', '_fmt_word_number', '_fmt_word_percent', '_apply_word_report_calculations'}
    nodes = [n for n in server.body if isinstance(n, ast.FunctionDef) and n.name in names]
    scope = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<server-calculations>', 'exec'), scope)
    return desktop_calculate, scope['_apply_word_report_calculations']


class DraftWordDifferenceTests(unittest.TestCase):
    def check_case(self, draft, bl, difference, percentage):
        for calculate in load_calculations():
            source = {'word_draft_figures': draft, 'word_bl_figures': bl,
                      'word_difference': '-999', 'word_percentage': '-999',
                      'word_shore_scale': '51231.90', 'word_shore_bl': '51442.00'}
            result = calculate(source)
            self.assertEqual(result['word_difference'], difference)
            self.assertEqual(result['word_percentage'], percentage)
            self.assertEqual(result['word_shore_difference'], '210.10')
            self.assertEqual(source['word_difference'], '-999')

    def test_reported_positive_difference(self):
        self.check_case('51444.60', '51442.00', '2.60', '0.0051')

    def test_shortage_stays_negative(self):
        self.check_case('51439.40', '51442.00', '-2.60', '-0.0051')

    def test_equal_figures(self):
        self.check_case('51442', '51442', '0.00', '0.0000')

    def test_decimal_comma(self):
        self.check_case('51 444,60', '51.442,00', '2.60', '0.0051')

    def test_zero_bill_of_lading(self):
        self.check_case('2.60', '0', '2.60', '0.0000')

    def test_missing_inputs_remain_unset(self):
        for calculate in load_calculations():
            for value in ('', None, 'invalid'):
                result = calculate({'word_draft_figures': value, 'word_bl_figures': '100'})
                self.assertNotIn('word_difference', result)


if __name__ == '__main__':
    unittest.main()
