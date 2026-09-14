from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from api_client import (
    post_corporate_card_history_api,
    post_corporate_card_statement_pdf_api,
    upload_tax_response_auto_api,
    upload_tax_xml_api,
)


ACCOUNT="gastos@mslogisticsgroup.com"
MCI_ACCOUNT="operations@xtravon.com"
CARD_ACCOUNT="contabilidad@mslogisticsgroup.com"
SAFE_DEFAULT_FOLDER="xml gastos electronicos"
DEFAULT_FOLDER="xml gastos electrónicos"
DEFAULT_RECEIVED_SUBFOLDER="FE recibidas"
MAX_ATTACHMENT_BYTES=20*1024*1024
MAX_ZIP_MEMBERS=50
STARTUP_SYNC_DELAY_SECONDS=180
DEFAULT_FISCAL_MAILBOXES=[
    {
        "company_code": "MSL-CR",
        "account": ACCOUNT,
        "folder": f"{SAFE_DEFAULT_FOLDER}/{DEFAULT_RECEIVED_SUBFOLDER}",
    },
    {
        "company_code": "MCI-CR",
        "account": MCI_ACCOUNT,
        "folder": DEFAULT_RECEIVED_SUBFOLDER,
    },
]
_scan_lock=threading.Lock()
_background_lock=threading.Lock()
_background_started=False


def _data_dir():
    path=Path(os.getenv("LOCALAPPDATA") or Path.home())/"ERP-SOM"
    path.mkdir(parents=True,exist_ok=True); return path


def _config_path(): return _data_dir()/"outlook_fiscal_config.json"
def _state_path(): return _data_dir()/"outlook_fiscal_state.json"


def load_config():
    default={
        "enabled": True,
        "interval_minutes": 15,
        "account": ACCOUNT,
        "folder": f"{SAFE_DEFAULT_FOLDER}/{DEFAULT_RECEIVED_SUBFOLDER}",
        "fiscal_mailboxes": DEFAULT_FISCAL_MAILBOXES,
        "card_account": CARD_ACCOUNT,
        "batch_size": 50,
        "process_corporate_cards": True,
        "corporate_card_years": [2025, 2026],
    }
    try:
        saved=json.loads(_config_path().read_text(encoding="utf-8")); default.update(saved if isinstance(saved,dict) else {})
    except Exception: pass
    default["folder"]=_repair_mojibake(default.get("folder") or SAFE_DEFAULT_FOLDER)
    mailboxes=default.get("fiscal_mailboxes")
    if not isinstance(mailboxes,list) or not mailboxes:
        mailboxes=DEFAULT_FISCAL_MAILBOXES
    normalized_mailboxes=[]
    seen=set()
    for item in mailboxes:
        if not isinstance(item,dict):
            continue
        account=str(item.get("account") or "").strip()
        company=str(item.get("company_code") or "").strip() or "MSL-CR"
        folder=_repair_mojibake(item.get("folder") or DEFAULT_RECEIVED_SUBFOLDER)
        key=(company.upper(),account.lower(),_normalized(folder))
        if account and key not in seen:
            seen.add(key)
            normalized_mailboxes.append({"company_code":company.upper(),"account":account,"folder":folder})
    for item in DEFAULT_FISCAL_MAILBOXES:
        key=(item["company_code"].upper(),item["account"].lower(),_normalized(item["folder"]))
        if key not in seen:
            seen.add(key)
            normalized_mailboxes.append(dict(item))
    default["fiscal_mailboxes"]=normalized_mailboxes
    return default


def save_config(config):
    current=load_config(); current.update(config)
    tmp=_config_path().with_suffix(".tmp"); tmp.write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding="utf-8"); os.replace(tmp,_config_path())
    return current


def start_background_sync():
    """Arranca el importador fiscal local al login y lo repite segun configuracion."""
    global _background_started
    with _background_lock:
        if _background_started:
            return False
        _background_started=True

    def worker():
        last_run=time.time()
        while True:
            try:
                config=load_config()
                interval=max(1,int(config.get("interval_minutes") or 15))*60
                elapsed=time.time()-last_run
                if config.get("enabled") and elapsed>=min(interval,STARTUP_SYNC_DELAY_SECONDS):
                    last_run=time.time()
                    try:
                        scan_and_import(max_messages=int(config.get("batch_size") or 50))
                    except Exception as exc:
                        print(f"Outlook fiscal automatico: {exc}")
            except Exception as exc:
                print(f"Outlook fiscal scheduler: {exc}")
            time.sleep(60)

    threading.Thread(target=worker,daemon=True).start()
    return True


