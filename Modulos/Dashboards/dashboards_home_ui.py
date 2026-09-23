import tkinter as tk
from tkinter import ttk, messagebox

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

        allowed = self._allowed_modules()
        badges = ttk.Frame(container, style="Home.TFrame")
        badges.pack(fill="x", pady=(0, 14))
        for item in allowed[:8]:
            ttk.Label(badges, text=item["label"], style="Badge.TLabel").pack(side="left", padx=(0, 7), pady=2)
        if not allowed:
            ttk.Label(badges, text="Sin módulos visibles configurados", style="Muted.TLabel").pack(anchor="w")

        grid = ttk.Frame(container, style="Home.TFrame")
        grid.pack(fill="x")
        for idx, item in enumerate(allowed):
            self._card(grid, item, idx // 4, idx % 4)

        insight = ttk.Frame(container, style="Home.TFrame")
        insight.pack(fill="both", expand=True, pady=(14, 0))
        self._automation_panel(insight).pack(side="left", fill="both", expand=True, padx=(0, 10))
        self._help_panel(insight).pack(side="right", fill="both", expand=True)

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
        style.configure("Badge.TLabel", background="#EDF7FF", foreground="#005DA8", font=("Segoe UI", 9, "bold"), padding=(10, 4))

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
