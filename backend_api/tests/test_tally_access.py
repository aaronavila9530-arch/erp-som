import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routers import tally_access as mod
from database import get_db


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.conn=MagicMock()
        self.cur=self.conn.cursor.return_value.__enter__.return_value
        self.app=FastAPI();self.app.include_router(mod.router)
        self.app.dependency_overrides[get_db]=lambda:self.conn
        self.client=TestClient(self.app)

    def test_missing_token_does_not_accept_admin_headers(self):
        response=self.client.get('/tally-access/api/bootstrap',headers={'X-User':'admin','X-Role':'master'})
        self.assertEqual(response.status_code,401)

    def test_expired_revoked_inactive_tokens_rejected(self):
        self.cur.fetchone.return_value=None
        self.assertEqual(self.client.get('/tally-access/api/bootstrap',headers={'X-Tally-Token':'a'*43}).status_code,401)
        sql=self.cur.execute.call_args.args[0]
        for condition in ['revoked_at IS NULL','expires_at>NOW()','u.activo IS TRUE']:
            self.assertIn(condition,sql)

    def test_scope_cannot_be_changed_by_headers(self):
        self.cur.fetchone.return_value={'id':1,'username':'patricia.omier','company_code':'MCI-CR'}
        with patch.object(mod.tally,'get_sheet',return_value={'rows':[]}) as get:
            result=self.client.get('/tally-access/api/projects/9/sheets/1',headers={'X-Tally-Token':'a'*43,'X-Company-Code':'MSL-CR'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(get.call_args.args[2]['company'],'MCI-CR')
        self.assertIn('patricia.omier',get.call_args.args[2]['user'])
        self.assertNotIn('a'*43,str(self.cur.execute.call_args_list))

    def test_links_require_admin_stepup(self):
        self.assertEqual(self.client.post('/tally/access-links',headers={'X-Tally-Token':'a'*43}).status_code,401)
        self.assertEqual(self.client.delete('/tally/access-links/1',headers={'X-Tally-Token':'a'*43}).status_code,401)
        self.assertEqual(self.client.post('/tally-access/api/projects',json={}).status_code,404)

    def test_page_security_headers(self):
        response=self.client.get('/tally-access')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers['referrer-policy'],'no-referrer')
        self.assertEqual(response.headers['cache-control'],'no-store')


if __name__=='__main__':unittest.main()
