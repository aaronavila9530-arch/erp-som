import sys
import unittest
from unittest.mock import MagicMock, patch
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
    def test_msl_requested_billing_exclusions_leave_services_and_reports_unchanged(self):
        rows = [service(5, buque_contenedor="MV ENISHI"), service(321, buque_contenedor="MV THORCO LIVA"),
                service(999, buque_contenedor="MV ENISHI")]
        result = classify_queues(rows, [], company="MSL-CR")
        self.assertEqual([r["consec"] for r in result["billing"]], [999])
        self.assertEqual(len(result["missing"]), 3)
        self.assertTrue(all(r["factura"] is None and r["estado"] == "Finalizado" for r in rows))
        other = classify_queues(rows, [], company="MCI-CR")
        self.assertEqual(len(other["billing"]), 3)

    def test_billing_exclusions_accept_database_or_api_identifiers(self):
        result = classify_queues([service("5"), service("321")], [], company="MSL-CR")
        self.assertEqual(result["billing"], [])

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


class EndpointTests(unittest.TestCase):
    def test_local_queue_icons_and_path_allowlist(self):
        from routers import som_web
        from fastapi import HTTPException
        import xml.etree.ElementTree as ET
        for name in ("receipt-text", "file-pen-line", "badge-check", "pencil-line", "unlink"):
            response = som_web.som_web_queue_icon(name + ".svg")
            self.assertEqual(response.media_type, "image/svg+xml")
            root = ET.parse(response.path).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertTrue(all(node.tag.split("}")[-1] in {"svg", "path", "line", "rect", "circle", "polyline"} for node in root.iter()))
        with self.assertRaises(HTTPException) as error:
            som_web.som_web_queue_icon("../som_web.py")
        self.assertEqual(error.exception.status_code, 404)

    def call_endpoint(self, modules, result=None, error=None):
        from routers import som_web
        conn = MagicMock()
        with patch.object(som_web.database, "get_conn", return_value=conn), \
             patch.object(som_web.database, "release_conn"), \
             patch.object(som_web, "_safe_action_scalar", return_value=0), \
             patch.object(som_web, "load_pending", return_value=result, side_effect=error) as load:
            payload = som_web.som_web_action_center(anio=2026, x_company_code="MCI-CR",
                x_role="user", x_modules=modules, x_permissions="")
        return payload, load, conn

    def test_no_finance_or_reports_permission_does_not_read_queues(self):
        payload, load, _ = self.call_endpoint("servicios")
        load.assert_not_called()
        self.assertEqual(payload["operational"]["queues"], {})

    def test_report_permission_does_not_return_billing_queue(self):
        expected = {"queues": {"missing": {"count": 1, "rows": [service()]}}, "company": "MCI-CR"}
        payload, load, _ = self.call_endpoint("informes", result=expected)
        self.assertEqual(load.call_args.kwargs, {"billing": False, "reports": True})
        self.assertEqual(load.call_args.args[1], "MCI-CR")
        self.assertEqual(payload["operational"], expected)

    def test_database_failure_is_error_not_zero_pending(self):
        with self.assertLogs("routers.som_web", level="ERROR"):
            payload, _, conn = self.call_endpoint("informes", error=RuntimeError("unavailable"))
        self.assertIn("error", payload["operational"])
        conn.cursor.return_value.execute.assert_any_call("ROLLBACK TO SAVEPOINT home_pending")


if __name__ == "__main__":
    unittest.main()
