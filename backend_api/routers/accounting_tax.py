from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from psycopg2.extras import Json, RealDictCursor
from pydantic import BaseModel

from database import get_db


router = APIRouter(prefix="/accounting/tax", tags=["Accounting Tax Costa Rica"])
MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(MONEY)
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def _ensure_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_electronic_documents (
                id BIGSERIAL PRIMARY KEY,
                direction VARCHAR(10) NOT NULL CHECK(direction IN ('SALE','PURCHASE')),
                document_type VARCHAR(20) NOT NULL,
                document_number TEXT,
                electronic_key VARCHAR(60),
                xml_hash VARCHAR(64),
                schema_version VARCHAR(10),
                issuer_identification TEXT,
                issuer_name TEXT,
                receiver_identification TEXT,
                receiver_name TEXT,
                economic_activity TEXT,
                issue_datetime TIMESTAMPTZ,
                currency_code VARCHAR(3) NOT NULL DEFAULT 'CRC',
                exchange_rate NUMERIC(18,6) NOT NULL DEFAULT 1,
                subtotal NUMERIC(18,2) NOT NULL DEFAULT 0,
                discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                exempt_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                tax_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                total NUMERIC(18,2) NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                hacienda_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                hacienda_message TEXT,
                xml_path TEXT,
                response_xml_path TEXT,
                pdf_path TEXT,
                source_table VARCHAR(80),
                source_id TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_by TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(direction, source_table, source_id)
            )
        """)
        cur.execute("DROP INDEX IF EXISTS uq_tax_document_key")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tax_document_key ON tax_electronic_documents(direction,electronic_key) WHERE electronic_key IS NOT NULL")
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_tax_document_hash ON tax_electronic_documents(direction,xml_hash) WHERE xml_hash IS NOT NULL")
        cur.execute("ALTER TABLE tax_electronic_documents ADD COLUMN IF NOT EXISTS xml_content BYTEA")
        cur.execute("ALTER TABLE tax_electronic_documents ADD COLUMN IF NOT EXISTS response_xml_content BYTEA")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_tax_documents_period ON tax_electronic_documents(direction,issue_datetime)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_document_lines (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES tax_electronic_documents(id) ON DELETE CASCADE,
                line_number INTEGER NOT NULL,
                cabys_code VARCHAR(20),
                description TEXT,
                quantity NUMERIC(18,5) NOT NULL DEFAULT 0,
                unit_code VARCHAR(20),
                unit_price NUMERIC(18,5) NOT NULL DEFAULT 0,
                subtotal NUMERIC(18,2) NOT NULL DEFAULT 0,
                discount_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                tax_code VARCHAR(10),
                tax_rate NUMERIC(9,5) NOT NULL DEFAULT 0,
                tax_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                exemption_amount NUMERIC(18,2) NOT NULL DEFAULT 0,
                total NUMERIC(18,2) NOT NULL DEFAULT 0,
                UNIQUE(document_id,line_number)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_cabys_catalog (
                code VARCHAR(20) PRIMARY KEY,
                description TEXT NOT NULL,
                suggested_tax_rate NUMERIC(9,5),
                active BOOLEAN NOT NULL DEFAULT TRUE,
                source TEXT NOT NULL DEFAULT 'MANUAL',
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_obligations (
                id BIGSERIAL PRIMARY KEY,
                tax_code VARCHAR(30) NOT NULL UNIQUE,
                name TEXT NOT NULL,
                periodicity VARCHAR(20) NOT NULL DEFAULT 'MONTHLY',
                due_day INTEGER,
                active BOOLEAN NOT NULL DEFAULT TRUE,
                last_period_filed VARCHAR(10),
                last_filed_at TIMESTAMPTZ,
                notes TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tax_settings (
                setting_key VARCHAR(40) PRIMARY KEY,
                setting_value TEXT,
                updated_by TEXT,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            INSERT INTO tax_obligations(tax_code,name,periodicity,due_day,notes) VALUES
              ('TRIBU-IVA-150','IVA - Formulario TRIBU-CR 150','MONTHLY',15,'La fecha real debe verificarse contra el calendario tributario oficial.'),
              ('TRIBU-RENTA-101','Impuesto sobre las utilidades','ANNUAL',NULL,'Configurar fecha conforme al periodo fiscal del contribuyente.'),
              ('TRIBU-RETENCIONES','Retenciones en la fuente','MONTHLY',15,'Aplica cuando existan retenciones sujetas a declaración.')
            ON CONFLICT(tax_code) DO NOTHING
        """)
        cur.execute("""
            INSERT INTO tax_settings(setting_key,setting_value,updated_by) VALUES
              ('IVA_DEBIT_ACCOUNT','2108','SYSTEM_DEFAULT'),
              ('IVA_CREDIT_ACCOUNT','1131','SYSTEM_DEFAULT'),
              ('REQUIRE_CABYS','true','SYSTEM_DEFAULT'),
              ('ELECTRONIC_DOCUMENT_VERSION','4.4','SYSTEM_DEFAULT')
            ON CONFLICT(setting_key) DO NOTHING
        """)
    conn.commit()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node, name, default=None):
    for item in node.iter():
        if _local(item.tag) == name and item.text and item.text.strip():
            return item.text.strip()
    return default


