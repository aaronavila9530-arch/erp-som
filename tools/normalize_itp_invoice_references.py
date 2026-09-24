from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend_api"))

import database  # noqa: E402


KEY_RE = re.compile(r"\d{50}")


def invoice_number(key: str) -> str:
    return key[21:41]


def replace_keys(text: str | None) -> tuple[str | None, int]:
    if text is None:
        return None, 0
    raw = str(text)
    count = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return invoice_number(match.group(0))

    return KEY_RE.sub(repl, raw), count


def first_key(value: str | None) -> str | None:
    match = KEY_RE.search(str(value or ""))
    return match.group(0) if match else None


def fetch_count(cur, sql: str, params: tuple = ()) -> int:
    cur.execute(sql, params)
    return int((cur.fetchone() or [0])[0] or 0)


def has_column(cur, table_name: str, column_name: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name=%s
          AND column_name=%s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return bool(cur.fetchone())


def preview(cur) -> dict:
    counts = {
        "payment_obligations_reference_keys": fetch_count(
            cur,
            "SELECT COUNT(*) FROM payment_obligations WHERE COALESCE(reference,'') ~ '\\d{50}'",
        ),
        "payment_obligations_notes_keys": fetch_count(
            cur,
            "SELECT COUNT(*) FROM payment_obligations WHERE COALESCE(notes,'') ~ '\\d{50}'",
        ),
        "accounting_entries_itp_keys": fetch_count(
            cur,
            """
            SELECT COUNT(*)
            FROM accounting_entries
            WHERE origin IN ('ITP','ITP_PAYMENT')
              AND COALESCE(description,'') ~ '\\d{50}'
            """,
        ),
        "accounting_lines_itp_keys": fetch_count(
            cur,
            """
            SELECT COUNT(*)
            FROM accounting_lines l
            JOIN accounting_entries e ON e.id = l.entry_id
            WHERE e.origin IN ('ITP','ITP_PAYMENT')
              AND COALESCE(l.line_description,'') ~ '\\d{50}'
            """,
        ),
        "tax_documents_missing_invoice_number": fetch_count(
            cur,
            """
            SELECT COUNT(*)
            FROM tax_electronic_documents
            WHERE COALESCE(document_number,'') = ''
              AND COALESCE(electronic_key,'') ~ '^\\d{50}$'
            """,
        ),
    }

    cur.execute(
        """
        SELECT id, payee_name, reference
        FROM payment_obligations
        WHERE COALESCE(reference,'') ~ '\\d{50}'
        ORDER BY id
        LIMIT 10
        """
    )
    samples = [
        {
            "id": row[0],
            "payee": row[1],
            "old_reference": row[2],
            "new_reference": invoice_number(first_key(row[2]) or ""),
        }
        for row in cur.fetchall()
    ]
    return {"counts": counts, "samples": samples}


def apply(cur) -> dict:
    changed = {
        "payment_obligations": 0,
        "payment_obligations_notes": 0,
        "itp_biweekly_lines": 0,
        "accounting_entries": 0,
        "accounting_lines": 0,
        "tax_documents": 0,
    }

    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS electronic_key TEXT")

    cur.execute(
        """
        SELECT id, reference, electronic_key, notes
        FROM payment_obligations
        WHERE COALESCE(reference,'') ~ '\\d{50}'
           OR COALESCE(notes,'') ~ '\\d{50}'
        ORDER BY id
        """
    )
    for row in cur.fetchall():
        obligation_id, reference, electronic_key, notes = row
        key = first_key(reference)
        new_reference = invoice_number(key) if key else reference
        new_notes, note_replacements = replace_keys(notes)
        new_electronic_key = electronic_key or key
        cur.execute(
            """
            UPDATE payment_obligations
               SET reference = %s,
                   electronic_key = %s,
                   notes = %s,
                   updated_at = NOW()
             WHERE id = %s
            """,
            (new_reference, new_electronic_key, new_notes, obligation_id),
        )
        if key:
            changed["payment_obligations"] += 1
        if note_replacements:
            changed["payment_obligations_notes"] += 1

    cur.execute("SELECT to_regclass('public.itp_biweekly_payment_lines')")
    if (cur.fetchone() or [None])[0]:
        cur.execute("ALTER TABLE itp_biweekly_payment_lines ADD COLUMN IF NOT EXISTS electronic_key TEXT")
        has_updated_at = has_column(cur, "itp_biweekly_payment_lines", "updated_at")
        cur.execute(
            """
            SELECT id, reference, electronic_key, notes
            FROM itp_biweekly_payment_lines
            WHERE COALESCE(reference,'') ~ '\\d{50}'
               OR COALESCE(notes,'') ~ '\\d{50}'
            ORDER BY id
            """
        )
        for row in cur.fetchall():
            line_id, reference, electronic_key, notes = row
            key = first_key(reference)
            new_reference = invoice_number(key) if key else reference
            new_notes, _ = replace_keys(notes)
            if has_updated_at:
                cur.execute(
                    """
                    UPDATE itp_biweekly_payment_lines
                       SET reference = %s,
                           electronic_key = %s,
                           notes = %s,
                           updated_at = NOW()
                     WHERE id = %s
                    """,
                    (new_reference, electronic_key or key, new_notes, line_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE itp_biweekly_payment_lines
                       SET reference = %s,
                           electronic_key = %s,
                           notes = %s
                     WHERE id = %s
                    """,
                    (new_reference, electronic_key or key, new_notes, line_id),
                )
            changed["itp_biweekly_lines"] += 1

    cur.execute(
        """
        SELECT id, description
        FROM accounting_entries
        WHERE origin IN ('ITP','ITP_PAYMENT')
          AND COALESCE(description,'') ~ '\\d{50}'
        ORDER BY id
        """
    )
    for entry_id, description in cur.fetchall():
        new_description, replacements = replace_keys(description)
        if replacements:
            cur.execute("UPDATE accounting_entries SET description=%s WHERE id=%s", (new_description, entry_id))
            changed["accounting_entries"] += 1

    cur.execute(
        """
        SELECT l.id, l.line_description
        FROM accounting_lines l
        JOIN accounting_entries e ON e.id = l.entry_id
        WHERE e.origin IN ('ITP','ITP_PAYMENT')
          AND COALESCE(l.line_description,'') ~ '\\d{50}'
        ORDER BY l.id
        """
    )
    for line_id, line_description in cur.fetchall():
        new_description, replacements = replace_keys(line_description)
        if replacements:
            cur.execute("UPDATE accounting_lines SET line_description=%s WHERE id=%s", (new_description, line_id))
            changed["accounting_lines"] += 1

    cur.execute(
        """
        SELECT id, electronic_key
        FROM tax_electronic_documents
        WHERE COALESCE(document_number,'') = ''
          AND COALESCE(electronic_key,'') ~ '^\\d{50}$'
        """
    )
    for doc_id, electronic_key in cur.fetchall():
        cur.execute(
            "UPDATE tax_electronic_documents SET document_number=%s WHERE id=%s",
            (invoice_number(electronic_key), doc_id),
        )
        changed["tax_documents"] += 1

    return changed


def apply_bulk(cur) -> dict:
    changed = {
        "payment_obligations": 0,
        "payment_obligations_notes": 0,
        "itp_biweekly_lines": 0,
        "accounting_entries": 0,
        "accounting_lines": 0,
        "tax_documents": 0,
    }
    key_pattern = r"(\d{21})(\d{20})(\d{9})"

    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS electronic_key TEXT")

    cur.execute(
        """
        UPDATE payment_obligations
           SET electronic_key = COALESCE(NULLIF(electronic_key,''), SUBSTRING(reference FROM '\\d{50}')),
               reference = SUBSTRING(SUBSTRING(reference FROM '\\d{50}') FROM 22 FOR 20),
               updated_at = NOW()
         WHERE COALESCE(reference,'') ~ '\\d{50}'
        """
    )
    changed["payment_obligations"] = cur.rowcount

    cur.execute(
        """
        UPDATE payment_obligations
           SET notes = REGEXP_REPLACE(notes, %s, '\\2', 'g'),
               updated_at = NOW()
         WHERE COALESCE(notes,'') ~ '\\d{50}'
        """,
        (key_pattern,),
    )
    changed["payment_obligations_notes"] = cur.rowcount

    cur.execute("SELECT to_regclass('public.itp_biweekly_payment_lines')")
    if (cur.fetchone() or [None])[0]:
        cur.execute("ALTER TABLE itp_biweekly_payment_lines ADD COLUMN IF NOT EXISTS electronic_key TEXT")
        has_updated_at = has_column(cur, "itp_biweekly_payment_lines", "updated_at")
        if has_updated_at:
            cur.execute(
                """
                UPDATE itp_biweekly_payment_lines
                   SET electronic_key = COALESCE(NULLIF(electronic_key,''), SUBSTRING(reference FROM '\\d{50}')),
                       reference = COALESCE(SUBSTRING(SUBSTRING(reference FROM '\\d{50}') FROM 22 FOR 20), reference),
                       notes = REGEXP_REPLACE(COALESCE(notes,''), %s, '\\2', 'g'),
                       updated_at = NOW()
                 WHERE COALESCE(reference,'') ~ '\\d{50}'
                    OR COALESCE(notes,'') ~ '\\d{50}'
                """,
                (key_pattern,),
            )
        else:
            cur.execute(
                """
                UPDATE itp_biweekly_payment_lines
                   SET electronic_key = COALESCE(NULLIF(electronic_key,''), SUBSTRING(reference FROM '\\d{50}')),
                       reference = COALESCE(SUBSTRING(SUBSTRING(reference FROM '\\d{50}') FROM 22 FOR 20), reference),
                       notes = REGEXP_REPLACE(COALESCE(notes,''), %s, '\\2', 'g')
                 WHERE COALESCE(reference,'') ~ '\\d{50}'
                    OR COALESCE(notes,'') ~ '\\d{50}'
                """,
                (key_pattern,),
            )
        changed["itp_biweekly_lines"] = cur.rowcount

    cur.execute(
        """
        UPDATE accounting_entries
           SET description = REGEXP_REPLACE(description, %s, '\\2', 'g')
         WHERE origin IN ('ITP','ITP_PAYMENT')
           AND COALESCE(description,'') ~ '\\d{50}'
        """,
        (key_pattern,),
    )
    changed["accounting_entries"] = cur.rowcount

    cur.execute(
        """
        UPDATE accounting_lines l
           SET line_description = REGEXP_REPLACE(l.line_description, %s, '\\2', 'g')
          FROM accounting_entries e
         WHERE e.id = l.entry_id
           AND e.origin IN ('ITP','ITP_PAYMENT')
           AND COALESCE(l.line_description,'') ~ '\\d{50}'
        """,
        (key_pattern,),
    )
    changed["accounting_lines"] = cur.rowcount

    cur.execute(
        """
        UPDATE tax_electronic_documents
           SET document_number = SUBSTRING(electronic_key FROM 22 FOR 20)
         WHERE COALESCE(document_number,'') = ''
           AND COALESCE(electronic_key,'') ~ '^\\d{50}$'
        """
    )
    changed["tax_documents"] = cur.rowcount
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize ITP references from CR electronic keys to invoice numbers.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Without this flag, only previews.")
    args = parser.parse_args()

    conn = database.get_conn()
    try:
        cur = conn.cursor()
        before = preview(cur)
        print("BEFORE", before)
        if args.apply:
            changed = apply_bulk(cur)
            conn.commit()
            print("CHANGED", changed)
            print("AFTER", preview(cur))
        else:
            conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        database.release_conn(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
