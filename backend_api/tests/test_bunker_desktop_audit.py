"""Read-only characterization of the desktop baseline before web migration.

Known defects are deliberately characterized, not accepted as web requirements.
No database connection, GUI initialization or source template writes occur.
"""
import ast
from pathlib import Path
import unittest
from decimal import Decimal, ROUND_HALF_UP

from openpyxl import load_workbook
from services.vessel_bunker_excel_service import TEMPLATE_PATH, VesselBunkerExcelGenerator

ROOT = Path(__file__).resolve().parents[2]


class BunkerDesktopAudit(unittest.TestCase):
    def setUp(self):
        self.book = load_workbook(TEMPLATE_PATH)
        self.addCleanup(self.book.close)

    def test_fifth_tank_source_mapping_is_recoverable(self):
        data = self.book['Data from DB']
        self.assertEqual([data.cell(r, 1).value for r in range(113, 121)], [
            'vlsfo_tank_5_' + suffix for suffix in
            ('name', 'dist_mtrs', 'gauge_mtrs', 'volume_m3', 'temp_c',
             'temp_f', 'density_15c', 'weight_mt')])
        original = [c.coordinate for row in self.book['CALCULATIONS'] for c in row
                    if c.data_type == 'f' and '#REF!' in c.value]
        self.assertEqual(original, ['D15','E15','F15','G15','H15','I15','J15'])
        VesselBunkerExcelGenerator()._restore_calculation_formulas(self.book)
        remaining = [c.coordinate for row in self.book['CALCULATIONS'] for c in row
                     if c.data_type == 'f' and '#REF!' in c.value]
        self.assertEqual(remaining, ['D15','E15','F15','G15','I15'])

    def test_printed_capacity_is_not_storage_capacity(self):
        fields = {row[0].value for row in self.book['Data from DB']}
        for fuel in ('vlsfo', 'mgo'):
            self.assertIn(f'{fuel}_tank_20_weight_mt', fields)
        VesselBunkerExcelGenerator()._restore_calculation_formulas(self.book)
        calc = self.book['CALCULATIONS']
        self.assertEqual(calc['J22'].value, '=SUM(J11:J21)')
        self.assertEqual(calc['J32'].value, '=SUM(J29:J31)')
        self.assertEqual(calc['E34'].value, '=J22+J32')

    def test_desktop_computation_without_tk_or_network(self):
        source = (ROOT/'Modulos/Informes/vessel_bunker/vessel_bunker_form.py').read_text(encoding='utf-8-sig')
        tree = ast.parse(source)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        names = {'_parse_decimal_for_formula', '_refresh_tank_formula_fields', '_normalize_numeric_for_db'}
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        isolated = ast.Module(body=[ast.ClassDef(name='Reference', bases=[], keywords=[],
                                                body=methods, decorator_list=[])], type_ignores=[])
        scope = {}
        exec(compile(ast.fix_missing_locations(isolated), '<desktop-bunker-reference>', 'exec'), scope)
        class Cell:
            def __init__(self, value=''): self.value = value
            def get(self): return self.value
            def set(self, value): self.value = value
        obj = scope['Reference']()
        def result(vol, temp, density):
            cells = {key: Cell(value) for key, value in
                     zip(('vol','tc','den','tf','w'), (vol,temp,density,'',''))}
            obj._refresh_tank_formula_fields(cells)
            return cells['tf'].get(), cells['w'].get()
        self.assertEqual(result('100', '30', '0.95'), ('86.00', '94.06'))
        self.assertEqual(result('', '30', '0.95'), ('86.00', ''))
        self.assertEqual(result('0', '15', '0.9'), ('59.00', '0.00'))
        self.assertEqual(result('1,25', '15', '0,9'), ('59.00', '1.12'))
        excel_round = (Decimal('1.25') * Decimal('0.9')).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        self.assertEqual(excel_round, Decimal('1.13'))


if __name__ == '__main__':
    unittest.main()
