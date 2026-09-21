from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_tb_from_lines(
    rows: List[Dict[str, Any]],
    opening_rows: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Construye el BALANCE DE COMPROBACIÓN (TB)
    a partir de accounting_lines

    ✔ Deriva periodo desde period, entry_date o created_at
    ✔ Soporta mes único, rango de meses o periodo fiscal
    ✔ Agrupa por cuenta contable
    ✔ Calcula saldo inicial, movimiento, saldo deudor / acreedor y saldo final
    ✔ Salida lista para Excel / PDF
    ✔ Totalmente blindado
    """

    # =====================================================
    # VALIDACIÓN FUERTE
    # =====================================================
    if not isinstance(rows, list):
        raise ValueError("build_tb_from_lines esperaba una LISTA de filas")

    if not rows:
        raise ValueError("No hay líneas contables para construir TB")

    # =====================================================
    # DERIVAR PERIODO / RANGO
    # =====================================================
    periods = set()

    for r in rows:
        period_value = str(r.get("period") or "").strip()
        if len(period_value) == 7 and period_value[4] == "-":
            periods.add(period_value)
            continue

        date_value = r.get("entry_date") or r.get("created_at")
        if not date_value:
            continue

        if isinstance(date_value, datetime):
            dt = date_value
        else:
            try:
                dt = datetime.fromisoformat(str(date_value).replace(" ", "T"))
            except Exception:
                continue

        periods.add(f"{dt.year}-{dt.month:02d}")

    if not periods:
        raise ValueError(
            "No se pudo determinar periodo fiscal desde period, entry_date o created_at"
        )

    sorted_periods = sorted(periods)
    first_period = sorted_periods[0]
    last_period = sorted_periods[-1]
    fiscal_year = int(last_period[:4])
    period = int(last_period[5:7])
    period_label = (
        first_period
        if first_period == last_period
        else f"{first_period} a {last_period}"
    )

    # =====================================================
    # ACUMULADORES
    # =====================================================
    accounts = defaultdict(lambda: {
        "opening_debit": 0.0,
        "opening_credit": 0.0,
        "debit": 0.0,
        "credit": 0.0
    })

    # =====================================================
    # PROCESAMIENTO
    # =====================================================
    def _infer_account_type(code: str, current: str) -> str:
        text = str(current or "").strip().upper()
        aliases = {
            "ASSET": "ACTIVO",
            "LIABILITY": "PASIVO",
            "EQUITY": "PATRIMONIO",
            "REVENUE": "INGRESO",
            "INCOME": "INGRESO",
            "COST": "COSTO",
            "EXPENSE": "GASTO",
        }
        if text:
            return aliases.get(text, text)
        clean = str(code or "").strip()
        if clean.startswith("1"):
            return "ACTIVO"
        if clean.startswith("2"):
            return "PASIVO"
        if clean.startswith("3"):
            return "PATRIMONIO"
        if clean.startswith("4"):
            return "INGRESO"
        if clean.startswith("5"):
            return "GASTO"
        if clean.startswith("6"):
            return "COSTO"
        return ""

    def _apply_row(r, bucket: str):

        account_code = str(r.get("account_code") or "").strip()
        account_name = str(r.get("account_name") or "SIN NOMBRE").strip()
        account_type = _infer_account_type(account_code, r.get("account_type"))

        if not account_code:
            return

        try:
            debit = float(r.get("debit") or 0)
        except Exception:
            debit = 0.0

        try:
            credit = float(r.get("credit") or 0)
        except Exception:
            credit = 0.0

        key = f"{account_code} - {account_name}"
        if bucket == "opening":
            accounts[key]["opening_debit"] += debit
            accounts[key]["opening_credit"] += credit
        else:
            accounts[key]["debit"] += debit
            accounts[key]["credit"] += credit
        if account_type:
            accounts[key]["account_type"] = account_type

    for r in opening_rows or []:
        _apply_row(r, "opening")

    for r in rows:
        _apply_row(r, "movement")

    # =====================================================
    # FORMATO FINAL
    # =====================================================
    rows_out = []

    total_debit = 0.0
    total_credit = 0.0
    total_opening_balance = 0.0
    total_closing_balance = 0.0
    total_saldo_neto = 0.0
    total_saldo_deudor = 0.0
    total_saldo_acreedor = 0.0

    for acc, vals in sorted(accounts.items()):
        account_type = vals.get("account_type") or ""
        credit_nature = account_type in ("PASIVO", "PATRIMONIO", "INGRESO")
        opening_raw = vals["opening_debit"] - vals["opening_credit"]
        movement_raw = vals["debit"] - vals["credit"]
        if credit_nature:
            opening_balance = -opening_raw
            closing_balance = -(opening_raw + movement_raw)
        else:
            opening_balance = opening_raw
            closing_balance = opening_raw + movement_raw

        debit = round(vals["debit"], 2)
        credit = round(vals["credit"], 2)
        balance = round((opening_raw + movement_raw), 2)
        natural_alert = closing_balance < -0.005

        saldo_deudor = balance if balance > 0 else 0.0
        saldo_acreedor = abs(balance) if balance < 0 else 0.0

        total_debit += debit
        total_credit += credit
        total_opening_balance += opening_balance
        total_closing_balance += closing_balance
        total_saldo_neto += balance
        total_saldo_deudor += saldo_deudor
        total_saldo_acreedor += saldo_acreedor

        rows_out.append({
            "account": acc,
            "account_type": account_type,
            "opening_balance": round(opening_balance, 2),
            "debit": debit,
            "credit": credit,
            "saldo_neto": round(balance, 2),
            "saldo_deudor": round(saldo_deudor, 2),
            "saldo_acreedor": round(saldo_acreedor, 2),
            "closing_balance": round(closing_balance, 2),
            "balance_alert": "Saldo contrario a naturaleza" if natural_alert else "",
        })

    return {
        "fiscal_year": fiscal_year,
        "period": period,
        "period_label": period_label,
        "rows": rows_out,
        "total_opening_balance": round(total_opening_balance, 2),
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "total_saldo_neto": round(total_saldo_neto, 2),
        "total_saldo_deudor": round(total_saldo_deudor, 2),
        "total_saldo_acreedor": round(total_saldo_acreedor, 2),
        "total_closing_balance": round(total_closing_balance, 2),
    }
