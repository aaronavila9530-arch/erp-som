import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routers import cotizaciones as quotes


class QuotationNumberingTests(unittest.TestCase):
    def test_schema_replaces_global_uniqueness_without_renumbering(self):
        cur = MagicMock()
        quotes._ensure_cotizaciones_schema(cur)
        sql = cur.execute.call_args.args[0]
        self.assertLess(sql.index('CREATE UNIQUE INDEX'), sql.index('DROP CONSTRAINT'))
        self.assertIn('company_code', sql)
        self.assertIn('quotation_number', sql)
        self.assertNotIn('DELETE', sql)
        self.assertNotIn('UPDATE', sql)

    def test_preview_and_create_use_company_maximum(self):
        cur = MagicMock()
        cur.fetchone.return_value = (12,)
        self.assertEqual(quotes._next_quotation_number(cur, 'MCI-CR'), 'Quotation 00012')
        sql, params = cur.execute.call_args.args
        self.assertIn('MAX(', sql)
        self.assertNotIn('ORDER BY id', sql)
        self.assertEqual(params, ('MCI-CR',))

    def test_create_serializes_and_preserves_quote(self):
        conn = MagicMock()
        cur = conn.cursor.return_value
        cur.fetchone.side_effect = [(1,), (42, 'Quotation 00001')]
        payload = quotes.CotizacionCreate(cliente='Figal Innova', servicio='CARGO CONDITION',
            continente='America', pais='El Salvador', puerto='Acajutla', precio=950,
            servicio_1='CARGO CONDITION', precio_1=950, texto_cotizacion='Original text')
        result = quotes.crear_cotizacion(payload, x_company_code='MCI-CR', conn=conn)
        calls = cur.execute.call_args_list
        lock = next(i for i,c in enumerate(calls) if 'pg_advisory_xact_lock' in c.args[0])
        allocation = next(i for i,c in enumerate(calls) if 'SELECT COALESCE(MAX' in c.args[0])
        self.assertLess(lock, allocation)
        params = calls[-1].args[1]
        self.assertEqual(params['company_code'], 'MCI-CR')
        self.assertEqual(params['precio'], 950)
        self.assertEqual(params['texto_cotizacion'], 'Original text')
        self.assertEqual(result['quotation_number'], 'Quotation 00001')
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()


if __name__ == '__main__':
    unittest.main()
