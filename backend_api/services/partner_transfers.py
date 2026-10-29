"""Partner transfers: beneficiary-based parsing and append-only accounting."""
import hashlib
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal


def normalize(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(text or ''))
                           if not unicodedata.combining(c)).upper().split())


def partner_name(text):
    tokens = set(re.findall(r'[A-Z]+', normalize(text)))
    if {'DIANA', 'QUIROS', 'BENAMBOURG'} <= tokens:
        return 'DIANA VERONICA QUIROS BENAMBOURG'
    if {'PABEL', 'PENA', 'BARRETO'} <= tokens:
        return 'PABEL GONZALO PEÑA BARRETO'
    return None


def company_name(text):
    value = normalize(text)
    if '3101969147' in re.sub(r'\D', '', value):
        return 'MCI-CR'
    if 'MSL MARINE SURVEYORS' in value:
        return 'MSL-CR'
    return None


def parse_transfer(text, subject='', mailbox='', message_id='', folder=''):
    raw = str(text or '')
    n = normalize(raw)
    bank = None
    if 'BAC CREDOMATIC' in n and 'TRANSFERENCIA LOCAL' in n:
        recipient = re.search(r'Estimad[oa]\s*\(a\)\s*([^:]+):', raw, re.I)
        sender = re.search(r'le comunica que\s+(.+?)\s+realiz[oó] una transferencia', raw, re.I | re.S)
        dt = re.search(r'se realiz[oó] el d[ií]a\s+(\d{2}[-/]\d{2}[-/]\d{4})', raw, re.I)
        money = re.search(r'monto de\s+([\d,]+\.\d{2})\s+(USD|CRC)', raw, re.I)
        ref = re.search(r'n[uú]mero de referencia\s+(?:es\s+)?(\d+)', raw, re.I)
        concept = re.search(r'por concepto de:\s*"([^"]*)"', raw, re.I)
        if not all((recipient, sender, dt, money, ref)):
            return None
        beneficiary, source = recipient[1], sender[1]
        amount, currency = Decimal(money[1].replace(',', '')), money[2].upper()
        bank, source_account = 'BAC', ''
    elif 'TRANSFERENCIA ENTRE CUENTAS BCR' in n:
        recipient = re.search(r'Cuenta destino\s+(CR\d+)\s+(.+?)\s+Monto debitado', raw, re.I | re.S)
        sender = re.search(r'Cuenta origen\s+(CR\d+)\s+(.+?)\s+Cuenta destino', raw, re.I | re.S)
        dt = re.search(r'Fecha\s+(\d{2}/\d{2}/\d{4})', raw, re.I)
        money = re.search(r'Monto transferido\s+([$₡])\s*([\d.]+,\d{2})', raw, re.I)
        ref = re.search(r'Documento\s+(\d+)', raw, re.I)
        concept = re.search(r'Motivo\s+(.+?)(?:\s+Para m[aá]s|$)', raw, re.I | re.S)
        if not all((recipient, sender, dt, money, ref)):
            return None
        beneficiary, source = recipient[2], sender[2]
        amount = Decimal(money[2].replace('.', '').replace(',', '.'))
        currency = 'USD' if money[1] == '$' else 'CRC'
        bank, source_account = 'BCR', sender[1]
    elif 'COMPROBANTE DE TRANSFERENCIA' in n and 'ENLACE BCT' in n:
        recipient = re.search(r'a nombre de\s+(.+?)\s+con\s+', raw, re.I | re.S)
        sender = re.search(r'(MSL MARINE SURVEYORS[^\r\n]+?)\s+realiz. una transferencia', raw, re.I)
        money = re.search(r'por un monto de\s*([$₡])([\d,]+\.\d{2})', raw, re.I)
        ref = re.search(r'referencia SINPE\s+(\d+)', raw, re.I)
        dt = re.search(r'se realiz. el d.a\s+(\d{2}/\d{2}/\d{4})', raw, re.I)
        concept = re.search(r'por concepto de\s+([^\r\n]+)', raw, re.I)
        if not all((recipient, sender, dt, money, ref)):
            return None
        beneficiary, source = recipient[1], sender[1]
        amount = Decimal(money[2].replace(',', ''))
        currency = 'USD' if money[1] == '$' else 'CRC'
        bank, source_account = 'BCT', ''
    else:
        return None
    partner, company = partner_name(beneficiary), company_name(source)
    if not partner or not company or amount <= 0:
        return None
    transaction_date = datetime.strptime(dt[1].replace('-', '/'), '%d/%m/%Y').date()
    return dict(company_code=company, partner_name=partner, bank=bank,
                source_account=source_account, source_name=' '.join(source.split()),
                transfer_date=transaction_date.isoformat(), amount=str(amount), currency=currency,
                reference=ref[1], concept=' '.join(concept[1].split()) if concept else '',
                mailbox=mailbox, message_id=message_id, folder=folder, subject=subject,
                partner_transfer_version=2, allow_closed_period=False)


