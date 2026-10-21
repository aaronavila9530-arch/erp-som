import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI
from fastapi.testclient import TestClient
import database
from routers import health
from services.availability import StandbyGate, runs_jobs, accepts_traffic, role


class AvailabilityTests(unittest.TestCase):
    def test_defaults_preserve_primary(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(role(), 'primary')
            self.assertTrue(runs_jobs()); self.assertTrue(accepts_traffic())

    def test_standby_never_runs_jobs(self):
        with patch.dict(os.environ, {'SOM_DEPLOYMENT_ROLE':'standby', 'SOM_BACKGROUND_JOBS':'true',
                                     'SOM_STANDBY_VALIDATED':'false'}):
            self.assertFalse(runs_jobs()); self.assertFalse(accepts_traffic())
        with patch.dict(os.environ, {'SOM_DEPLOYMENT_ROLE':'standby', 'SOM_STANDBY_VALIDATED':'true'}):
            self.assertTrue(accepts_traffic()); self.assertFalse(runs_jobs())

    def test_invalid_role_rejected(self):
        with patch.dict(os.environ, {'SOM_DEPLOYMENT_ROLE':'stanbdy'}):
            with self.assertRaises(RuntimeError): role()

    def test_gate_does_not_reach_business_routes(self):
        app=FastAPI(); app.include_router(health.router); app.add_middleware(StandbyGate)
        handler=MagicMock(return_value={'ok':True})
        @app.post('/save')
        def save(): return handler()
        with patch.dict(os.environ, {'SOM_DEPLOYMENT_ROLE':'standby', 'SOM_STANDBY_VALIDATED':'false'}):
            client=TestClient(app)
            self.assertEqual(client.get('/health/live').status_code,200)
            self.assertEqual(client.get('/health/ready').status_code,503)
            self.assertEqual(client.post('/save').status_code,503)
            handler.assert_not_called()

    def test_readiness_database_failure_and_success(self):
        with patch.dict(os.environ, {'SOM_DEPLOYMENT_ROLE':'primary'}), patch.object(health,'probe_database',return_value=False):
            self.assertEqual(health.ready().status_code,503)
        with patch.dict(os.environ, {'SOM_DEPLOYMENT_ROLE':'primary'}), patch.object(health,'probe_database',return_value=True):
            self.assertEqual(health.ready().status_code,200)

    def test_probe_releases_on_success_error_readonly(self):
        for row,fail,want in [((True,True),False,True),((False,True),False,False),((True,False),False,False),(None,True,False)]:
            pool=MagicMock(); conn=pool.getconn.return_value
            cur=conn.cursor.return_value.__enter__.return_value; cur.fetchone.return_value=row
            if fail: cur.execute.side_effect=RuntimeError('private DSN')
            with patch.object(database,'_connection_pool',pool), patch.object(database,'_initialize_pool'), patch.object(database,'release_conn') as release:
                self.assertEqual(database.probe_database(),want)
                release.assert_called_once_with(conn)

    def test_exhausted_pool_not_retried(self):
        pool=MagicMock(); pool.getconn.side_effect=RuntimeError('exhausted')
        with patch.object(database,'_connection_pool',pool), patch.object(database,'_initialize_pool'):
            self.assertFalse(database.probe_database())
            pool.getconn.assert_called_once()

    def test_release_failure_is_not_ready(self):
        pool=MagicMock()
        with patch.object(database,'_connection_pool',pool), patch.object(database,'_initialize_pool'), \
             patch.object(database,'release_conn',side_effect=RuntimeError('private connection details')):
            self.assertFalse(database.probe_database())


if __name__=='__main__': unittest.main()