def _load_state():
    try:
        state=json.loads(_state_path().read_text(encoding="utf-8")); return state if isinstance(state,dict) else {}
    except Exception:return {}


def _save_state(state):
    if len(state)>20000:
        runtime=state.get("__runtime__")
        state=dict(list(state.items())[-20000:])
        if runtime:
            state["__runtime__"]=runtime
    tmp=_state_path().with_suffix(".tmp"); tmp.write_text(json.dumps(state,ensure_ascii=False,default=str),encoding="utf-8"); os.replace(tmp,_state_path())


def _update_runtime_status(**values):
    state=_load_state()
    runtime=state.get("__runtime__",{})
    if not isinstance(runtime,dict):
        runtime={}
    runtime.update(values)
    state["__runtime__"]=runtime
    _save_state(state)


def _repair_mojibake(value):
    text=str(value or "").strip()
    if "Ã" not in text and "Ă" not in text and "Â" not in text:
        return text
    try:
        return text.encode("latin1").decode("utf-8")
    except Exception:
        return text


def _normalized(value):
    text=_repair_mojibake(value)
    return "".join(x for x in unicodedata.normalize("NFKD",str(text or "").lower()) if not unicodedata.combining(x)).strip()


def _split_folder_path(folder_name):
    text=_repair_mojibake(folder_name or "").replace("\\","/").replace(">","/")
    return [part.strip() for part in text.split("/") if part.strip()]


def _folder_candidates(folder_name):
    parts=_split_folder_path(folder_name)
    leaf=parts[-1] if parts else folder_name
    candidates=[
        folder_name,
        _repair_mojibake(folder_name),
        leaf,
        _repair_mojibake(leaf),
        f"{DEFAULT_FOLDER}/{DEFAULT_RECEIVED_SUBFOLDER}",
        f"{SAFE_DEFAULT_FOLDER}/{DEFAULT_RECEIVED_SUBFOLDER}",
        DEFAULT_RECEIVED_SUBFOLDER,
        SAFE_DEFAULT_FOLDER,
        "xml gastos electronicos",
        "xml gastos electrónicos",
        "fe recibidas",
        "facturas recibidas",
    ]
    seen=set(); output=[]
    for item in candidates:
        key=_normalized(item)
        if key and key not in seen:
            seen.add(key); output.append(item)
    return output


def _iter_folders(folder,depth=0,max_depth=8):
    if depth>max_depth:
        return
    for index in range(1,folder.Folders.Count+1):
        child=folder.Folders.Item(index)
        yield child
        yield from _iter_folders(child,depth+1,max_depth)


def _child_by_name(folder, name):
    wanted=_normalized(name)
    for index in range(1,folder.Folders.Count+1):
        child=folder.Folders.Item(index)
        if _normalized(child.Name)==wanted:
            return child
    return None


def _resolve_folder_path(root, folder_name):
    parts=_split_folder_path(folder_name)
    if not parts:
        return None
    current=root
    if _normalized(getattr(root, "Name", "")) == _normalized(parts[0]):
        parts=parts[1:]
    for part in parts:
        child=_child_by_name(current, part)
        if child is None:
            return None
        current=child
    return current


def _prefer_received_subfolder(folder, requested_name):
    requested_leaf=(_split_folder_path(requested_name) or [""])[-1]
    if _normalized(requested_leaf)==_normalized(DEFAULT_RECEIVED_SUBFOLDER):
        return folder
    child=_child_by_name(folder, DEFAULT_RECEIVED_SUBFOLDER)
    return child or folder