def post_transfer(conn, payload, actor='PARTNER_TRANSFER_AUTO'):
    """Caller owns transaction. Never updates an existing posting or ITP obligation."""
    from psycopg2.extras import RealDictCursor, Json
    p = dict(payload)
    company, bank, currency = p['company_code'], p['bank'], p['currency']
    partner = partner_name(p['partner_name'])
    amount = Decimal(str(p['amount'])).quantize(Decimal('.01'))
    dt = date.fromisoformat(p['transfer_date'])
    if company not in ('MCI-CR', 'MSL-CR') or not partner or amount <= 0:
        raise ValueError('Invalid partner transfer')
    # MCI uses the shared BAC ledger, not an MSL-specific IBAN subaccount.
    bank_codes = {('MSL-CR', 'BAC', 'USD'): '1.1.02.02.02',
                  ('MSL-CR', 'BAC', 'CRC'): '1.1.02.02.01',
                  ('MSL-CR', 'BCR', 'USD'): '1.1.02.04.01',
                  ('MSL-CR', 'BCT', 'USD'): '1.1.02.03',
                  ('MSL-CR', 'BCT', 'CRC'): '1.1.02.03',
                  ('MCI-CR', 'BAC', 'USD'): '1.1.02.02',
                  ('MCI-CR', 'BAC', 'CRC'): '1.1.02.02'}
    bank_code = bank_codes.get((company, bank, currency))
    if not bank_code:
        raise ValueError('Bank/company/currency mapping requires review')
    if bank == 'BCR' and p.get('source_account') != 'CR90015202001393623379':
        raise ValueError('Unknown BCR source account')
    ref = str(p['reference'])
    key = '|'.join((company, bank, ref, str(dt)))
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', ('partner-transfer:' + key,))
        cur.execute("""SELECT id,company_code,entry_date,currency_code,posting_metadata,description
          FROM accounting_entries WHERE COALESCE(reversed,FALSE)=FALSE
          AND (posting_metadata->>'reference'=%s OR description ~ %s)
          AND entry_date=%s""", (ref, r'\m' + re.escape(ref) + r'\M', dt))
        matches = cur.fetchall()
        if matches:
            if len(matches) != 1:
                raise ValueError('Multiple existing entries for bank reference; manual review required')
            existing = matches[0]
            metadata = existing.get('posting_metadata') or {}
            if existing['company_code'] != company:
                raise ValueError('Existing reference belongs to different company; review required')
            cur.execute('SELECT account_code,debit,credit FROM accounting_lines WHERE entry_id=%s', (existing['id'],))
            lines = cur.fetchall()
            if not any(r['account_code'] == '5.4.04' and r['debit'] > 0 for r in lines):
                raise ValueError('Reference already booked with another treatment; review required')
            if Decimal(str(metadata.get('original_amount', '-1'))) != amount or metadata.get('original_currency') != currency:
                raise ValueError('Existing reference amount/currency differs; review required')
            return dict(status='EXISTING', entry_id=existing['id'], **p)
        cur.execute('SELECT status FROM accounting_period_controls WHERE company_code=%s AND period=%s', (company, dt.strftime('%Y-%m')))
        period = cur.fetchone()
        if period and period['status'] == 'CLOSED' and not p.get('allow_closed_period'):
            raise ValueError('Closed accounting period: review required')
        cur.execute("SELECT account_code,account_name FROM accounting_accounts WHERE account_code=ANY(%s) AND active=TRUE AND accepts_posting=TRUE", (['5.4.04', bank_code],))
        accounts = {r['account_code']: r['account_name'] for r in cur.fetchall()}
        if len(accounts) != 2:
            raise ValueError('Required posting account unavailable')
        rate = Decimal('1')
        if currency == 'USD':
            cur.execute('SELECT rate FROM exchange_rate WHERE rate_date<=%s ORDER BY rate_date DESC LIMIT 1', (dt,))
            row = cur.fetchone()
            if not row or Decimal(str(row['rate'])) <= 0:
                raise ValueError('Exchange rate unavailable')
            rate = Decimal(str(row['rate']))
        elif currency != 'CRC':
            raise ValueError('Unsupported currency')
        crc = (amount * rate).quantize(Decimal('.01'))
        origin = bank + '_PARTNER_TRANSFER'
        origin_id = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 2147483647
        description = f'{bank} transferencia socio {partner} Ref {ref}'
        metadata = dict(p, original_amount=str(amount), original_currency=currency,
                        source='partner_bank_notifications_v2', source_key=key,
                        accounting_treatment='5.4.04 confirmed by user', actor=actor)
        cur.execute("""INSERT INTO accounting_entries
          (company_code,entry_date,period,description,origin,origin_id,created_by,workflow_status,
           currency_code,exchange_rate,posting_rule_code,posting_metadata,posted_by,posted_at)
          VALUES(%s,%s,%s,%s,%s,%s,%s,'POSTED',%s,%s,%s,%s,%s,NOW()) RETURNING id""",
          (company,dt,dt.strftime('%Y-%m'),description,origin,origin_id,actor,currency,rate,origin,Json(metadata),actor))
        entry_id = cur.fetchone()['id']
        for code, debit, credit in [('5.4.04', crc, 0), (bank_code, 0, crc)]:
            cur.execute("""INSERT INTO accounting_lines(entry_id,account_code,account_name,debit,credit,line_description)
              VALUES(%s,%s,%s,%s,%s,%s)""", (entry_id,code,accounts[code],debit,credit,description + ' | ' + p.get('concept','')))
        return dict(status='POSTED', entry_id=entry_id, amount_crc=str(crc), exchange_rate=str(rate), **p)
