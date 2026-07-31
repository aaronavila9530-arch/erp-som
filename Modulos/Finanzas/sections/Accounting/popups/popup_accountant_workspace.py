import tkinter as tk
import threading
from datetime import date
from tkinter import messagebox, simpledialog, ttk

from api_client import (
    get_accountant_dashboard_api,
    get_accounting_close_checklist_api,
    search_accounting_workspace_api,
    update_accounting_close_checklist_api,
)
from session_context import get_user


class PopupAccountantWorkspace(tk.Toplevel):
    PRIORITY_COLORS = {"CRITICAL":"#B91C1C","HIGH":"#DC2626","MEDIUM":"#D97706","LOW":"#2563EB"}
    CLOSE_LABELS = {
        "SOURCE_SYNC": "Sincronizar fuentes operativas",
        "ENTRY_WORKFLOW": "Contabilizar asientos completos",
        "BANK_RECONCILIATION": "Cerrar conciliaciones bancarias",
        "AR_REVIEW": "Revisar cuentas por cobrar",
        "AP_REVIEW": "Revisar cuentas por pagar",
        "AUX_RECONCILIATION": "Cuadrar auxiliares vs mayor",
        "TAX_REVIEW": "Revisar IVA y documentos fiscales",
        "FX_REVALUATION": "Revaluar saldos en USD",
        "FINANCIAL_STATEMENTS": "Revisar estados financieros",
        "MANAGEMENT_APPROVAL": "Aprobacion final del cierre",
    }

    def __init__(self, parent, period=None):
        super().__init__(parent)
        self.accounting = parent
        self.period = tk.StringVar(value=period or date.today().strftime("%Y-%m"))
        self.status = tk.StringVar(value="Cargando…")
        self.health = tk.StringVar(value="—")
        self.period_status = tk.StringVar(value="—")
        self.kpi_scope = tk.StringVar(value="")
        self._loading = False
        self.title("Mi espacio contable")
        self.geometry("1240x760")
        self.minsize(1040, 650)
        self._build()
        self.after(120, self.refresh)

    def _build(self):
        header=ttk.Frame(self,padding=10); header.pack(fill="x")
        ttk.Label(header,text="Periodo:").pack(side="left")
        ttk.Entry(header,textvariable=self.period,width=10).pack(side="left",padx=5)
        ttk.Button(header,text="Actualizar",command=self.refresh).pack(side="left",padx=4)
        ttk.Button(header,text="Nuevo asiento",command=self._manual_entry).pack(side="left",padx=4)
        ttk.Button(header,text="Auxiliares",command=self._auxiliaries).pack(side="left",padx=4)
        ttk.Button(header,text="Centro fiscal",command=self._tax_center).pack(side="left",padx=4)
        ttk.Button(header,text="Reporte mensual",command=self._monthly_report).pack(side="left",padx=4)
        ttk.Label(header,text="Salud:").pack(side="left",padx=(30,3))
        ttk.Label(header,textvariable=self.health,font=("Segoe UI",12,"bold")).pack(side="left")
        ttk.Label(header,textvariable=self.period_status,font=("Segoe UI",10,"bold")).pack(side="right")

        tabs=ttk.Notebook(self); tabs.pack(fill="both",expand=True,padx=10,pady=(0,5))
        self.today_tab=ttk.Frame(tabs,padding=10); self.close_tab=ttk.Frame(tabs,padding=10); self.search_tab=ttk.Frame(tabs,padding=10)
        tabs.add(self.today_tab,text="Hoy"); tabs.add(self.close_tab,text="Cierre mensual"); tabs.add(self.search_tab,text="Buscar en contabilidad")
        self._build_today(); self._build_close(); self._build_search()
        ttk.Label(self,textvariable=self.status,anchor="w").pack(fill="x",padx=12,pady=(0,8))

    def _build_today(self):
        self.kpi_vars={}
        cards=ttk.Frame(self.today_tab); cards.pack(fill="x",pady=(0,10))
        specs=(("posted_entries","Asientos contabilizados",False),("open_ar","Cuentas por cobrar",True),
               ("overdue_ar","CxC vencida",True),("open_ap","Cuentas por pagar",True),("overdue_ap","CxP vencida",True))
        for col,(key,label,money) in enumerate(specs):
            box=ttk.LabelFrame(cards,text=label,padding=10); box.grid(row=0,column=col,sticky="nsew",padx=3); cards.columnconfigure(col,weight=1)
            var=tk.StringVar(value="—"); ttk.Label(box,textvariable=var,font=("Segoe UI",12,"bold")).pack(); self.kpi_vars[key]=(var,money)
        ttk.Label(self.today_tab,textvariable=self.kpi_scope,foreground="#555").pack(anchor="w",pady=(0,8))
        pane=ttk.Panedwindow(self.today_tab,orient="horizontal"); pane.pack(fill="both",expand=True)
        queue=ttk.LabelFrame(pane,text="Bandeja priorizada",padding=6); recent=ttk.LabelFrame(pane,text="Actividad reciente",padding=6)
        pane.add(queue,weight=3); pane.add(recent,weight=2)
        self.queue=ttk.Treeview(queue,columns=("priority","area","title","count"),show="headings")
        for c,l,w in (("priority","Prioridad",90),("area","Área",110),("title","Pendiente",380),("count","Cantidad",80)):
            self.queue.heading(c,text=l); self.queue.column(c,width=w)
        for priority,color in self.PRIORITY_COLORS.items(): self.queue.tag_configure(priority,foreground=color)
        self.queue.pack(fill="both",expand=True); self.queue.bind("<Double-1>",lambda _e:self._open_queue_action())
        ttk.Button(queue,text="Abrir seleccionado",command=self._open_queue_action).pack(anchor="e",pady=5)
        self.recent=ttk.Treeview(recent,columns=("date","id","description","status"),show="headings")
        for c,l,w in (("date","Fecha",90),("id","Asiento",70),("description","Descripción",260),("status","Estado",100)):
            self.recent.heading(c,text=l); self.recent.column(c,width=w)
        self.recent.pack(fill="both",expand=True)

    def _build_close(self):
        summary=ttk.Frame(self.close_tab); summary.pack(fill="x",pady=(0,7))
        self.close_summary=tk.StringVar(value="—"); ttk.Label(summary,textvariable=self.close_summary,font=("Segoe UI",11,"bold")).pack(side="left")
        ttk.Button(summary,text="Actualizar validaciones",command=self._load_checklist).pack(side="right")
        ttk.Label(
            self.close_tab,
            text="Complete los pasos de arriba hacia abajo. Las lineas rojas bloquean el cierre; resuelva el punto indicado y pulse Actualizar validaciones.",
            wraplength=1100,
        ).pack(anchor="w", pady=(0, 6))
        self.checklist=ttk.Treeview(self.close_tab,columns=("seq","category","title","validation","status","user"),show="headings")
        for c,l,w in (("seq","#",40),("category","Área",110),("title","Paso de cierre",390),("validation","Validación",310),("status","Estado",110),("user","Completado por",120)):
            self.checklist.heading(c,text=l); self.checklist.column(c,width=w)
        self.checklist.tag_configure("COMPLETE",foreground="#15803D"); self.checklist.tag_configure("BLOCKED",foreground="#B91C1C")
        self.checklist.pack(fill="both",expand=True)
        buttons=ttk.Frame(self.close_tab); buttons.pack(fill="x",pady=6)
        ttk.Button(buttons,text="Iniciar",command=lambda:self._set_check("IN_PROGRESS")).pack(side="left",padx=3)
        ttk.Button(buttons,text="Marcar completado",command=lambda:self._set_check("COMPLETE")).pack(side="left",padx=3)
        ttk.Button(buttons,text="Reabrir paso",command=lambda:self._set_check("PENDING")).pack(side="left",padx=3)
        ttk.Button(buttons,text="Abrir cierre / mayorización",command=self._closing).pack(side="right",padx=3)

    def _build_search(self):
        bar=ttk.Frame(self.search_tab); bar.pack(fill="x",pady=(0,7))
        self.query=tk.StringVar(); entry=ttk.Entry(bar,textvariable=self.query); entry.pack(side="left",fill="x",expand=True)
        entry.bind("<Return>",lambda _e:self._search()); ttk.Button(bar,text="Buscar",command=self._search).pack(side="left",padx=5)
        self.results=ttk.Treeview(self.search_tab,columns=("type","reference","title","detail"),show="headings")
        for c,l,w in (("type","Tipo",110),("reference","Referencia",130),("title","Resultado",340),("detail","Detalle",420)):
            self.results.heading(c,text=l); self.results.column(c,width=w)
        self.results.pack(fill="both",expand=True); self.results.bind("<Double-1>",lambda _e:self._open_search_result())
        ttk.Label(self.search_tab,text="Busca asientos, cuentas, clientes, proveedores, cédulas, facturas y claves electrónicas.").pack(anchor="w",pady=5)

    def refresh(self):
        if self._loading:
            return
        self._loading=True; self.status.set("Actualizando espacio contable…")
        period=self.period.get()
        threading.Thread(target=self._refresh_worker,args=(period,),daemon=True).start()

    def _refresh_worker(self,period):
        try:
            dashboard=get_accountant_dashboard_api(period); checklist=get_accounting_close_checklist_api(period)
            self.after(0,self._apply_refresh,dashboard,checklist)
        except Exception as exc:
            self.after(0,self._refresh_error,str(exc))

    def _refresh_error(self,message):
        self._loading=False; self.status.set("Error de actualización"); messagebox.showerror("Mi espacio contable",message,parent=self)

    def _apply_refresh(self,data,checklist):
        self.health.set(f"{data['health_score']} / 100"); self.period_status.set(f"Periodo: {data['period_control'].get('status','OPEN')}")
        scope=data.get("kpi_scope") or {}
        if scope.get("as_of"):
            fx = scope.get("fx_rate")
            fx_date = scope.get("fx_date") or scope.get("as_of")
            self.kpi_scope.set(f"Saldos abiertos al {scope.get('as_of')}. USD convertido a CRC con TC {fx:,.2f} ({fx_date}).")
        elif scope.get("from") and scope.get("to"):
            self.kpi_scope.set(f"KPIs calculados para el periodo seleccionado: {scope.get('from')} a {scope.get('to')}.")
        else:
            self.kpi_scope.set("")
        for key,(var,money) in self.kpi_vars.items():
            value=data["kpis"].get(key,0)
            if key == "overdue_ar":
                count = int(data["kpis"].get("overdue_ar_count") or 0)
                label = "factura" if count == 1 else "facturas"
                var.set(f"₡{value:,.2f}\n{count:,} {label}")
            elif key == "open_ar":
                count = int(data["kpis"].get("open_ar_count") or 0)
                label = "factura" if count == 1 else "facturas"
                var.set(f"₡{value:,.2f}\n{count:,} {label}")
            elif key == "overdue_ap":
                count = int(data["kpis"].get("overdue_ap_count") or 0)
                label = "obligación" if count == 1 else "obligaciones"
                var.set(f"₡{value:,.2f}\n{count:,} {label}")
            elif key == "open_ap":
                count = int(data["kpis"].get("open_ap_count") or 0)
                label = "obligación" if count == 1 else "obligaciones"
                var.set(f"₡{value:,.2f}\n{count:,} {label}")
            else:
                var.set(f"₡{value:,.2f}" if money else f"{int(value):,}")
        self.queue.delete(*self.queue.get_children()); self._queue_actions={}
        for i,item in enumerate(data["work_items"]):
            iid=f"q{i}"; self.queue.insert("","end",iid=iid,values=(item["priority"],item["area"],item["title"],item["count"]),tags=(item["priority"],)); self._queue_actions[iid]=item["action"]
        self.recent.delete(*self.recent.get_children())
        for row in data["recent_entries"]:
            self.recent.insert("","end",values=(str(row.get("entry_date") or ""),row["id"],row.get("description") or "",row.get("workflow_status") or ""))
        self._render_checklist(checklist); self._loading=False; self.status.set("Espacio contable actualizado")

    def _load_checklist(self):
        data=get_accounting_close_checklist_api(self.period.get()); self._render_checklist(data)

    def _render_checklist(self,data):
        self.checklist.delete(*self.checklist.get_children())
        for row in data["data"]:
            check=row["automatic_check"]; tag="COMPLETE" if row["status"]=="COMPLETE" else ("BLOCKED" if not check["ready"] else "")
            title = self.CLOSE_LABELS.get(row["item_code"], row["title"])
            self.checklist.insert("","end",iid=row["item_code"],values=(row["sequence"],row["category"],title,check["detail"],row["status"],row.get("completed_by") or ""),tags=(tag,))
        ready="LISTO PARA CERRAR" if data["ready_to_close"] else "CIERRE PENDIENTE"
        self.close_summary.set(f"{ready} · {data['completed']} de {data['total']} pasos completados · Periodo {data['period_status']}")

    def _set_check(self,status):
        selected=self.checklist.selection()
        if not selected: messagebox.showwarning("Cierre mensual","Seleccione un paso.",parent=self); return
        notes=simpledialog.askstring("Evidencia del cierre","Nota o referencia de soporte:",parent=self) or ""
        try: update_accounting_close_checklist_api(self.period.get(),selected[0],status,get_user() or "unknown",notes); self._load_checklist()
        except Exception as exc: messagebox.showerror("Cierre mensual",str(exc),parent=self)

    def _search(self):
        try:
            data=search_accounting_workspace_api(self.query.get()); self.results.delete(*self.results.get_children())
            for row in data["data"]: self.results.insert("","end",values=(row["result_type"],row["reference"],row["title"],row["subtitle"]))
            self.status.set(f"{data['count']} resultados")
        except Exception as exc: messagebox.showerror("Búsqueda contable",str(exc),parent=self)

    def _open_queue_action(self):
        selected=self.queue.selection()
        if not selected:return
        action=self._queue_actions.get(selected[0])
        if action=="TAX_CENTER": self._tax_center()
        elif action and action.startswith("AUXILIARIES"): self._auxiliaries()
        else: self.destroy(); self.accounting._on_search()

    def _open_search_result(self):
        selected=self.results.selection()
        if not selected:return
        kind=self.results.item(selected[0],"values")[0]
        if kind=="TAX_DOCUMENT": self._tax_center()
        elif kind=="AUXILIARY": self._auxiliaries()
        else: self.status.set("Use la referencia mostrada en los filtros del libro contable.")

    def _manual_entry(self): self.accounting._open_manual_entry()
    def _auxiliaries(self):
        try:
            from Modulos.Finanzas.sections.Accounting.popups.popup_auxiliaries import PopupAccountingAuxiliaries
            popup = PopupAccountingAuxiliaries(self, period=self.period.get())
            popup.transient(self)
        except Exception as exc:
            messagebox.showerror("Auxiliares contables", str(exc), parent=self)

    def _tax_center(self):
        try:
            from Modulos.Finanzas.sections.Accounting.popups.popup_tax_center import PopupTaxCenter
            popup = PopupTaxCenter(self, period=self.period.get())
            popup.transient(self)
        except Exception as exc:
            messagebox.showerror("Centro fiscal", str(exc), parent=self)
    def _monthly_report(self): self.accounting._open_monthly_financial_report()
    def _closing(self): self.accounting._open_closing_wizard()
