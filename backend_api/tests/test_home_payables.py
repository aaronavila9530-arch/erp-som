import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.home_payables import payment_queues, load_payment_queues, merge_biweekly_rows


class HomePayablesTests(unittest.TestCase):
    def run_close(self, completed=False, fail=False):
        from services.itp_september_close import close_historical_itp
        database = ModuleType('database')
        connection = MagicMock()
        database.connect = MagicMock(return_value=connection)
        cur = connection.cursor.return_value.__enter__.return_value
        cur.fetchone.return_value = {'affected': 2} if completed else None
        cur.fetchall.return_value = [{'id': 11}, {'id': 12}]
        router = ModuleType('routers.invoice_to_pay')
        router._sync_itp_sources = MagicMock()
        if fail:
            router._sync_itp_sources.side_effect = RuntimeError('sync failed')
        with patch.dict(sys.modules, {'database': database, 'routers.invoice_to_pay': router}):
            if fail:
                with self.assertRaises(RuntimeError):
                    close_historical_itp()
            else:
                close_historical_itp()
        return connection, cur, router

    def test_migration_commit_and_backup_before_update(self):
        conn, cur, router = self.run_close()
        conn.commit.assert_called_once()
        conn.close.assert_called_once()
        self.assertEqual(router._sync_itp_sources.call_count, 2)
        sql = [call.args[0] for call in cur.execute.call_args_list]
        backup = next(i for i,s in enumerate(sql) if 'INSERT INTO itp_historical_closure_rows' in s)
        update = next(i for i,s in enumerate(sql) if 'UPDATE payment_obligations' in s)
        self.assertLess(backup, update)
        self.assertEqual(cur.execute.call_args_list[update].args[1][1], [11,12])

    def test_migration_idempotent_and_rolls_back_on_error(self):
        conn, cur, router = self.run_close(completed=True)
        conn.commit.assert_not_called()
        router._sync_itp_sources.assert_not_called()
        conn, cur, router = self.run_close(fail=True)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        conn.close.assert_called_once()

    def test_half_month_currency_and_undated(self):
        rows = [dict(payment_date=date(2026,10,d), currency=c, balance=a)
                for d,c,a in [(15,'CRC',1000),(16,'CRC',2000),(16,'USD',25)]]
        rows.append(dict(payment_date=None,currency='USD',balance=10))
        result = payment_queues(rows, [])
        self.assertEqual(result['payable_half']['count'], 3)
        self.assertEqual(result['payable_month']['count'], 2)
        monthly = result['payable_month']['summary']
        self.assertIn(dict(periodo='2026-10',currency='CRC',cantidad=2,balance=Decimal(3000)),monthly)
        self.assertEqual(rows[0]['quincena'],'2026-10 Q1')
        self.assertEqual(rows[1]['quincena'],'2026-10 Q2')

    def test_queries_are_scoped_and_open_only(self):
        cur=MagicMock();cur.fetchall.return_value=[]
        with patch('services.home_payables.load_biweekly_home_rows', return_value=[]):
            load_payment_queues(cur,'MCI-CR')
        for call in cur.execute.call_args_list:
            self.assertIn('company_code=%s',call.args[0])
            self.assertEqual(call.args[1],('MCI-CR',))
        self.assertIn("status IN ('PENDING','PARTIAL')",cur.execute.call_args_list[0].args[0])

    def test_biweekly_lines_include_zero_amount_and_deduplicate_carryover(self):
        real = [dict(id=1)]
        lines = [dict(obligation_id=1, amount=20),
                 dict(name='Planilla', amount=100, due_date='2026-10-15', currency='CRC'),
                 dict(name='CCSS', amount=0, due_date='2026-10-15', currency='CRC')]
        merged = merge_biweekly_rows(real, [('2026-10',1,lines),('2026-10',2,lines)])
        self.assertEqual(len(merged),3)
        self.assertEqual(merged[2]['status'],'PENDIENTE_MONTO')
        self.assertEqual(merged[1]['balance'],Decimal(100))

    def test_close_is_one_time_and_issue_date_not_due_date(self):
        source=(Path(__file__).parents[1]/'services/itp_september_close.py').read_text()
        self.assertIn("issue_date < DATE '2026-10-01'",source)
        self.assertIn('before_row JSONB',source)
        self.assertIn("status='PAID', balance=0",source)
        self.assertIn('if cur.fetchone():',source)
        self.assertNotIn('INSERT INTO accounting',source)
        self.assertNotIn('INSERT INTO bank',source)
        accounting=(Path(__file__).parents[1]/'services/accounting_auto.py').read_text(encoding='utf-8')
        self.assertIn('and not ob.get("historical_closed")', accounting)
        self.assertIn('historical_closed=TRUE', source)


if __name__=='__main__': unittest.main()
