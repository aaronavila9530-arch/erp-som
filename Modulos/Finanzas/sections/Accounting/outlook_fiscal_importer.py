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

from api_client import upload_tax_response_auto_api, upload_tax_xml_api


ACCOUNT="gastos@mslogisticsgroup.com"
SAFE_DEFAULT_FOLDER="xml gastos electronicos"
DEFAULT_FOLDER="xml gastos electrónicos"
MAX_ATTACHMENT_BYTES=20*1024*1024
MAX_ZIP_MEMBERS=50
_scan_lock=threading.Lock()
_background_lock=threading.Lock()
_background_started=False


def _data_dir():
    path=Path(os.getenv("LOCALAPPDATA") or Path.home())/"ERP-SOM"
    path.mkdir(parents=True,exist_ok=True); return path


def _config_path(): return _data_dir()/"outlook_fiscal_config.json"
def _state_path(): return _data_dir()/"outlook_fiscal_state.json"


def load_config():
    default={"enabled":True,"interval_minutes":15,"account":ACCOUNT,"folder":SAFE_DEFAULT_FOLDER,"batch_size":50}
    try:
        saved=json.loads(_config_path().read_text(encoding="utf-8")); default.update(saved if isinstance(saved,dict) else {})
    except Exception: pass
    default["folder"]=_repair_mojibake(default.get("folder") or SAFE_DEFAULT_FOLDER)
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
        last_run=0
        while True:
            try:
                config=load_config()
                interval=max(1,int(config.get("interval_minutes") or 15))*60
                if config.get("enabled") and time.time()-last_run>=interval:
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
    tmp=_state_path().with_suffix(".tmp"); tmp.write_text(json.dumps(state,ensure_ascii=False),encoding="utf-8"); os.replace(tmp,_state_path())


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


def _folder_candidates(folder_name):
    candidates=[folder_name,_repair_mojibake(folder_name),SAFE_DEFAULT_FOLDER,"xml gastos electronicos","xml gastos electrónicos"]
    seen=set(); output=[]
    for item in candidates:
        key=_normalized(item)
        if key and key not in seen:
            seen.add(key); output.append(item)
    return output


def _iter_folders(folder,depth=0,max_depth=4):
    if depth>max_depth:
        return
    for index in range(1,folder.Folders.Count+1):
        child=folder.Folders.Item(index)
        yield child
        yield from _iter_folders(child,depth+1,max_depth)


def _find_folder(namespace,account,folder_name):
    target_store=None
    account_norm=_normalized(account)
    for index in range(1,namespace.Stores.Count+1):
        store=namespace.Stores.Item(index)
        store_name=_normalized(store.DisplayName)
        if store_name==account_norm or store_name.startswith("gastos@") or account_norm in store_name:
            target_store=store; break
    if target_store is None: raise RuntimeError(f"Outlook no contiene el buzón {account}")
    root=target_store.GetRootFolder()
    wanted={_normalized(item) for item in _folder_candidates(folder_name)}
    for folder in _iter_folders(root):
        if _normalized(folder.Name) in wanted:
            return target_store.DisplayName,folder
    available=[str(folder.Name) for folder in _iter_folders(root,max_depth=2)]
    raise RuntimeError(f"No se encontró la carpeta '{folder_name}'. Carpetas disponibles: {', '.join(available)}")


def inspect_outlook():
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    try:
        namespace=win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        config=load_config()
        store,folder=_find_folder(namespace,config["account"],config["folder"])
        return {"connected":True,"store":str(store),"folder":str(folder.Name),"message_count":int(folder.Items.Count)}
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


def _xml_kind(path):
    root=ET.parse(path).getroot().tag.rsplit("}",1)[-1]
    return "HACIENDA" if root in {"MensajeHacienda","RespuestaHacienda"} else "DOCUMENT"


def scan_and_import(max_messages=None,progress=None):
    if not _scan_lock.acquire(blocking=False): return {"status":"busy","message":"Ya existe una revisión de Outlook en curso","results":[]}
    import pythoncom
    import win32com.client
    config=load_config(); limit=int(max_messages or config.get("batch_size",50)); state=_load_state(); results=[]
    summary={"status":"ok","messages":0,"attachments":0,"xml":0,"imported":0,"duplicates":0,"errors":0,"results":results}
    _update_runtime_status(last_started_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_error=None)
    pythoncom.CoInitialize()
    try:
        namespace=win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
        store,folder=_find_folder(namespace,config["account"],config["folder"]); items=folder.Items; items.Sort("[ReceivedTime]",True)
        with tempfile.TemporaryDirectory(prefix="erp_som_outlook_") as temp_dir:
            scanned=0
            for index in range(1,items.Count+1):
                if summary["messages"]>=limit or scanned>=5000: break
                scanned+=1; message=items.Item(index)
                try: attachment_count=int(message.Attachments.Count)
                except Exception: continue
                pending=[]
                for attachment_index in range(1,attachment_count+1):
                    attachment=message.Attachments.Item(attachment_index); filename=str(attachment.FileName or "")
                    if not filename.lower().endswith((".xml",".zip")): continue
                    key=hashlib.sha256(f"{message.EntryID}|{attachment_index}|{filename}|{getattr(attachment,'Size',0)}".encode()).hexdigest()
                    if state.get(key,{}).get("status") in {"IMPORTED","DUPLICATE"}: continue
                    pending.append((attachment,key,filename))
                if not pending: continue
                summary["messages"]+=1
                subject=str(getattr(message,"Subject","") or ""); received=str(getattr(message,"ReceivedTime","") or "")
                for attachment,key,filename in pending:
                    summary["attachments"]+=1
                    try:
                        safe=hashlib.sha256(key.encode()).hexdigest()[:12]+"_"+Path(filename).name
                        attachment_path=Path(temp_dir)/safe; attachment.SaveAsFile(str(attachment_path))
                        xml_paths=_xml_files(filename,attachment_path,temp_dir)
                        if not xml_paths: raise ValueError("El ZIP no contiene XML")
                        for xml_path in xml_paths:
                            summary["xml"]+=1
                            try:
                                response=upload_tax_response_auto_api(str(xml_path)) if _xml_kind(xml_path)=="HACIENDA" else upload_tax_xml_api(str(xml_path),"PURCHASE","OUTLOOK_LOCAL")
                                summary["imported"]+=1; status="IMPORTED"; detail=f"Registro fiscal {response.get('id')}"
                            except Exception as exc:
                                text=str(exc)
                                if "duplicado" in text.lower() or "409" in text:
                                    summary["duplicates"]+=1; status="DUPLICATE"; detail=text
                                else:
                                    summary["errors"]+=1; status="ERROR"; detail=text
                            results.append({"received":received,"subject":subject,"filename":xml_path.name,"status":status,"detail":detail})
                            state[key]={"status":status,"filename":filename,"updated_at":received}
                    except Exception as exc:
                        summary["errors"]+=1; results.append({"received":received,"subject":subject,"filename":filename,"status":"ERROR","detail":str(exc)})
                        state[key]={"status":"ERROR","filename":filename,"updated_at":received}
                _save_state(state)
                if progress: progress(dict(summary))
        summary["store"]=str(store); summary["folder"]=str(folder.Name)
        _update_runtime_status(last_finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_summary={k:v for k,v in summary.items() if k!="results"},last_error=None)
        return summary
    except Exception as exc:
        _update_runtime_status(last_finished_at=time.strftime("%Y-%m-%d %H:%M:%S"),last_error=str(exc))
        raise
    finally:
        pythoncom.CoUninitialize(); _scan_lock.release()
