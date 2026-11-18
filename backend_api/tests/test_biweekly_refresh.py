import unittest
from datetime import date
from unittest.mock import MagicMock
from routers import invoice_to_pay as itp


class BiweeklyRefreshTests(unittest.TestCase):
    def test_monthly_fixed_invoice_and_explicit_schedule(self):
        start, end = date(2026,11,16), date(2026,11,30)
        row=dict(payee_name='American Data',issue_date=date(2026,11,1),schedule_date=date(2026,12,1))
        self.assertTrue(itp._biweekly_obligation_due(row,start,end))
        self.assertFalse(itp._biweekly_obligation_due({**row,'planned_payment_date':date(2026,12,1)},start,end))
        self.assertFalse(itp._biweekly_obligation_due({**row,'payee_name':'Other supplier'},start,end))
        self.assertTrue(itp._biweekly_obligation_due({**row,'schedule_date':date(2026,10,1)},start,end))
    def test_saved_draft_includes_open_overdue_suppliers_without_duplicates(self):
        cur = MagicMock()
        cur.fetchall.return_value = [
            dict(id=10, company_code='MSL-CR', payee_name='American Data', reference='AD1', balance=100, currency='USD'),
            dict(id=11, company_code='MSL-CR', payee_name='Prime Properties', reference='PP1', balance=200, currency='USD'),
        ]
        existing = dict(obligation_id=10, category='Internet', name='American Data', amount=100, currency='USD')
        rows = itp._refresh_biweekly_supplier_draft(cur, 'MSL-CR', '2026-11', 2, [existing])
        self.assertEqual([r['obligation_id'] for r in rows], [10, 11])
        self.assertEqual(rows[1]['category'], 'Alquiler')
        sql, params = cur.execute.call_args.args
        self.assertIn("status IN ('PENDING','PARTIAL')", sql)
        self.assertIn('balance > 0', sql)
        self.assertNotIn('BETWEEN', sql)
        self.assertEqual(params[1].month, 11)


if __name__ == '__main__':
    unittest.main()
