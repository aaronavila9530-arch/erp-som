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
from services.port_captancy_web_fields import SPEC
from services.port_captancy_web_export import word
from services.mci_survey_schema import SurveySave
from services.mci_survey_export import build_word
from routers.mci_surveys_web import persist
from fastapi import UploadFile
from services.port_captancy_bundle import read_annexes, merge
from pypdf import PdfWriter, PdfReader

class PortCaptancyTests(unittest.TestCase):
    def test_annex_order_and_invalid_pdf(self):
        def pdf(width):
            w=PdfWriter();w.add_blank_page(width=width,height=300);out=BytesIO();w.write(out);return out.getvalue()
        first,second=pdf(100),pdf(200)
        files=[UploadFile(filename='second.pdf',file=BytesIO(second))]
        annexes=read_annexes(files)
        result=PdfReader(BytesIO(merge(first,annexes)))
        self.assertEqual([float(p.mediabox.width) for p in result.pages],[100,200])
        self.assertTrue(files[0].file.closed)
        with self.assertRaises(HTTPException):read_annexes([UploadFile(filename='bad.pdf',file=BytesIO(b'not a PDF'))])

    def test_exact_desktop_contract(self):
        tree=ast.parse((ROOT/'backend_api/routers/port_captancy_reports_router.py').read_text(encoding='utf-8-sig'))
        base=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BASE_FIELDS' for t in n.targets))
        expected=set(base)|{f'{k}_{i}' for k in ('operation_summary','remarks','conclusion') for i in range(1,16)}
        self.assertEqual(set(SPEC['fields']),expected)

    def test_tenant_scope(self):
        self.assertEqual(web.specification('port_captancy',{'company':'MSL-CR'}),SPEC)
        with self.assertRaises(HTTPException):web.specification('port_captancy',{'company':'MCI-CR'})
        self.assertIn('s.companies=1',web.source(SPEC))

    def test_dates_and_times(self):
        self.assertEqual(web.clean_fields(SPEC,{'ts_date_0':'02/11/2026','ts_hour_0':'8','ts_min_0':'5'}),
                         {'ts_date_0':'2026-11-02','ts_hour_0':'08','ts_min_0':'05'})
        for key,value in [('ts_hour_0','24'),('ts_min_0','60'),('arrival_hour','-1'),('ts_date_0','31/02/2026')]:
            with self.assertRaises(HTTPException):web.clean_fields(SPEC,{key:value})

    def test_duplicate_does_not_write(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value=[{'company_code':'MSL-CR'}];cur.fetchone.return_value={'id':1}
        with self.assertRaises(HTTPException) as error:
            web.create('port_captancy',web.SaveInput(fields={'report_number':'QA'}),{'company':'MSL-CR','permissions':{'create':True}},conn)
        self.assertEqual(error.exception.status_code,409);conn.commit.assert_not_called()

    def test_service_identity_and_order(self):
        cur=MagicMock();cur.fetchone.return_value=dict(cliente='Client',buque_contenedor='Ship',continente='America',puerto='Caldera',pais='Costa Rica',operacion='Steel')
        values=dict(report_number='QA',vessel='Spoof',ts_date_3='2026-11-02',ts_date_4='2026-11-01')
        with self.assertRaises(HTTPException):web.port_captancy_identity(cur,values,{'company':'MSL-CR'})
        values['ts_date_4']='2026-11-03';web.port_captancy_identity(cur,values,{'company':'MSL-CR'})
        self.assertEqual(values['vessel'],'Ship');self.assertNotIn('company_code',values)

    def test_mci_limits(self):
        for content in ({'ts_time_0':'25:00'},{'ts_date_3':'2026-11-03','ts_date_4':'2026-11-02'},
                        {'sections':{'operation_summary':{'blocks':[{'text':'x'}]*16}}},
                        {'sections':{'enclosure':{'blocks':[{'text':'x'}]*2}}}):
            with self.assertRaises(ValueError):SurveySave(kind='port_captancy',service_id=1,content=content)

    def test_mci_identity_and_storage(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect=[dict(num_informe='QA',buque_contenedor='Ship',cliente='Client',puerto='Caldera',pais='Costa Rica',operacion='Steel',continente='America'),
                                 None, dict(id=1,updated_at='now',content={})]
        persist(SurveySave(kind='port_captancy',service_id=1,content={'operation':'Spoof'}),{'permissions':{'create':True}},conn)
        sql,params=cur.execute.call_args.args
        self.assertIn('mci_generic_surveys',sql)
        self.assertEqual(params[5].adapted['operation'],'Steel')
        self.assertTrue(any("tipo='Buque'" in c.args[0] for c in cur.execute.call_args_list))

    def test_original_templates_preserved(self):
        paths=[ROOT/'backend_api/templates'/n for n in ('port_captancy_template.docx','presentation_port_captancy_aceros.docx','presentation_port_captancy_granos.docx')]
        hashes=[sha256(p.read_bytes()).hexdigest() for p in paths]
        data={k:('2026-11-02' if f['type']=='date' else 'QA_'+k) for k,f in SPEC['fields'].items()}
        data['company_code']='MSL-CR'
        with tempfile.TemporaryDirectory() as folder:
            for operation,cover in [('Steel',False),('Steel',True),('Grains',True)]:
                data['operation']=operation
                target=Path(folder)/'qa.docx';word(data,target,cover)
                doc=Document(target)
                text=' '.join(doc.element.xpath('.//w:t/text()'))
                self.assertIn('QA_vessel',text)
                self.assertNotIn('{report_number}',text)
                if not cover:
                    for key in ('operation_summary_15','remarks_15','conclusion_15','ts_hour_4','link_picture'):
                        self.assertIn('QA_'+key,text)
                self.assertTrue(any('image' in rel.reltype for part in doc.part.package.parts for rel in part.rels.values()))
            data['company_code']='MCI-CR'
            with self.assertRaises(ValueError):word(data,target)
        self.assertEqual(hashes,[sha256(p.read_bytes()).hexdigest() for p in paths])

    def test_mci_specific_sections_and_no_hidden_text(self):
        content={'hierarchy_version':2,'report_type':'Port attendance','operation':'Steel','grt':'12345',
                 'ts_date_3':'2026-11-02','ts_time_3':'08:15','sections':{
                 'instructions':{'enabled':True},'chronology':{'enabled':True},'particulars':{'enabled':True},
                 'operation_summary':{'enabled':True,'blocks':[{'text':'QA operation'}]},
                 'remarks':{'enabled':False,'blocks':[{'text':'HIDDEN'}]}}}
        row=dict(company_code='MCI-CR',kind='port_captancy',vessel='QA Ship',requested_by='Client',report_number='QA-PORT',content=content)
        doc=Document(BytesIO(build_word(row)));text=' '.join(doc.element.xpath('.//w:t/text()'))
        for value in ('Port Captancy','QA operation','GRT: 12345','08:15 LT','Port attendance'):self.assertIn(value,text)
        self.assertNotIn('HIDDEN',text)

if __name__=='__main__':unittest.main()
