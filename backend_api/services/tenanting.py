from __future__ import annotations

import re

import database


DEFAULT_COMPANY_CODE = "MSL-CR"


def company_code(value: str | None = None, header_value: str | None = None) -> str:
    code = str(value or header_value or DEFAULT_COMPANY_CODE).strip().upper()
    return code or DEFAULT_COMPANY_CODE


def company_prefix(code: str) -> str:
    prefix = str(code or DEFAULT_COMPANY_CODE).split("-")[0].strip().upper()
    return re.sub(r"[^A-Z0-9]", "", prefix) or "MSL"


def ensure_company_column(table_name: str) -> None:
    safe_table = re.sub(r"[^a-zA-Z0-9_]", "", table_name or "")
    if not safe_table:
        raise ValueError("Invalid table name")
    database.sql(
        f"ALTER TABLE {safe_table} ADD COLUMN IF NOT EXISTS company_code VARCHAR(30) NOT NULL DEFAULT %s",
        (DEFAULT_COMPANY_CODE,),
    )


def set_payload_company(payload: dict, code: str) -> dict:
    payload = dict(payload or {})
    payload["company_code"] = company_code(code)
    return payload