def _find_folder(namespace,account,folder_name):
    target_store=None
    account_norm=_normalized(account)
    legacy_gastos=account_norm==_normalized(ACCOUNT)
    for index in range(1,namespace.Stores.Count+1):
        store=namespace.Stores.Item(index)
        store_name=_normalized(store.DisplayName)
        if store_name==account_norm or account_norm in store_name or (legacy_gastos and store_name.startswith("gastos@")):
            target_store=store; break
    if target_store is None: raise RuntimeError(f"Outlook no contiene el buzón {account}")
    root=target_store.GetRootFolder()
    direct=_resolve_folder_path(root,folder_name)
    if direct is not None:
        return target_store.DisplayName,_prefer_received_subfolder(direct,folder_name)
    for candidate in _folder_candidates(folder_name):
        direct=_resolve_folder_path(root,candidate)
        if direct is not None:
            return target_store.DisplayName,direct
    wanted={_normalized(item) for item in _folder_candidates(folder_name)}
    for folder in _iter_folders(root):
        if _normalized(folder.Name) in wanted:
            return target_store.DisplayName,folder
    available=[str(folder.Name) for folder in _iter_folders(root,max_depth=2)]
    raise RuntimeError(f"No se encontró la carpeta '{folder_name}'. Carpetas disponibles: {', '.join(available)}")


def _find_inbox(namespace, account):
    account_norm=_normalized(account)
    for index in range(1,namespace.Stores.Count+1):
        store=namespace.Stores.Item(index)
        store_name=_normalized(store.DisplayName)
        if store_name==account_norm or account_norm in store_name:
            root=store.GetRootFolder()
            for folder in _iter_folders(root,max_depth=2):
                if _normalized(folder.Name) in {"inbox","bandeja de entrada","entrada"}:
                    return store.DisplayName,folder
            return store.DisplayName,root
    raise RuntimeError(f"Outlook no contiene el buzÃ³n {account}")


def inspect_outlook():
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        namespace=win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        config=load_config()
        fiscal=[]
        for mailbox in config.get("fiscal_mailboxes") or [{"company_code":"MSL-CR","account":config["account"],"folder":config["folder"]}]:
            try:
                store,folder=_find_folder(namespace,mailbox["account"],mailbox["folder"])
                fiscal.append({
                    "connected": True,
                    "company_code": mailbox.get("company_code") or "MSL-CR",
                    "store": str(store),
                    "account": mailbox.get("account"),
                    "folder": str(folder.Name),
                    "folder_path": str(getattr(folder,"FolderPath",folder.Name)),
                    "message_count": int(folder.Items.Count),
                })
            except Exception as exc:
                fiscal.append({
                    "connected": False,
                    "company_code": mailbox.get("company_code") or "MSL-CR",
                    "account": mailbox.get("account"),
                    "folder": mailbox.get("folder"),
                    "error": str(exc),
                })
        primary=next((item for item in fiscal if item.get("connected")), fiscal[0] if fiscal else {})
        return {"connected":any(item.get("connected") for item in fiscal),"store":primary.get("store",""),"folder":primary.get("folder",""),"folder_path":primary.get("folder_path",""),"message_count":primary.get("message_count",0),"fiscal_mailboxes":fiscal}
    finally: pythoncom.CoUninitialize()


def _xml_files(filename,path,temp_dir):
    if path.stat().st_size>MAX_ATTACHMENT_BYTES: raise ValueError("Adjunto mayor a 20 MB")
    if filename.lower().endswith(".xml"): return [path]
    if not filename.lower().endswith(".zip"): return []
    output=[]
    with zipfile.ZipFile(path) as archive:
        members=[x for x in archive.infolist() if not x.is_dir()]
        if len(members)>MAX_ZIP_MEMBERS: raise ValueError("ZIP con más de 50 archivos")
        for member in members:
            parts=Path(member.filename).parts
            if Path(member.filename).is_absolute() or ".." in parts: raise ValueError("ZIP con ruta insegura")
            if member.file_size>MAX_ATTACHMENT_BYTES: raise ValueError("XML comprimido mayor a 20 MB")
            if member.filename.lower().endswith(".xml"):
                data=archive.read(member); digest=hashlib.sha256(data).hexdigest(); target=Path(temp_dir)/f"{digest[:12]}_{Path(member.filename).name}"
                target.write_bytes(data); output.append(target)
    return output


