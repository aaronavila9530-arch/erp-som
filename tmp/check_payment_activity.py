from pathlib import Path
import sys,runpy
import psycopg2
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"backend_api"))
config=runpy.run_path(str(root/"backend_api/hr.py"))
with psycopg2.connect(config["DATABASE_URL"],host="tramway.proxy.rlwy.net",port=15258,sslmode="require",connect_timeout=15) as conn:
    conn.set_session(readonly=True)
    with conn.cursor() as cur:
        cur.execute("""SELECT pid,state,wait_event_type,wait_event,now()-xact_start AS age,
            left(query,160),pg_blocking_pids(pid) FROM pg_stat_activity
            WHERE datname=current_database() AND pid<>pg_backend_pid() AND xact_start IS NOT NULL
            ORDER BY xact_start LIMIT 12""")
        for row in cur.fetchall():print(row)
