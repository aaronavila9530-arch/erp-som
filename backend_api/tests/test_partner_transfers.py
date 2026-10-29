import unittest
from backend_api.services.partner_transfers import parse_transfer, partner_name


def receipt(name='PABEL GONZALO PEÑA BARRETO', sender='MSL MARINE SURVEYORS AND LOGIS', concept='Otro concepto'):
    return f'''Notificacion de Transferencia Local
Estimado(a) {name} :
BAC Credomatic le comunica que {sender} realizó una transferencia electrónica a su cuenta.
La transferencia se realizó el día 15-10-2026 a las 21:18:39 horas; por un monto de 1,700.00 USD , por concepto de:
"{concept}"
El número de referencia es 406456105'''


class PartnerTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(partner_name('PENA BARRETO PABEL GONZALO'), partner_name('Pabel Gonzalo Peña Barreto'))
        self.assertTrue(partner_name('QUIROS BENAMBOURG DIANA VERONI'))
        self.assertIsNone(partner_name('Diana Otra Persona'))

    def test_any_concept(self):
        p = parse_transfer(receipt())
        self.assertEqual(p['company_code'], 'MSL-CR')
        self.assertEqual(p['amount'], '1700.00')
        self.assertEqual(p['concept'], 'Otro concepto')
        self.assertFalse(p['allow_closed_period'])

    def test_mci(self):
        self.assertEqual(parse_transfer(receipt(sender='3-101-969147 SOCIEDAD ANONIMA'))['company_code'], 'MCI-CR')

    def test_sender_is_not_recipient(self):
        self.assertIsNone(parse_transfer(receipt(name='OTRO BENEFICIARIO',sender='DIANA VERONICA QUIROS BENAMBOURG')))

    def test_unknown_company(self):
        self.assertIsNone(parse_transfer(receipt(sender='OTRA EMPRESA')))

    def test_missing_reference(self):
        self.assertIsNone(parse_transfer(receipt().replace('406456105','')))

    def test_bcr_destination_not_operator(self):
        text = '''Informe de transferencia entre cuentas BCR
Hola, QUIROS BENAMBOURG DIANA VERONICA.
Fecha 19/10/2026
Documento 12491838
Cuenta origen CR90015202001393623379
MSL MARINE SURVEYORS AND LOGIS
Cuenta destino CR56015202001055349683
PENA BARRETO PABEL GONZALO
Monto debitado $2.400,00
Monto transferido $2.400,00
Motivo Otro concepto
Para más informacion'''
        p=parse_transfer(text)
        self.assertTrue(p['partner_name'].startswith('PABEL'))
        self.assertEqual(p['amount'],'2400.00')
        self.assertEqual(p['bank'],'BCR')


if __name__ == '__main__':
    unittest.main()
