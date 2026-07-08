from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend_api"))

import database  # noqa: E402


def agenda_key(item: dict) -> str:
    values = [
        item.get("date_iso") or item.get("date") or "",
        item.get("start_time") or "",
        item.get("end_time") or "",
        item.get("place") or "",
        item.get("person") or "",
        item.get("phone") or item.get("telefono") or "",
        item.get("company") or item.get("company_role") or "",
        item.get("topic") or "",
    ]
    return "|".join(str(value).strip().lower() for value in values)


def main() -> None:
    conn = database.connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, status, agenda_items, updated_at
            FROM logra_reports
            WHERE category = 'ONG'
              AND jsonb_array_length(COALESCE(agenda_items, '[]'::jsonb)) > 0
            ORDER BY updated_at DESC, id DESC
            """
        )
        rows = cur.fetchall()
        summary = []
        all_keys = []
        for report_id, title, status, agenda_items, updated_at in rows:
            items = agenda_items if isinstance(agenda_items, list) else []
            keys = [agenda_key(item) for item in items if isinstance(item, dict)]
            all_keys.extend(keys)
            summary.append(
                {
                    "id": report_id,
                    "title": title,
                    "status": status,
                    "items": len(items),
                    "unique_inside_report": len(set(keys)),
                    "updated_at": str(updated_at),
                }
            )
        counts = Counter(all_keys)
        duplicate_keys = sum(1 for count in counts.values() if count > 1)
        duplicate_items = sum(count - 1 for count in counts.values() if count > 1)
        print(json.dumps({
            "reports_with_agenda": summary,
            "total_items": len(all_keys),
            "unique_items": len(counts),
            "duplicate_keys": duplicate_keys,
            "duplicate_items": duplicate_items,
        }, ensure_ascii=False, indent=2))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
