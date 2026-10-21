"""Real SQL validation in connection-local temporary tables only."""
from pathlib import Path
import runpy
import sys
from unittest.mock import patch
import psycopg2
from psycopg2 import sql
from fastapi import HTTPException

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"backend_api"))
from routers import certificates_web as web
from services.certificate_web_fields import TYPES
from routers import weight_certificates_router as weight
from routers import vessel_holds_inspection_certificates_router as holds
from routers import sampling_certificates_router as sampling
from routers import sealing_certificates_router as sealing
from routers import lashing_certificates_router as lashing
config=runpy.run_path(str(root/"backend_api/hr.py"))
conn=psycopg2.connect(config["DATABASE_URL"],host="tramway.proxy.rlwy.net",port=15258,connect_timeout=15,sslmode="require")
class BorrowedConnection:
    def __getattr__(self,name): return getattr(conn,name)
    def close(self): pass
try:
    with conn.cursor() as cur:
        cur.execute("SET statement_timeout='15s'")
        cur.execute("CREATE TEMP TABLE servicios (num_informe text,company_code text,cliente text,buque_contenedor text,continente text,pais text,puerto text,operacion text,fecha_inicio date)")
        for company in ("MCI-CR","MSL-CR"):
            cur.execute("INSERT INTO pg_temp.servicios VALUES (%s,%s,'QA Client','QA Vessel','America','Costa Rica','Caldera','Inspection',CURRENT_DATE)",("QA-"+company,company))
        for spec in TYPES.values():
            table=spec["table"]
            cur.execute(sql.SQL("CREATE TEMP TABLE {} (LIKE public.{} INCLUDING ALL)").format(sql.Identifier(table),sql.Identifier(table)))
            seq=table+"_qa_seq"
            cur.execute(sql.SQL("CREATE TEMP SEQUENCE {}").format(sql.Identifier(seq)))
            cur.execute(sql.SQL("ALTER TABLE pg_temp.{} ALTER COLUMN id SET DEFAULT nextval(%s)").format(sql.Identifier(table)),("pg_temp."+seq,))
            cur.execute("SELECT to_regclass(%s)::oid<>to_regclass(%s)::oid",(table,"public."+table))
            assert cur.fetchone()[0]
        for field in ("holds_inspected","observations","closing_date","closing_time","master"):
            cur.execute(sql.SQL("ALTER TABLE pg_temp.sampling_certificates ADD COLUMN IF NOT EXISTS {} text").format(sql.Identifier(field)))
    conn.commit()
    ctx=dict(company="MCI-CR",user="qa",permissions=dict(view=True,create=True,edit=True,approve=True))
    for kind,spec in TYPES.items():
        fields={k:"20/10/2026" if f["type"]=="date" else "09:01" if f["type"]=="time" else "00123" for k,f in spec["fields"].items()}
        fields[spec["number"]]="QA-MCI-CR"
        created=web.create(kind,web.SaveInput(fields=fields,submit=True),ctx,conn)
        rid=created["data"]["id"]
        listed=web.listing(kind,q="",status="",offset=0,ctx=ctx,conn=conn)
        assert listed["total"]==1
        assert web.listing(kind,q="",status="",offset=0,ctx={**ctx,"company":"MSL-CR"},conn=conn)["total"]==0
        if kind=="weight": legacy=weight.get_weight_certificate(rid,conn)
        elif kind=="holds": legacy=holds.get_vessel_holds_certificate(rid,conn)
        elif kind=="sampling": legacy=sampling.get_sampling_certificate(rid,conn)
        elif kind=="sealing":
            with patch.object(sealing,"get_conn",return_value=BorrowedConnection()):legacy=sealing.get_sealing_certificate(rid)
        else:
            with patch.object(lashing,"get_conn",return_value=BorrowedConnection()):legacy=lashing.get_lashing_certificate(rid)
        assert legacy[spec["number"]]=="QA-MCI-CR"
        changed=web.update(kind,rid,web.SaveInput(fields={"date":"21/10/2026"},version=created["version"],submit=True),ctx,conn)
        try:
            web.update(kind,rid,web.SaveInput(fields={"date":"22/10/2026"},version=created["version"]),ctx,conn)
            raise AssertionError("Stale update allowed")
        except HTTPException as e:assert e.status_code==409
        approved=web.change_status(kind,rid,web.StatusInput(status="Approved",version=changed["version"]),ctx,conn)
        assert approved["data"]["status"]=="Approved"
        print("PASS",kind,"real SQL CRUD, tenant isolation, version conflict, approval and desktop reader")
    print("No public business records or sequences were modified.")
finally:
    conn.rollback();conn.close()