def _is_corporate_card_pdf(filename, subject=""):
    text=_normalized(f"{filename} {subject}")
    return filename.lower().endswith(".pdf") and (
        "estadocta" in text
        or "estado de cuenta" in text
        or "tarjeta de credito" in text
        or "baccredomatic" in text
        or "bac" in text
    )


def _message_year(message):
    try:
        return int(getattr(message,"ReceivedTime").year)
    except Exception:
        return None


def _scan_card_folder(folder,temp_dir,state,summary,years):
    items=folder.Items; items.Sort("[ReceivedTime]",True)
    scanned=0
    for index in range(1,items.Count+1):
        if scanned>=20000:
            break
        scanned+=1
        message=items.Item(index)
        msg_year=_message_year(message)
        if years and msg_year and msg_year not in years:
            continue
        try:
            attachment_count=int(message.Attachments.Count)
        except Exception:
            continue
        subject=str(getattr(message,"Subject","") or "")
        received=str(getattr(message,"ReceivedTime","") or "")
        pending=[]
        for attachment_index in range(1,attachment_count+1):
            attachment=message.Attachments.Item(attachment_index); filename=str(attachment.FileName or "")
            if not _is_corporate_card_pdf(filename,subject):
                continue
            key=hashlib.sha256(f"CARD|{message.EntryID}|{attachment_index}|{filename}|{getattr(attachment,'Size',0)}".encode()).hexdigest()
            if state.get(key,{}).get("status") in {"IMPORTED","DUPLICATE"}:
                continue
            pending.append((attachment,key,filename))
        if not pending:
            continue
        summary["messages"]+=1
        for attachment,key,filename in pending:
            summary["attachments"]+=1; summary["card_pdfs"]+=1
            try:
                safe=hashlib.sha256(key.encode()).hexdigest()[:12]+"_"+Path(filename).name
                attachment_path=Path(temp_dir)/safe; attachment.SaveAsFile(str(attachment_path))
                response=post_corporate_card_statement_pdf_api(str(attachment_path))
                if response.get("status")=="exists":
                    summary["card_duplicates"]+=1; status="DUPLICATE"; detail="Estado BAC ya importado"
                else:
                    summary["card_imported"]+=1; status="IMPORTED"; detail=f"Estado BAC {response.get('statement',{}).get('statement_period','')} movimientos {response.get('transactions_inserted',0)}"
                state[key]={"status":status,"filename":filename,"updated_at":received}
            except Exception as exc:
                summary["card_errors"]+=1; summary["errors"]+=1; status="ERROR"; detail=str(exc)
                state[key]={"status":"ERROR","filename":filename,"updated_at":received}
            summary["results"].append({"received":received,"subject":subject,"filename":filename,"status":status,"detail":detail})
        _save_state(state)


def _card_scan_folders(root_folder):
    folders=[root_folder]
    seen={str(getattr(root_folder,"FolderPath",root_folder))}
    for child in _iter_folders(root_folder,max_depth=4):
        name=_normalized(getattr(child,"Name",""))
        path=str(getattr(child,"FolderPath",child))
        if path in seen:
            continue
        if "bac" in name or "tarjeta" in name or "notificacion" in name or "estado" in name:
            folders.append(child)
            seen.add(path)
    return folders


