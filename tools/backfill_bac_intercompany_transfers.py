from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend_api"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from psycopg2.extras import RealDictCursor  # noqa: E402

from database import get_conn, release_conn  # noqa: E402
from services.gmail_fiscal_service import (  # noqa: E402
    _access_token,
    _api,
    _headers,
    _message_body_text,
    _parse_bac_partner_transfer,
    _process_bac_partner_transfer,
    decrypt_token,
    ensure_schema,
)


ACCOUNT_EMAIL = "contabilidad@mslogisticsgroup.com"
DEFAULT_QUERY = (
    'from:baccredomatic.com ("Estimado(a) MSL" OR "Estimado MSL" OR "MSL MARINE") '
    '(Intercompany OR intercompany) after:2025/01/01 before:2026/10/02'
)


def _is_intercompany_payload(payload: dict | None) -> bool:
    if not payload:
        return False
    beneficiary = str(payload.get("partner_name") or "").upper()
    if not any(token in beneficiary for token in (
        "MSL MARINE SURVEYORS",
        "MSL MARINE SURVEYORS AND LOGIS",
        "MARINE SURVEYORS AND LOGISTICS",
        "MARINE SURVEYORS LOGISTICS",
    )):
        return False
    subject = str(payload.get("subject") or "").upper().replace("_", " ")
    return any(token in subject for token in (
        "MSL",
        "MARINE SURVEYOR",
        "MARITIME MASTERS",
        "MARITIME CORPORATION",
        "3-101-969147",
        "3101969147",
    ))


def _message_date(headers: dict) -> datetime:
    raw = headers.get("date")
    if not raw:
        return datetime.now(timezone.utc)
    from email.utils import parsedate_to_datetime

    parsed = parsedate_to_datetime(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill BAC intercompany transfer notifications from Gmail.")
    parser.add_argument("--account", default=ACCOUNT_EMAIL)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--max", type=int, default=500)
    parser.add_argument("--apply", action="store_true", help="Create/update accounting entries. Omit for dry-run.")
    args = parser.parse_args()

    conn = get_conn()
    try:
        ensure_schema(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT encrypted_refresh_token FROM gmail_fiscal_connections WHERE account_email=%s",
                (args.account.strip().lower(),),
            )
            row = cur.fetchone()
            if not row or not row.get("encrypted_refresh_token"):
                raise RuntimeError(f"Gmail account is not authorized: {args.account}")
            token = _access_token(decrypt_token(row["encrypted_refresh_token"]))

        remaining = max(1, int(args.max))
        page_token = None
        scanned = detected = applied = skipped = errors = 0
        rows: list[dict] = []

        while remaining > 0:
            batch_size = min(100, remaining)
            params = {"q": args.query, "maxResults": batch_size}
            if page_token:
                params["pageToken"] = page_token
            listed = _api(token, "GET", "/messages", params=params)
            messages = listed.get("messages") or []
            if not messages:
                break
            for item in messages:
                scanned += 1
                remaining -= 1
                msg = _api(token, "GET", f"/messages/{item['id']}", params={"format": "full"})
                payload = msg.get("payload") or {}
                headers = _headers(payload)
                received = _message_date(headers)
                body_text = _message_body_text(payload)
                parsed = _parse_bac_partner_transfer(
                    body_text,
                    headers.get("subject") or "",
                    args.account.strip().lower(),
                    item["id"],
                    "Gmail/BAC backfill intercompany",
                    received.date(),
                    "MSL-CR",
                )
                if not _is_intercompany_payload(parsed):
                    skipped += 1
                    continue
                detected += 1
                record = {
                    "date": parsed.get("transfer_date"),
                    "reference": parsed.get("reference"),
                    "currency": parsed.get("currency"),
                    "amount": parsed.get("amount"),
                    "beneficiary": parsed.get("partner_name"),
                    "concept": parsed.get("concept"),
                    "gmail_message_id": item["id"],
                    "status": "DRY_RUN",
                }
                if args.apply:
                    try:
                        result = _process_bac_partner_transfer(parsed)
                        record["status"] = str((result or {}).get("status") or "")
                        record["entry_id"] = (result or {}).get("entry_id")
                        applied += 1
                    except Exception as exc:
                        record["status"] = "ERROR"
                        record["error"] = str(exc)
                        errors += 1
                rows.append(record)
                print(record)
                if remaining <= 0:
                    break
            page_token = listed.get("nextPageToken")
            if not page_token or remaining <= 0:
                break

        print({
            "mode": "apply" if args.apply else "dry-run",
            "query": args.query,
            "scanned": scanned,
            "detected": detected,
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
        })
        return 1 if errors else 0
    finally:
        release_conn(conn)


if __name__ == "__main__":
    raise SystemExit(main())
