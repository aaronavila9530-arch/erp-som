import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.home_pending import REPORT_SOURCES, classify_queues, load_pending


def service(n=1, **changes):
    return {"consec": n, "estado": "Finalizado", "factura": None,
            "num_informe": f"REP-{n}", "fecha_fin": "2024-01-01", **changes}


def report(n=1, **changes):
    return {"tipo_informe": "Bunker Survey", "informe_id": n, "numero": f"REP-{n}",
            "numbers": [f"REP-{n}"], "estado_informe": "Pending for review",
            "has_approval": True, **changes}


class PendingTests(unittest.TestCase):
    def test_billing_uses_empty_invoice_not_value_or_year(self):
        rows = [service(1, valor_factura=500), service(2, factura="  "),
                service(3, factura="2209", valor_factura=0), service(4, estado="Activo")]
        result = classify_queues(rows, [])
        self.assertEqual([r["consec"] for r in result["billing"]], [1, 2])

    def test_assigned_number_is_not_a_created_report(self):
        result = classify_queues([service(), service(2, num_informe=None)], [])
        self.assertEqual(len(result["missing"]), 2)

    def test_all_operational_report_types(self):
        for table, (label, columns) in REPORT_SOURCES.items():
            if not columns:
                continue
            with self.subTest(table=table):
                result = classify_queues([service()], [report(tipo_informe=label)])
                self.assertEqual(len(result["missing"]), 0)
                self.assertEqual(len(result["approval"]), 1)

    def test_approved_report_ignores_stale_service_status(self):
        result = classify_queues([service(status_informe="Pending")], [report(estado_informe="Approved")])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["approval"], [])

    def test_one_approved_type_does_not_hide_another_pending_type(self):
        result = classify_queues([service()], [report(estado_informe="Approved"), report(tipo_informe="Weight Certificate")])
        self.assertEqual(len(result["approval"]), 1)

    def test_aliases_normalization_and_multiple_services_do_not_duplicate_report(self):
        result = classify_queues([service(), service(2)], [report(numbers=[" rep - 1 ", "REP-2"])])
        self.assertEqual(len(result["approval"]), 1)
        self.assertEqual(result["approval"][0]["servicios"], "1, 2")
        self.assertEqual(result["missing"], [])

    def test_draft_headers_deduplicated_authoritative_status(self):
        result = classify_queues([service()], [report(tipo_informe="Draft Survey", estado_informe="Approved"),
                                              report(tipo_informe="Draft Survey")])
        self.assertEqual(result["approval"], [])

    def test_rejected_drafts_and_unlinked_remain_visible(self):
        result = classify_queues([service(), service(2)], [report(estado_informe="Rejected"),
                report(2, estado_informe="draft"), report(3)])
        self.assertEqual(len(result["rework"]), 2)
        self.assertEqual(len(result["unlinked"]), 1)

    def test_tally_link_has_no_fictitious_approval_workflow(self):
        result = classify_queues([service()], [report(tipo_informe="Tally Control", numbers=[], service_id=1, has_approval=False)])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["approval"], [])

    def test_no_limit_on_services(self):
        result = classify_queues([service(n) for n in range(1205)], [])
        self.assertEqual(len(result["billing"]), 1205)
        self.assertEqual(len(result["missing"]), 1205)

    def test_schema_queries_tenant_and_permission_scope(self):
        class Cursor:
            def __init__(self):
                self.calls = []
                self.rows = []

            def execute(self, query, params=()):
                self.calls.append((str(query), params))
                if "information_schema" in str(query):
                    self.rows = [{"table_name": "container_reports", "column_name": c}
                                 for c in ("id", "report_no", "status", "company_code")]
                    self.rows += [{"table_name": "weight_certificates", "column_name": c}
                                  for c in ("id", "report_number", "status")]
                else:
                    self.rows = []

            def fetchall(self):
                return self.rows

        cur = Cursor()
        result = load_pending(cur, "MCI-CR", billing=False)
        self.assertNotIn("billing", result["queues"])
        self.assertNotIn("Weight Certificate", result["sources"])
        self.assertEqual(cur.calls[0][1], ("MSL-CR", "MCI-CR"))
        self.assertEqual(cur.calls[-1][1], ("MSL-CR", "MCI-CR"))
        cur = Cursor()
        result = load_pending(cur, "MSL-CR", reports=False)
        self.assertEqual(set(result["queues"]), {"billing"})
        self.assertEqual(len(cur.calls), 1)


if __name__ == "__main__":
    unittest.main()
