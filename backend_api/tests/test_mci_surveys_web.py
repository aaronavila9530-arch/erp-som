import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock
from fastapi import HTTPException

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from routers.mci_surveys_web import mci_access, persist
from services.mci_survey_schema import SurveySave
from routers.container_web import version


class MCISurveyTests(unittest.TestCase):
    def test_tenant_boundary(self):
        with self.assertRaises(HTTPException):mci_access({'company':'MSL-CR'})
        self.assertEqual(mci_access({'company':'MCI-CR'})['company'],'MCI-CR')

    def test_identity_derived_from_service(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
        cur.fetchone.side_effect=[{'num_informe':'QA-1','buque_contenedor':'MV QA','cliente':'CLIENT','puerto':'Caldera','pais':'Costa Rica'},
                                 {'id':1,'updated_at':'now','content':{}}]
        ctx={'permissions':{'create':True}}
        persist(SurveySave(kind='cargo',service_id=1,content={'location':'Wrong location'}),ctx,conn)
        sql,params=cur.execute.call_args_list[-1].args
        self.assertIn('INSERT INTO mci_generic_surveys',sql)
        self.assertEqual(params[2:5],('QA-1','MV QA','CLIENT'))
        self.assertEqual(params[5].adapted['location'], 'Caldera, Costa Rica')
        conn.commit.assert_called_once()

    def test_wrong_company_service_cannot_create(self):
        conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value;cur.fetchone.return_value=None
        with self.assertRaises(HTTPException) as e:
            persist(SurveySave(kind='cargo',service_id=1,content={}),{'permissions':{'create':True}},conn)
        self.assertEqual(e.exception.status_code,404);conn.commit.assert_not_called();conn.rollback.assert_called_once()
        self.assertIn("company_code='MCI-CR'",cur.execute.call_args.args[0])

    def test_conflicts_and_approved_records(self):
        row={'id':1,'updated_at':'now','status':'Approved','service_id':1,'kind':'cargo'}
        for token in ('stale',version(row)):
            conn=MagicMock();conn.cursor.return_value.__enter__.return_value.fetchone.return_value=row
            with self.assertRaises(HTTPException) as e:
                persist(SurveySave(kind='cargo',service_id=1,content={},version=token),{'permissions':{'edit':True}},conn,1)
            self.assertEqual(e.exception.status_code,409);conn.commit.assert_not_called()


if __name__=='__main__':unittest.main()
