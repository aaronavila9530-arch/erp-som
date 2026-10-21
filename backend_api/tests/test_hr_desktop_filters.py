import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from routers import hr_events


class HrDesktopFiltersTests(unittest.TestCase):
    def test_filters_never_remove_user_restriction(self):
        for role in ('user', 'admin'):
            conn = MagicMock()
            conn.cursor.return_value.fetchall.return_value = []
            hr_events.listar_eventos({'usuario': 'surveyor01', 'rol': role}, conn,
                                    event_type='VACACIONES', status='PENDING', empleado_id=7)
            sql, params = conn.cursor.return_value.execute.call_args.args
            self.assertIn('UPPER(e.event_type)', sql)
            self.assertIn('UPPER(e.status)', sql)
            self.assertEqual(params[-2:], ['7', 7])
            self.assertEqual('LOWER(e.created_by) = LOWER(%s)' in sql, role == 'user')

    def request(self, employee=7):
        request = MagicMock()
        request.headers = {'X-Company-Code': 'MCI-CR'}
        async def body():
            return json.dumps({'event_type': 'LIQUIDATION', 'payload': {'empleado_id': employee}}).encode()
        request.body = body
        return request

    def test_user_cannot_register_liquidation(self):
        conn = MagicMock()
        with self.assertRaises(HTTPException) as error:
            asyncio.run(hr_events.crear_evento(self.request(), {'usuario': 'surveyor01', 'rol': 'user'}, conn))
        self.assertEqual(error.exception.status_code, 403)
        conn.commit.assert_not_called()

    def test_liquidation_targets_selected_employee_not_admin(self):
        conn = MagicMock()
        cur = conn.cursor.return_value
        cur.fetchone.side_effect = [None, {'nombre': 'Selected', 'apellidos': 'Employee'}, {'id': 15}]
        with patch.object(hr_events, '_notify_new_request', return_value=0):
            result = asyncio.run(hr_events.crear_evento(self.request(), {'usuario': 'admin', 'rol': 'admin'}, conn))
        self.assertEqual(result['id'], 15)
        inserts = [c for c in cur.execute.call_args_list if 'INSERT INTO hr_events' in c.args[0]]
        self.assertEqual(inserts[0].args[1][0], 'Selected Employee')
        queries = [c for c in cur.execute.call_args_list if 'company_code = %s' in c.args[0]]
        self.assertEqual(queries[0].args[1], (7, 'MCI-CR'))
        conn.commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