def _direct_child(node, name):
    for item in list(node):
        if _local(item.tag) == name:
            return item
    return None


def _party(root, label):
    party = next((x for x in root.iter() if _local(x.tag) == label), None)
    if party is None:
        return None, None
    identification = next((x for x in party.iter() if _local(x.tag) == "Identificacion"), None)
    return _child_text(identification, "Numero") if identification is not None else None, _child_text(party, "Nombre")


def _parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(value[:10])
        except ValueError:
            return None


def _parse_xml(content: bytes) -> dict:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise HTTPException(400, f"XML inválido: {exc}")
    root_type = _local(root.tag)
    supported = {
        "FacturaElectronica": "FE", "FacturaElectronicaExportacion": "FEE",
        "TiqueteElectronico": "TE", "NotaCreditoElectronica": "NC",
        "NotaDebitoElectronica": "ND", "ReciboElectronicoPago": "REP",
    }
    if root_type not in supported:
        raise HTTPException(400, f"Tipo XML no soportado: {root_type}")
    namespace = root.tag.split("}")[0].strip("{") if "}" in root.tag else ""
    version_match = re.search(r"(?:v|/)(\d+\.\d+)(?:/|$)", namespace)
    version = version_match.group(1) if version_match else None
    issuer_id, issuer_name = _party(root, "Emisor")
    receiver_id, receiver_name = _party(root, "Receptor")
    currency = _child_text(root, "CodigoMoneda", "CRC")
    exchange = _money(_child_text(root, "TipoCambio", 1))
    lines = []
    for index, node in enumerate((x for x in root.iter() if _local(x.tag) == "LineaDetalle"), 1):
        taxes = [x for x in list(node) if _local(x.tag) == "Impuesto"]
        tax_amount = sum((_money(_child_text(x, "Monto")) for x in taxes), Decimal("0"))
        tax_rate = sum((_money(_child_text(x, "Tarifa")) for x in taxes), Decimal("0"))
        exemption = sum((_money(_child_text(x, "MontoExoneracion")) for x in taxes), Decimal("0"))
        discount = sum((_money(_child_text(x, "MontoDescuento")) for x in node.iter() if _local(x.tag) == "Descuento"), Decimal("0"))
        lines.append({
            "line_number": int(_child_text(node, "NumeroLinea", index)),
            "cabys_code": _child_text(node, "CodigoCABYS") or _child_text(node, "CodigoCabys"),
            "description": _child_text(node, "Detalle", ""),
            "quantity": _money(_child_text(node, "Cantidad")),
            "unit_code": _child_text(node, "UnidadMedida"),
            "unit_price": _money(_child_text(node, "PrecioUnitario")),
            "subtotal": _money(_child_text(node, "SubTotal")),
            "discount_amount": discount,
            "tax_code": _child_text(taxes[0], "Codigo") if taxes else None,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "exemption_amount": exemption,
            "total": _money(_child_text(node, "MontoTotalLinea")),
        })
    return {
        "document_type": supported[root_type], "document_number": _child_text(root, "NumeroConsecutivo"),
        "electronic_key": _child_text(root, "Clave"), "schema_version": version,
        "issuer_identification": issuer_id, "issuer_name": issuer_name,
        "receiver_identification": receiver_id, "receiver_name": receiver_name,
        "economic_activity": _child_text(root, "CodigoActividadEmisor") or _child_text(root, "CodigoActividad"),
        "issue_datetime": _parse_datetime(_child_text(root, "FechaEmision")),
        "currency_code": currency, "exchange_rate": exchange,
        "subtotal": _money(_child_text(root, "TotalVentaNeta")),
        "discount_amount": _money(_child_text(root, "TotalDescuentos")),
        "exempt_amount": _money(_child_text(root, "TotalExento")) + _money(_child_text(root, "TotalExonerado")),
        "tax_amount": _money(_child_text(root, "TotalImpuesto")),
        "total": _money(_child_text(root, "TotalComprobante")), "lines": lines,
    }


