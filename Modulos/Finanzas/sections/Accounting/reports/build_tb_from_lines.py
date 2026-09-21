from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_tb_from_lines(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye el BALANCE DE COMPROBACIÓN (TB)
    a partir de accounting_lines

    ✔ Deriva periodo desde period o created_at
    ✔ Soporta mes único, rango de meses o periodo fiscal
    ✔ Agrupa por cuenta contable
    ✔ Calcula saldo deudor / acreedor
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

        created_at = r.get("created_at")
        if not created_at:
            continue

        if isinstance(created_at, datetime):
            dt = created_at
        else:
            try:
                dt = datetime.fromisoformat(str(created_at))
            except Exception:
                continue

        periods.add(f"{dt.year}-{dt.month:02d}")

    if not periods:
        raise ValueError(
            "No se pudo determinar periodo fiscal desde period o created_at"
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

    for r in rows:

        account_code = str(r.get("account_code") or "").strip()
        account_name = str(r.get("account_name") or "SIN NOMBRE").strip()
        account_type = _infer_account_type(account_code, r.get("account_type"))

        if not account_code:
            continue

        try:
            debit = float(r.get("debit") or 0)
        except Exception:
            debit = 0.0

        try:
            credit = float(r.get("credit") or 0)
        except Exception:
            credit = 0.0

        key = f"{account_code} - {account_name}"
        accounts[key]["debit"] += debit
        accounts[key]["credit"] += credit
        if account_type:
            accounts[key]["account_type"] = account_type

    # =====================================================
    # FORMATO FINAL
    # =====================================================
    rows_out = []

    total_debit = 0.0
    total_credit = 0.0
    total_saldo_deudor = 0.0
    total_saldo_acreedor = 0.0

    for acc, vals in sorted(accounts.items()):
        debit = round(vals["debit"], 2)
        credit = round(vals["credit"], 2)
        balance = round(debit - credit, 2)

        saldo_deudor = balance if balance > 0 else 0.0
        saldo_acreedor = abs(balance) if balance < 0 else 0.0

        total_debit += debit
        total_credit += credit
        total_saldo_deudor += saldo_deudor
        total_saldo_acreedor += saldo_acreedor

        rows_out.append({
            "account": acc,
            "account_type": vals.get("account_type") or "",
            "debit": debit,
            "credit": credit,
            "saldo_deudor": round(saldo_deudor, 2),
            "saldo_acreedor": round(saldo_acreedor, 2),
        })

    return {
        "fiscal_year": fiscal_year,
        "period": period,
        "period_label": period_label,
        "rows": rows_out,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
        "total_saldo_deudor": round(total_saldo_deudor, 2),
        "total_saldo_acreedor": round(total_saldo_acreedor, 2),
    }
