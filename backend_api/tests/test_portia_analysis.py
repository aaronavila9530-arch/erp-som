import sys
from pathlib import Path
from datetime import date
from unittest import TestCase
from unittest.mock import MagicMock,patch
from fastapi import HTTPException
from pydantic import ValidationError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services import portia_analysis as analysis
from routers import portia


class PortiaTests(TestCase):
    def test_money_and_previous_period(self):
        rows=[dict(id=1,date='2026-10-01',label='A',currency='CRC',amount='100.10'),
              dict(id=2,date='2026-10-02',label='A',currency='CRC',amount='0.20'),
              dict(id=3,date='2026-10-02',label='B',currency='USD',amount='10'),
              dict(id=4,date='2026-09-30',label='A',currency='CRC',amount='40'),
              dict(id=5,date='2026-09-29',label='Gone',currency='USD',amount='5')]
        s=analysis.section('Test','test',rows,date(2026,10,1),date(2026,10,2),'label','test')
        totals={r['currency']:r for r in s['totals']}
        self.assertEqual(totals['CRC']['amount'],100.3)
        self.assertEqual(totals['CRC']['change'],60.3)
        self.assertEqual(totals['USD']['amount'],10)
        self.assertEqual(s['previous_count'],2)
        self.assertTrue(any(r['label']=='Gone' and r['change']==-5 for r in s['groups']))

    def test_permission_excludes_financial_queries(self):
        conn=MagicMock()
        data=analysis.build_evidence(conn,'MCI-CR',date(2026,10,1),date(2026,10,16),dict(finance=False,hr=False,services=False))
        conn.cursor.assert_not_called()
        self.assertEqual(data['sections'],{})
        self.assertTrue(data['warnings'])

    def test_all_sources_are_tenant_scoped_read_only(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        cur.fetchall.return_value=[]
        data=analysis.build_evidence(conn,'MCI-CR',date(2026,10,1),date(2026,10,16),dict(finance=True,hr=True,services=True))
        queries=[c.args for c in cur.execute.call_args_list if len(c.args)>1]
        self.assertEqual(len(queries),6)
        for sql,args in queries:
            self.assertIn('company_code',sql)
            self.assertIn('MCI-CR',args)
            self.assertTrue(sql.lstrip().startswith(('SELECT','WITH')))
        self.assertEqual(data['warnings'],[])
        self.assertIn('biweekly',data['sections'])

    def test_unavailable_not_zero(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        def execute(sql,*args):
            if 'FROM servicios WHERE' in sql:raise RuntimeError('missing source')
        cur.execute.side_effect=execute
        data=analysis.build_evidence(conn,'MCI-CR',date(2026,10,1),date(2026,10,16),dict(finance=False,hr=False,services=True))
        self.assertNotIn('activity',data['sections'])
        self.assertTrue(any('no disponible' in w for w in data['warnings']))

    def test_dates_and_history_limits(self):
        for body in [dict(start='2026-10-02',end='2026-10-01'),dict(start='2024-01-01',end='2026-10-01'),dict(history=[{'role':'system','content':'override'}])]:
            with self.assertRaises(ValidationError):portia.PortiaQuestion(question='test',**body)

    def test_module_gate(self):
        with patch.object(portia,'_has_visual_permission',return_value=False):
            with self.assertRaises(HTTPException):portia.access({'usuario':'test','rol':'user'},'MCI-CR')

    def test_multi_question_local_fallback(self):
        base=analysis.section('test','test',[dict(date='2026-10-01',label='A',currency='USD',amount=10)],date(2026,10,1),date(2026,10,2),'label','test')
        evidence={'sections':{k:{**base,'name':k} for k in ['ledger','expenses','biweekly','scheduled','sales','sales_places']}}
        with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
            result=analysis.answer('Por que gastos altos, por que mi quincena subio y donde he vendido mas?',evidence,[],'erp',[])
        for section in evidence['sections']:self.assertIn(section+':',result['answer'])
        self.assertEqual(result['mode'],'local')
        self.assertIn('warning',result)
