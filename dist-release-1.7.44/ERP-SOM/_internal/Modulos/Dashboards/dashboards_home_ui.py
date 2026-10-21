import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import api_client

try:
    from session_context import get_company_code
except Exception:
    def get_company_code():
        return "MSL-CR"


class DashboardsHomeUI(ttk.Frame):
    """Role-aware command center for SOM desktop."""

    MODULES = [
        {
            "code": "servicios",
            "label": "Servicios",
            "module": "Servicios",
            "tone": "#005DA8",
            "summary": "Operaciones activas, edición, cierres, costos y trazabilidad.",
            "action": "_open_servicios",
        },
        {
            "code": "finanzas",
            "label": "Finanzas",
            "module": "Finanzas",
            "tone": "#00703C",
            "summary": "Billing, Collections, bancos, ITP, Accounting y automatizaciones.",
            "action": "_open_finanzas",
        },
        {
            "code": "comercial",
            "label": "Comercial",
            "module": "Comercial",
            "tone": "#8A5CF6",
            "summary": "Cotizaciones, precios, clientes, puertos y analítica comercial.",
            "action": "_open_comercial",
        },
        {
            "code": "informes",
            "label": "Informes",
            "module": "Informes",
            "tone": "#029FCF",
            "summary": "Draft, bunker, condition, certificados y revisiones.",
            "action": "_open_informes",
        },
        {
            "code": "hhrre",
            "label": "HHRR",
            "module": "HHRR",
            "tone": "#A66700",
            "summary": "Horas, vacaciones, payroll, colillas y red médica.",
        },
        {
            "code": "master_data",
            "label": "Master Data",
            "module": "Master Data",
            "tone": "#334155",
            "summary": "Catálogos base, clientes, proveedores, bancos y estructura.",
        },
        {
            "code": "admin_users",
            "label": "Admin",
            "module": "Admin",
            "tone": "#B42318",
            "summary": "Usuarios, permisos, auditoría y gobierno del ERP.",
        },
        {
            "code": "qa_som",
            "label": "Q&A SOM",
            "module": "Q&A SOM",
            "tone": "#4B5563",
            "summary": "Manual vivo, soporte guiado y conocimiento operativo.",
        },
    ]

    def __init__(self, parent, usuario=None, rol=None, can_access=None, open_module=None):
        super().__init__(parent)
        self.parent = parent
        self.usuario = usuario or "-"
        self.rol = rol or "user"
        self.can_access = can_access or (lambda _code: True)
        self.open_module = open_module
        self.pack(fill="both", expand=True)
        self._build_ui()

    class Collapsible(ttk.Frame):
        def __init__(self, parent, title, expanded=True):
            super().__init__(parent)
            self.expanded = tk.BooleanVar(value=expanded)
            self.head = ttk.Frame(self)
            self.head.pack(fill="x")
            self.button = ttk.Button(self.head, text="-" if expanded else "+", width=3, command=self.toggle)
            self.button.pack(side="left", padx=(0, 6))
            ttk.Label(self.head, text=title, font=("Segoe UI", 10, "bold")).pack(side="left", fill="x", expand=True)
            self.body = ttk.Frame(self)
            if expanded:
                self.body.pack(fill="both", expand=True, pady=(8, 0))

        def toggle(self):
            if self.expanded.get():
                self.body.forget()
                self.expanded.set(False)
                self.button.configure(text="+")
            else:
                self.body.pack(fill="both", expand=True, pady=(8, 0))
                self.expanded.set(True)
                self.button.configure(text="-")

    def _allowed_modules(self):
        return [item for item in self.MODULES if self.can_access(item["code"])]

    def _build_ui(self):
        self.configure(style="Home.TFrame")
        self._configure_styles()
        self.summary = {}
        self.actions_payload = {}

        container = ttk.Frame(self, style="Home.TFrame")
        container.pack(fill="both", expand=True, padx=22, pady=18)

        hero = ttk.Frame(container, style="Hero.TFrame")
        hero.pack(fill="x", pady=(0, 14))

        title_box = ttk.Frame(hero, style="Hero.TFrame")
        title_box.pack(side="left", fill="both", expand=True, padx=(0, 16))
        ttk.Label(title_box, text="Centro de control SOM", style="HeroTitle.TLabel").pack(anchor="w")
        ttk.Label(
            title_box,
            text="Inicio personalizado por rol, permisos y empresa activa. Desde aquí solo se muestran áreas autorizadas.",
            style="HeroText.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(6, 0))

        session_box = ttk.Frame(hero, style="Session.TFrame", padding=14)
        session_box.pack(side="right", fill="y")
        ttk.Label(session_box, text="SESIÓN", style="Eyebrow.TLabel").pack(anchor="w")
        ttk.Label(session_box, text=self.usuario, style="SessionUser.TLabel").pack(anchor="w", pady=(4, 2))
        ttk.Label(
            session_box,
            text=f"{str(self.rol).upper()} · {get_company_code()}",
            style="Muted.TLabel",
        ).pack(anchor="w")

        self.kpi_frame = ttk.Frame(container, style="Home.TFrame")
        self.kpi_frame.pack(fill="x", pady=(0, 14))

        body = ttk.Frame(container, style="Home.TFrame")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Home.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        right = ttk.Frame(body, style="Home.TFrame")
        right.grid(row=0, column=1, sticky="nsew")

        command = ttk.Frame(left, style="Hero.TFrame", padding=16)
        command.pack(fill="x", pady=(0, 12))
        ttk.Label(command, text="Centro de control SOM", style="SectionTitle.TLabel").pack(anchor="w")
        ttk.Label(
            command,
            text="Pendientes reales, indicadores y alertas filtradas por rol, permisos y empresa.",
            style="HeroText.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(4, 10))
        self.task_summary = ttk.Frame(command, style="Hero.TFrame")
        self.task_summary.pack(fill="x")

        tasks = self.Collapsible(left, "Pendientes y aprobaciones")
        tasks.pack(fill="both", expand=True)
        self.tasks_frame = ttk.Frame(tasks.body)
        self.tasks_frame.pack(fill="both", expand=True)

        self.exec_frame = self.Collapsible(right, "Vista ejecutiva")
        self.exec_frame.pack(fill="both", expand=True)
        self.exec_body = ttk.Frame(self.exec_frame.body)
        self.exec_body.pack(fill="both", expand=True)

        self._load_live_home()

    def _configure_styles(self):
        style = ttk.Style(self)
        style.configure("Home.TFrame", background="#EEF3F8")
        style.configure("Hero.TFrame", background="#FFFFFF")
        style.configure("Session.TFrame", background="#F8FBFE", relief="solid", borderwidth=1)
        style.configure("HeroTitle.TLabel", background="#FFFFFF", foreground="#122033", font=("Segoe UI", 24, "bold"))
        style.configure("HeroText.TLabel", background="#FFFFFF", foreground="#607086", font=("Segoe UI", 10))
        style.configure("SessionUser.TLabel", background="#F8FBFE", foreground="#122033", font=("Segoe UI", 16, "bold"))
        style.configure("Eyebrow.TLabel", background="#F8FBFE", foreground="#005DA8", font=("Segoe UI", 8, "bold"))
        style.configure("Muted.TLabel", background="#F8FBFE", foreground="#607086", font=("Segoe UI", 9))
        style.configure("SectionTitle.TLabel", background="#FFFFFF", foreground="#122033", font=("Segoe UI", 20, "bold"))
        style.configure("Badge.TLabel", background="#EDF7FF", foreground="#005DA8", font=("Segoe UI", 9, "bold"), padding=(10, 4))

    def _module_codes(self):
        return [item["code"] for item in self._allowed_modules()]

    def _load_live_home(self):
        year = datetime.now().year
        try:
            modules = self._module_codes()
            self.summary = api_client.get_som_summary_api(year, modules=modules) or {}
            self.actions_payload = api_client.get_som_action_center_api(year, modules=modules) or {}
        except Exception as exc:
            self._render_error(exc)
            return
        self._render_kpis()
        self._render_tasks()
        self._render_executive()

    def _render_error(self, exc):
        ttk.Label(self.kpi_frame, text=f"No se pudo cargar Inicio: {exc}", foreground="#B42318").pack(anchor="w")

    def _money_short(self, value):
        amount = float(value or 0)
        if abs(amount) >= 1_000_000:
            return f"${amount/1_000_000:,.1f}M"
        if abs(amount) >= 1_000:
            return f"${amount/1_000:,.1f}K"
        return f"${amount:,.2f}"

    def _kpi(self, parent, label, value, hint):
        box = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#D7E1EC", highlightthickness=1)
        box.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(box, text=label.upper(), bg="#FFFFFF", fg="#607086", font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(box, text=value, bg="#FFFFFF", fg="#122033", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=12, pady=(5, 0))
        tk.Label(box, text=hint, bg="#FFFFFF", fg="#122033", font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 10))

    def _render_kpis(self):
        for child in self.kpi_frame.winfo_children():
            child.destroy()
        kpis = self.summary.get("kpis") or {}
        can_finance = bool((self.summary.get("visibility") or {}).get("finance"))
        self._kpi(self.kpi_frame, "Servicios YTD", str(int(kpis.get("services") or 0)), "Operaciones del año")
        if can_finance:
            self._kpi(self.kpi_frame, "Facturas FE", self._money_short(kpis.get("invoiced")), "Electrónicas año a fecha")
            self._kpi(self.kpi_frame, "CxC", self._money_short(kpis.get("ar")), "Saldo pendiente")
        self._kpi(self.kpi_frame, "Informes YTD", str(int(kpis.get("reports") or 0)), "Servicios con informe")

    def _render_tasks(self):
        for child in self.task_summary.winfo_children():
            child.destroy()
        for child in self.tasks_frame.winfo_children():
            child.destroy()
        rows = [item for item in (self.actions_payload.get("actions") or []) if self.can_access(item.get("module"))]
        critical = sum(int(item.get("count") or 0) for item in rows if item.get("severity") == "critical")
        review = sum(int(item.get("count") or 0) for item in rows if item.get("severity") == "warning")
        total = sum(int(item.get("count") or 0) for item in rows)
        for label, value in (("Críticos", critical), ("Revisión", review), ("Total tareas", total)):
            item = ttk.Frame(self.task_summary, style="Hero.TFrame")
            item.pack(side="left", fill="x", expand=True, padx=(0, 8))
            ttk.Label(item, text=label.upper(), style="Eyebrow.TLabel").pack(anchor="w")
            ttk.Label(item, text=str(value), style="SessionUser.TLabel").pack(anchor="w")
        if not rows:
            ttk.Label(self.tasks_frame, text="Sin pendientes visibles para tu rol.", foreground="#607086").pack(anchor="w")
            return
        for item in rows:
            self._task_row(self.tasks_frame, item)

    def _task_row(self, parent, item):
        tone = {"critical": "#B42318", "warning": "#B7791F", "info": "#005DA8"}.get(item.get("severity"), "#64748B")
        row = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#D7E1EC", highlightthickness=1)
        row.pack(fill="x", pady=(0, 8))
        row.bind("<Button-1>", lambda _event, i=item: self._show_insight("action", i))
        tk.Frame(row, bg=tone, width=4).pack(side="left", fill="y")
        count = tk.Label(row, text=str(item.get("count") or 0), bg="#EDF7FF", fg=tone, font=("Segoe UI", 12, "bold"), width=4)
        count.pack(side="left", padx=10, pady=10)
        count.bind("<Button-1>", lambda _event, i=item: self._show_insight("action", i))
        copy = tk.Frame(row, bg="#FFFFFF")
        copy.pack(side="left", fill="x", expand=True, pady=10)
        copy.bind("<Button-1>", lambda _event, i=item: self._show_insight("action", i))
        title = tk.Label(copy, text=item.get("title") or "-", bg="#FFFFFF", fg="#122033", font=("Segoe UI", 10, "bold"))
        title.pack(anchor="w")
        title.bind("<Button-1>", lambda _event, i=item: self._show_insight("action", i))
        detail = tk.Label(copy, text=item.get("detail") or "", bg="#FFFFFF", fg="#607086", font=("Segoe UI", 9))
        detail.pack(anchor="w")
        detail.bind("<Button-1>", lambda _event, i=item: self._show_insight("action", i))
        ttk.Button(row, text=item.get("cta") or "Abrir", command=lambda m=item.get("module"): self._open_module_code(m)).pack(side="right", padx=10)

    def _render_executive(self):
        for child in self.exec_body.winfo_children():
            child.destroy()
        visibility = self.summary.get("visibility") or {}
        executive = self.summary.get("executive") or {}
        if not visibility.get("finance"):
            ttk.Label(self.exec_body, text="Métricas financieras ocultas por rol/permisos.", foreground="#607086", wraplength=360).pack(anchor="w")
            return
        top = executive.get("top_clients") or []
        aging = executive.get("aging") or []
        mix = executive.get("service_mix") or []
        monthly = self.summary.get("monthly") or []
        kpis = self.summary.get("kpis") or {}
        if visibility.get("executive"):
            self._pill_rows(
                "Indicadores ejecutivos",
                [
                    ("Top cliente", top[0].get("client") if top else "-", "topClient", top[0] if top else {}),
                    ("Facturas FE top 3", self._money_short(sum(float(r.get("amount") or 0) for r in top[:3])), "top3", {"rows": top[:3]}),
                    ("CxC abierta", self._money_short(kpis.get("ar")), "ar", {"amount": kpis.get("ar"), "aging": aging}),
                ],
            )
        else:
            self._pill_rows(
                "Indicadores financieros",
                [
                    ("Facturas FE año a fecha", self._money_short(kpis.get("invoiced")), "top3", {"amount": kpis.get("invoiced"), "rows": []}),
                    ("CxC abierta", self._money_short(kpis.get("ar")), "ar", {"amount": kpis.get("ar"), "aging": aging}),
                ],
            )
        self._section_rows("Últimos 6 meses", monthly, "month", "services", money=False, kind="month")
        if visibility.get("executive"):
            self._section_rows("Top 3 clientes FE", top, "client", "amount", money=True, kind="topClient")
        self._section_rows("Aging CxC", aging, "bucket", "amount", money=True, kind="aging")
        self._section_rows("Mix de servicios", mix, "label", "value", money=False, kind="service")

    def _pill_rows(self, title, rows):
        section = self.Collapsible(self.exec_body, title)
        section.pack(fill="x", pady=(0, 10))
        for label, value, kind, payload in rows:
            line = tk.Frame(section.body, bg="#FBFDFE", highlightbackground="#D7E1EC", highlightthickness=1)
            line.pack(fill="x", pady=2)
            line.bind("<Button-1>", lambda _event, k=kind, p=payload: self._show_insight(k, p))
            left = tk.Label(line, text=label, bg="#FBFDFE", fg="#122033", font=("Segoe UI", 9, "bold"))
            left.pack(side="left", padx=8, pady=6)
            right = tk.Label(line, text=str(value), bg="#FBFDFE", fg="#122033", font=("Segoe UI", 9))
            right.pack(side="right", padx=8, pady=6)
            left.bind("<Button-1>", lambda _event, k=kind, p=payload: self._show_insight(k, p))
            right.bind("<Button-1>", lambda _event, k=kind, p=payload: self._show_insight(k, p))

    def _section_rows(self, title, rows, label_key, value_key, money=False, kind=None):
        section = self.Collapsible(self.exec_body, title)
        section.pack(fill="x", pady=(0, 10))
        if not rows:
            ttk.Label(section.body, text="Sin datos visibles.", foreground="#607086").pack(anchor="w", pady=(0, 6))
            return
        max_value = max(float(row.get(value_key) or 0) for row in rows[:6]) or 1
        for row in rows[:5]:
            line = tk.Frame(section.body, bg="#FFFFFF")
            line.pack(fill="x", pady=2)
            line.bind("<Button-1>", lambda _event, k=kind, p=row: self._show_insight(k, p))
            label = tk.Label(line, text=str(row.get(label_key) or "-")[:28], bg="#FFFFFF", fg="#122033")
            label.pack(side="left", fill="x", expand=True)
            label.bind("<Button-1>", lambda _event, k=kind, p=row: self._show_insight(k, p))
            bar = tk.Frame(line, bg="#E8EEF5", width=110, height=8)
            bar.pack(side="left", padx=8)
            fill_width = max(8, int(float(row.get(value_key) or 0) / max_value * 110))
            tk.Frame(bar, bg="#00703C" if kind != "aging" else "#B7791F", width=fill_width, height=8).place(x=0, y=0)
            value = self._money_short(row.get(value_key)) if money else str(row.get(value_key) or 0)
            value_label = tk.Label(line, text=value, bg="#FFFFFF", fg="#122033")
            value_label.pack(side="right")
            value_label.bind("<Button-1>", lambda _event, k=kind, p=row: self._show_insight(k, p))

    def _show_insight(self, kind, item):
        item = item or {}
        title = {
            "action": "Pendiente",
            "month": "Lectura mensual",
            "service": "Mix de servicios",
            "topClient": "Top cliente",
            "top3": "Facturas FE",
            "ar": "CxC abierta",
            "aging": "Aging CxC",
        }.get(kind, "Detalle inteligente")
        text = self._insight_text(kind, item)
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("520x300")
        win.transient(self.winfo_toplevel())
        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text=text, wraplength=470, justify="left").pack(anchor="w", pady=(12, 14))
        actions = ttk.Frame(frame)
        actions.pack(fill="x", side="bottom")
        module = item.get("module")
        if kind in {"month", "ar", "aging", "topClient", "top3"} and self.can_access("finanzas"):
            ttk.Button(actions, text="Abrir Finanzas", command=lambda: [win.destroy(), self._open_module_code("finanzas")]).pack(side="left", padx=(0, 8))
        if kind == "service" and self.can_access("servicios"):
            ttk.Button(actions, text="Abrir Servicios", command=lambda: [win.destroy(), self._open_module_code("servicios")]).pack(side="left", padx=(0, 8))
        if kind == "action" and module:
            ttk.Button(actions, text=item.get("cta") or "Abrir módulo", command=lambda: [win.destroy(), self._open_module_code(module)]).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Cerrar", command=win.destroy).pack(side="right")

    def _insight_text(self, kind, item):
        if kind == "action":
            return (
                f"Cantidad: {item.get('count') or 0}\n"
                f"Severidad: {item.get('severity') or 'info'}\n"
                f"Módulo: {item.get('module') or '-'}\n\n"
                f"{item.get('detail') or 'Pendiente visible según rol y permisos.'}"
            )
        if kind == "month":
            return (
                f"Mes: {item.get('month') or '-'}\n"
                f"Servicios: {int(item.get('services') or 0)}\n"
                f"CxC abierta: {self._money_short(item.get('ar_open'))}\n\n"
                "Úsalo para comparar movimiento operativo contra cobros abiertos y priorizar gestión."
            )
        if kind == "service":
            return (
                f"Servicio: {item.get('label') or '-'}\n"
                f"Cantidad: {item.get('value') or 0}\n\n"
                "Indica concentración del mix de servicios. Sirve para revisar demanda, asignación y oportunidades comerciales."
            )
        if kind == "topClient":
            return (
                f"Cliente: {item.get('client') or '-'}\n"
                f"Facturas FE: {item.get('count') or 0}\n"
                f"Monto: {self._money_short(item.get('amount'))}\n\n"
                "Cliente con mayor peso en facturación electrónica del año. Conviene revisar crédito y cobros abiertos."
            )
        if kind == "aging":
            return (
                f"Rango: {item.get('bucket') or '-'}\n"
                f"Monto: {self._money_short(item.get('amount'))}\n\n"
                "Prioriza rangos vencidos antes de nueva facturación al mismo cliente."
            )
        rows = item.get("rows") or []
        return (
            f"Monto: {self._money_short(item.get('amount') or sum(float(r.get('amount') or 0) for r in rows))}\n"
            f"Clientes: {len(rows)}\n\n"
            "Suma visible según rol/permisos. No expone información financiera a usuarios sin acceso."
        )

    def _card(self, parent, item, row, col):
        card = tk.Frame(parent, bg="#FFFFFF", highlightbackground="#D7E1EC", highlightthickness=1)
        card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
        parent.grid_columnconfigure(col, weight=1, minsize=210)

        tk.Frame(card, bg=item["tone"], height=4).pack(fill="x")
        body = tk.Frame(card, bg="#FFFFFF")
        body.pack(fill="both", expand=True, padx=14, pady=12)
        tk.Label(body, text=item["label"], bg="#FFFFFF", fg="#122033", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(
            body,
            text=item["summary"],
            bg="#FFFFFF",
            fg="#607086",
            font=("Segoe UI", 9),
            wraplength=230,
            justify="left",
        ).pack(anchor="w", pady=(6, 12))
        ttk.Button(body, text=f"Abrir {item['label']}", command=lambda i=item: self._open_item(i)).pack(anchor="w")

    def _automation_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Automatizaciones visibles")
        rows = [
            ("Seguridad", "Las tarjetas se filtran por permisos de usuario."),
            ("BAC / Gmail fiscal", "Visible para Finanzas; backend automático cada 15 min."),
            ("Tarjetas corporativas", "PDF recibido y contabilización histórica día 3."),
            ("Alertas", "Informes, fiscal y negocio respetan rol y permisos."),
        ]
        for label, text in rows:
            ttk.Label(frame, text=label, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(10, 0))
            ttk.Label(frame, text=text, foreground="#607086", wraplength=460).pack(anchor="w", padx=12)
        return frame

    def _help_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Siguiente mejor acción")
        allowed = self._allowed_modules()
        if allowed:
            text = f"Empezá por {allowed[0]['label']} o usá el menú lateral para ir directo al flujo autorizado."
        else:
            text = "Este usuario no tiene permisos visibles. Revisá Admin > Permisos con un usuario autorizado."
        ttk.Label(frame, text=text, wraplength=460, foreground="#334155").pack(anchor="w", padx=12, pady=12)
        ttk.Label(
            frame,
            text="La pantalla de inicio no expone datos financieros ni operativos si el rol no tiene acceso al módulo.",
            wraplength=460,
            foreground="#607086",
        ).pack(anchor="w", padx=12, pady=(0, 12))
        return frame

    def _open_item(self, item):
        action = item.get("action")
        if action and hasattr(self, action):
            return getattr(self, action)()
        if self.open_module:
            return self.open_module(item["module"])
        messagebox.showinfo("SOM", f"Abrir {item['label']}")

    def _open_module_code(self, code):
        found = next((item for item in self.MODULES if item["code"] == code), None)
        if found:
            return self._open_item(found)
        messagebox.showinfo("SOM", f"Abrir {code or 'módulo'}")

    def _clear_host(self):
        for child in self.parent.winfo_children():
            child.destroy()

    def _open_servicios(self):
        try:
            self._clear_host()
            from Modulos.Dashboards.dashboards_servicios import DashboardsServiciosUI
            DashboardsServiciosUI(self.parent)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir el dashboard de servicios:\n{exc}")

    def _open_finanzas(self):
        try:
            self._clear_host()
            from Modulos.Dashboards.dashboards_finanzas_ui import DashboardsFinanzasUI
            DashboardsFinanzasUI(self.parent)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir el dashboard de finanzas:\n{exc}")

    def _open_comercial(self):
        try:
            self._clear_host()
            from Modulos.Dashboards.dashboards_comercial_ui import DashboardsComercialUI
            DashboardsComercialUI(self.parent)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir el dashboard comercial:\n{exc}")

    def _open_informes(self):
        try:
            self._clear_host()
            from Modulos.Dashboards.dashboards_informes_ui import DashboardsInformesUI
            DashboardsInformesUI(self.parent)
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir el dashboard de informes:\n{exc}")
