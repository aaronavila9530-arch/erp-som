from decimal import Decimal
from pathlib import Path
import sqlite3
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routers.accounting_tax import _fiscal_amount_sql, _signed_book_rows, _preferred_tax_documents_sql


class TaxCreditSignsTests(unittest.TestCase):
    def test_positive_and_negative_credit_notes_always_reduce_book(self):
        for kind in ('NC', 'NCE', '03', ' nc '):
            for value in (113, -113):
                row = dict(document_type=kind, subtotal=value, exempt_amount=0, tax_amount=13, total=value)
                self.assertEqual(_signed_book_rows([row])[0]['total'], Decimal('-113.00'))
                self.assertEqual(row['tax_amount'], Decimal('-13.00'))

    def test_invoices_and_manual_norden_rows_are_unchanged(self):
        row = dict(document_type='FE', document_number='2209', receiver_name='NORDEN', total=25000)
        self.assertEqual(_signed_book_rows([row.copy()]), [row])

    def test_sql_signs_match_book_and_do_not_double_negate(self):
        conn = sqlite3.connect(':memory:')
        try:
            for kind, value, expected in [('NC', 13, -13), ('NC', -13, -13), ('FE', 13, 13), ('FE', -13, -13)]:
                result = conn.execute(f'SELECT {_fiscal_amount_sql("tax_amount")} FROM (SELECT ? document_type, ? tax_amount)', (kind, value)).fetchone()[0]
                self.assertEqual(result, expected)
        finally:
            conn.close()

    def test_amount_sql_rejects_arbitrary_columns(self):
        with self.assertRaises(ValueError):
            _fiscal_amount_sql('unexpected_column')

    def test_rejected_documents_filtered_after_source_selection(self):
        sql = _preferred_tax_documents_sql('d.company_code = %s')
        self.assertIn("'REJECTED', 'RECHAZADO', 'RECHAZADA'", sql)
        self.assertGreater(sql.index('COALESCE(hacienda_status'), sql.index('WHERE tax_rank = 1'))


if __name__ == '__main__':
    unittest.main()
