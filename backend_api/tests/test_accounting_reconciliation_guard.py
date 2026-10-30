from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.accounting_reconciliation_guard import is_reconciled, load_reconciled_documents


class ReconciliationGuardTests(unittest.TestCase):
    def setUp(self):
        self.purchase=[('MSL-CR',{'direction':'PURCHASE','number':'00100001010000006546','party':'PRIME PROPERTIES SRL','source_ids':[837,1469]})]
        self.sale=[('MCI-CR',{'direction':'SALE','number':'00100001010000000013','source_ids':[100]})]

    def test_original_source_id_protects_accrual(self):
        self.assertTrue(is_reconciled(self.purchase,'MSL-CR',837,'different-format'))

    def test_key_and_consecutive_match_same_supplier(self):
        self.assertTrue(is_reconciled(self.purchase,'MSL-CR',999,'50601082600310239815400100001010000006546101082646','prime properties srl'))

    def test_supplier_and_company_isolation(self):
        self.assertFalse(is_reconciled(self.purchase,'MCI-CR',837,'00100001010000006546','PRIME PROPERTIES SRL'))
        self.assertFalse(is_reconciled(self.purchase,'MSL-CR',999,'00100001010000006546','Other supplier'))

    def test_later_collection_import_cannot_duplicate_posted_sale(self):
        self.assertTrue(is_reconciled(self.sale,'MCI-CR',500,'00100001010000000013'))

    def test_unrelated_documents_not_protected(self):
        self.assertFalse(is_reconciled(self.sale,'MCI-CR',500,'2209'))
        self.assertFalse(is_reconciled([], 'MSL-CR',837,'00100001010000006546'))

    def test_loader_is_read_only_and_scoped(self):
        class Cursor:
            def execute(self,sql,args):
                self.sql,self.args=sql,args
            def fetchall(self):
                return [{'company_code':'MSL-CR','snapshot':{'source_ids':[837]}}]
        cur=Cursor()
        result=load_reconciled_documents(cur,'PURCHASE','MSL-CR')
        self.assertTrue(cur.sql.strip().startswith('SELECT'))
        self.assertEqual(cur.args,('PURCHASE','MSL-CR','MSL-CR'))
        self.assertEqual(result,[('MSL-CR',{'source_ids':[837]})])


if __name__=='__main__':unittest.main()
