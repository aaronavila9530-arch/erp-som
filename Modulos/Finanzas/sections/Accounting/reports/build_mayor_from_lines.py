from collections import defaultdict
from typing import List, Dict, Any
from datetime import datetime


def build_mayor_from_lines(
    rows: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Construye el LIBRO MAYOR a partir de accounting_lines

    ✔ Deriva fiscal_year y period desde created_at
    ✔ Falla si hay mezcla de periodos
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
                "El Libro Mayor debe construirse por un solo mes fiscal."
            )

    period_label = f"{period:02d}/{fiscal_year}"

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
