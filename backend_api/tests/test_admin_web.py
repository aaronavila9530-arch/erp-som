import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from database import get_db
from routers import user_admin as admin


class AdminWebTests(unittest.TestCase):
    def test_people_only_collapses_equivalent_entries(self):
        person = dict(source_type='empleado', source_id='1', label='Ana Test', nombre='Ana', apellido='Test', email='', usuario='ana')
        copy = dict(person, source_id='2')
        other = dict(person, source_id='3', email='other@example.test')
        provider = dict(person, source_type='proveedor')
        self.assertEqual(admin._unique_people([person, copy, other, provider]), [person, other, provider])

    def test_routes_require_verified_authorization(self):
        app = FastAPI()
        app.include_router(admin.router)
        app.dependency_overrides[get_db] = lambda: MagicMock()
        with TestClient(app) as client, patch.object(admin, 'connect') as connect:
            for method, path in [('GET', ''), ('GET', '/meta'), ('GET', '/people'),
                                 ('GET', '/audit'), ('GET', '/test/permissions'),
                                 ('PUT', '/test/permissions'), ('POST', '')]:
                response = client.request(method, '/admin/users' + path,
                    headers={'X-User': 'admin', 'X-User-Role': 'master'}, json={})
                self.assertEqual(response.status_code, 401, path)
            connect.assert_not_called()

    def test_empty_permissions_never_touch_database(self):
        for permissions in ({}, {'invalid': ['admin']}, {'dashboard': []}):
            with patch.object(admin, 'connect') as connect, self.assertRaises(HTTPException) as ctx:
                admin.save_permissions('test', admin.PermissionPayload(permissions=permissions),
                                       {'user': 'admin'}, 'admin', 'master')
            self.assertEqual(ctx.exception.status_code, 400)
            connect.assert_not_called()

    def test_password_and_role_validation(self):
        self.assertEqual(admin._validate_password('StrongPassword123!'), [])
        self.assertTrue(admin._validate_password('weak'))
        self.assertTrue(admin._validate_password('StrongPassword123!' + '\u00e9' * 30))
        with self.assertRaises(ValidationError):
            admin.UserCreatePayload(usuario='test', password='StrongPassword123!', rol='unknown')

    def test_metadata_includes_every_desktop_module(self):
        data = admin.meta('admin', 'master')
        self.assertEqual(len(data['modules']), 10)
        self.assertEqual({m['code'] for m in data['modules']}, set(data['module_actions']))

    def test_permissions_distinguish_inherited_and_explicit(self):
        for rows, source in [([], 'inherited'), ([{'module_code':'dashboard','action_code':'view'}], 'explicit')]:
            conn = MagicMock()
            cur = conn.cursor.return_value
            cur.fetchone.return_value = {'usuario':'test','rol':'user'}
            cur.fetchall.return_value = rows
            with patch.object(admin, 'connect', return_value=conn):
                data = admin.get_permissions('test')
            self.assertEqual(data['source'], source)
            self.assertIn('servicios', data['inherited_permissions'])
            conn.close.assert_called_once()

    def test_missing_user(self):
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = None
        with patch.object(admin, 'connect', return_value=conn), self.assertRaises(HTTPException) as ctx:
            admin.get_permissions('missing')
        self.assertEqual(ctx.exception.status_code, 404)

    def test_audit_pagination_selects_no_secrets(self):
        conn = MagicMock()
        cur = conn.cursor.return_value
        cur.fetchall.return_value = [{'id': n} for n in range(3)]
        with patch.object(admin, 'connect', return_value=conn):
            data = admin.audit_history(2, 10)
        self.assertEqual(len(data['data']), 2)
        self.assertTrue(data['has_more'])
        query, params = cur.execute.call_args.args
        self.assertNotIn('detail', query)
        self.assertNotIn('pass', query)
        self.assertEqual(params, (3, 10))

    def test_creation_audit_excludes_password_and_uses_verified_actor(self):
        conn = MagicMock()
        conn.cursor.return_value.fetchone.return_value = None
        payload = admin.UserCreatePayload(usuario='test', password='StrongPassword123!')
        with patch.object(admin, 'connect', return_value=conn), patch.object(admin, '_audit') as audit:
            admin.create_user(payload, {'user':'verified-admin'}, 'admin', 'master')
        self.assertEqual(audit.call_args.args[1], 'verified-admin')
        self.assertNotIn('password', audit.call_args.args[4])
        conn.commit.assert_called_once()


if __name__ == '__main__':
    unittest.main()
