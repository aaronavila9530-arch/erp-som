import hashlib
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.web_report_branding import apply_mci_web_branding, MSL_ARTWORK
from services.container_web_export import build
from services.certificate_web_export import build as certificate

ROOT = Path(__file__).resolve().parents[1]


class WebBrandingTests(unittest.TestCase):
    def test_msl_and_unknown_are_byte_identical(self):
        raw = (ROOT / 'templates/container_report_template.xlsx').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.xlsx'
            for company in ('MSL-CR', '', 'OTHER'):
                path.write_bytes(raw)
                apply_mci_web_branding(path, {'company_code': company})
                self.assertEqual(raw, path.read_bytes())

    def test_only_audited_artwork_and_its_drawing_xml_change(self):
        raw = (ROOT / 'templates/container_report_template.xlsx').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'report.xlsx'
            path.write_bytes(raw)
            apply_mci_web_branding(path, {'company_code': 'MCI-CR'})
            with ZipFile(BytesIO(raw)) as before, ZipFile(path) as after:
                changed = {n for n in before.namelist() if before.read(n) != after.read(n)}
                self.assertEqual(changed, {'xl/media/image2.png', 'xl/media/image3.png',
                                           'xl/drawings/drawing1.xml', 'xl/sharedStrings.xml', '[Content_Types].xml'})
                self.assertEqual(after.read('xl/media/image1.jpeg'), before.read('xl/media/image1.jpeg'))
                self.assertIn(b'fillRect l=', after.read('xl/drawings/drawing1.xml'))
            once = path.read_bytes()
            apply_mci_web_branding(path, {'company_code': 'MCI-CR'})
            self.assertEqual(once, path.read_bytes())

    def assert_mci(self, raw):
        with ZipFile(BytesIO(raw)) as archive:
            media = [archive.read(n) for n in archive.namelist() if '/media/' in n]
            self.assertIn((ROOT / 'assets/mci_logo.png').read_bytes(), media)
            self.assertFalse({hashlib.sha256(data).hexdigest() for data in media} & MSL_ARTWORK)

    def test_container_export_and_template_integrity(self):
        template = ROOT / 'templates/container_report_template.xlsx'
        before = template.read_bytes()
        self.assert_mci(build({'company_code': 'MCI-CR', 'report_no': 'QA'}, 'QA', 'excel'))
        self.assertEqual(before, template.read_bytes())

    def test_certificate_exports(self):
        for kind, fmt in [('holds', 'excel'), ('sampling', 'excel'), ('sealing', 'excel'),
                          ('weight', 'word'), ('lashing', 'word')]:
            with self.subTest(kind=kind):
                self.assert_mci(certificate(kind, {'company_code': 'MCI-CR'}, fmt))

    def test_grain_report_and_cover(self):
        data = {'company_code': 'MCI-CR', 'report_no': 'QA', 'vessel': 'QA VESSEL'}
        self.assert_mci(certificate('grain', data, 'word'))
        # Inspect the exact document passed to PDF conversion, without requiring
        # a converter in the unit-test environment.
        with patch('services.certificate_web_export.convert', side_effect=lambda source, folder: source):
            self.assert_mci(certificate('grain', data, 'presentation'))


if __name__ == '__main__':
    unittest.main()
