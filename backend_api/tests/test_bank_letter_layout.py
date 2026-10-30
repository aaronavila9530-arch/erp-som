from io import BytesIO
from pathlib import Path
import sys
import unittest

from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routers.masterdata_bank_accounts import _build_bank_letter_pdf


class BankLetterLayoutTests(unittest.TestCase):
    def test_multiline_beneficiary_does_not_overlap_next_row(self):
        row = dict(beneficiary_name='MSL Marine\nSurveyors and Logistics Sociedad de\nResponsabilidad Limitada',
                   bank_name='BANCO DE COSTA RICA', currency='CRC',
                   iban='CR90015202001393623379', bank_address='Address\nSecond line\nThird line')
        for company in ('MSL-CR', 'MCI-CR'):
            for language in ('ES', 'EN'):
                pdf = PdfReader(BytesIO(_build_bank_letter_pdf(row, company, None, language)))
                self.assertEqual(len(pdf.pages), 1)
                positions = {}
                def visitor(text, cm, tm, font, size):
                    if text.strip():
                        positions[text.strip()] = tm[5]
                pdf.pages[0].extract_text(visitor_text=visitor)
                self.assertGreater(positions['Responsabilidad Limitada'] - positions['BANCO DE COSTA RICA'], 15)

    def test_large_values_paginate_without_losing_text(self):
        row = dict(beneficiary_name='\n'.join('Line%03d' % i for i in range(150)),
                   bank_name='BANK', currency='USD', iban='X' * 200)
        pdf = PdfReader(BytesIO(_build_bank_letter_pdf(row, 'MSL-CR', None, 'EN')))
        text = '\n'.join(p.extract_text() for p in pdf.pages)
        self.assertGreater(len(pdf.pages), 1)
        for i in range(150):
            self.assertIn('Line%03d' % i, text)


if __name__ == '__main__':
    unittest.main()
