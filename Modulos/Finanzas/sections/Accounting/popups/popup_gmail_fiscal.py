import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from api_client import (
    get_gmail_fiscal_messages_api,
    get_gmail_fiscal_status_api,
    start_gmail_fiscal_oauth_api,
    sync_gmail_fiscal_api,
    update_gmail_fiscal_automation_api,
)
from session_context import get_user


class PopupGmailFiscal(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent)
        self.title("Bandeja fiscal de correo")
        self.geometry("1120x650"); self.minsize(940,560)
        self.connection=tk.StringVar(value="Consultando…")
        self.last_sync=tk.StringVar(value="Nunca")
        self.auto=tk.BooleanVar(value=False)
        self.interval=tk.IntVar(value=10)
        self.filter=tk.StringVar(value="TODOS")
        self.footer=tk.StringVar(value="")
        self._busy=False
        self._build(); self.after(100,self.refresh)

    def _build(self):
        info=ttk.LabelFrame(self,text="Conexión Gmail",padding=10); info.pack(fill="x",padx=10,pady=10)
        ttk.Label(info,text="Cuenta:").grid(row=0,column=0,sticky="w"); ttk.Label(info,text="gastos@mslogisticsgroup.com",font=("Segoe UI",10,"bold")).grid(row=0,column=1,sticky="w",padx=5)
        ttk.Label(info,text="Estado:").grid(row=1,column=0,sticky="w"); ttk.Label(info,textvariable=self.connection).grid(row=1,column=1,sticky="w",padx=5)
        ttk.Label(info,text="Última revisión:").grid(row=2,column=0,sticky="w"); ttk.Label(info,textvariable=self.last_sync).grid(row=2,column=1,sticky="w",padx=5)
        ttk.Button(info,text="Autorizar con Google",command=self._authorize).grid(row=0,column=3,rowspan=2,padx=10)
        ttk.Button(info,text="Revisar correo ahora",command=self._sync).grid(row=0,column=4,rowspan=2,padx=4)
        ttk.Checkbutton(info,text="Revisión automática",variable=self.auto,command=self._save_automation).grid(row=2,column=3,sticky="e")
        ttk.Spinbox(info,from_=5,to=1440,textvariable=self.interval,width=6,command=self._save_automation).grid(row=2,column=4,sticky="w")
        ttk.Label(info,text="minutos").grid(row=2,column=4,padx=(55,0),sticky="w")
        info.columnconfigure(2,weight=1)

        bar=ttk.Frame(self,padding=(10,0)); bar.pack(fill="x")
        ttk.Label(bar,text="Mostrar:").pack(side="left")
        cmb=ttk.Combobox(bar,textvariable=self.filter,values=("TODOS","PROCESSED","REVIEW","DUPLICATE"),state="readonly",width=14)
        cmb.pack(side="left",padx=5); cmb.bind("<<ComboboxSelected>>",lambda _e:self._load_messages())
        ttk.Button(bar,text="Actualizar",command=self.refresh).pack(side="right")

        cols=("date","sender","subject","status","attachments","xml","imported","duplicates","errors")
        self.tree=ttk.Treeview(self,columns=cols,show="headings")
        specs=(("date","Fecha",125),("sender","Remitente",190),("subject","Asunto",260),("status","Estado",95),
               ("attachments","Adj.",55),("xml","XML",50),("imported","Cargados",65),("duplicates","Duplicados",70),("errors","Errores",55))
        for col,label,width in specs: self.tree.heading(col,text=label); self.tree.column(col,width=width)
        self.tree.tag_configure("PROCESSED",foreground="#15803D"); self.tree.tag_configure("REVIEW",foreground="#B91C1C"); self.tree.tag_configure("DUPLICATE",foreground="#A16207")
        self.tree.pack(fill="both",expand=True,padx=10,pady=8)
        ttk.Label(self,textvariable=self.footer,anchor="w").pack(fill="x",padx=12,pady=(0,8))

    def refresh(self):
        if self._busy:return
        self._busy=True; self.footer.set("Actualizando bandeja…")
        threading.Thread(target=self._refresh_worker,daemon=True).start()

    def _refresh_worker(self):
        try:
            status=get_gmail_fiscal_status_api(); messages=get_gmail_fiscal_messages_api(None if self.filter.get()=="TODOS" else self.filter.get())
            self.after(0,self._apply_refresh,status,messages)
        except Exception as exc:self.after(0,self._error,str(exc))

    def _apply_refresh(self,status,messages):
        connection=status.get("connection") or {}; state=connection.get("status","PENDING_AUTH")
        configured=status.get("oauth_configured")
        self.connection.set(f"{state}"+("" if configured else " · faltan credenciales OAuth en el servidor"))
        self.last_sync.set(str(connection.get("last_sync_at") or "Nunca")); self.auto.set(bool(connection.get("auto_enabled"))); self.interval.set(connection.get("interval_minutes") or 10)
        self._render_messages(messages); self._busy=False

    def _render_messages(self,data):
        self.tree.delete(*self.tree.get_children())
        for row in data.get("data",[]):
            sender=(row.get("sender") or "")[:55]; status=row.get("status") or "NEW"
            self.tree.insert("","end",values=(str(row.get("received_at") or "")[:16],sender,row.get("subject") or "",status,
              row.get("attachment_count",0),row.get("xml_count",0),row.get("imported_count",0),row.get("duplicate_count",0),row.get("error_count",0)),tags=(status,))
        self.footer.set(f"{data.get('count',0)} correos en la bandeja fiscal")

    def _load_messages(self): self.refresh()

    def _authorize(self):
        try:
            data=start_gmail_fiscal_oauth_api(get_user() or "unknown"); webbrowser.open(data["authorization_url"])
            messagebox.showinfo("Autorizar Gmail","Se abrió Google en el navegador. Inicie sesión con gastos@mslogisticsgroup.com y regrese aquí al finalizar.",parent=self)
        except Exception as exc:messagebox.showerror("Autorizar Gmail",str(exc),parent=self)

    def _save_automation(self):
        try:
            update_gmail_fiscal_automation_api(self.auto.get(),int(self.interval.get()),get_user() or "unknown")
            self.footer.set("Programación automática actualizada")
        except Exception as exc:messagebox.showerror("Automatización",str(exc),parent=self)

    def _sync(self):
        if self._busy:return
        self._busy=True; self.footer.set("Revisando Gmail y procesando adjuntos…")
        threading.Thread(target=self._sync_worker,daemon=True).start()

    def _sync_worker(self):
        try:
            result=sync_gmail_fiscal_api(get_user() or "unknown"); self.after(0,self._sync_done,result)
        except Exception as exc:self.after(0,self._error,str(exc))

    def _sync_done(self,result):
        self._busy=False
        messagebox.showinfo("Correo fiscal",f"Correos: {result.get('messages',0)}\nXML: {result.get('xml',0)}\nCargados: {result.get('imported',0)}\nDuplicados: {result.get('duplicates',0)}\nRevisar: {result.get('review',0)}",parent=self)
        self.refresh()

    def _error(self,message):
        self._busy=False; self.footer.set("No se pudo completar la operación"); messagebox.showerror("Correo fiscal",message,parent=self)
