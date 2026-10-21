"""One-time historical close explicitly requested on 2026-10-14."""
import logging

KEY = 'user_20261014_itp_issue_through_20260930'


def close_historical_itp():
    import database
    from psycopg2.extras import RealDictCursor
    from routers.invoice_to_pay import _sync_itp_sources
    conn = database.connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', (KEY,))
            cur.execute('''CREATE TABLE IF NOT EXISTS itp_historical_closures (
                closure_key TEXT PRIMARY KEY, cutoff DATE NOT NULL,
                completed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), affected INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS itp_historical_closure_rows (
                closure_key TEXT NOT NULL, obligation_id BIGINT NOT NULL,
                company_code TEXT NOT NULL, before_row JSONB NOT NULL,
                PRIMARY KEY(closure_key, obligation_id));''')
            cur.execute('SELECT affected FROM itp_historical_closures WHERE closure_key=%s', (KEY,))
            if cur.fetchone():
                conn.rollback()
                return
            for company in ('MSL-CR', 'MCI-CR'):
                _sync_itp_sources(cur, company)
            cur.execute('ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS historical_closed BOOLEAN NOT NULL DEFAULT FALSE')
            cur.execute('''SELECT id FROM payment_obligations
                WHERE company_code IN ('MSL-CR','MCI-CR')
                  AND record_type='OBLIGATION' AND COALESCE(active,TRUE)
                  AND issue_date < DATE '2026-10-01'
                  AND status IN ('PENDING','PARTIAL') FOR UPDATE''')
            ids = [r['id'] for r in cur.fetchall()]
            if ids:
                cur.execute('''INSERT INTO itp_historical_closure_rows
                    SELECT %s, p.id, p.company_code, to_jsonb(p)
                    FROM payment_obligations p WHERE p.id=ANY(%s)''', (KEY, ids))
                cur.execute('''UPDATE payment_obligations SET status='PAID', balance=0, historical_closed=TRUE,
                    notes=CONCAT_WS(E'\\n', NULLIF(notes,''), %s), updated_at=NOW()
                    WHERE id=ANY(%s)''',
                    ('Cierre historico autorizado 2026-10-14: factura hasta 2026-09-30. Sin movimiento bancario nuevo.', ids))
            cur.execute('''INSERT INTO itp_historical_closures(closure_key,cutoff,affected)
                VALUES (%s,DATE '2026-09-30',%s)''', (KEY, len(ids)))
            conn.commit()
            logging.getLogger(__name__).warning('ITP historical closure completed: %s obligations', len(ids))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
