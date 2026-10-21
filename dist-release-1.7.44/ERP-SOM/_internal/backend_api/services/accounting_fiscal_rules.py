from __future__ import annotations

from datetime import date
from decimal import Decimal

from psycopg2.extras import RealDictCursor

from services.accounting_bank_rules import external_surveyor_settlement, is_costa_rica_country, normalize_text


FISCAL_COLUMNS = (
    "fiscal_deductible",
    "fiscal_iva_creditable",
    "fiscal_requires_support",
    "fiscal_support_status",
    "fiscal_rule_code",
    "fiscal_tax_form",
    "fiscal_risk_level",
    "fiscal_notes",
    "fiscal_updated_at",
)


def ensure_accounting_fiscal_schema(cur):
    for statement in (
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_deductible BOOLEAN",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_iva_creditable BOOLEAN",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_requires_support BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_support_status VARCHAR(30) NOT NULL DEFAULT 'NOT_EVALUATED'",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_rule_code VARCHAR(80)",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_tax_form VARCHAR(40)",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_risk_level VARCHAR(20) NOT NULL DEFAULT 'LOW'",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_notes TEXT",
        "ALTER TABLE accounting_lines ADD COLUMN IF NOT EXISTS fiscal_updated_at TIMESTAMP",
    ):
        cur.execute(statement)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_lines_fiscal_rule ON accounting_lines(fiscal_rule_code)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounting_lines_fiscal_support ON accounting_lines(fiscal_support_status)")


def _expense_account(code, name):
    text = normalize_text(f"{code} {name}")
    return str(code or "").startswith("5") or "gasto" in text or "sueldo" in text


def _has_text(row, *tokens):
    text = normalize_text(" ".join(str(row.get(key) or "") for key in ("account_code", "account_name", "line_description", "entry_description", "origin")))
    return any(token in text for token in tokens)


def _base_classification(row):
    code = str(row.get("account_code") or "").strip()
    name = str(row.get("account_name") or "").strip()
    origin = str(row.get("origin") or "").strip().upper()
    debit = Decimal(str(row.get("debit") or 0))
    credit = Decimal(str(row.get("credit") or 0))

    result = {
        "fiscal_deductible": None,
        "fiscal_iva_creditable": False,
        "fiscal_requires_support": False,
        "fiscal_support_status": "NOT_EVALUATED",
        "fiscal_rule_code": "GENERAL_LEDGER_LINE",
        "fiscal_tax_form": None,
        "fiscal_risk_level": "LOW",
        "fiscal_notes": "Linea contable clasificada por regla general.",
    }

    if code.startswith(("1.", "2.")):
        result.update({
            "fiscal_deductible": False,
            "fiscal_support_status": "BALANCE_SHEET",
            "fiscal_rule_code": "BALANCE_SHEET_ACCOUNT",
            "fiscal_notes": "Cuenta de balance; no se trata como gasto deducible.",
        })

    if code.startswith("4"):
        result.update({
            "fiscal_deductible": False,
            "fiscal_support_status": "REVENUE",
            "fiscal_rule_code": "REVENUE_D101",
            "fiscal_tax_form": "D101",
            "fiscal_notes": "Ingreso operativo para impuesto sobre utilidades.",
        })

    if _expense_account(code, name) and (debit > 0 or credit > 0):
        result.update({
            "fiscal_deductible": True,
            "fiscal_requires_support": True,
            "fiscal_support_status": "REQUIRES_DOCUMENT",
            "fiscal_rule_code": "OPERATING_EXPENSE_REQUIRES_SUPPORT",
            "fiscal_tax_form": "D101",
            "fiscal_notes": "Gasto operativo; deducible si mantiene soporte suficiente.",
        })

    if origin in {"PAYROLL", "PAYROLL_PAYMENT"} or code in {"500-001-001-001", "500-001-001-002", "500-001-001-003", "500-001-001-004"}:
        result.update({
            "fiscal_deductible": True if debit > 0 else False,
            "fiscal_requires_support": True,
            "fiscal_support_status": "PAYROLL_SUPPORT",
            "fiscal_rule_code": "PAYROLL_DEDUCTIBLE",
            "fiscal_tax_form": "D101",
            "fiscal_notes": "Gasto laboral/provision asociado a planilla y cargas sociales.",
        })

    if code == "5.2.03":
        result.update({
            "fiscal_deductible": True,
            "fiscal_requires_support": True,
            "fiscal_support_status": "BANK_STATEMENT",
            "fiscal_rule_code": "BANK_FEES_DEDUCTIBLE",
            "fiscal_tax_form": "D101",
            "fiscal_notes": "Comision bancaria; requiere estado de cuenta o comprobante bancario.",
        })

    if code == "1.1.13.99":
        result.update({
            "fiscal_deductible": False,
            "fiscal_iva_creditable": True,
            "fiscal_requires_support": True,
            "fiscal_support_status": "XML_REQUIRED",
            "fiscal_rule_code": "IVA_CREDIT_REQUIRES_XML",
            "fiscal_tax_form": "D150",
            "fiscal_notes": "Credito fiscal de IVA; solo procede con XML/factura electronica valida.",
        })

    if code == "2.1.02.03":
        result.update({
            "fiscal_deductible": False,
            "fiscal_iva_creditable": False,
            "fiscal_requires_support": True,
            "fiscal_support_status": "SALES_XML_REQUIRED",
            "fiscal_rule_code": "IVA_DEBIT_D150",
            "fiscal_tax_form": "D150",
            "fiscal_notes": "Debito fiscal de IVA por ventas; debe cuadrar contra facturacion electronica.",
        })

    if code == "2.1.02.04" and credit > 0:
        result.update({
            "fiscal_deductible": False,
            "fiscal_requires_support": True,
            "fiscal_support_status": "WITHHOLDING_SUPPORT",
            "fiscal_rule_code": "WITHHOLDING_PAYABLE",
            "fiscal_tax_form": "TRIBU_RETENCIONES",
            "fiscal_notes": "Retencion por pagar; requiere soporte de calculo y declaracion.",
        })

    if code == "2.1.02.09" and credit > 0:
        result.update({
            "fiscal_deductible": False,
            "fiscal_requires_support": True,
            "fiscal_support_status": "TRANSFER_SUPPORT",
            "fiscal_rule_code": "EXTERNAL_SURVEYOR_TRANSFER_DEDUCTION",
            "fiscal_tax_form": "D101",
            "fiscal_notes": "Deduccion aplicada a liquidacion de surveyor exterior; requiere comprobante de transferencia.",
        })

    if _has_text(row, "interes bancario", "intereses bancarios", "rendimiento bancario", "rendimientos bancarios"):
        result.update({
            "fiscal_deductible": False,
            "fiscal_requires_support": True,
            "fiscal_support_status": "BANK_STATEMENT",
            "fiscal_rule_code": "BANK_INTEREST_INCOME_D270",
            "fiscal_tax_form": "D270",
            "fiscal_notes": "Ingreso financiero por intereses bancarios; debe reportarse segun formulario 270 cuando aplique.",
        })

    if _has_text(row, "no deducible", "no-deducible", "personal", "estipendio", "telefono personal", "vehiculo personal", "trabajador informal", "chamba"):
        result.update({
            "fiscal_deductible": False,
            "fiscal_iva_creditable": False,
            "fiscal_requires_support": True,
            "fiscal_support_status": "INTERNAL_SUPPORT",
            "fiscal_rule_code": "NON_DEDUCTIBLE_OR_RISK_EXPENSE",
            "fiscal_tax_form": "D101",
            "fiscal_risk_level": "HIGH",
            "fiscal_notes": "Gasto marcado como no deducible o de riesgo fiscal/laboral; requiere soporte interno y revision.",
        })

    return result


