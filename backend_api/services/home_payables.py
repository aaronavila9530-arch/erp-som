"""Company-scoped outstanding balances for the home drilldowns."""
from collections import defaultdict
from decimal import Decimal


def payment_queues(rows, receivables):
    groups = {key: defaultdict(list) for key in ('payable_month', 'payable_half')}
    for row in rows:
        day = str(row.get('payment_date') or '')[:10]
        month = day[:7] if day else 'Sin fecha'
        half = ('Q1' if int(day[8:10]) <= 15 else 'Q2') if day else ''
        row['mes'] = month
        row['quincena'] = f'{month} {half}'.strip()
        groups['payable_month'][(month, row['currency'])].append(row)
        groups['payable_half'][(row['quincena'], row['currency'])].append(row)
    result = {'payable_invoices': {'count': len(rows), 'rows': rows},
              'receivable_invoices': {'count': len(receivables), 'rows': receivables}}
    for key, items in groups.items():
        summary = [{'periodo': period, 'currency': currency, 'cantidad': len(items),
                    'balance': sum((Decimal(str(r['balance'])) for r in items), Decimal(0))}
                   for (period, currency), items in sorted(items.items())]
        result[key] = {'count': len({r['periodo'] for r in summary}), 'rows': rows,
                       'summary': summary}
    return result


def load_payment_queues(cur, company):
    cur.execute('''SELECT id, payee_name, reference, issue_date, due_date,
        COALESCE(planned_payment_date,due_date,issue_date) AS payment_date,
        currency, total, balance, status, obligation_type
        FROM payment_obligations WHERE company_code=%s
        AND COALESCE(active,TRUE) AND record_type='OBLIGATION'
        AND status IN ('PENDING','PARTIAL') AND balance>0
        ORDER BY COALESCE(planned_payment_date,due_date,issue_date) NULLS LAST,id''', (company,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.execute('''SELECT codigo_cliente, nombre_cliente, numero_documento,
        fecha_emision, fecha_vencimiento, moneda, total, saldo_pendiente, estado_factura
        FROM collections WHERE company_code=%s AND saldo_pendiente>0
        AND COALESCE(estado_factura,'') NOT IN ('ANULADA','CANCELADA','WRITE_OFF')
        ORDER BY fecha_vencimiento NULLS LAST,numero_documento''', (company,))
    return payment_queues(rows, [dict(r) for r in cur.fetchall()])
