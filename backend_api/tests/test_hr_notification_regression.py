import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services import notifications as n
from routers import hr_events


class NotificationRegressionTests(unittest.TestCase):
    def test_generated_pem_is_parsed_as_pem(self):
        if n.Vapid is None:
            self.skipTest('pywebpush not installed')
        public, private = n._generate_vapid_pair()
        with self.assertRaises(ValueError):
            n.Vapid.from_string(private)
        self.assertIsInstance(n._push_private_key(private), n.Vapid)
        self.assertEqual(n._push_private_key('base64-key'), 'base64-key')

    def test_push_failure_preserves_notification(self):
        for error in (ValueError('bad key'), RuntimeError('network failed')):
            cur = MagicMock()
            cur.fetchone.return_value = {'id': 42}
            with patch.object(n, 'dispatch_push_notification', side_effect=error):
                self.assertEqual(n.create_notification(cur, 'admin', 'title', 'body'), 42)
            statements = [c.args[0] for c in cur.execute.call_args_list]
            self.assertIn('ROLLBACK TO SAVEPOINT notification_push', statements)
            self.assertEqual(statements[-1], 'RELEASE SAVEPOINT notification_push')

    def test_insert_failure_is_not_silenced(self):
        cur = MagicMock()
        with patch.object(n, 'ensure_notifications_table'), patch.object(cur, 'execute', side_effect=RuntimeError('insert')):
            with self.assertRaises(RuntimeError):
                n.create_notification(cur, 'admin', 'title', 'body')

    def test_vacation_commits_even_when_push_fails(self):
        conn = MagicMock()
        cur = conn.cursor.return_value
        cur.fetchone.side_effect = [None, {'id': 10}, {'id': 42}]
        request = MagicMock()
        async def body():
            return json.dumps({'event_type': 'VACACIONES', 'payload': {'dias': 2}, 'event_date': '2026-10-17'}).encode()
        request.body = body
        with patch.object(hr_events, 'get_admin_master_users', return_value=['admin']), patch.object(n, 'dispatch_push_notification', side_effect=ValueError('key')):
            result = asyncio.run(hr_events.crear_evento(request, {'usuario': 'test'}, conn))
        self.assertEqual(result['id'], 10)
        self.assertEqual(result['notifications_created'], 1)
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()


if __name__ == '__main__':
    unittest.main()
