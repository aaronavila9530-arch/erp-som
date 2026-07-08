from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend_api"))

import database  # noqa: E402


def main() -> None:
    conn = database.connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, title, jsonb_array_length(COALESCE(agenda_items, '[]'::jsonb))
            FROM logra_reports
            WHERE category = 'ONG'
              AND title = 'ONG - Agenda'
            ORDER BY id ASC
            LIMIT 1
            """
        )
        agenda = cur.fetchone()
        if not agenda:
            raise SystemExit("No existe el reporte tecnico ONG - Agenda; no se limpia nada.")

        cur.execute(
            """
            UPDATE logra_reports
            SET agenda_items = '[]'::jsonb,
                agenda_notes = '',
                updated_at = NOW()
            WHERE category = 'ONG'
              AND COALESCE(title, '') <> 'ONG - Agenda'
              AND jsonb_array_length(COALESCE(agenda_items, '[]'::jsonb)) > 0
            RETURNING id, title
            """
        )
        cleaned = cur.fetchall()
        conn.commit()
        print({
            "agenda_report_id": agenda[0],
            "agenda_items_kept": agenda[2],
            "questionnaire_reports_cleaned": cleaned,
        })
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
