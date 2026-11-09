import ast
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock

from docx import Document
from fastapi import HTTPException
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend_api'))
from routers import certificates_web as web
from routers.mci_surveys_web import persist
from services.crane_web_fields import SPEC, POINTS
from services.crane_web_export import word
from services.mci_survey_schema import SurveySave
from services.mci_survey_export import build_word


class CraneTests(unittest.TestCase):
    def test_desktop_contract(self):
        from routers.vessel_crane_inspection_router import FORM_ALLOWED_COLUMNS as expected
        self.assertEqual(set(SPEC['fields']),set(expected)-{'status'})

    def test_tenant_scope(self):
        self.assertEqual(web.specification('crane',{'company':'MSL-CR'}),SPEC)
        with self.assertRaises(HTTPException):web.specification('crane',{'company':'MCI-CR'})
        self.assertIn('s.companies=1',web.source(SPEC))

    def test_clean_fields(self):
        self.assertEqual(web.clean_fields(SPEC,{'crane_access_done':False,'gear_start_hour':'8','gear_start_minute':'9'}),
                         {'crane_access_done':False,'gear_start_hour':'08','gear_start_minute':'09'})
        for key,value in [('crane_access_done','true'),('crane_access_status','invented'),('gear_end_hour','24'),
                          ('gear_end_minute','60'),('gear_end_date','31/02/2026')]:
            with self.assertRaises(HTTPException):web.clean_fields(SPEC,{key:value})

    def test_identity_and_period(self):
        cur=MagicMock();cur.fetchone.return_value=dict(cliente='Client',buque_contenedor='Ship',puerto='Caldera',pais='Costa Rica')
        values=dict(report_number='QA',vessel='wrong',gear_start_date='2026-11-09',gear_end_date='2026-11-08')
        with self.assertRaises(HTTPException):web.crane_identity(cur,values,{'company':'MSL-CR'})
        values['gear_end_date']='2026-11-10';web.crane_identity(cur,values,{'company':'MSL-CR'})
        self.assertEqual(values['vessel'],'Ship');self.assertEqual(values['client'],'Client')

    def test_duplicate_no_write(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value=[{'company_code':'MSL-CR'}];cur.fetchone.return_value={'id':1}
        with self.assertRaises(HTTPException) as err:
            web.create('crane',web.SaveInput(fields={'report_number':'QA'}),{'company':'MSL-CR','permissions':{'create':True}},conn)
        self.assertEqual(err.exception.status_code,409);conn.commit.assert_not_called()

    def test_approved_and_stale_protection(self):
        for status,version in [('Approved','now'),('Draft','old')]:
            conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
            cur.fetchone.return_value={'id':1,'status':status,'updated_at':'now'}
            with self.assertRaises(HTTPException) as err:
                web.update('crane',1,web.SaveInput(fields={},version=version),{'company':'MSL-CR','permissions':{'edit':True}},conn)
            self.assertEqual(err.exception.status_code,409);conn.commit.assert_not_called()

    def test_mci_validation(self):
        for content in ({'crane_checks':{'unknown':{}}},{'crane_checks':{'crane_access':{'done':'true'}}},
                        {'crane_checks':{'crane_access':{'status':'invented'}}},
                        {'sections':{'crane1':{'blocks':[{'text':'x'}]*11}}},
                        {'sections':{'crane_checklist':{'blocks':[{'text':'x'}]}}},
                        {'sections':{'enclosure':{'blocks':[{'text':'x'}]*2}}},
                        {'period_start':'2026-11-09T10:00','period_end':'2026-11-09T09:00'}):
            with self.assertRaises(ValueError):SurveySave(kind='crane',service_id=1,content=content)

    def test_mci_storage_and_identity(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect=[dict(num_informe='QA',buque_contenedor='Ship',cliente='Client',puerto='Caldera',pais='Costa Rica'),
                                 None,dict(id=1,updated_at='now',content={})]
        persist(SurveySave(kind='crane',service_id=1,content={}),{'permissions':{'create':True}},conn)
        sql,params=cur.execute.call_args.args
        self.assertIn('mci_generic_surveys',sql)
        self.assertEqual(params[5].adapted['location'],'Caldera, Costa Rica')
        self.assertTrue(any("tipo='Buque'" in c.args[0] for c in cur.execute.call_args_list))

    def test_msl_original_and_mapping(self):
        paths=[ROOT/'backend_api/templates'/n for n in ('crane_inspection_template.docx','presentation_crane_inspection.docx')]
        before=[sha256(p.read_bytes()).hexdigest() for p in paths]
        data={'company_code':'MSL-CR','report_number':'QA-CRANE','vessel':'QA Ship','client':'QA Client',
              'crane_wire_visual_status3':'Working','luffing_center_sheave_status2':'Greased',
              'cargo_block_sheave_status':'Not working','crane3_remark_7':'SEVEN','crane3_remark_9':'NINE',
              'intro_text':'CUSTOM INTRO','intro_inspection_date':'2026-11-09','link_picture':'https://example.org/photos'}
        with tempfile.TemporaryDirectory() as folder:
            for cover in (False,True):
                target=Path(folder)/'qa.docx';word(data,target,cover);doc=Document(target)
                text=' '.join(doc.element.xpath('.//w:t/text()'))
                self.assertNotIn('{report_number}',text)
                if not cover:
                    self.assertIn('CUSTOM INTRO',text);self.assertEqual(text.count('SEVEN'),1);self.assertIn('NINE',text)
                    self.assertIn('Crane wire rope visual inspection: Working.',text)
                    self.assertIn('Luffing center sheave visual inspection: Greased.',text)
                    self.assertIn('Cargo block sheave shaft: Not working.',text)
                self.assertTrue(any('image' in rel.reltype for part in doc.part.package.parts for rel in part.rels.values()))
            with self.assertRaises(ValueError):word({**data,'company_code':'MCI-CR'},target)
        self.assertEqual(before,[sha256(p.read_bytes()).hexdigest() for p in paths])

    def test_mci_sections_and_hidden_data(self):
        content={'hierarchy_version':2,'sections':{'instructions':{'enabled':True},'crane_intro':{'enabled':True,'blocks':[{'text':'INTRO'}]},
                 'gear':{'enabled':False},'gear_wires':{'enabled':True,'blocks':[{'text':'HIDDEN'}]},
                 'crane_checklist':{'enabled':True},'remarks':{'enabled':True},'crane3':{'enabled':True,'blocks':[{'text':'CRANE THREE'}]}},
                 'crane_checks':{'crane_access':{'done':True,'status3':'Working'}},'inspection_date':'2026-11-09','inspection_time':'08:45'}
        row=dict(company_code='MCI-CR',kind='crane',vessel='QA Ship',requested_by='Client',report_number='QA',content=content)
        doc=Document(BytesIO(build_word(row)));text=' '.join(doc.element.xpath('.//w:t/text()'))
        for value in ('Crane Inspections','INTRO','CRANE THREE','Crane Access: Working.','08:45 LT'):self.assertIn(value,text)
        self.assertNotIn('HIDDEN',text)


if __name__=='__main__':unittest.main()
