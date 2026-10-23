import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from routers.certificates_web import specification, clean_fields
from services.vessel_web_fields import VESSEL_TYPES


class VesselWebTests(unittest.TestCase):
    def test_company_boundary(self):
        for kind in VESSEL_TYPES:
            for company in ("MCI-CR", "OTHER"):
                with self.assertRaises(HTTPException):
                    specification(kind, {"company": company})
            self.assertEqual(specification(kind, {"company": "MSL-CR"}), VESSEL_TYPES[kind])

    def test_desktop_limits_and_different_field_names(self):
        cargo = VESSEL_TYPES["cargo_condition"]["fields"]
        vessel = VESSEL_TYPES["condition"]["fields"]
        self.assertIn("findings_10", cargo)
        self.assertNotIn("findings_11", cargo)
        self.assertIn("survey_findings_20", vessel)
        self.assertNotIn("survey_findings_21", vessel)
        self.assertIn("time_0_date", cargo)
        self.assertIn("ts_8_minute", vessel)

    def test_time_validation(self):
        spec = VESSEL_TYPES["condition"]
        self.assertEqual(clean_fields(spec, {"ts_1_hour": "9", "ts_1_minute": "1"}),
                         {"ts_1_hour": "09", "ts_1_minute": "01"})
        for key, value in (("ts_1_hour", "24"), ("ts_1_minute", "60"), ("ts_1_hour", "noon")):
            with self.assertRaises(HTTPException):
                clean_fields(spec, {key: value})

    def test_unknown_fields_rejected(self):
        with self.assertRaises(HTTPException):
            clean_fields(VESSEL_TYPES["condition"], {"company_code": "MCI-CR"})


if __name__ == "__main__":
    unittest.main()
