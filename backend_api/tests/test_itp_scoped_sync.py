from pathlib import Path
import sys, unittest
from datetime import date
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services import accounting_auto as accounting
from routers import invoice_to_pay as itp
from fastapi import HTTPException

class ScopedSyncTests(unittest.TestCase):
    def test_scoped_sync_does_not_reclassify_or_backfill_unrelated_records(self):
        conn=MagicMock();cur=conn.cursor.return_value
        cur.fetchone.return_value={"rate":500,"rate_date":date(2026,10,20),"source":"test"}
        cur.fetchall.return_value=[]
        with patch.object(accounting,"employee_obligation_ids",return_value=[12,99]), \
             patch.object(accounting,"load_employee_name_keys",return_value=set()), \
             patch.object(accounting,"backfill_missing_bank_accounts") as backfill, \
             patch.object(accounting,"_apply_current_fiscal_classification") as fiscal:
            accounting.sync_itp_to_accounting(conn,"MCI-CR",[12,13])
        backfill.assert_not_called();fiscal.assert_not_called()
        queries=cur.execute.call_args_list
        obligation_query=next(c for c in queries if "p.active = TRUE" in c.args[0])
        self.assertIn("p.id = ANY(%s)",obligation_query.args[0])
        self.assertIn("p.company_code = %s",obligation_query.args[0])
        self.assertEqual(obligation_query.args[1],[[12,13],"MCI-CR"])
        for call in queries:
            if "DELETE FROM" in call.args[0]:
                self.assertIn("ANY(%s)",call.args[0])
                self.assertNotIn("99",str(call.args[1]))
        conn.commit.assert_called_once()

    def test_hazel_is_not_allowed_for_new_payments(self):
        conn=MagicMock()
        with self.assertRaises(HTTPException) as err:
            itp.apply_payment(1,10,date(2026,10,20),bank_account_code="",bank_account_name="",
                bank_name="",payment_reference="test",payment_method="THIRD_PARTY_HAZEL",
                payment_card_last4="",conn=conn,x_user="test",x_role="admin",x_user_role="admin")
        self.assertEqual(err.exception.status_code,422)
        conn.commit.assert_not_called()
        conn.cursor.return_value.execute.assert_not_called()

    def test_default_sync_retains_existing_full_sync_behavior(self):
        conn=MagicMock();cur=conn.cursor.return_value
        cur.fetchone.return_value={"rate":500,"rate_date":date(2026,10,20),"source":"test"}
        cur.fetchall.return_value=[]
        with patch.object(accounting,"employee_obligation_ids",return_value=[]), \
             patch.object(accounting,"load_employee_name_keys",return_value=set()), \
             patch.object(accounting,"backfill_missing_bank_accounts") as backfill, \
             patch.object(accounting,"_apply_current_fiscal_classification") as fiscal:
            accounting.sync_itp_to_accounting(conn)
        backfill.assert_called_once_with(cur)
        fiscal.assert_called_once_with(conn)
        query=next(c for c in cur.execute.call_args_list if "p.active = TRUE" in c.args[0])
        self.assertNotIn("p.id = ANY",query.args[0])

    def test_hazel_account_cannot_be_disguised_as_bank(self):
        conn=MagicMock()
        with self.assertRaises(HTTPException) as err:
            itp.apply_payment(1,10,date(2026,10,20),bank_account_code="3.1.99",bank_account_name="",
                bank_name="",payment_reference="test",payment_method="BANK",
                payment_card_last4="",conn=conn,x_user="test",x_role="admin",x_user_role="admin")
        self.assertEqual(err.exception.status_code,422)
        conn.cursor.return_value.execute.assert_not_called()

if __name__=="__main__":unittest.main()
