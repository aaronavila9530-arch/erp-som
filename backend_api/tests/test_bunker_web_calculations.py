import unittest
from services.bunker_web_calculations import calculate, number


def tank(fuel='vlsfo', index=1, volume='100', temp='30', density='.95'):
    return {f'{fuel}_tank_{index}_{key}': value for key, value in
            dict(name=f'T{index}', volume_m3=volume, temp_c=temp, density_15c=density).items()}


class BunkerWebCalculations(unittest.TestCase):
    def test_explicit_empty_without_inventing_measurements(self):
        for field in ('gauge_mtrs','volume_m3'):
            with self.subTest(field=field):
                result=calculate({'vlsfo_tank_1_name':'EMPTY TANK','vlsfo_tank_1_'+field:'EMPTY'})
                self.assertTrue(result['valid'])
                self.assertEqual(result['total_mt'],'0.00')
                self.assertIsNone(result['fields']['vlsfo_tank_1_temp_f'])
                self.assertIsNone(result['fields']['vlsfo_tank_1_density_15c'])

    def test_empty_does_not_override_measured_remaining_volume(self):
        result=calculate({**tank(volume='.745',temp='34',density='.9483'),'vlsfo_tank_1_gauge_mtrs':'EMPTY'})
        self.assertEqual(result['total_mt'],'0.70')

    def test_aquitania_every_tank_and_signed_dlosp(self):
        from tests.bunker_reference import aquitania
        result=calculate(aquitania())
        expected={'vlsfo':['145.85','0.70','0.20','81.78','26.62','28.66','33.34','31.45','4.44'],
                  'mgo':['10.72','78.48','5.28','11.25','12.46','3.11']}
        for fuel,weights in expected.items():
            self.assertEqual([t['weight_mt'] for t in result['tanks'] if t['fuel']==fuel],weights)
        self.assertEqual(result['totals'],{'vlsfo':'353.04','mgo':'121.30'})
        self.assertEqual(result['total_mt'],'474.34')
        self.assertEqual(result['dlosp'],{'vlsfo':'351.44','mgo':'121.30'})

    def test_reference_formula(self):
        result = calculate(tank())
        self.assertTrue(result['valid'])
        self.assertEqual(result['total_mt'], '94.06')
        self.assertEqual(result['tanks'][0]['temp_f'], '86.00')

    def test_excel_midpoint_rounding(self):
        self.assertEqual(calculate(tank(volume='1.25', temp='15', density='.9'))['total_mt'], '1.13')

    def test_all_forty_tanks_included(self):
        payload = {}
        for fuel in ('vlsfo','mgo'):
            for i in range(1,21): payload.update(tank(fuel,i))
        result = calculate(payload)
        self.assertEqual(len(result['tanks']),40)
        self.assertEqual(result['totals'], {'vlsfo':'1881.20','mgo':'1881.20'})
        self.assertEqual(result['total_mt'],'3762.40')

    def test_missing_is_not_zero(self):
        result=calculate(tank(volume=''))
        self.assertFalse(result['valid'])
        self.assertIsNone(result['total_mt'])
        self.assertIsNone(result['totals'])
        self.assertEqual(calculate(tank(volume='0'))['total_mt'],'0.00')

    def test_client_cannot_forge_derived_values(self):
        payload=tank()
        payload.update(vlsfo_tank_1_weight_mt='99999',vlsfo_tank_1_temp_f='99999')
        result=calculate(payload)
        self.assertEqual(result['fields']['vlsfo_tank_1_weight_mt'],'94.06')
        self.assertEqual(result['fields']['vlsfo_tank_1_temp_f'],'86.00')

    def test_invalid_numbers_fail_closed(self):
        for value in ('NaN','Infinity','1e3','1,2,3','1.2.3','1,00.23',True,'=1+1'):
            with self.subTest(value=value), self.assertRaises(ValueError):number(value,'test')
        for kwargs in ({'volume':'-1'},{'density':'0'},{'temp':'2000'}):
            self.assertFalse(calculate(tank(**kwargs))['valid'])

    def test_locales(self):
        self.assertEqual(number('1.234,56','test'),number('1,234.56','test'))
        self.assertEqual(calculate(tank(volume='1,25',temp='15',density='0,9'))['total_mt'],'1.13')

    def test_capacity_overflow_rejected(self):
        self.assertFalse(calculate(tank(index=21))['valid'])

    def test_temperature_below_fifteen(self):
        self.assertEqual(calculate(tank(temp='5'))['total_mt'],'95.63')

    def test_sum_rounded_tanks_not_round_raw_sum(self):
        payload={**tank(index=1,volume='1.25',temp='15',density='.9'),
                 **tank(index=2,volume='1.25',temp='15',density='.9')}
        self.assertEqual(calculate(payload)['total_mt'],'2.26')

    def test_united_harmony_reference_all_tanks_and_dlosp(self):
        # User-supplied MV UNITED HARMONY BUNKER SURVEY...xlsx, SHA256:
        # 71c4ad0c5d3fdcbc b89e23a002cbadc8 c1abb101da9e7546 e35179f9e5ccf3e1
        payload={}
        data={'vlsfo':[(285.502,30,.9686),(147.4,30,.9686),(248,30,.8909),
                       (5.59,30,.9248),(4.12,30,.9339),(7.09,55,.9339),(8.5,95,.9339)],
              'mgo':[(15.86,30,.8482),(86.48,30,.8639),(51.45,30,.8639),(5.5,35,.8562),(4.5,35,.8562)]}
        expected={'vlsfo':['273.84','141.38','218.60','5.12','3.81','6.44','7.51'],
                  'mgo':['13.30','73.89','43.96','4.64','3.80']}
        for fuel,rows in data.items():
            for i,(vol,temp,den) in enumerate(rows,1):payload.update(tank(fuel,i,str(vol),str(temp),str(den)))
        payload.update(bunker_figure_2_lsmgo='0',bunker_figure_3_lsmgo='0.05')
        result=calculate(payload)
        for fuel in data:self.assertEqual([r['weight_mt'] for r in result['tanks'] if r['fuel']==fuel],expected[fuel])
        self.assertEqual(result['totals'],{'vlsfo':'656.70','mgo':'139.59'})
        self.assertEqual(result['total_mt'],'796.29')
        self.assertEqual(result['dlosp'],{'vlsfo':None,'mgo':'139.64'})
        payload['bunker_figure_3_lsmgo']='-0.05'
        self.assertEqual(calculate(payload)['dlosp']['mgo'],'139.54')


if __name__=='__main__':unittest.main()
