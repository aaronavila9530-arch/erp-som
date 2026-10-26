import unittest

from pydantic import ValidationError
from backend_api.services.mci_survey_schema import SurveyContent, SurveySave, export_sections


class SurveySchemaTests(unittest.TestCase):
    def test_only_three_kinds(self):
        for kind in ("vessel", "condition", "cargo"):
            self.assertEqual(SurveySave(kind=kind, service_id=1, content={}).kind, kind)
        with self.assertRaises(ValidationError):
            SurveySave(kind="draft", service_id=1, content={})

    def test_identity_cannot_be_supplied(self):
        for field in ("company_code", "vessel", "requested_by", "report_number", "status"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                SurveySave(kind="cargo", service_id=1, content={}, **{field: "untrusted"})

    def test_disabled_text_preserved_but_not_exported(self):
        content = SurveyContent(sections={
            "work": {"enabled": False, "blocks": [{"text": "Retained"}]},
            "conclusion": {"enabled": True, "blocks": [{"text": "Observed"}, {"text": " "}]},
        })
        self.assertEqual(content.sections["work"].blocks[0].text, "Retained")
        self.assertEqual([s[0] for s in export_sections(content)], ["conclusion"])
        self.assertEqual(export_sections(content)[0][2], ["Observed"])

    def test_template_order(self):
        content = SurveyContent(sections={key: {"enabled": True} for key in ("enclosure", "work", "instructions")})
        self.assertEqual([s[0] for s in export_sections(content)], ["instructions", "work", "enclosure"])

    def test_invalid_period_and_inputs(self):
        cases = [
            {"period_start": "2026-10-23T10:00", "period_end": "2026-10-22T10:00"},
            {"period_start": "2026-10-23T10:00Z", "period_end": "2026-10-23T11:00"},
            {"issue_date": "2026-02-30"}, {"sections": {"arbitrary": {}}},
            {"cargo": "bad\x00value"},
            {"sections": {"work": {"blocks": [{"text": "x"}] * 101}}},
        ]
        for content in cases:
            with self.subTest(content=content), self.assertRaises(ValidationError):
                SurveyContent(**content)

    def test_parent_gates_children_without_erasing_text(self):
        content = SurveyContent(hierarchy_version=2, sections={
            'instructions': {'enabled': False},
            'work': {'enabled': True, 'blocks': [{'text':'Keep this'}]},
            'findings': {'enabled': True},
            'provided': {'enabled': True, 'blocks': [{'text':'Document A'}]},
        })
        self.assertEqual([s[0] for s in export_sections(content)], ['findings','provided'])
        self.assertEqual(content.sections['work'].blocks[0].text, 'Keep this')
        content.sections['instructions'].enabled = True
        self.assertEqual([s[0] for s in export_sections(content)], ['instructions','work','findings','provided'])

    def test_legacy_flat_reports_keep_visible_children(self):
        content = SurveyContent(sections={'visual': {'enabled': True}})
        self.assertEqual([s[0] for s in export_sections(content)], ['findings','visual'])


if __name__ == "__main__":
    unittest.main()