def _save_document(cur, direction, data, *, xml_hash=None, xml_path=None, xml_content=None, source_table=None, source_id=None, user=None):
    cur.execute("""
        INSERT INTO tax_electronic_documents(
          direction,document_type,document_number,electronic_key,xml_hash,schema_version,
          issuer_identification,issuer_name,receiver_identification,receiver_name,economic_activity,
          issue_datetime,currency_code,exchange_rate,subtotal,discount_amount,exempt_amount,tax_amount,total,
          status,hacienda_status,xml_path,xml_content,source_table,source_id,metadata,created_by)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PENDING','PENDING',%s,%s,%s,%s,%s,%s)
        ON CONFLICT(direction,source_table,source_id) DO UPDATE SET
          document_number=EXCLUDED.document_number,electronic_key=COALESCE(EXCLUDED.electronic_key,tax_electronic_documents.electronic_key),
          issue_datetime=EXCLUDED.issue_datetime,currency_code=EXCLUDED.currency_code,subtotal=EXCLUDED.subtotal,
          tax_amount=EXCLUDED.tax_amount,total=EXCLUDED.total,xml_path=COALESCE(EXCLUDED.xml_path,tax_electronic_documents.xml_path),
          xml_content=COALESCE(EXCLUDED.xml_content,tax_electronic_documents.xml_content),
          updated_at=NOW()
        RETURNING id
    """, (direction,data["document_type"],data.get("document_number"),data.get("electronic_key"),xml_hash,
           data.get("schema_version"),data.get("issuer_identification"),data.get("issuer_name"),
           data.get("receiver_identification"),data.get("receiver_name"),data.get("economic_activity"),
           data.get("issue_datetime"),data.get("currency_code") or "CRC",data.get("exchange_rate") or 1,
           data.get("subtotal") or 0,data.get("discount_amount") or 0,data.get("exempt_amount") or 0,
           data.get("tax_amount") or 0,data.get("total") or 0,xml_path,xml_content,source_table,str(source_id) if source_id is not None else None,
           Json({"quality_origin": "XML" if xml_hash else "ERP_SYNC"}),user))
    document_id = cur.fetchone()["id"]
    if data.get("lines"):
        cur.execute("DELETE FROM tax_document_lines WHERE document_id=%s", (document_id,))
        for line in data["lines"]:
            cur.execute("""
                INSERT INTO tax_document_lines(document_id,line_number,cabys_code,description,quantity,unit_code,
                  unit_price,subtotal,discount_amount,tax_code,tax_rate,tax_amount,exemption_amount,total)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (document_id,line["line_number"],line.get("cabys_code"),line.get("description"),line.get("quantity",0),
                   line.get("unit_code"),line.get("unit_price",0),line.get("subtotal",0),line.get("discount_amount",0),
                   line.get("tax_code"),line.get("tax_rate",0),line.get("tax_amount",0),line.get("exemption_amount",0),line.get("total",0)))
    return document_id


def _ensure_purchase_obligation(cur, data, xml_path):
    reference=data.get("electronic_key") or data.get("document_number")
    if not reference:
        return None
    cur.execute("SELECT id FROM payment_obligations WHERE reference=%s AND active=TRUE ORDER BY id LIMIT 1",(reference,))
    existing=cur.fetchone()
    if existing:
        return existing["id"]
    issue_value=data.get("issue_datetime") or datetime.now()
    issue=issue_value.date() if hasattr(issue_value,"date") else issue_value
    due=issue+timedelta(days=30)
    is_credit=data.get("document_type") in {"NC","NCE"}
    total=-(abs(data.get("total") or 0)) if is_credit else data.get("total") or 0
    cur.execute("""INSERT INTO payment_obligations(record_type,payee_type,payee_name,obligation_type,reference,
      issue_date,due_date,country,currency,total,balance,status,origin,file_xml,active,notes,created_at,updated_at)
      VALUES('OBLIGATION','SUPPLIER',%s,%s,%s,%s,%s,'Costa Rica',%s,%s,%s,'PENDING','EMAIL',%s,TRUE,%s,NOW(),NOW()) RETURNING id""",
                (data.get("issuer_name") or "PROVEEDOR POR VALIDAR","SUPPLIER_CREDIT_NOTE" if is_credit else "SUPPLIER_INVOICE",
                 reference,issue,due,data.get("currency_code") or "CRC",total,total,xml_path,"Importado automáticamente desde correo fiscal"))
    return cur.fetchone()["id"]


@router.post("/sync")
def sync_tax_documents(conn=Depends(get_db)):
    _ensure_schema(conn)
    counts = {"sales": 0, "purchases": 0}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id,numero_factura,clave_electronica,fecha_emision,moneda,total,estado,xml_path,pdf_path FROM factura")
            for row in cur.fetchall():
                data = {"document_type":"FE","document_number":row["numero_factura"],"electronic_key":row.get("clave_electronica"),
                        "issue_datetime":row.get("fecha_emision"),"currency_code":row.get("moneda") or "CRC","total":row.get("total") or 0}
                doc_id = _save_document(cur,"SALE",data,source_table="factura",source_id=row["id"],xml_path=row.get("xml_path"),user="SYSTEM_SYNC")
                cur.execute("UPDATE tax_electronic_documents SET pdf_path=%s,status=%s WHERE id=%s",(row.get("pdf_path"),"ACCEPTED" if str(row.get("estado","")).upper() in {"PAGADA","EMITIDA","ACEPTADA"} else "PENDING",doc_id))
                cur.execute("SELECT * FROM factura_detalle WHERE factura_id=%s ORDER BY id",(row["id"],))
                details=cur.fetchall()
                if details:
                    cur.execute("DELETE FROM tax_document_lines WHERE document_id=%s",(doc_id,))
                    for index,line in enumerate(details,1):
                        cur.execute("INSERT INTO tax_document_lines(document_id,line_number,description,quantity,unit_price,tax_amount,total) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                                    (doc_id,index,line.get("descripcion"),line.get("cantidad") or 0,line.get("precio_unitario") or 0,line.get("impuesto") or 0,line.get("total_linea") or 0))
                counts["sales"] += 1
            cur.execute("""
                INSERT INTO tax_electronic_documents(
                  direction,document_type,document_number,electronic_key,issuer_name,issue_datetime,
                  currency_code,total,status,hacienda_status,xml_path,pdf_path,source_table,source_id,metadata,created_by)
                SELECT 'PURCHASE',CASE WHEN UPPER(COALESCE(obligation_type,'')) LIKE '%%CREDIT%%' THEN 'NC' ELSE 'FE' END,
                  reference,CASE WHEN LENGTH(COALESCE(reference,''))=50 THEN reference END,payee_name,issue_date,
                  COALESCE(currency,'CRC'),COALESCE(total,0),CASE WHEN UPPER(COALESCE(status,''))='PAID' THEN 'ACCEPTED' ELSE 'PENDING' END,
                  'PENDING',file_xml,file_pdf,'payment_obligations',id::text,
                  jsonb_build_object('quality_origin','ERP_SYNC'),'SYSTEM_SYNC'
                FROM payment_obligations WHERE active=TRUE AND record_type='OBLIGATION'
                ON CONFLICT(direction,source_table,source_id) DO UPDATE SET
                  document_number=EXCLUDED.document_number,electronic_key=EXCLUDED.electronic_key,
                  issuer_name=EXCLUDED.issuer_name,issue_datetime=EXCLUDED.issue_datetime,currency_code=EXCLUDED.currency_code,
                  total=EXCLUDED.total,status=EXCLUDED.status,xml_path=COALESCE(EXCLUDED.xml_path,tax_electronic_documents.xml_path),
                  pdf_path=COALESCE(EXCLUDED.pdf_path,tax_electronic_documents.pdf_path),updated_at=NOW()
            """)
            cur.execute("SELECT COUNT(*) count FROM payment_obligations WHERE active=TRUE AND record_type='OBLIGATION'")
            counts["purchases"] = cur.fetchone()["count"]
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise HTTPException(500,f"Error sincronizando registro fiscal: {exc}")
    return {"message":"Registro fiscal sincronizado","counts":counts}


@router.post("/documents/upload-xml")
async def upload_tax_xml(direction: str = Form(...), user: str = Form("ERP_USER"), file: UploadFile = File(...), conn=Depends(get_db)):
    _ensure_schema(conn)
    direction=direction.upper()
    if direction not in {"SALE","PURCHASE"}: raise HTTPException(400,"direction debe ser SALE o PURCHASE")
    content=await file.read()
    if not content or len(content)>10_000_000: raise HTTPException(400,"XML vacío o mayor a 10 MB")
    data=_parse_xml(content)
    digest=hashlib.sha256(content).hexdigest()
    folder=Path("storage/tax/xml")/datetime.now().strftime("%Y/%m")
    folder.mkdir(parents=True,exist_ok=True)
    safe=re.sub(r"[^A-Za-z0-9_.-]","_",file.filename or "document.xml")
    path=folder/f"{digest[:12]}_{safe}"
    path.write_bytes(content)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id,source_table,source_id,xml_hash FROM tax_electronic_documents WHERE direction=%s AND (xml_hash=%s OR (electronic_key=%s AND %s IS NOT NULL))",(direction,digest,data.get("electronic_key"),data.get("electronic_key")))
            duplicate=cur.fetchone()
            if duplicate and duplicate.get("xml_hash"):
                raise HTTPException(409,f"Documento duplicado; registro fiscal {duplicate['id']}")
            if duplicate:
                doc_id=_save_document(cur,direction,data,xml_hash=digest,xml_path=str(path),xml_content=content,
                                      source_table=duplicate["source_table"],source_id=duplicate["source_id"],user=user)
                cur.execute("UPDATE tax_electronic_documents SET xml_hash=%s,schema_version=%s,issuer_identification=%s,issuer_name=%s,receiver_identification=%s,receiver_name=%s,economic_activity=%s,discount_amount=%s,exempt_amount=%s,updated_at=NOW() WHERE id=%s",
                            (digest,data.get("schema_version"),data.get("issuer_identification"),data.get("issuer_name"),data.get("receiver_identification"),data.get("receiver_name"),data.get("economic_activity"),data.get("discount_amount",0),data.get("exempt_amount",0),doc_id))
            else:
                doc_id=_save_document(cur,direction,data,xml_hash=digest,xml_path=str(path),xml_content=content,source_table="xml_upload",source_id=digest,user=user)
            if direction=="PURCHASE":
                _ensure_purchase_obligation(cur,data,str(path))
        conn.commit()
    except HTTPException:
        conn.rollback(); path.unlink(missing_ok=True); raise
    except Exception as exc:
        conn.rollback(); path.unlink(missing_ok=True); raise HTTPException(500,str(exc))
    return {"id":doc_id,"document":data,"warnings":(["El XML no indica versión 4.4"] if data.get("schema_version")!="4.4" else [])}


@router.post("/documents/{document_id}/hacienda-response")
async def upload_hacienda_response(document_id:int,file:UploadFile=File(...),conn=Depends(get_db)):
    _ensure_schema(conn); content=await file.read()
    try: root=ET.fromstring(content)
    except ET.ParseError as exc: raise HTTPException(400,f"Respuesta XML inválida: {exc}")
    message=_child_text(root,"Mensaje") or _child_text(root,"IndEstado") or ""
    detail=_child_text(root,"DetalleMensaje") or _child_text(root,"RespuestaXml") or ""
    status={"1":"ACCEPTED","2":"PARTIAL","3":"REJECTED"}.get(str(message),str(message).upper() or "PENDING")
    folder=Path("storage/tax/responses")/datetime.now().strftime("%Y/%m"); folder.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(content).hexdigest(); path=folder/f"{document_id}_{digest[:12]}.xml"; path.write_bytes(content)
    with conn.cursor() as cur:
        cur.execute("UPDATE tax_electronic_documents SET hacienda_status=%s,hacienda_message=%s,response_xml_path=%s,response_xml_content=%s,status=%s,updated_at=NOW() WHERE id=%s RETURNING id",
                    (status,detail,str(path),content,status,document_id))
        if not cur.fetchone(): path.unlink(missing_ok=True); raise HTTPException(404,"Documento no encontrado")
    conn.commit(); return {"id":document_id,"hacienda_status":status,"message":detail}


@router.post("/documents/import-hacienda-response")
async def import_hacienda_response(file:UploadFile=File(...),conn=Depends(get_db)):
    _ensure_schema(conn); content=await file.read()
    try: root=ET.fromstring(content)
    except ET.ParseError as exc: raise HTTPException(400,f"Respuesta XML inválida: {exc}")
    if _local(root.tag) not in {"MensajeHacienda","RespuestaHacienda"}:
        raise HTTPException(400,"El XML no es una respuesta de Hacienda")
    key=_child_text(root,"Clave"); message=_child_text(root,"Mensaje") or _child_text(root,"IndEstado") or ""
    detail=_child_text(root,"DetalleMensaje") or _child_text(root,"RespuestaXml") or ""
    if not key: raise HTTPException(400,"Respuesta de Hacienda sin clave")
    status={"1":"ACCEPTED","2":"PARTIAL","3":"REJECTED"}.get(str(message),str(message).upper() or "PENDING")
    digest=hashlib.sha256(content).hexdigest(); folder=Path("storage/tax/responses")/datetime.now().strftime("%Y/%m"); folder.mkdir(parents=True,exist_ok=True)
    path=folder/f"{digest[:12]}_hacienda.xml"; path.write_bytes(content)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT id FROM tax_electronic_documents WHERE electronic_key=%s ORDER BY id DESC LIMIT 1",(key,)); doc=cur.fetchone()
        if not doc: path.unlink(missing_ok=True); raise HTTPException(404,"No existe un comprobante fiscal con la clave de esta respuesta")
        cur.execute("""UPDATE tax_electronic_documents SET hacienda_status=%s,hacienda_message=%s,response_xml_path=%s,
          response_xml_content=%s,status=%s,updated_at=NOW() WHERE id=%s""",(status,detail,str(path),content,status,doc["id"]))
    conn.commit(); return {"id":doc["id"],"electronic_key":key,"hacienda_status":status}


def _period_bounds(period):
    if not re.fullmatch(r"\d{4}-\d{2}",period): raise HTTPException(400,"Periodo debe tener formato YYYY-MM")
    start=date.fromisoformat(period+"-01"); end=(start.replace(day=28)+timedelta(days=4)).replace(day=1)
    return start,end


@router.get("/documents")
def list_documents(direction:str|None=None,period:str|None=None,status:str|None=None,quality_only:bool=False,conn=Depends(get_db)):
    _ensure_schema(conn); where=["1=1"]; params=[]
    if direction: where.append("d.direction=%s"); params.append(direction.upper())
    if period:
        start,end=_period_bounds(period); where.append("d.issue_datetime >= %s AND d.issue_datetime < %s"); params.extend([start,end])
    if status: where.append("d.hacienda_status=%s"); params.append(status.upper())
    quality="""(d.xml_path IS NULL OR d.electronic_key IS NULL OR d.hacienda_status='PENDING' OR
       NOT EXISTS(SELECT 1 FROM tax_document_lines l WHERE l.document_id=d.id) OR
       EXISTS(SELECT 1 FROM tax_document_lines l WHERE l.document_id=d.id AND (l.cabys_code IS NULL OR l.cabys_code='')) OR
       (d.electronic_key IS NOT NULL AND EXISTS(SELECT 1 FROM tax_electronic_documents x WHERE x.direction=d.direction AND x.electronic_key=d.electronic_key AND x.id<>d.id)))"""
    if quality_only: where.append(quality)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(f"""SELECT
          d.id,d.direction,d.document_type,d.document_number,d.electronic_key,d.xml_hash,d.schema_version,
          d.issuer_identification,d.issuer_name,d.receiver_identification,d.receiver_name,d.economic_activity,
          d.issue_datetime,d.currency_code,d.exchange_rate,d.subtotal,d.discount_amount,d.exempt_amount,
          d.tax_amount,d.total,d.status,d.hacienda_status,d.hacienda_message,d.xml_path,d.response_xml_path,
          d.pdf_path,d.source_table,d.source_id,d.metadata,d.created_by,d.created_at,d.updated_at,
          (SELECT COUNT(*) FROM tax_document_lines l WHERE l.document_id=d.id) line_count,
          (SELECT COUNT(*) FROM tax_document_lines l WHERE l.document_id=d.id AND COALESCE(l.cabys_code,'')='') missing_cabys_lines,
          (SELECT COUNT(*) FROM tax_electronic_documents x WHERE x.direction=d.direction AND x.electronic_key=d.electronic_key AND x.id<>d.id) duplicate_key_count
          FROM tax_electronic_documents d WHERE {' AND '.join(where)} ORDER BY issue_datetime DESC NULLS LAST,id DESC""",params)
        rows=cur.fetchall()
    return {"data":rows,"count":len(rows)}


@router.get("/books/{direction}")
def tax_book(direction:str,period:str,conn=Depends(get_db)):
    _ensure_schema(conn); direction=direction.upper()
    if direction not in {"SALE","PURCHASE"}: raise HTTPException(400,"Libro debe ser SALE o PURCHASE")
    start,end=_period_bounds(period)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT id,document_type,document_number,electronic_key,issue_datetime,currency_code,exchange_rate,
          issuer_identification,issuer_name,receiver_identification,receiver_name,subtotal,exempt_amount,tax_amount,total,
          hacienda_status,xml_path FROM tax_electronic_documents
          WHERE direction=%s AND issue_datetime >= %s AND issue_datetime < %s ORDER BY issue_datetime,document_number""",(direction,start,end))
        rows=cur.fetchall()
    totals={k:float(sum((_money(r[k]) for r in rows),Decimal("0"))) for k in ("subtotal","exempt_amount","tax_amount","total")}
    return {"period":period,"direction":direction,"data":rows,"totals":totals}


