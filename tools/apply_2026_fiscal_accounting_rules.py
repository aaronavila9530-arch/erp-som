from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend_api"
sys.path.insert(0, str(BACKEND))

import database  # noqa: E402
from services.accounting_fiscal_rules import apply_fiscal_classification, ensure_accounting_fiscal_schema  # noqa: E402


YEAR = 2026
REPORT_DIR = ROOT / "reports" / "migrations"


def _json_value(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def fetch_summary(cur):
    cur.execute("""
        SELECT fiscal_rule_code,
               fiscal_support_status,
               fiscal_tax_form,
               fiscal_risk_level,
               fiscal_deductible,
               fiscal_iva_creditable,
               COUNT(*) AS lines,
               ROUND(SUM(COALESCE(debit,0)),2) AS debit,
               ROUND(SUM(COALESCE(credit,0)),2) AS credit
        FROM accounting_lines l
        JOIN accounting_entries e ON e.id = l.entry_id
        WHERE e.entry_date >= %s
          AND e.entry_date < %s
        GROUP BY fiscal_rule_code, fiscal_support_status, fiscal_tax_form,
                 fiscal_risk_level, fiscal_deductible, fiscal_iva_creditable
        ORDER BY fiscal_rule_code, fiscal_support_status
    """, (date(YEAR, 1, 1), date(YEAR + 1, 1, 1)))
    return [{k: _json_value(v) for k, v in dict(row).items()} for row in (cur.fetchall() or [])]


def fetch_high_risk(cur):
    cur.execute("""
        SELECT e.id AS entry_id, e.entry_date, e.origin, e.origin_id,
               l.id AS line_id, l.account_code, l.account_name,
               l.debit, l.credit, l.line_description,
               l.fiscal_rule_code, l.fiscal_notes
        FROM accounting_lines l
        JOIN accounting_entries e ON e.id = l.entry_id
        WHERE e.entry_date >= %s
          AND e.entry_date < %s
          AND l.fiscal_risk_level IN ('HIGH', 'CRITICAL')
        ORDER BY e.entry_date, e.id, l.id
    """, (date(YEAR, 1, 1), date(YEAR + 1, 1, 1)))
    return [{k: _json_value(v) for k, v in dict(row).items()} for row in (cur.fetchall() or [])]


def fetch_support_required(cur):
    cur.execute("""
        SELECT fiscal_support_status,
               COUNT(*) AS lines,
               ROUND(SUM(COALESCE(debit,0)),2) AS debit,
               ROUND(SUM(COALESCE(credit,0)),2) AS credit
        FROM accounting_lines l
        JOIN accounting_entries e ON e.id = l.entry_id
        WHERE e.entry_date >= %s
          AND e.entry_date < %s
          AND l.fiscal_requires_support = TRUE
        GROUP BY fiscal_support_status
        ORDER BY fiscal_support_status
    """, (date(YEAR, 1, 1), date(YEAR + 1, 1, 1)))
    return [{k: _json_value(v) for k, v in dict(row).items()} for row in (cur.fetchall() or [])]


def preview_summary(changes):
    summary = {}
    for item in changes:
        key = (
            item["fiscal_rule_code"],
            item["fiscal_support_status"],
            item["fiscal_tax_form"],
            item["fiscal_risk_level"],
            str(item["fiscal_deductible"]),
            str(item["fiscal_iva_creditable"]),
        )
        summary[key] = summary.get(key, 0) + 1
    return [
        {
            "fiscal_rule_code": key[0],
            "fiscal_support_status": key[1],
            "fiscal_tax_form": key[2],
            "fiscal_risk_level": key[3],
            "fiscal_deductible": key[4],
            "fiscal_iva_creditable": key[5],
            "lines": count,
        }
        for key, count in sorted(summary.items())
    ]


def preview_support_required(changes):
    counter = Counter(item["fiscal_support_status"] for item in changes if item["fiscal_requires_support"])
    return [{"fiscal_support_status": key, "lines": value} for key, value in sorted(counter.items())]


def main():
    parser = argparse.ArgumentParser(description="Clasifica fiscalmente Accounting 2026.")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios. Sin esto hace preview y rollback.")
    args = parser.parse_args()

    conn = database.connect()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        ensure_accounting_fiscal_schema(cur)
        changes = apply_fiscal_classification(conn, year=YEAR, apply=args.apply)

        rule_counts = Counter(item["fiscal_rule_code"] for item in changes)
        tax_form_counts = Counter(item["fiscal_tax_form"] or "NO_FORM" for item in changes)
        support_counts = Counter(item["fiscal_support_status"] for item in changes)
        deductible_counts = Counter(str(item["fiscal_deductible"]) for item in changes)
        iva_counts = Counter(str(item["fiscal_iva_creditable"]) for item in changes)

        if args.apply:
            conn.commit()
            summary = fetch_summary(cur)
            support_required = fetch_support_required(cur)
            high_risk = fetch_high_risk(cur)
        else:
            conn.rollback()
            summary = preview_summary(changes)
            support_required = preview_support_required(changes)
            high_risk = []

        report = {
            "year": YEAR,
            "applied": args.apply,
            "line_count": len(changes),
            "rule_counts": dict(rule_counts),
            "tax_form_counts": dict(tax_form_counts),
            "support_counts": dict(support_counts),
            "deductible_counts": dict(deductible_counts),
            "iva_creditable_counts": dict(iva_counts),
            "summary": summary,
            "support_required_summary": support_required,
            "high_risk_lines": high_risk,
        }

        if not args.apply:
            conn.rollback()

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        suffix = "apply" if args.apply else "preview"
        report_path = REPORT_DIR / f"apply_2026_fiscal_accounting_rules_{suffix}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps({
            "applied": args.apply,
            "line_count": len(changes),
            "rules": dict(rule_counts),
            "report": str(report_path),
        }, indent=2, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