def _enrich_itp_surveyor_rule(cur, row, result):
    if str(row.get("origin") or "").upper() != "ITP_PAYMENT":
        return result
    origin_id = row.get("origin_id")
    if not origin_id:
        return result
    cur.execute("""
        SELECT payee_name, payee_type, obligation_type, country, total, currency
        FROM payment_obligations
        WHERE id = %s
        LIMIT 1
    """, (origin_id,))
    obligation = cur.fetchone()
    if not obligation:
        return result
    settlement = external_surveyor_settlement(
        cur,
        obligation.get("total"),
        payee_name=obligation.get("payee_name"),
        fallback_country=obligation.get("country"),
        payee_type=obligation.get("payee_type"),
        obligation_type=obligation.get("obligation_type"),
    )
    if settlement["applies"]:
        notes = (
            f"Surveyor exterior: gross={settlement['gross']} "
            f"withholding={settlement['withholding']} deduction={settlement['deduction']} "
            f"net={settlement['net_payment']}."
        )
        if str(row.get("account_code") or "") == "1.1.02.02":
            result.update({
                "fiscal_rule_code": "EXTERNAL_SURVEYOR_NET_BANK_PAYMENT",
                "fiscal_requires_support": True,
                "fiscal_support_status": "TRANSFER_SUPPORT",
                "fiscal_notes": notes,
            })
    return result


def classify_accounting_line(cur, row):
    result = _base_classification(row)
    result = _enrich_itp_surveyor_rule(cur, row, result)
    return result


def apply_fiscal_classification(conn, year: int | None = None, apply: bool = True):
    cur = conn.cursor(cursor_factory=RealDictCursor)
    ensure_accounting_fiscal_schema(cur)
    params = []
    where = []
    if year:
        where.append("e.entry_date >= %s AND e.entry_date < %s")
        params.extend([date(year, 1, 1), date(year + 1, 1, 1)])
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    cur.execute(f"""
        SELECT l.id, l.account_code, l.account_name, l.debit, l.credit, l.line_description,
               e.id AS entry_id, e.origin, e.origin_id, e.description AS entry_description,
               e.entry_date, e.period, e.company_code
        FROM accounting_lines l
        JOIN accounting_entries e ON e.id = l.entry_id
        {where_sql}
        ORDER BY e.entry_date, e.id, l.id
    """, params)
    rows = cur.fetchall() or []
    changes = []
    for row in rows:
        rule = classify_accounting_line(cur, row)
        changes.append({"line_id": row["id"], **rule})
        if apply:
            cur.execute("""
                UPDATE accounting_lines
                   SET fiscal_deductible = %s,
                       fiscal_iva_creditable = %s,
                       fiscal_requires_support = %s,
                       fiscal_support_status = %s,
                       fiscal_rule_code = %s,
                       fiscal_tax_form = %s,
                       fiscal_risk_level = %s,
                       fiscal_notes = %s,
                       fiscal_updated_at = NOW()
                 WHERE id = %s
            """, (
                rule["fiscal_deductible"],
                rule["fiscal_iva_creditable"],
                rule["fiscal_requires_support"],
                rule["fiscal_support_status"],
                rule["fiscal_rule_code"],
                rule["fiscal_tax_form"],
                rule["fiscal_risk_level"],
                rule["fiscal_notes"],
                row["id"],
            ))
    return changes
