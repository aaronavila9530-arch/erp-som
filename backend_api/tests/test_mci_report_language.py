import sys
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from unittest.mock import MagicMock, patch
from docx import Document
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.mci_survey_export import build_word
from services.mci_container_export import build_word as container_word
from services.mci_survey_schema import SurveyContent, SECTION_TITLES
from services.mci_report_language import ES, translate


class LanguageTests(unittest.TestCase):
    def test_export_override_does_not_change_saved_report(self):
        from routers.mci_surveys_web import export
        row=dict(company_code='MCI-CR',kind='condition',vessel='QA',requested_by='CLIENT',
                 report_number='QA',status='Approved',content={'language':'EN','sections':{}})
        with patch('routers.mci_surveys_web.record',return_value=row), patch('routers.mci_surveys_web.enrich',return_value=row):
            response=export(1,'word',{},MagicMock(),language='ES')
        self.assertIn('INFORME',Document(BytesIO(response.body)).paragraphs[0].text)
        self.assertEqual(row['content']['language'],'EN')
        self.assertEqual(row['status'],'Approved')

    def test_all_mci_report_kinds(self):
        from services.mci_logistics_schema import TITLES as logistics
        from services.mci_port_captancy_schema import TITLES as port
        from services.mci_crane_schema import TITLES as crane
        from services.mci_container_schema import TITLES as container
        narrative = 'La carga presenta humedad. Working es una cita textual, no debe cambiar.'
        for kind, titles in [('vessel',SECTION_TITLES),('condition',SECTION_TITLES),('cargo',SECTION_TITLES),
                             ('logistics',logistics),('port_captancy',port),('crane',crane),('container',container)]:
            for language in ('EN','ES'):
                with self.subTest(kind=kind, language=language):
                    row=dict(company_code='MCI-CR',kind=kind,vessel='VESSEL NAME',requested_by='Working SA',
                             report_number='QA-123',location='Caldera',content=dict(language=language,
                             hierarchy_version=2,issue_date='2026-11-16',inspection_date='2026-11-16',
                             sections={k:dict(enabled=True,blocks=[dict(text=narrative)]) for k in titles},
                             crane_checks={'crane_access':dict(done=True,status='Working')}))
                    data=(container_word if kind=='container' else build_word)(row)
                    doc=Document(BytesIO(data))
                    text='\n'.join(doc.element.xpath('.//w:t/text()'))
                    self.assertIn(narrative,text)
                    self.assertIn('Working SA',text)
                    for key,title in titles.items():
                        expected=translate(title,language)
                        # Some common headings have specialized logistics/port labels.
                        if key not in ('chronology','findings','remarks'):
                            self.assertIn(expected,text)
                    if language=='ES':
                        self.assertNotIn('PROFESSIONAL TECHNICAL REPORT',text)
                        self.assertNotIn('THIS BONAFIDE',text)
                        self.assertNotIn('THIS BONA FIDE',text)
                        if kind!='container':
                            self.assertIn('16 de noviembre de 2026',text)
                            self.assertEqual(doc.tables[0].cell(0,0).text,'Preparado para')
                        for section in doc.sections:
                            footer=''.join(section.footer._element.xpath('.//w:t/text()'))
                            self.assertNotIn('Head Office',footer)
                            self.assertNotIn('Page',footer)
                    with ZipFile(BytesIO(data)) as z:
                        self.assertTrue(any(n.startswith('word/media/') for n in z.namelist()))

    def test_default_and_validation(self):
        self.assertEqual(SurveyContent().language,'EN')
        with self.assertRaises(ValueError):SurveyContent(language='FR')
        self.assertEqual(translate('1.1 Work performed','ES'),'1.1 Trabajo realizado')

    def test_all_crane_options_are_translated(self):
        from services.crane_web_fields import POINTS, OPTIONS
        for label in list(POINTS.values())+OPTIONS[1:]:
            self.assertIn(label,ES)


if __name__=='__main__':unittest.main()