def scan_corporate_card_history(progress=None):
    if not _scan_lock.acquire(blocking=False): return {"status":"busy","message":"Ya existe una revisiÃ³n de Outlook en curso","results":[]}
    import pythoncom
    import win32com.client
    config=load_config(); state=_load_state(); results=[]
    years={int(y) for y in (config.get("corporate_card_years") or [2025,2026])}
    summary={"status":"ok","messages":0,"attachments":0,"card_pdfs":0,"card_imported":0,"card_duplicates":0,"card_errors":0,"errors":0,"results":results}
    _update_runtime_status(last_started_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_error=None)
    pythoncom.CoInitialize()
    try:
        namespace=win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        with tempfile.TemporaryDirectory(prefix="erp_som_cards_") as temp_dir:
            for account, folder_name in (
                (config.get("account") or ACCOUNT, config.get("folder") or SAFE_DEFAULT_FOLDER),
                (config.get("card_account") or CARD_ACCOUNT, "INBOX"),
            ):
                try:
                    if _normalized(folder_name)=="inbox":
                        store,folder=_find_inbox(namespace,account)
                    else:
                        store,folder=_find_folder(namespace,account,folder_name)
                    for scan_folder in _card_scan_folders(folder):
                        _scan_card_folder(scan_folder,temp_dir,state,summary,years)
                        summary["last_store"]=str(store); summary["last_folder"]=str(scan_folder.Name)
                        if progress: progress(dict(summary))
                except Exception as exc:
                    summary["card_errors"]+=1; summary["errors"]+=1
                    results.append({"received":"","subject":"Tarjetas corporativas","filename":account,"status":"ERROR","detail":str(exc)})
        try:
            summary["card_history"]=post_corporate_card_history_api({"years":sorted(years),"settle_previous":True,"leave_latest_pending":True})
        except Exception as exc:
            summary["card_errors"]+=1; summary["errors"]+=1
            results.append({"received":"","subject":"Tarjetas corporativas","filename":"historial","status":"ERROR","detail":str(exc)})
        _update_runtime_status(last_finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_summary={k:v for k,v in summary.items() if k!="results"},last_error=None)
        return summary
    except Exception as exc:
        _update_runtime_status(last_finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_error=str(exc))
        raise
    finally:
        pythoncom.CoUninitialize(); _scan_lock.release()


def _xml_kind(path):
    root=ET.parse(path).getroot().tag.rsplit("}",1)[-1]
    return "HACIENDA" if root in {"MensajeHacienda","RespuestaHacienda"} else "DOCUMENT"


