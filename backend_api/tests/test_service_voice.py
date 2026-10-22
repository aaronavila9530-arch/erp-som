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
from services.service_voice import ServiceDraft, extract, validate_vessel


class VoiceTests(unittest.TestCase):
    def test_vessel_rejects_other_fields_without_losing_valid_data(self):
        cases = [
            'Buque MV prueba, cliente Pandi',
            'MV prueba cliente Pandi',
            'MV Laura contacto Diego Vargas',
            'MV Laura operaci\u00f3n Draft Survey',
            'MV Laura descarga maiz',
            'MV Laura, puerto Caldera',
            'MV Laura en el puerto Caldera',
            'MV Laura; pa\u00eds Costa Rica',
            'MV Laura fecha inicio 24 de octubre',
            'MV Laura hora 10:00',
            'MV Laura surveyor Pavel Pe\u00f1a',
            'MV Laura honorarios 300',
            'MV Laura perd\u00f3n MV prueba',
            'MV Laura customer Pandi',
            'MV Laura operation Draft Survey',
            'MV Laura at port Caldera',
        ]
        for name in cases:
            with self.subTest(name=name):
                d = ServiceDraft(buque_contenedor=name, cliente='Pandi', detalle='Maiz')
                validate_vessel(d, name)
                self.assertIsNone(d.buque_contenedor)
                self.assertEqual(d.cliente, 'Pandi')
                self.assertEqual(d.detalle, 'Maiz')
                self.assertTrue(d.advertencias)

    def test_preserves_names_identifiers_and_empty_values(self):
        for name in ['MV Santa Carolina V2', 'MV Puerto Limon', 'MT Costa Rica',
                     'MV Pacific 1', 'MSCU1234567', 'MV Pandi', None]:
            with self.subTest(name=name):
                d = ServiceDraft(buque_contenedor=name)
                validate_vessel(d, 'Cliente Pandi buque ' + (name or ''))
                self.assertEqual(d.buque_contenedor, name)
                self.assertFalse(d.advertencias)

    def test_model_contamination_is_blocked_at_extraction(self):
        model = MagicMock()
        model.chat.completions.create.return_value.choices[0].message.content = json.dumps({
            'buque_contenedor': 'Buque MV prueba, cliente Pandi', 'cliente': 'Pandi'})
        with patch('ai.maritime_ai._get_openai_client') as factory:
            factory.return_value.with_options.return_value.__enter__.return_value = model
            result = extract('Buque MV prueba, cliente Pandi')
        self.assertIsNone(result['buque_contenedor'])
        self.assertEqual(result['cliente'], 'Pandi')
        self.assertTrue(result['advertencias'])

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

    def test_combined_audio_draft(self):
        model = MagicMock()
        model.audio.transcriptions.create.return_value.text = 'Cliente PANDI'
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test'}), \
             patch('ai.maritime_ai._get_openai_client') as factory, \
             patch.object(web, 'extract', return_value={'cliente':'PANDI'}) as parse:
            factory.return_value.with_options.return_value.__enter__.return_value = model
            r = self.client.post('/servicios/voice/transcribe?prepare=true', content=b'a'*200,
                                 headers={'Content-Type':'audio/webm'})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['draft']['cliente'], 'PANDI')
            parse.assert_called_once_with('Cliente PANDI')

    def test_rate_limit(self):
        for _ in range(8): web.rate_limit({'usuario':'qa'})
        with self.assertRaises(HTTPException) as err: web.rate_limit({'usuario':'qa'})
        self.assertEqual(err.exception.status_code,429)

    def test_oversized_text(self):
        r=self.client.post('/servicios/voice/draft',json={'text':'x'*6001})
        self.assertEqual(r.status_code,422)


if __name__ == '__main__': unittest.main()
