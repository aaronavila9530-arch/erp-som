"""Read-only compatibility probe. Never inserts/updates business records."""
import json
from pathlib import Path
import runpy
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend_api"))
from routers import container_web as web
from services.container_web_fields import FIELDS

config = runpy.run_path(str(root / "backend_api/hr.py"))
conn = psycopg2.connect(config["DATABASE_URL"], host="tramway.proxy.rlwy.net", port=15258,
                        connect_timeout=15, sslmode="require")
conn.set_session(readonly=True)
try:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SET LOCAL statement_timeout='15s'")
        cur.execute("SELECT column_name,data_type,character_maximum_length FROM information_schema.columns WHERE table_schema='public' AND table_name='container_reports'")
        columns = {r["column_name"]:dict(r) for r in cur.fetchall()}
        missing = set(FIELDS) | {"created_at","updated_at","status","user"}
        missing -= columns.keys()
        print("Missing columns:", sorted(missing))
        print("Limited columns:", json.dumps({k:v["character_maximum_length"] for k,v in columns.items() if v["character_maximum_length"]}))
        print("Date types:", json.dumps({k:v["data_type"] for k,v in columns.items() if k in web.DATE_FIELDS}))
    for company in ("MCI-CR", "MSL-CR"):
        ctx = {"company":company,"user":"admin","permissions":dict(view=True,create=True,edit=True,approve=True)}
        listing = web.listing(q="",status="",offset=0,ctx=ctx,conn=conn)
        services = web.services(q="",offset=0,ctx=ctx,conn=conn)
        print(company, "reports", listing["total"], "services page", len(services["data"]))
        if listing["data"]:
            report = web.detail(listing["data"][0]["id"],ctx,conn)
            print("Detail/version", bool(report["data"]), len(report["version"]))
    assert not missing, missing
finally:
    conn.rollback()
    conn.close()
