"""Isolated voice tests: no production data or paid provider calls."""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError
from routers import service_voice as web
from services.service_voice import ServiceDraft, extract


class VoiceTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI(); app.include_router(web.router)
        app.dependency_overrides[web.access] = lambda: {'usuario':'qa'}
        self.client = TestClient(app)
        web._recent.clear()

    def test_valid_full_draft(self):
        d = ServiceDraft(tipo='Buque', buque_contenedor='MV prueba', cliente='Pandi',
                         operacion='Draft Survey', detalle='Descarga maiz', puerto='Caldera',
                         pais='Costa Rica', surveyors=[{'nombre':'Erick Garay'}],
                         fecha_inicio='2026-10-24', hora_inicio='10:00')
        self.assertEqual(d.model_dump(mode='json')['fecha_inicio'], '2026-10-24')
        self.assertIsNone(d.surveyors[0].honorario)

    def test_bad_times_dates_amounts_and_extra_fields(self):
        for d in [{'hora_inicio':'24:01'},{'hora_fin':'09:01:00'}, {'fecha_inicio':'2026-02-30'},
                  {'costo_operativo':-1},{'credit_release_approved':True},{'company':'MCI-CR'},
                  {'tipo':'Otro'},{'honorarios':float('inf')}]:
            with self.subTest(d=d), self.assertRaises(ValidationError): ServiceDraft(**d)

    def test_auth_releases_before_permission_and_model(self):
        with patch('database.get_conn') as get, patch('database.release_conn') as release, \
             patch.object(web, 'get_current_user', return_value={'usuario':'qa','rol':'user'}), \
             patch.object(web, '_has_visual_permission', side_effect=lambda *a: release.called):
            self.assertEqual(web.access('qa','user')['usuario'],'qa')
            release.assert_called_once_with(get.return_value)

    def test_permission_denied(self):
        with patch('database.get_conn'), patch('database.release_conn'), \
             patch.object(web,'get_current_user',return_value={'usuario':'qa','rol':'user'}), \
             patch.object(web,'_has_visual_permission',return_value=False):
            with self.assertRaises(HTTPException) as err: web.access('qa','user')
            self.assertEqual(err.exception.status_code,403)

    def test_provider_failure_and_missing_key(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':''}):
            self.assertEqual(self.client.post('/servicios/voice/draft',json={'text':'Buque prueba'}).status_code,503)
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test'}), patch.object(web,'extract',side_effect=RuntimeError('secret')):
            r=self.client.post('/servicios/voice/draft',json={'text':'Buque prueba'})
            self.assertEqual(r.status_code,502); self.assertNotIn('secret',r.text)
        self.assertTrue(web._slots.acquire(blocking=False)); web._slots.release()

    def test_upload_limits_and_bad_formats(self):
        r=self.client.post('/servicios/voice/transcribe',content=b'abc',headers={'Content-Type':'text/html'})
        self.assertEqual(r.status_code,415)
        r=self.client.post('/servicios/voice/transcribe',content=b'abc',headers={'Content-Type':'audio/webm'})
        self.assertEqual(r.status_code,422)
        with patch.object(web,'MAX_AUDIO',120):
            r=self.client.post('/servicios/voice/transcribe',content=b'a'*121,headers={'Content-Type':'audio/webm'})
            self.assertEqual(r.status_code,413)

    def test_schema_no_write_and_model_output(self):
        model=MagicMock(); model.chat.completions.create.return_value.choices[0].message.content=json.dumps({
            'buque_contenedor':'MV prueba','fecha_inicio':'2026-10-24','fecha_fin':'2026-10-23'})
        with patch('ai.maritime_ai._get_openai_client') as factory:
            factory.return_value.with_options.return_value.__enter__.return_value=model
            result=extract('Buque MV prueba')
        self.assertIsNone(result['fecha_fin']); self.assertTrue(result['advertencias'])
        self.assertIsNone(result['cliente'])

    def test_rate_limit(self):
        for _ in range(8): web.rate_limit({'usuario':'qa'})
        with self.assertRaises(HTTPException) as err: web.rate_limit({'usuario':'qa'})
        self.assertEqual(err.exception.status_code,429)

    def test_oversized_text(self):
        r=self.client.post('/servicios/voice/draft',json={'text':'x'*6001})
        self.assertEqual(r.status_code,422)


if __name__ == '__main__': unittest.main()