@router.get("/iva")
def tax_iva(period:str,conn=Depends(get_db)):
    _ensure_schema(conn); start,end=_period_bounds(period)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""SELECT direction,COALESCE(SUM(subtotal),0) subtotal,COALESCE(SUM(exempt_amount),0) exempt,
          COALESCE(SUM(tax_amount),0) tax,COALESCE(SUM(total),0) total,COUNT(*) documents,
          COUNT(*) FILTER(WHERE xml_path IS NULL) missing_xml,COUNT(*) FILTER(WHERE hacienda_status='PENDING') pending_hacienda
          FROM tax_electronic_documents WHERE issue_datetime >= %s AND issue_datetime < %s GROUP BY direction""",(start,end))
        by_direction={r["direction"]:r for r in cur.fetchall()}
        cur.execute("SELECT setting_key,setting_value FROM tax_settings WHERE setting_key IN ('IVA_DEBIT_ACCOUNT','IVA_CREDIT_ACCOUNT')")
        settings={r["setting_key"]:r["setting_value"] for r in cur.fetchall()}
        cur.execute("""SELECT account_code,COALESCE(SUM(debit),0) debit,COALESCE(SUM(credit),0) credit
          FROM accounting_lines l JOIN accounting_entries e ON e.id=l.entry_id
          WHERE e.entry_date >= %s AND e.entry_date < %s AND e.workflow_status='POSTED' AND account_code IN (%s,%s) GROUP BY account_code""",
                    (start,end,settings.get("IVA_DEBIT_ACCOUNT","2108"),settings.get("IVA_CREDIT_ACCOUNT","1131")))
        gl={r["account_code"]:r for r in cur.fetchall()}
        cur.execute("""SELECT
          COUNT(*) FILTER(WHERE NOT EXISTS(SELECT 1 FROM tax_document_lines x WHERE x.document_id=d.id)) documents_without_lines,
          COALESCE(SUM((SELECT COUNT(*) FROM tax_document_lines l WHERE l.document_id=d.id AND COALESCE(l.cabys_code,'')='')),0) missing_cabys
          FROM tax_electronic_documents d WHERE d.issue_datetime >= %s AND d.issue_datetime < %s""",(start,end))
        quality=cur.fetchone()
    sales=by_direction.get("SALE",{}); purchases=by_direction.get("PURCHASE",{})
    debit=_money(sales.get("tax")); credit=_money(purchases.get("tax")); net=debit-credit
    debit_gl=_money(gl.get(settings.get("IVA_DEBIT_ACCOUNT","2108"),{}).get("credit"))-_money(gl.get(settings.get("IVA_DEBIT_ACCOUNT","2108"),{}).get("debit"))
    credit_gl=_money(gl.get(settings.get("IVA_CREDIT_ACCOUNT","1131"),{}).get("debit"))-_money(gl.get(settings.get("IVA_CREDIT_ACCOUNT","1131"),{}).get("credit"))
    return {"period":period,"fiscal":{"sales_tax":float(debit),"purchase_tax_credit":float(credit),"net_tax":float(net),
      "sales_total":float(_money(sales.get('total'))),"purchase_total":float(_money(purchases.get('total')))},
      "accounting":{"debit_tax":float(debit_gl),"credit_tax":float(credit_gl),"net_tax":float(debit_gl-credit_gl)},
      "differences":{"debit":float(debit-debit_gl),"credit":float(credit-credit_gl),"net":float(net-(debit_gl-credit_gl))},
      "quality":{"missing_xml":int(sales.get("missing_xml",0) or 0)+int(purchases.get("missing_xml",0) or 0),
      "pending_hacienda":int(sales.get("pending_hacienda",0) or 0)+int(purchases.get("pending_hacienda",0) or 0),**quality},
      "ready_to_file": all(_money(x)==0 for x in (debit-debit_gl,credit-credit_gl)) and not any(int(quality.get(k,0) or 0)>0 for k in quality)}


class CabysItem(BaseModel):
    code:str; description:str; suggested_tax_rate:Decimal|None=None; active:bool=True; source:str="MANUAL"


@router.get("/cabys")
def search_cabys(search:str="",limit:int=Query(100,ge=1,le=500),conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM tax_cabys_catalog WHERE active=TRUE AND (code ILIKE %s OR description ILIKE %s) ORDER BY code LIMIT %s",(f"%{search}%",f"%{search}%",limit))
        rows=cur.fetchall()
        # Consulta oficial bajo demanda y caché local para respetar los límites de Hacienda.
        if search and len(search.strip()) >= 3 and not rows:
            params={"codigo":search.strip()} if re.fullmatch(r"\d{13}",search.strip()) else {"q":search.strip(),"top":min(limit,20)}
            try:
                req=Request("https://api.hacienda.go.cr/fe/cabys?"+urlencode(params),headers={"User-Agent":"ERP-SOM/1.0"})
                with urlopen(req,timeout=12) as response:
                    official=json.loads(response.read().decode("utf-8"))
                for item in official.get("cabys",[]):
                    cur.execute("""INSERT INTO tax_cabys_catalog(code,description,suggested_tax_rate,source)
                      VALUES(%s,%s,%s,'HACIENDA_API') ON CONFLICT(code) DO UPDATE SET
                      description=EXCLUDED.description,suggested_tax_rate=EXCLUDED.suggested_tax_rate,
                      source='HACIENDA_API',updated_at=NOW() RETURNING *""",
                                (item.get("codigo"),item.get("descripcion") or item.get("codigo"),item.get("impuesto")))
                    rows.append(cur.fetchone())
                conn.commit()
            except Exception:
                conn.rollback()  # La indisponibilidad externa no impide usar el catálogo en caché.
    return {"data":rows,"source":"HACIENDA_API" if any(r.get("source")=="HACIENDA_API" for r in rows) else "LOCAL_CACHE"}


@router.put("/cabys/{code}")
def upsert_cabys(code:str,payload:CabysItem,conn=Depends(get_db)):
    _ensure_schema(conn)
    if not re.fullmatch(r"\d{13}",code): raise HTTPException(400,"El código CAByS debe contener 13 dígitos")
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO tax_cabys_catalog(code,description,suggested_tax_rate,active,source) VALUES(%s,%s,%s,%s,%s)
          ON CONFLICT(code) DO UPDATE SET description=EXCLUDED.description,suggested_tax_rate=EXCLUDED.suggested_tax_rate,
          active=EXCLUDED.active,source=EXCLUDED.source,updated_at=NOW()""",(code,payload.description,payload.suggested_tax_rate,payload.active,payload.source))
    conn.commit(); return {"message":"CAByS guardado","code":code}


