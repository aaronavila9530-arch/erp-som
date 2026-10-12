import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from pypdf import PdfReader
from routers.billing import _invoice_row
from services.pdf import factura_manual_pdf as pdf


class InvoiceIdentityTests(unittest.TestCase):
    def test_duplicate_numbers_require_id(self):
        cur = MagicMock()
        cur.fetchall.return_value = [{'id': 11}, {'id': 76}]
        with self.assertRaises(HTTPException) as exc:
            _invoice_row(cur, '2201', 'MSL-CR')
        self.assertEqual(exc.exception.status_code, 409)

    def test_lookup_includes_id_number_and_company(self):
        cur = MagicMock()
        cur.fetchall.return_value = [{'id': 76}]
        self.assertEqual(_invoice_row(cur, '2201', 'MSL-CR', 76)['id'], 76)
        self.assertEqual(cur.execute.call_args.args[1], ('2201', 'MSL-CR', 76, 76))

    def test_pdf_bank_rules_and_noncolliding_files(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(pdf, 'BASE_DIR', folder):
            first = pdf.generar_factura_manual_pdf(dict(numero_documento='2201',
                storage_key='MSL-CR_11', cliente='MAERSK A/S', total=900, termino_pago=0))
            second = pdf.generar_factura_manual_pdf(dict(numero_documento='2201',
                storage_key='MSL-CR_76', cliente='Pandi Costa Rica', total=0, termino_pago=30))
            self.assertNotEqual(first, second)
            a = ' '.join(PdfReader(first).pages[0].extract_text().split())
            b = ' '.join(PdfReader(second).pages[0].extract_text().split())
            for text in (a, b):
                for expected in ['Banco de Costa Rica', 'CR90015202001393623379', 'BCRICRSJ.',
                                 '019339.', 'MSL MARINE SURVEYORS AND LOGISTICS GROUP SOCIEDAD DE RESPONSABILIDAD LIMITADA', 'Avenida Central y']:
                    self.assertIn(expected, text)
            self.assertIn('MAERSK A/S', a)
            self.assertIn('PANDI COSTA RICA', b)
            self.assertIn('DUE UPON RECEIPT', a)
            self.assertIn('CREDIT 30 DAYS', b)

    def test_bank_fields_are_single_lines_inside_margins(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        self.assertEqual(len(pdf.BANK_LINES), 6)
        for label, value in pdf.BANK_LINES:
            self.assertTrue(label)
            self.assertNotIn('\n', value)
            self.assertLessEqual(stringWidth(f'{label} {value}', 'Times-Roman', 9), A4[0] - 3.5 * cm)
        with tempfile.TemporaryDirectory() as folder, patch.object(pdf, 'BASE_DIR', folder):
            path = pdf.generar_factura_manual_pdf(dict(numero_documento='layout', total=1))
            lines = PdfReader(path).pages[0].extract_text().splitlines()
            for label, value in pdf.BANK_LINES:
                self.assertIn(f'{label} {value}', lines)


if __name__ == '__main__':
    unittest.main()
