"""Read-only operational queues across service-report headers and legacy Draft sections."""
from collections import defaultdict
import re

from psycopg2 import sql

from services.tenanting import DEFAULT_COMPANY_CODE


# User-requested dashboard exclusions (2026-10-09), scoped to existing services.
# Do not match vessel names: future operations must remain billable.
BILLING_QUEUE_EXCLUSIONS = frozenset({("MSL-CR", "5"), ("MSL-CR", "321")})


# Draft sections share a document number; header order establishes status precedence.
REPORT_SOURCES = {
    "container_reports": ("Contenedores", ("report_no", "linked_report_number")),
    "vessel_grain_sampling_reports": ("Grain Sampling", ("cert_no",)),
    "vessel_truck_supervision_reports": ("Truck Supervision", ("cert_no",)),
    "general_draft_survey": ("Draft Survey", ("draft_report_number",)),
    "draft_survey": ("Draft Survey", ("draft_report_number",)),
    "draft_survey_word_report": ("Draft Survey", ("draft_report_number",)),
    "draft_survey_ballast": ("Draft Survey", ("draft_report_number",)),
    "vessel_bunker_reports": ("Bunker Survey", ("bunker_cert_no",)),
    "vessel_cargo_condition_surveys": ("Cargo Condition", ("report_number",)),
    "vessel_crane_inspection_reports": ("Crane Inspection", ("report_number",)),
    "vessel_condition_surveys": ("Condition Survey", ("report_number",)),
    "port_captancy_reports": ("Port Captancy", ("report_number",)),
    "weight_certificates": ("Weight Certificate", ("report_number",)),
    "vessel_holds_inspection_certificates": ("Holds Inspection", ("report_number",)),
    "sampling_certificates": ("Sampling Certificate", ("report_no", "report_number", "certificate_no")),
    "sealing_certificates": ("Sealing Certificate", ("report_no", "report_number", "certificate_no")),
    "lashing_certificates": ("Lashing Certificate", ("report_no",)),
    "logra_reports": ("Cuestionarios ONG", ()),
    "tally_projects": ("Tally Control", ()),
}


def normalized(value):
    return re.sub(r"\s+", "", str(value or "")).upper()


def empty_reference(value):
    return normalized(value) in {"", "NONE", "NULL", "N/A"}


def classify_queues(services, reports, *, company=None):
    queues = {key: [] for key in ("billing", "missing", "approval", "rework", "unlinked")}
    by_number, by_service = defaultdict(list), defaultdict(list)
    for service in services:
        if not empty_reference(service.get("num_informe")):
            by_number[normalized(service["num_informe"])].append(service)
        by_service[str(service["consec"])].append(service)
    linked_services = set()
    seen_drafts = set()
    for report in reports:
        # general_draft_survey is authoritative when both legacy headers exist.
        draft_key = normalized(report.get("numero"))
        if report["tipo_informe"] == "Draft Survey" and draft_key:
            if draft_key in seen_drafts:
                continue
            seen_drafts.add(draft_key)
        matches = {}
        for number in report.get("numbers", []):
            for service in by_number.get(normalized(number), []):
                matches[service["consec"]] = service
        for service in by_service.get(str(report.get("service_id")), []):
            matches[service["consec"]] = service
        linked_services.update(matches)
        status = normalized(report.get("estado_informe"))
        if status in {"APPROVED", "APROBADO", "APROBADA", "CANCELLED", "CANCELED", "CANCELADO", "ANULADO"}:
            continue
        public = {k: v for k, v in report.items() if k != "numbers"}
        if not matches:
            queues["unlinked"].append(public)
            continue
        if not report.get("has_approval"):
            continue
        key = "rework" if status in {"DRAFT", "BORRADOR", "REJECTED", "RECHAZADO", "RECHAZADA"} else "approval"
        # One row per document, with all service IDs, so aliases never inflate counts.
        first = next(iter(matches.values()))
        queues[key].append({**first, **public, "servicios": ", ".join(str(n) for n in matches)})
    for service in services:
        if str(service.get("estado") or "").strip().lower() != "finalizado":
            continue
        if empty_reference(service.get("factura")) and (company, str(service["consec"])) not in BILLING_QUEUE_EXCLUSIONS:
            queues["billing"].append(service)
        if service["consec"] not in linked_services:
            queues["missing"].append(service)
    return queues


def load_pending(cur, company, *, billing=True, reports=True):
    cur.execute("""SELECT consec, num_informe, cliente, buque_contenedor, tipo,
                   operacion, puerto, fecha_inicio, fecha_fin, estado, factura
                   FROM servicios
                   WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), %s) = %s
                     AND LOWER(TRIM(COALESCE(estado, ''))) NOT IN ('cancelado', 'anulado')
                   ORDER BY fecha_fin ASC NULLS LAST, consec ASC""", (DEFAULT_COMPANY_CODE, company))
    services = [dict(row) for row in cur.fetchall()]
    documents, sources = [], []
    if reports:
        cur.execute("""SELECT table_name, column_name FROM information_schema.columns
                       WHERE table_schema='public' AND table_name=ANY(%s)""", (list(REPORT_SOURCES),))
        schema = defaultdict(set)
        for row in cur.fetchall():
            schema[row["table_name"]].add(row["column_name"])
        for table, (label, candidates) in REPORT_SOURCES.items():
            columns = schema.get(table)
            if not columns:
                continue
            # Legacy report tables without tenant metadata belong only to MSL.
            if "company_code" not in columns and company != DEFAULT_COMPANY_CODE:
                continue
            number_cols = [c for c in candidates if c in columns]
            wanted = [c for c in ("id", "status", "service_id", "title", "name") if c in columns]
            wanted += number_cols
            if not wanted:
                raise ValueError(f"No se pudo identificar el encabezado de {label}")
            query = sql.SQL("SELECT {} FROM public.{}").format(
                sql.SQL(", ").join(map(sql.Identifier, wanted)), sql.Identifier(table))
            params = ()
            if "company_code" in columns:
                query += sql.SQL(" WHERE COALESCE(NULLIF(TRIM(company_code::text), ''), %s) = %s")
                params = (DEFAULT_COMPANY_CODE, company)
            cur.execute(query, params)
            sources.append(label)
            for row in cur.fetchall():
                numbers = [row[c] for c in number_cols if not empty_reference(row[c])]
                documents.append({"tipo_informe": label, "origen": table,
                    "informe_id": row.get("id"), "numero": str(numbers[0]) if numbers else "",
                    "numbers": numbers, "service_id": row.get("service_id"),
                    "titulo": row.get("title") or row.get("name") or "",
                    "estado_informe": row.get("status") or "Sin estado",
                    "has_approval": "status" in columns})
    queues = classify_queues(services, documents, company=company)
    allowed = (["billing"] if billing else []) + (["missing", "approval", "rework", "unlinked"] if reports else [])
    return {"queues": {key: {"count": len(queues[key]), "rows": queues[key]} for key in allowed},
            "sources": sorted(set(sources)), "company": company}
