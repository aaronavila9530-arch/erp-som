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

        tasks = ttk.LabelFrame(left, text="Pendientes y aprobaciones")
        tasks.pack(fill="both", expand=True)
        self.tasks_frame = ttk.Frame(tasks)
        self.tasks_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.exec_frame = ttk.LabelFrame(right, text="Vista ejecutiva")
        self.exec_frame.pack(fill="both", expand=True)
        self.exec_body = ttk.Frame(self.exec_frame)
        self.exec_body.pack(fill="both", expand=True, padx=10, pady=10)

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
        tk.Frame(row, bg=tone, width=4).pack(side="left", fill="y")
        count = tk.Label(row, text=str(item.get("count") or 0), bg="#EDF7FF", fg=tone, font=("Segoe UI", 12, "bold"), width=4)
        count.pack(side="left", padx=10, pady=10)
        copy = tk.Frame(row, bg="#FFFFFF")
        copy.pack(side="left", fill="x", expand=True, pady=10)
        tk.Label(copy, text=item.get("title") or "-", bg="#FFFFFF", fg="#122033", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        tk.Label(copy, text=item.get("detail") or "", bg="#FFFFFF", fg="#607086", font=("Segoe UI", 9)).pack(anchor="w")
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
        self._section_rows("Top 3 clientes FE", top, "client", "amount", money=True)
        self._section_rows("Aging CxC", aging, "bucket", "amount", money=True)
        self._section_rows("Mix de servicios", mix, "label", "value", money=False)

    def _section_rows(self, title, rows, label_key, value_key, money=False):
        ttk.Label(self.exec_body, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 6))
        if not rows:
            ttk.Label(self.exec_body, text="Sin datos visibles.", foreground="#607086").pack(anchor="w", pady=(0, 10))
            return
        for row in rows[:5]:
            line = ttk.Frame(self.exec_body)
            line.pack(fill="x", pady=2)
            ttk.Label(line, text=str(row.get(label_key) or "-")[:28]).pack(side="left", fill="x", expand=True)
            value = self._money_short(row.get(value_key)) if money else str(row.get(value_key) or 0)
            ttk.Label(line, text=value).pack(side="right")
        ttk.Separator(self.exec_body).pack(fill="x", pady=8)

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
