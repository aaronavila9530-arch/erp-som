import threading
import tkinter as tk
from tkinter import messagebox, ttk

from Modulos.Finanzas.sections.Accounting.outlook_fiscal_importer import (
    inspect_outlook,
    load_config,
    save_config,
    scan_and_import,
    scan_corporate_card_history,
)


class PopupOutlookFiscal(tk.Toplevel):
    def __init__(self,parent):
        super().__init__(parent)
        config=load_config()
        self.title("Correo fiscal - Outlook local")
        self.geometry("1120x650"); self.minsize(920,540)
        self.connection=tk.StringVar(value="Verificando Outlook…")
        self.auto=tk.BooleanVar(value=bool(config.get("enabled")))
        self.cards=tk.BooleanVar(value=bool(config.get("process_corporate_cards",True)))
        self.interval=tk.IntVar(value=int(config.get("interval_minutes",15)))
        self.batch=tk.IntVar(value=int(config.get("batch_size",50)))
        self.footer=tk.StringVar(value="")
        self._busy=False
        self._build(); self.after(100,self._inspect)

    def _build(self):
        info=ttk.LabelFrame(self,text="Origen local",padding=10); info.pack(fill="x",padx=10,pady=10)
        ttk.Label(info,text="Buzón:").grid(row=0,column=0,sticky="w"); ttk.Label(info,text="gastos@mslogisticsgroup.com",font=("Segoe UI",10,"bold")).grid(row=0,column=1,sticky="w",padx=5)
        ttk.Label(info,text="Carpeta:").grid(row=1,column=0,sticky="w"); ttk.Label(info,text="xml gastos electrónicos",font=("Segoe UI",10,"bold")).grid(row=1,column=1,sticky="w",padx=5)
        ttk.Label(info,text="Estado:").grid(row=2,column=0,sticky="w"); ttk.Label(info,textvariable=self.connection).grid(row=2,column=1,sticky="w",padx=5)
        info.columnconfigure(2,weight=1)
        ttk.Button(info,text="Revisar Outlook ahora",command=self._scan).grid(row=0,column=3,rowspan=2,padx=8)
        ttk.Checkbutton(info,text="Automático con ERP abierto",variable=self.auto,command=self._save).grid(row=2,column=3,sticky="e",padx=5)
        ttk.Spinbox(info,from_=5,to=1440,textvariable=self.interval,width=6,command=self._save).grid(row=2,column=4,sticky="w")
        ttk.Label(info,text="min").grid(row=2,column=4,padx=(55,0),sticky="w")

        options=ttk.Frame(self,padding=(10,0)); options.pack(fill="x")
        ttk.Label(options,text="Correos nuevos por lote:").pack(side="left")
        batch=ttk.Combobox(options,textvariable=self.batch,values=(10,25,50,100),state="readonly",width=6); batch.pack(side="left",padx=5); batch.bind("<<ComboboxSelected>>",lambda _e:self._save())
        ttk.Checkbutton(options,text="Detectar estados BAC PDF",variable=self.cards,command=self._save).pack(side="left",padx=10)
        ttk.Button(options,text="Cargar tarjetas 2025-2026 y contabilizar",command=self._scan_cards_history).pack(side="left",padx=8)
        ttk.Label(options,text="La primera carga se realiza por lotes para poder revisar los resultados.").pack(side="left",padx=15)

        cols=("date","subject","file","status","detail")
        self.tree=ttk.Treeview(self,columns=cols,show="headings")
        for col,label,width in (("date","Fecha",125),("subject","Asunto",300),("file","Archivo",220),("status","Estado",95),("detail","Detalle",300)):
            self.tree.heading(col,text=label); self.tree.column(col,width=width)
        self.tree.tag_configure("IMPORTED",foreground="#15803D"); self.tree.tag_configure("DUPLICATE",foreground="#A16207"); self.tree.tag_configure("ERROR",foreground="#B91C1C")
        self.tree.pack(fill="both",expand=True,padx=10,pady=8)
        ttk.Label(self,textvariable=self.footer,anchor="w").pack(fill="x",padx=12,pady=(0,8))

    def _inspect(self):
        threading.Thread(target=self._inspect_worker,daemon=True).start()

    def _inspect_worker(self):
        try:self.after(0,self._apply_inspect,inspect_outlook())
        except Exception as exc:self.after(0,self._error,str(exc))

    def _apply_inspect(self,data):
        self.connection.set(f"Conectado · {data['message_count']} mensajes disponibles")
        self.footer.set("Outlook está listo. No se almacena ninguna contraseña.")

    def _save(self):
        try:
            save_config({"enabled":self.auto.get(),"interval_minutes":int(self.interval.get()),"batch_size":int(self.batch.get()),"process_corporate_cards":self.cards.get()})
            self.footer.set("Configuración guardada")
        except Exception as exc:messagebox.showerror("Correo fiscal",str(exc),parent=self)

    def _scan(self):
        if self._busy:return
        self._save(); self._busy=True; self._current_batch=int(self.batch.get()); self._card_history=False; self.footer.set("Leyendo Outlook y cargando XML/PDF BAC…")
        threading.Thread(target=self._scan_worker,daemon=True).start()

    def _scan_cards_history(self):
        if self._busy:return
        if not messagebox.askyesno("Tarjetas corporativas","Se importaran estados BAC 2025-2026, se contabilizaran cargos y se marcaran pagados todos menos el ultimo. Continuar?",parent=self):
            return
        self._save(); self._busy=True; self._current_batch=100; self._card_history=True; self.footer.set("Cargando historial BAC 2025-2026 desde Outlook…")
        threading.Thread(target=self._scan_worker,daemon=True).start()

    def _scan_worker(self):
        try:
            if getattr(self,"_card_history",False):
                result=scan_corporate_card_history()
            else:
                result=scan_and_import(max_messages=self._current_batch)
            self.after(0,self._scan_done,result)
        except Exception as exc:self.after(0,self._error,str(exc))

    def _scan_done(self,result):
        self._busy=False; self.tree.delete(*self.tree.get_children())
        for row in result.get("results",[]):
            status=row.get("status","ERROR"); self.tree.insert("","end",values=(row.get("received",""),row.get("subject",""),row.get("filename",""),status,row.get("detail","")),tags=(status,))
        history=result.get("card_history") or {}
        history_text=f" · Estados contabilizados: {history.get('statements',0)}" if history else ""
        self.footer.set(f"Correos: {result.get('messages',0)} · XML: {result.get('xml',0)} · Cargados: {result.get('imported',0)} · BAC PDF: {result.get('card_imported',0)} · Duplicados: {result.get('duplicates',0)+result.get('card_duplicates',0)} · Errores: {result.get('errors',0)}{history_text}")

    def _error(self,message):
        self._busy=False; self.connection.set("No disponible"); self.footer.set("No se pudo completar la operación"); messagebox.showerror("Correo fiscal Outlook",message,parent=self)