def scan_and_import(max_messages=None,progress=None, process_corporate_cards=None, post_corporate_card_history=False):
    if not _scan_lock.acquire(blocking=False): return {"status":"busy","message":"Ya existe una revisión de Outlook en curso","results":[]}
    import pythoncom
    import win32com.client
    config=load_config(); limit=int(max_messages or config.get("batch_size",50)); state=_load_state(); results=[]
    if process_corporate_cards is None:
        process_corporate_cards=bool(config.get("process_corporate_cards",True))
    summary={
        "status":"ok","messages":0,"attachments":0,"xml":0,"imported":0,"duplicates":0,"errors":0,
        "card_pdfs":0,"card_imported":0,"card_duplicates":0,"card_errors":0,"results":results
    }
    _update_runtime_status(last_started_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_error=None)
    pythoncom.CoInitialize()
    try:
        namespace=win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        with tempfile.TemporaryDirectory(prefix="erp_som_outlook_") as temp_dir:
            fiscal_mailboxes=config.get("fiscal_mailboxes") or [{"company_code":"MSL-CR","account":config["account"],"folder":config["folder"]}]
            for mailbox in fiscal_mailboxes:
                company_code=str(mailbox.get("company_code") or "MSL-CR").strip().upper()
                account=str(mailbox.get("account") or config["account"]).strip()
                folder_name=str(mailbox.get("folder") or config["folder"]).strip()
                try:
                    store,folder=_find_folder(namespace,account,folder_name)
                    items=folder.Items; items.Sort("[ReceivedTime]",True)
                except Exception as exc:
                    summary["errors"]+=1
                    results.append({"received":"","subject":"Correo fiscal Outlook","filename":account,"status":"ERROR","detail":str(exc)})
                    continue
                scanned=0
                imported_messages=0
                for index in range(1,items.Count+1):
                    if imported_messages>=limit or scanned>=5000: break
                    scanned+=1; message=items.Item(index)
                    try: attachment_count=int(message.Attachments.Count)
                    except Exception: continue
                    pending=[]
                    for attachment_index in range(1,attachment_count+1):
                        attachment=message.Attachments.Item(attachment_index); filename=str(attachment.FileName or "")
                        subject=str(getattr(message,"Subject","") or "")
                        if not filename.lower().endswith((".xml",".zip")) and not (process_corporate_cards and _is_corporate_card_pdf(filename,subject)): continue
                        key=hashlib.sha256(f"{company_code}|{account}|{message.EntryID}|{attachment_index}|{filename}|{getattr(attachment,'Size',0)}".encode()).hexdigest()
                        if state.get(key,{}).get("status") in {"IMPORTED","DUPLICATE"}: continue
                        pending.append((attachment,key,filename))
                    if not pending: continue
                    summary["messages"]+=1; imported_messages+=1
                    subject=str(getattr(message,"Subject","") or ""); received=str(getattr(message,"ReceivedTime","") or "")
                    for attachment,key,filename in pending:
                        summary["attachments"]+=1
                        try:
                            safe=hashlib.sha256(key.encode()).hexdigest()[:12]+"_"+Path(filename).name
                            attachment_path=Path(temp_dir)/safe; attachment.SaveAsFile(str(attachment_path))
                            if process_corporate_cards and _is_corporate_card_pdf(filename,subject):
                                summary["card_pdfs"]+=1
                                try:
                                    response=post_corporate_card_statement_pdf_api(str(attachment_path))
                                    if response.get("status")=="exists":
                                        summary["card_duplicates"]+=1; status="DUPLICATE"; detail="Estado BAC ya importado"
                                    else:
                                        summary["card_imported"]+=1; status="IMPORTED"; detail=f"Estado BAC {response.get('statement',{}).get('statement_period','')} movimientos {response.get('transactions_inserted',0)}"
                                except Exception as exc:
                                    summary["card_errors"]+=1; summary["errors"]+=1; status="ERROR"; detail=str(exc)
                                results.append({"received":received,"subject":subject,"filename":filename,"status":status,"detail":detail,"company_code":company_code,"account":account})
                                state[key]={"status":status,"filename":filename,"updated_at":received,"company_code":company_code,"account":account}
                                continue
                            xml_paths=_xml_files(filename,attachment_path,temp_dir)
                            if not xml_paths: raise ValueError("El ZIP no contiene XML")
                            for xml_path in xml_paths:
                                summary["xml"]+=1
                                try:
                                    response=upload_tax_response_auto_api(str(xml_path),company_code=company_code) if _xml_kind(xml_path)=="HACIENDA" else upload_tax_xml_api(str(xml_path),"PURCHASE","OUTLOOK_LOCAL",company_code=company_code)
                                    summary["imported"]+=1; status="IMPORTED"; detail=f"Registro fiscal {response.get('id')}"
                                except Exception as exc:
                                    text=str(exc)
                                    if "duplicado" in text.lower() or "409" in text:
                                        summary["duplicates"]+=1; status="DUPLICATE"; detail=text
                                    else:
                                        summary["errors"]+=1; status="ERROR"; detail=text
                                results.append({"received":received,"subject":subject,"filename":xml_path.name,"status":status,"detail":detail,"company_code":company_code,"account":account})
                                state[key]={"status":status,"filename":filename,"updated_at":received,"company_code":company_code,"account":account}
                        except Exception as exc:
                            summary["errors"]+=1; results.append({"received":received,"subject":subject,"filename":filename,"status":"ERROR","detail":str(exc),"company_code":company_code,"account":account})
                            state[key]={"status":"ERROR","filename":filename,"updated_at":received,"company_code":company_code,"account":account}
                    _save_state(state)
                    if progress: progress(dict(summary))
                summary["store"]=str(store); summary["folder"]=str(folder.Name)
                summary["last_mailbox"]={"company_code":company_code,"account":account,"folder":str(folder.Name)}
        if post_corporate_card_history and process_corporate_cards:
            try:
                history=post_corporate_card_history_api({
                    "years": config.get("corporate_card_years") or [2025,2026],
                    "settle_previous": True,
                    "leave_latest_pending": True,
                })
                summary["card_history"]=history
            except Exception as exc:
                summary["card_errors"]+=1; summary["errors"]+=1
                results.append({"received":"","subject":"Tarjetas corporativas","filename":"historial","status":"ERROR","detail":str(exc)})
        _update_runtime_status(last_finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_summary={k:v for k,v in summary.items() if k!="results"},last_error=None)
        return summary
    except Exception as exc:
        _update_runtime_status(last_finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_error=str(exc))
        raise
    finally:
        pythoncom.CoUninitialize(); _scan_lock.release()
