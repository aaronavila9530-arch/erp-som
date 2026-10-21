import ast
import runpy
from pathlib import Path
import psycopg2

root = Path(__file__).resolve().parents[1]
tree = ast.parse((root / "backend_api/routers/invoicing.py").read_text(encoding="utf-8"))
fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_servicios_facturables")
query = next(n.args[0].value for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "execute" and isinstance(n.args[0], ast.Constant))
config = runpy.run_path(str(root / "backend_api/hr.py"))
conn = psycopg2.connect(config["DATABASE_URL"], host="tramway.proxy.rlwy.net",
                       port=15258, sslmode="require", connect_timeout=15)
conn.set_session(readonly=True)
try:
    with conn.cursor() as cur:
        cur.execute("SET LOCAL statement_timeout='15s'")
        cur.execute(query, ("EL SURCO", "EL SURCO", "MCI-CR"))
        print("Query OK; rows:", len(cur.fetchall()))
except psycopg2.Error as exc:
    print("SQLSTATE:", exc.pgcode)
    print("ERROR:", exc.diag.message_primary)
finally:
    conn.rollback()
    conn.close()
