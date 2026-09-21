from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_mayor_from_lines(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye el LIBRO MAYOR a partir de accounting_lines

    ✔ Deriva periodo desde period, entry_date o created_at
    ✔ Soporta mes único, rango de meses o periodo fiscal
    ✔ Agrupa por cuenta contable
    ✔ Salida lista para Excel / PDF
    ✔ Totalmente blindado
    """

    # =====================================================
    # VALIDACIÓN FUERTE
    # =====================================================
    if not isinstance(rows, list):
        raise ValueError("build_mayor_from_lines esperaba una LISTA de filas")

    if not rows:
        raise ValueError("No hay líneas contables para construir Libro Mayor")

    # =====================================================
    # DERIVAR PERIODO / RANGO
    # =====================================================
    periods = set()

    def _row_period(row):
        period_value = str(row.get("period") or "").strip()
        if len(period_value) == 7 and period_value[4] == "-":
            return period_value

        date_value = row.get("entry_date") or row.get("created_at")
        if not date_value:
            return None
        if isinstance(date_value, datetime):
            dt = date_value
        else:
            try:
                dt = datetime.fromisoformat(str(date_value).replace(" ", "T"))
            except Exception:
                return None
        return f"{dt.year}-{dt.month:02d}"

    for r in rows:
        if not isinstance(r, dict):
            continue
        period_value = _row_period(r)
        if period_value:
            periods.add(period_value)

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
    # AGRUPACIÓN POR CUENTA
    # =====================================================
    accounts = defaultdict(list)

    for r in rows:
        account_code = str(r.get("account_code") or "").strip()
        account_name = str(r.get("account_name") or "SIN NOMBRE").strip()

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

        accounts[f"{account_code} - {account_name}"].append({
            "date": r.get("created_at"),
            "entry_id": r.get("entry_id"),
            "detail": r.get("line_description"),
            "debit": debit,
            "credit": credit,
        })

    # =====================================================
    # FORMATO FINAL
    # =====================================================
    result = []

    for account, lines in sorted(accounts.items()):
        total_debit = sum(l["debit"] for l in lines)
        total_credit = sum(l["credit"] for l in lines)

        result.append({
            "account": account,
            "lines": lines,
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
        })

    return {
        "fiscal_year": fiscal_year,
        "period": period,
        "period_label": period_label,
        "accounts": result,
    }
