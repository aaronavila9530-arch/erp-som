from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_tb_from_lines(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye el BALANCE DE COMPROBACIÓN (TB)
    a partir de accounting_lines

    ✔ Deriva fiscal_year y period desde created_at
    ✔ Falla si hay mezcla de periodos
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
    # DERIVAR Y VALIDAR PERIODO
    # =====================================================
    fiscal_year = None
    period = None

    for r in rows:
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

        fiscal_year = dt.year
        period = dt.month
        break

    if fiscal_year is None or period is None:
        raise ValueError(
            "No se pudo determinar año y periodo fiscal desde created_at"
        )

    for r in rows:
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

        if dt.year != fiscal_year or dt.month != period:
            raise ValueError(
                "Las líneas contables contienen múltiples periodos. "
                "El Balance de Comprobación debe construirse por un solo mes fiscal."
            )

    period_label = f"{period:02d}/{fiscal_year}"

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

        key = f"{account_code} - {account_name}"
        accounts[key]["debit"] += debit
        accounts[key]["credit"] += credit

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
