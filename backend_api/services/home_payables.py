"""Company-scoped outstanding balances for the home drilldowns."""
from collections import defaultdict
from decimal import Decimal
from datetime import date
from calendar import monthrange


def merge_biweekly_rows(rows, previews):
    result = list(rows)
    obligation_ids = {str(r['id']) for r in rows}
    seen = set()
    for period, fortnight, lines in previews:
        for line in lines:
            obligation_id = line.get('obligation_id')
            if obligation_id and str(obligation_id) in obligation_ids:
                continue
            amount = Decimal(str(line.get('balance') if line.get('balance') is not None else line.get('amount') or 0))
            if amount < 0:
                continue
            year, month = map(int, period.split('-'))
            fallback_day = 15 if fortnight == 1 else monthrange(year, month)[1]
            due = str(line.get('due_date') or f'{period}-{fallback_day:02d}')[:10]
            key = (str(obligation_id), line.get('origin_company_code'), line.get('category'), line.get('name'), line.get('currency'), line.get('reference'), due, amount)
            if key in seen:
                continue
            seen.add(key)
            if obligation_id:
                obligation_ids.add(str(obligation_id))
            result.append(dict(id=obligation_id or f'{period}-Q{fortnight}-{len(seen)}',
                payee_name=line.get('name'), reference=line.get('reference') or '',
                issue_date=None, due_date=due, payment_date=due,
                currency=line.get('currency') or 'CRC', total=amount, balance=amount,
                status='PENDIENTE' if amount else 'PENDIENTE_MONTO',
                obligation_type=line.get('category'), source=line.get('source') or 'QUINCENAL',
                notes=line.get('notes') or ''))
    return result


def load_biweekly_home_rows(company):
    import database
    from psycopg2.extras import RealDictCursor
    from routers.invoice_to_pay import (biweekly_obligations_preview,
        _load_biweekly_paid_markers, _biweekly_row_key_text, _biweekly_row_identity_text)
    today = date.today()
    first = today.year * 12 + today.month - 1
    periods = [f'{n // 12:04d}-{n % 12 + 1:02d}' for n in range(first, first + 4)]
    # Preview synchronizes its sources and commits, so keep it outside the home savepoint.
    conn = database.get_conn()
    previews = []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT to_regclass('itp_biweekly_payment_batches') AS table_name")
            if cur.fetchone()['table_name']:
                cur.execute("SELECT DISTINCT period FROM itp_biweekly_payment_batches WHERE company_code=%s AND status='DRAFT'", (company,))
                periods = sorted(set(periods) | {row['period'] for row in cur.fetchall()})
        conn.commit()
        for period in periods:
            for fortnight in (1, 2):
                preview = biweekly_obligations_preview(period=period, fortnight=fortnight,
                    force=False, conn=conn, x_company_code=company)
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    paid = _load_biweekly_paid_markers(cur, company, period, fortnight)
                lines = [line for line in preview.get('rows', [])
                    if _biweekly_row_key_text(line) not in paid['keys']
                    and _biweekly_row_identity_text(line) not in paid['identities']]
                previews.append((period, fortnight, lines))
        return previews
    finally:
        conn.rollback()
        conn.close()


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
    previews = load_biweekly_home_rows(company)
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
    receivables = [dict(r) for r in cur.fetchall()]
    rows = merge_biweekly_rows(rows, previews)
    return payment_queues(rows, receivables)
