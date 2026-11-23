import ast
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock,patch

from fastapi import HTTPException
from openpyxl import load_workbook
from docx import Document
from routers import certificates_web as web
from services.bunker_web_fields import SPEC,normalize
from services.bunker_web_export import msl_excel,mci_word,build
from tests.bunker_reference import aquitania

ROOT=Path(__file__).resolve().parents[2]


def sample():
    return dict(company_code='MSL-CR',bunker_cert_no='BUNKER-QA',certificate='OFF_HIRE',ship_name='QA Vessel',
        client='QA Client',report_date='2026-11-18',surveyor_name='QA Surveyor',
        vlsfo_tank_5_name='FIFTH',vlsfo_tank_5_volume_m3='100',vlsfo_tank_5_temp_c='30',vlsfo_tank_5_density_15c='.95',
        mgo_tank_20_name='TWENTIETH',mgo_tank_20_volume_m3='10',mgo_tank_20_temp_c='30',mgo_tank_20_density_15c='.85',
        bunker_figure_2_lsmgo='0',bunker_figure_3_lsmgo='.05')


class BunkerWebTests(unittest.TestCase):
    def test_empty_export_does_not_invent_temperature_or_density(self):
        data={**aquitania(),'mgo_tank_9_name':'EMPTY TANK','mgo_tank_9_gauge_mtrs':'EMPTY'}
        values,result=normalize(data,strict=True)
        self.assertEqual(result['totals']['mgo'],'121.30')
        self.assertIsNone(values['mgo_tank_9_temp_f'])
        book=load_workbook(BytesIO(build({**data,'company_code':'MCI-CR'},'excel')))
        try:
            self.assertEqual(book['MGO']['C13'].value,'EMPTY')
            self.assertIn(book['MGO']['G13'].value,(None,''))
            self.assertIn('COUNT',book['MGO']['H13'].value)
        finally:book.close()

    def test_real_word_and_excel_for_every_company_and_variant(self):
        for company in ('MSL-CR','MCI-CR'):
            for kind in ('ON_HIRE','OFF_HIRE','SPOT'):
                data={**aquitania(),'company_code':company,'certificate':kind}
                for fmt in ('word','excel'):
                    with self.subTest(company=company,kind=kind,fmt=fmt):
                        conn=MagicMock()
                        with patch.object(web,'read_record',return_value=data):
                            response=web.export('bunker',1,fmt,dict(company=company),conn,'EN')
                        stream=BytesIO(response.body)
                        if fmt=='word':
                            doc=Document(stream);body=' '.join(doc.element.xpath('.//w:t/text()'))
                            self.assertIn('351.44',body);self.assertIn('121.30',body)
                            self.assertIn(kind.replace('_',' '),body)
                            if company=='MSL-CR':self.assertIn('This certificate is issued without prejudice',body)
                        else:
                            book=load_workbook(stream)
                            self.assertIn('CALCULATIONS' if company=='MSL-CR' else 'Bunker',book.sheetnames)
                            book.close()
                        conn.commit.assert_not_called()

    def test_msl_no_invented_condition_or_spot_delivery(self):
        data={**aquitania(),'certificate':'SPOT'}
        book=load_workbook(BytesIO(build(data,'excel')))
        try:
            for cell in ('B19','B20','B37','B38','A35'):self.assertIn(book['CERTIFICATE'][cell].value,(None,''))
            self.assertIn('2026-07-04',book['CERTIFICATE']['B15'].value)
            self.assertEqual(book['CALCULATIONS']['I11'].number_format,'0.0000')
            self.assertEqual(book['LOG BOOK FIGURES']['G18'].value,"='CALCULATIONS'!J22")
        finally:book.close()

    def test_sounding_totals_override_stale_log_values(self):
        values,result=normalize({**aquitania(),'log_at_survey_vlsfo':'999','log_at_survey_lsmgo':'999'},strict=True)
        self.assertEqual(values['log_at_survey_vlsfo'],'353.04')
        self.assertEqual(values['log_at_survey_lsmgo'],'121.30')

    def test_condition_annex_for_every_company_and_variant(self):
        from pypdf import PdfReader,PdfWriter
        from fastapi import UploadFile
        writer=PdfWriter();writer.add_blank_page(width=612,height=792)
        stream=BytesIO();writer.write(stream);pdf=stream.getvalue()
        from fastapi.responses import Response
        for company in ('MSL-CR','MCI-CR'):
            for kind in ('ON_HIRE','OFF_HIRE','SPOT'):
                data={**aquitania(),'company_code':company,'certificate':kind}
                with patch.object(web,'read_record',return_value=data),patch.object(web,'export',return_value=Response(pdf)) as export:
                    result=web.bunker_bundle(1,[UploadFile(filename='condition.pdf',file=BytesIO(pdf))],dict(company=company),MagicMock(),'EN')
                    self.assertEqual(len(PdfReader(BytesIO(result.body)).pages),2)
                    self.assertEqual(export.call_args.args[2],'complete')
        with patch.object(web,'read_record',return_value=aquitania()),self.assertRaises(HTTPException):
            web.bunker_bundle(1,[UploadFile(filename='bad.pdf',file=BytesIO(b'not a pdf'))],dict(company='MSL-CR'),MagicMock(),'EN')

    def test_desktop_contract(self):
        tree=ast.parse((ROOT/'Modulos/Informes/vessel_bunker/vessel_bunker_form.py').read_text(encoding='utf-8-sig'))
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='static_columns' for t in n.targets))
        keys=set(ast.literal_eval(node.value))-{'workflow_status','status'}
        self.assertTrue(keys<=SPEC['fields'].keys(),keys-SPEC['fields'].keys())
        with load_template() as book:
            columns={row[0].value for row in book['Data from DB']}
            self.assertTrue(SPEC['fields'].keys()<=columns,SPEC['fields'].keys()-columns)

    def test_scope_and_bootstrap(self):
        for company in ('MSL-CR','MCI-CR'):
            ctx=dict(company=company,permissions={})
            self.assertIs(web.specification('bunker',ctx),SPEC)
            self.assertEqual(web.bootstrap(ctx)['types']['bunker']['document'],'word' if company=='MCI-CR' else 'excel')
        self.assertIn('s.companies=1',web.source(SPEC))

    def test_invalid_and_incomplete_submission(self):
        for change in ({'mgo_tank_20_density_15c':'850'}, {'dslop_hour':'24'},
                       {'antecedent_survey_date_from':'2026-11-18','antecedent_survey_date_to':'2026-11-17'},
                       {'vlsfo_tank_5_temp_c':None}):
            with self.subTest(change=change),self.assertRaises(HTTPException):normalize({**sample(),**change},strict=True)
        _,result=normalize({**sample(),'vlsfo_tank_5_temp_c':None})
        self.assertFalse(result['valid']);self.assertIsNone(result['total_mt'])

    def test_tenant_identity(self):
        cur=MagicMock();cur.fetchall.return_value=[dict(cliente='A',buque_contenedor='B',puerto='C',pais='D')]
        values={'bunker_cert_no':'QA','client':'forged'}
        web.bunker_identity(cur,values,{'company':'MCI-CR'})
        self.assertEqual(values['client'],'A')
        cur.fetchall.return_value=[]
        with self.assertRaises(HTTPException):web.bunker_identity(cur,values,{'company':'MCI-CR'})

    def test_stale_and_approved_no_write(self):
        for status,version in [('Approved','now'),('Draft','old')]:
            conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
            cur.fetchone.return_value={'id':1,'status':status,'updated_at':'now'}
            with self.assertRaises(HTTPException) as err:
                web.update('bunker',1,web.SaveInput(fields={},version=version),{'company':'MSL-CR','permissions':{'edit':True}},conn)
            self.assertEqual(err.exception.status_code,409);conn.commit.assert_not_called()

    def test_export_all_tanks_and_no_source_mutation(self):
        template=ROOT/'backend_api/templates/on_off_spot_template.xlsx';before=sha256(template.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'out.xlsx';msl_excel(sample(),target)
            book=load_workbook(target)
            try:
                visible=[s for s in book if s.sheet_state=='visible']
                self.assertEqual(len(visible),9) # certificate + calculations + six continuations + log
                self.assertFalse(any('#REF!' in str(c.value) for s in visible for row in s for c in row))
                self.assertIn("'Data from DB'",book['CALCULATIONS']['F15'].value)
                self.assertIn("'Data from DB'",book['TANKS 7']['A30'].value)
                self.assertEqual(book['CERTIFICATE']['J33'].value,'=SUM(J28,J30:J31)')
                self.assertIn(book['CERTIFICATE']['B33'].value,(None,''))
            finally:book.close()
        self.assertEqual(before,sha256(template.read_bytes()).hexdigest())

    def test_mci_docx_has_all_tanks_and_language(self):
        with tempfile.TemporaryDirectory() as folder:
            for language in ('EN','ES'):
                target=Path(folder)/'out.docx';mci_word({**sample(),'company_code':'MCI-CR'},target,language)
                doc=Document(target);body=' '.join(doc.element.xpath('.//w:t/text()'))
                for value in ('FIFTH','TWENTIETH','94.06','8.41','8.46','QA Surveyor'):self.assertIn(value,body)
                self.assertNotIn('Pabel',body)
                self.assertIn('INSPECCION DE COMBUSTIBLE' if language=='ES' else 'BUNKER SURVEY',body)


class load_template:
    def __enter__(self):
        self.book=load_workbook(ROOT/'backend_api/templates/on_off_spot_template.xlsx');return self.book
    def __exit__(self,*args):self.book.close()


if __name__=='__main__':unittest.main()
