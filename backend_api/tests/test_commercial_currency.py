import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from services import commercial_currency as fx
from backend_api.tests.test_comercial_web import invoke
from routers import comercial_clients_analytics as clients, comercial_ports_analytics as ports
from routers import comercial_servicios_analytics as services


class CurrencyTests(unittest.TestCase):
    def test_conversion_before_sum_preserves_usd_and_original_amounts(self):
        db = sqlite3.connect(':memory:')
        self.addCleanup(db.close)
        db.executescript('''CREATE TABLE servicios(honorarios NUMERIC, honorarios_moneda TEXT);
            CREATE TABLE exchange_rate(rate REAL, rate_date TEXT);
            INSERT INTO exchange_rate VALUES(500.0, '2020-01-01'), (0, '2021-01-01'), (1, '2099-01-01');
            INSERT INTO servicios VALUES(1850940, 'CRC'), (1101750, 'CRC'),
                (1023780, 'CRC'), (18000, 'USD'), (750, NULL), (NULL, NULL);''')
        values = db.execute(f'SELECT {fx.HONORARIOS_USD} FROM servicios s').fetchall()
        self.assertEqual([r[0] for r in values], [3701.88, 2203.5, 2047.56, 18000, 750, 0])
        total = db.execute(f'SELECT SUM({fx.HONORARIOS_USD}) FROM servicios s').fetchone()[0]
        self.assertAlmostEqual(total, 26702.94)
        self.assertEqual(db.execute('SELECT SUM(honorarios) FROM servicios').fetchone()[0], 3995220)

    def test_missing_rate_is_not_silently_zero_cost(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect = [None, {'total': 3}]
        with patch.object(fx, 'ensure_currency_schema'), self.assertRaises(HTTPException) as error:
            fx.currency_context(conn)
        self.assertEqual(error.exception.status_code, 503)

    def test_rate_provenance(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect = [{'rate': 500, 'rate_date': '2026-10-12'}, {'total': 3}]
        with patch.object(fx, 'ensure_currency_schema'):
            result = fx.currency_context(conn, 'MSL-CR')
        self.assertEqual(result, {'currency': 'USD', 'rate': 500, 'rate_date': '2026-10-12'})

    def test_migration_only_marks_exact_confirmed_records(self):
        conn = MagicMock()
        cur = conn.cursor.return_value.__enter__.return_value
        cur.fetchall.side_effect = [[(10,)], [(20,)], [(30,)]]
        with patch.object(fx, '_ready', False):
            fx.ensure_currency_schema(conn)
            fx.ensure_currency_schema(conn)
        conn.commit.assert_called_once()
        updates = [c.args for c in cur.execute.call_args_list if c.args[0].startswith('UPDATE')]
        self.assertEqual([args[1] for args in updates], [(10,), (20,), (30,)])
        self.assertTrue(all("SET honorarios_moneda = 'CRC'" in args[0] for args in updates))
        selects = [c.args for c in cur.execute.call_args_list if c.args[0].startswith('SELECT')]
        self.assertEqual([args[1] for args in selects], list(fx.CONFIRMED_CRC))
        self.assertTrue(all("'MSL-CR'" in args[0] for args in selects))

    def test_ambiguous_migration_rolls_back(self):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchall.return_value = [(1,), (2,)]
        with patch.object(fx, '_ready', False), self.assertRaises(RuntimeError):
            fx.ensure_currency_schema(conn)
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    def test_every_financial_query_uses_conversion_before_aggregation(self):
        for function in [clients.comercial_client_view, ports.comercial_ports_analytics,
                         ports.comercial_ports_kpis, services.servicios_analytics_by_servicio,
                         services.servicios_kpis_ejecutivos, services.costos_surveyor_pareto]:
            conn = MagicMock()
            cur = conn.cursor.return_value
            cur.fetchall.return_value = []
            cur.fetchone.return_value = dict.fromkeys(['total', 'clientes', 'paises', 'puertos',
                'facturacion_neta', 'honorarios', 'costos_operativos', 'costo_tarjetas'], 0)
            invoke(function, conn=conn, year_from=2026, year_to=2026, x_company_code='MSL-CR')
            queries = [call.args[0] for call in cur.execute.call_args_list]
            self.assertTrue(any(fx.HONORARIOS_USD in q for q in queries), function.__name__)


if __name__ == '__main__':
    unittest.main()
