import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from routers import certificates_web as web
from services.grain_web_fields import SPEC


class GrainWebTests(unittest.TestCase):
    def setUp(self):
        self.ctx = dict(company='MCI-CR', user='qa', permissions=dict(view=True,create=True,edit=True,approve=False))
        self.conn = MagicMock()
        self.cur = self.conn.cursor.return_value.__enter__.return_value
        self.row = dict(id=1, cert_no='QA', status='Draft', legacy='preserved')
        self.cur.fetchone.return_value = self.row
        self.cur.fetchall.return_value = [{'company_code':'MCI-CR'}]

    def test_all_ten_holds_and_samples(self):
        for i in range(1, 11):
            for part in ('product','hold','tonnage'):
                self.assertIn(f'hold{i}_{part}', SPEC['fields'])
            for part in ('hold','proa_babor','proa_estribor','centro','popa_babor','popa_estribor'):
                self.assertIn(f'sample{i}_{part}', SPEC['fields'])
        self.assertEqual(len(SPEC['fields']), 112)

    def test_dates_and_no_privilege_fields(self):
        result = web.clean_fields(SPEC, {'sampling_start_time':'22/10/2026 09:01','place_date':'22/10/2026','sample10_centro':'001'})
        self.assertEqual(result['sampling_start_time'], '2026-10-22 09:01')
        self.assertEqual(result['sample10_centro'], '001')
        for fields in ({'status':'Approved'},{'company_code':'MSL-CR'},{'sampling_end_time':'31/02/2026 09:00'}):
            with self.assertRaises(HTTPException): web.clean_fields(SPEC, fields)

    def test_create_is_scoped_and_no_schema_changes(self):
        web.create('grain', web.SaveInput(fields={'cert_no':'QA'},submit=True),self.ctx,self.conn)
        sql, values = self.cur.execute.call_args.args
        self.assertIn('vessel_grain_sampling_reports', sql)
        self.assertIn('MCI-CR',values)
        self.assertIn('Pending for review',values)
        self.assertFalse(any('ALTER ' in c.args[0] for c in self.cur.execute.call_args_list))

    def test_company_read_conflict_and_approval_permissions(self):
        web.read_record(self.cur,SPEC,1,self.ctx)
        sql, params = self.cur.execute.call_args.args
        self.assertIn('s.companies=1',sql)
        self.assertEqual(params,('MCI-CR',1))
        with self.assertRaises(HTTPException) as error:
            web.update('grain',1,web.SaveInput(fields={'conclusion':'new'},version='old'),self.ctx,self.conn)
        self.assertEqual(error.exception.status_code,409)
        with self.assertRaises(HTTPException) as error:
            web.change_status('grain',1,web.StatusInput(version=web.version(self.row),status='Approved'),self.ctx,self.conn)
        self.assertEqual(error.exception.status_code,403)

    def test_ai_requires_write_permission(self):
        ctx = {**self.ctx, 'permissions':dict(view=True)}
        with self.assertRaises(HTTPException) as error:
            web.grain_assist(web.GrainAssistInput(text='Conclusion'), ctx)
        self.assertEqual(error.exception.status_code,403)

    def test_web_exports_use_unique_output_and_preserve_templates(self):
        from services.certificate_web_export import build
        from io import BytesIO
        from docx import Document
        import hashlib
        root = Path(__file__).resolve().parents[1]
        template = root / 'templates/Supervision_Muestreo_Granos.docx'
        before = hashlib.sha256(template.read_bytes()).digest()
        data = {'cert_no':'QA-WEB','vessel_name':'QA VESSEL','requested_by':'QA CLIENT'}
        content = build('grain',data,'word')
        doc = Document(BytesIO(content))
        self.assertTrue(any('QA VESSEL' in p.text for p in doc.paragraphs))
        self.assertEqual(before,hashlib.sha256(template.read_bytes()).digest())

if __name__ == '__main__': unittest.main()
