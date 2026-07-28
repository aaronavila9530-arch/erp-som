import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk

from api_client import (
    get_tax_book_api,
    get_tax_documents_api,
    get_tax_iva_api,
    get_tax_obligations_api,
    search_tax_cabys_api,
    sync_accounting_tax_api,
    upload_tax_hacienda_response_api,
    upload_tax_xml_api,
)


class PopupTaxCenter(tk.Toplevel):
    def __init__(self, parent, period=None):
        super().__init__(parent)
        self.title("Centro fiscal Costa Rica")
        self.geometry("1180x720")
        self.minsize(980, 620)
        self.period = tk.StringVar(value=period or date.today().strftime("%Y-%m"))
        self.status = tk.StringVar(value="Listo")
        self._shown_obligation_alerts = set()
        self._build()
        self.after(100, self.refresh_all)

    def _build(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Periodo (AAAA-MM):").pack(side="left")
        ttk.Entry(top, textvariable=self.period, width=10).pack(side="left", padx=6)
        ttk.Button(top, text="Actualizar", command=self.refresh_all).pack(side="left", padx=4)
        ttk.Button(top, text="Sincronizar ERP", command=self._sync).pack(side="left", padx=4)
        ttk.Button(top, text="Cargar XML venta", command=lambda: self._upload_xml("SALE")).pack(side="left", padx=4)
        ttk.Button(top, text="Cargar XML compra", command=lambda: self._upload_xml("PURCHASE")).pack(side="left", padx=4)
        ttk.Button(top, text="Correo fiscal Outlook", command=self._open_gmail_inbox).pack(side="left", padx=4)

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.tab_dashboard = ttk.Frame(self.tabs, padding=12)
        self.tab_sales = ttk.Frame(self.tabs, padding=8)
        self.tab_purchases = ttk.Frame(self.tabs, padding=8)
        self.tab_quality = ttk.Frame(self.tabs, padding=8)
        self.tab_obligations = ttk.Frame(self.tabs, padding=8)
        self.tab_cabys = ttk.Frame(self.tabs, padding=8)
        for tab, name in ((self.tab_dashboard,"IVA y conciliación"),(self.tab_sales,"Libro de ventas"),
                          (self.tab_purchases,"Libro de compras"),(self.tab_quality,"Control documental"),
                          (self.tab_obligations,"Obligaciones"),(self.tab_cabys,"CAByS")):
            self.tabs.add(tab, text=name)
        self._build_dashboard()
        self.sales_tree = self._book_tree(self.tab_sales)
        self.purchases_tree = self._book_tree(self.tab_purchases)
        self.quality_tree = self._quality_tree(self.tab_quality)
        self._build_obligations()
        self._build_cabys()
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=12, pady=(0, 8))

    def _build_dashboard(self):
        self.kpis = {}
        cards = ttk.Frame(self.tab_dashboard)
        cards.pack(fill="x")
        for col, (key, label) in enumerate((("sales_tax","IVA débito fiscal"),("purchase_tax_credit","Crédito fiscal"),
                                            ("net_tax","IVA neto documental"),("accounting_net","IVA neto contable"),
                                            ("difference","Diferencia"))):
            box = ttk.LabelFrame(cards, text=label, padding=12)
            box.grid(row=0, column=col, sticky="nsew", padx=4)
            cards.columnconfigure(col, weight=1)
            value = tk.StringVar(value="₡0.00")
            ttk.Label(box, textvariable=value, font=("Segoe UI", 13, "bold")).pack()
            self.kpis[key] = value
        self.ready = tk.StringVar(value="Pendiente de revisión")
        ttk.Label(self.tab_dashboard, textvariable=self.ready, font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20, 8))
        self.quality_text = tk.Text(self.tab_dashboard, height=9, state="disabled", wrap="word")
        self.quality_text.pack(fill="both", expand=True)

    @staticmethod
    def _book_tree(parent):
        cols=("date","number","party","currency","subtotal","tax","total","hacienda")
        tree=ttk.Treeview(parent,columns=cols,show="headings")
        labels=("Fecha","Documento","Contraparte","Moneda","Subtotal","IVA","Total","Hacienda")
        for col,label in zip(cols,labels):
            tree.heading(col,text=label); tree.column(col,width=120,anchor="e" if col in {"subtotal","tax","total"} else "w")
        tree.column("party",width=220); tree.pack(fill="both",expand=True)
        return tree

    @staticmethod
    def _quality_tree(parent):
        ttk.Label(
            parent,
            text="Control documental muestra documentos fiscales incompletos: XML faltante, clave electronica faltante, lineas sin detalle/CAByS, duplicados o respuesta de Hacienda pendiente.",
            wraplength=1120,
        ).pack(anchor="w", pady=(0, 6))
        cols=("id","direction","date","number","xml","key","lines","cabys","duplicates","hacienda")
        tree=ttk.Treeview(parent,columns=cols,show="headings")
        for col,label in zip(cols,("ID","Tipo","Fecha","Documento","XML","Clave","Líneas","CAByS faltante","Clave repetida","Hacienda")):
            tree.heading(col,text=label); tree.column(col,width=110)
        tree.column("number",width=190); tree.pack(fill="both",expand=True)
        ttk.Button(parent,text="Adjuntar respuesta de Hacienda al seleccionado",
                   command=lambda: parent.winfo_toplevel()._upload_response()).pack(anchor="e",pady=6)
        return tree

    def _build_obligations(self):
        self.obligations_tree=ttk.Treeview(self.tab_obligations,columns=("code","name","periodicity","period","due","alert"),show="headings")
        self.obligations_tree.heading("alert", text="Alerta")
        self.obligations_tree.column("alert", width=230)
        self.obligations_tree.tag_configure("DUE_TODAY", background="#FEE2E2", foreground="#991B1B")
        self.obligations_tree.tag_configure("DUE_TOMORROW", background="#FEF3C7", foreground="#92400E")
        self.obligations_tree.tag_configure("DUE_SOON", background="#FEF3C7", foreground="#92400E")
        self.obligations_tree.tag_configure("PENDING", foreground="#1F2937")
        for col,label,width in (("code","Código",150),("name","Obligación",300),("periodicity","Periodicidad",110),("period","Periodo",90),("due","Vencimiento estimado",160)):
            self.obligations_tree.heading(col,text=label); self.obligations_tree.column(col,width=width)
        self.obligations_tree.pack(fill="both",expand=True)
        ttk.Label(self.tab_obligations,text="Las fechas estimadas deben contrastarse con feriados, prórrogas y el calendario oficial de Hacienda.").pack(anchor="w",pady=6)

    def _build_cabys(self):
        search_frame=ttk.Frame(self.tab_cabys); search_frame.pack(fill="x",pady=(0,6))
        self.cabys_search=tk.StringVar(); ttk.Entry(search_frame,textvariable=self.cabys_search,width=50).pack(side="left")
        ttk.Button(search_frame,text="Buscar",command=self._load_cabys).pack(side="left",padx=5)
        self.cabys_tree=ttk.Treeview(self.tab_cabys,columns=("code","description","rate","source"),show="headings")
        for col,label,width in (("code","Código CAByS",150),("description","Descripción",600),("rate","Tarifa sugerida",120),("source","Fuente",100)):
            self.cabys_tree.heading(col,text=label); self.cabys_tree.column(col,width=width)
        self.cabys_tree.pack(fill="both",expand=True)

    def refresh_all(self):
        try:
            self.status.set("Consultando registro fiscal…")
            self._load_dashboard(); self._load_book("SALE",self.sales_tree); self._load_book("PURCHASE",self.purchases_tree)
            self._load_quality(); self._load_obligations(); self._load_cabys()
            self.status.set("Información fiscal actualizada")
        except Exception as exc:
            self.status.set("No se pudo actualizar")
            messagebox.showerror("Centro fiscal",str(exc),parent=self)

    def _load_dashboard(self):
        data=get_tax_iva_api(self.period.get()); fiscal=data["fiscal"]; accounting=data["accounting"]; diff=data["differences"]
        values={"sales_tax":fiscal["sales_tax"],"purchase_tax_credit":fiscal["purchase_tax_credit"],"net_tax":fiscal["net_tax"],
                "accounting_net":accounting["net_tax"],"difference":diff["net"]}
        for key,value in values.items(): self.kpis[key].set(f"₡{value:,.2f}")
        self.ready.set("LISTO PARA REVISIÓN Y PRESENTACIÓN" if data["ready_to_file"] else "NO PRESENTAR: existen diferencias o datos incompletos")
        q=data["quality"]
        text=(f"XML faltantes: {q.get('missing_xml',0)}\nRespuestas de Hacienda pendientes: {q.get('pending_hacienda',0)}\n"
              f"Documentos sin detalle: {q.get('documents_without_lines',0)}\nLíneas sin CAByS: {q.get('missing_cabys',0)}\n\n"
              "El cálculo documental se compara con las cuentas configuradas de IVA. Una diferencia requiere revisión antes de declarar.")
        self.quality_text.configure(state="normal"); self.quality_text.delete("1.0","end"); self.quality_text.insert("1.0",text); self.quality_text.configure(state="disabled")

    def _load_book(self,direction,tree):
        data=get_tax_book_api(direction,self.period.get())
        tree.delete(*tree.get_children())
        for row in data["data"]:
            party=row.get("receiver_name") if direction=="SALE" else row.get("issuer_name")
            total = float(row.get("total") or 0)
            missing_detail = not row.get("xml_path") or total == 0
            hacienda = row.get("hacienda_status") or ""
            if missing_detail:
                hacienda = f"{hacienda} / INCOMPLETO".strip(" /")
            tree.insert("","end",values=(str(row.get("issue_datetime") or "")[:10],row.get("document_number") or "",party or "",
              row.get("currency_code"),f"{float(row.get('subtotal') or 0):,.2f}",f"{float(row.get('tax_amount') or 0):,.2f}",
              f"{total:,.2f}",hacienda))

    def _load_quality(self):
        rows=get_tax_documents_api(period=self.period.get(),quality_only=True)["data"]
        self.quality_tree.delete(*self.quality_tree.get_children())
        for row in rows:
            self.quality_tree.insert("","end",iid=str(row["id"]),values=(row["id"],row["direction"],str(row.get("issue_datetime") or "")[:10],
              row.get("document_number") or "","Sí" if row.get("xml_path") else "No","Sí" if row.get("electronic_key") else "No",
              row.get("line_count"),row.get("missing_cabys_lines"),row.get("duplicate_key_count"),row.get("hacienda_status")))

    def _load_obligations(self):
        data=get_tax_obligations_api(int(self.period.get()[:4]), period=self.period.get(), pending_only=True); self.obligations_tree.delete(*self.obligations_tree.get_children())
        alerts = []
        for item in data["data"]:
            calendar=item.get("calendar") or [{}]
            for due in calendar:
                status = due.get("alert_status") or "PENDING"
                message = due.get("alert_message") or ""
                key = f"{item['tax_code']}:{due.get('period','')}:{status}"
                self.obligations_tree.insert("","end",values=(item["tax_code"],item["name"],item["periodicity"],due.get("period",""),due.get("estimated_due_date","Configurar"),message),tags=(status,))
                if status in {"DUE_TODAY", "DUE_TOMORROW"} and key not in self._shown_obligation_alerts:
                    alerts.append(f"{item['name']} ({due.get('period','')}): {message}")
                    self._shown_obligation_alerts.add(key)
        if alerts:
            messagebox.showwarning("Obligaciones fiscales", "Vencimientos fiscales proximos:\n\n" + "\n".join(alerts[:8]), parent=self)

    def _load_cabys(self):
        rows=search_tax_cabys_api(self.cabys_search.get()); self.cabys_tree.delete(*self.cabys_tree.get_children())
        for row in rows: self.cabys_tree.insert("","end",values=(row["code"],row["description"],row.get("suggested_tax_rate") or "",row.get("source")))

    def _sync(self):
        try:
            result=sync_accounting_tax_api(); counts=result.get("counts",{})
            messagebox.showinfo("Centro fiscal",f"Sincronización terminada.\nVentas: {counts.get('sales',0)}\nCompras: {counts.get('purchases',0)}",parent=self)
            self.refresh_all()
        except Exception as exc: messagebox.showerror("Sincronización fiscal",str(exc),parent=self)

    def _upload_xml(self,direction):
        path=filedialog.askopenfilename(parent=self,filetypes=[("XML","*.xml")])
        if not path:return
        try:
            result=upload_tax_xml_api(path,direction)
            warnings="\n".join(result.get("warnings",[])); messagebox.showinfo("XML fiscal",f"Documento #{result['id']} registrado.\n{warnings}",parent=self); self.refresh_all()
        except Exception as exc: messagebox.showerror("XML fiscal",str(exc),parent=self)

    def _upload_response(self):
        selected=self.quality_tree.selection()
        if not selected: messagebox.showwarning("Hacienda","Seleccione un documento.",parent=self); return
        path=filedialog.askopenfilename(parent=self,filetypes=[("XML","*.xml")])
        if not path:return
        try: upload_tax_hacienda_response_api(int(selected[0]),path); self.refresh_all()
        except Exception as exc: messagebox.showerror("Respuesta Hacienda",str(exc),parent=self)

    def _open_gmail_inbox(self):
        from Modulos.Finanzas.sections.Accounting.popups.popup_outlook_fiscal import PopupOutlookFiscal
        PopupOutlookFiscal(self)