@router.get("/obligations")
def obligations(year:int|None=None,period:str|None=None,pending_only:bool=False,conn=Depends(get_db)):
    _ensure_schema(conn); year=year or date.today().year; results=[]
    min_period = period if pending_only and period else date.today().strftime("%Y-%m") if pending_only else None
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT * FROM tax_obligations WHERE active=TRUE ORDER BY tax_code")
        for item in cur.fetchall():
            due_dates=[]
            if item["periodicity"]=="MONTHLY" and item.get("due_day"):
                for month in range(1,13):
                    item_period = f"{year}-{month:02d}"
                    if min_period and item_period < min_period:
                        continue
                    nxt=date(year+(month==12),(month%12)+1,1)
                    due_dates.append({"period":item_period,"estimated_due_date":min(nxt-timedelta(days=1),date(nxt.year,nxt.month,min(item["due_day"],28))).isoformat()})
            results.append({**item,"calendar":due_dates})
    return {"year":year,"data":results,"warning":"Fechas estimadas; valide feriados y prórrogas en el calendario oficial de Hacienda."}


class Setting(BaseModel): value:str; user:str="ERP_USER"


@router.get("/settings")
def settings(conn=Depends(get_db)):
    _ensure_schema(conn)
    with conn.cursor(cursor_factory=RealDictCursor) as cur: cur.execute("SELECT * FROM tax_settings ORDER BY setting_key"); rows=cur.fetchall()
    return {"data":rows}


@router.put("/settings/{key}")
def update_setting(key:str,payload:Setting,conn=Depends(get_db)):
    _ensure_schema(conn)
    allowed={"IVA_DEBIT_ACCOUNT","IVA_CREDIT_ACCOUNT","REQUIRE_CABYS","ELECTRONIC_DOCUMENT_VERSION"}
    if key not in allowed: raise HTTPException(400,"Configuración no permitida")
    with conn.cursor() as cur:
        cur.execute("INSERT INTO tax_settings(setting_key,setting_value,updated_by) VALUES(%s,%s,%s) ON CONFLICT(setting_key) DO UPDATE SET setting_value=EXCLUDED.setting_value,updated_by=EXCLUDED.updated_by,updated_at=NOW()",(key,payload.value,payload.user))
    conn.commit(); return {"message":"Configuración fiscal actualizada"}
