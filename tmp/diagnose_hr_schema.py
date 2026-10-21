import runpy
import sys
sys.path.insert(0, 'tmp/hr-diagnostic-deps')
import psycopg2
from psycopg2.extras import RealDictCursor

config=runpy.run_path('backend_api/hr.py')
conn=psycopg2.connect(config['DATABASE_URL'],host='tramway.proxy.rlwy.net',port=15258,connect_timeout=15,sslmode='require')
conn.set_session(readonly=True)
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT column_name,is_nullable,data_type,column_default FROM information_schema.columns WHERE table_name='hr_events' ORDER BY ordinal_position")
        print('HR schema',cur.fetchall())
        cur.execute("SELECT conname,pg_get_constraintdef(oid) AS definition FROM pg_constraint WHERE conrelid='hr_events'::regclass")
        print('Constraints',cur.fetchall())
        for table in ('hr_events', 'app_notifications', 'app_push_subscriptions'):
            cur.execute(f"SELECT max(id) AS maximum FROM {table}")
            print(table, 'max', cur.fetchone())
            cur.execute(f"SELECT last_value,is_called FROM {table}_id_seq")
            print(table, 'sequence', cur.fetchone())
        cur.execute("SELECT id,usuario,nombre,apellidos,company_code,activo FROM empleados WHERE lower(usuario)='surveyor01'")
        print('Employee',cur.fetchall())
        cur.execute("SELECT setting_value FROM app_system_settings WHERE setting_key='vapid_private_key'")
        key = cur.fetchone()['setting_value']
        from py_vapid import Vapid
        try:
            Vapid.from_string(key)
            print('Push key accepted as string')
        except Exception as exc:
            print('Push key parse error:', type(exc).__name__)
        try:
            Vapid.from_pem(key.encode('ascii'))
            print('Push key accepted as PEM')
        except Exception as exc:
            print('PEM parse error:', type(exc).__name__)
finally:
    conn.rollback();conn.close()
