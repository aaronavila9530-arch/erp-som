from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api_client import post_bac_partner_transfer_api  # noqa: E402
from Modulos.Finanzas.sections.Accounting.outlook_fiscal_importer import (  # noqa: E402
    BAC_PARTNER_FOLDER,
    CARD_ACCOUNT,
    _find_folder,
    _message_year,
    _parse_bac_partner_transfer,
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Outlook BAC intercompany notifications.")
    parser.add_argument("--account", default=CARD_ACCOUNT)
    parser.add_argument("--folder", default=BAC_PARTNER_FOLDER)
    parser.add_argument("--years", default="2025,2026")
    parser.add_argument("--max-scan", type=int, default=50000)
    parser.add_argument("--summary-only", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Create/update accounting entries. Omit for dry-run.")
    args = parser.parse_args()

    years = {int(part.strip()) for part in args.years.split(",") if part.strip()}

    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    scanned = detected = applied = skipped = errors = 0
    try:
        namespace = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        _store, folder = _find_folder(namespace, args.account, args.folder)
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        for index in range(1, items.Count + 1):
            if scanned >= args.max_scan:
                break
            message = items.Item(index)
            msg_year = _message_year(message)
            if years and msg_year and msg_year not in years:
                if msg_year < min(years):
                    break
                skipped += 1
                continue
            scanned += 1
            parsed = _parse_bac_partner_transfer(
                message,
                args.account,
                str(getattr(folder, "FolderPath", args.folder)),
            )
            if not _is_intercompany_payload(parsed):
                skipped += 1
                continue
            detected += 1
            record = {
                "received": str(getattr(message, "ReceivedTime", "") or ""),
                "subject": parsed.get("subject"),
                "date": parsed.get("transfer_date"),
                "reference": parsed.get("reference"),
                "currency": parsed.get("currency"),
                "amount": parsed.get("amount"),
                "beneficiary": parsed.get("partner_name"),
                "concept": parsed.get("concept"),
                "status": "DRY_RUN",
            }
            if args.apply:
                try:
                    result = post_bac_partner_transfer_api(parsed)
                    record["status"] = str((result or {}).get("status") or "")
                    record["entry_id"] = (result or {}).get("entry_id")
                    applied += 1
                except Exception as exc:
                    record["status"] = "ERROR"
                    record["error"] = str(exc)
                    errors += 1
            if not args.summary_only:
                print(json.dumps(record, ensure_ascii=True, sort_keys=True))
        print(json.dumps({
            "mode": "apply" if args.apply else "dry-run",
            "account": args.account,
            "folder": args.folder,
            "years": sorted(years),
            "scanned": scanned,
            "detected": detected,
            "applied": applied,
            "skipped": skipped,
            "errors": errors,
        }, ensure_ascii=True, sort_keys=True))
        return 1 if errors else 0
    finally:
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    raise SystemExit(main())
