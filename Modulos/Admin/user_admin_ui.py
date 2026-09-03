import tkinter as tk
from tkinter import ttk, messagebox

import api_client


LOCAL_MODULE_ACTIONS = {
    "dashboard": [{"code": "view", "label": "Ver dashboard"}],
    "master_data": [
        {"code": "view", "label": "Ver Master Data"},
        {"code": "company_profile", "label": "Ver/editar datos de empresa"},
        {"code": "clients_view", "label": "Ver clientes"},
        {"code": "clients_edit", "label": "Crear/editar clientes"},
        {"code": "providers_view", "label": "Ver proveedores"},
        {"code": "providers_edit", "label": "Crear/editar proveedores"},
        {"code": "employees_view", "label": "Ver empleados"},
        {"code": "employees_edit", "label": "Crear/editar empleados"},
        {"code": "surveyors_view", "label": "Ver surveyors"},
        {"code": "surveyors_edit", "label": "Crear/editar surveyors"},
        {"code": "ports_view", "label": "Ver puertos"},
        {"code": "ports_edit", "label": "Crear/editar puertos"},
        {"code": "operations_view", "label": "Ver operaciones"},
        {"code": "operations_edit", "label": "Crear/editar operaciones"},
        {"code": "bulk_import", "label": "Importaciones masivas"},
        {"code": "export", "label": "Exportar Master Data"},
        {"code": "delete", "label": "Eliminar registros"},
    ],
    "servicios": [
        {"code": "view", "label": "Ver servicios"},
        {"code": "view_detail", "label": "Ver detalle de servicio"},
        {"code": "create", "label": "Crear servicio"},
        {"code": "edit", "label": "Editar servicio"},
        {"code": "edit_client", "label": "Editar cliente/contacto"},
        {"code": "edit_vessel", "label": "Editar buque/contenedor"},
        {"code": "edit_operation", "label": "Editar operacion/puerto/pais"},
        {"code": "assign_surveyor", "label": "Asignar surveyor"},
        {"code": "close_service", "label": "Cerrar servicio"},
        {"code": "cancel_service", "label": "Cancelar servicio"},
        {"code": "delays", "label": "Gestionar demoras"},
        {"code": "generate_report", "label": "Generar informe de servicio"},
        {"code": "billing_ready", "label": "Enviar a facturacion"},
        {"code": "download", "label": "Exportar/descargar"},
    ],
    "finanzas": [
        {"code": "view", "label": "Ver Finanzas"},
        {"code": "billing_view", "label": "Ver Billing"},
        {"code": "billing_manual_invoice", "label": "Crear factura manual"},
        {"code": "billing_xml_invoice", "label": "Crear factura XML"},
        {"code": "billing_advance_invoice", "label": "Factura anticipada"},
        {"code": "billing_credit_note", "label": "Crear nota de credito"},
        {"code": "collections_view", "label": "Ver Collections"},
        {"code": "collections_edit", "label": "Editar Collections"},
        {"code": "collections_apply_payment", "label": "Aplicar pagos CxC"},
        {"code": "collections_post_accounting", "label": "Contabilizar Collections"},
        {"code": "collections_bank_select", "label": "Seleccionar banco en Collections"},
        {"code": "itp_view", "label": "Ver ITP"},
        {"code": "itp_edit", "label": "Editar ITP"},
        {"code": "itp_apply_payment", "label": "Aplicar pagos ITP"},
        {"code": "itp_upload_xml", "label": "Cargar XML compras"},
        {"code": "itp_post_accounting", "label": "Contabilizar ITP"},
        {"code": "itp_quincenal", "label": "Obligaciones quincenales"},
        {"code": "bank_reconciliation_view", "label": "Ver bancos/conciliacion"},
        {"code": "bank_reconciliation_import", "label": "Importar extractos"},
        {"code": "bank_reconciliation_match", "label": "Matching bancario"},
        {"code": "bank_reconciliation_close", "label": "Cerrar conciliacion"},
        {"code": "accounting_view", "label": "Ver Accounting"},
        {"code": "accounting_post", "label": "Postear asientos"},
        {"code": "accounting_adjust", "label": "Ajustar/reversar asientos"},
        {"code": "accounting_catalog", "label": "Catalogo de cuentas"},
        {"code": "accounting_engine", "label": "Motor de contabilizacion"},
        {"code": "accounting_auxiliaries", "label": "Auxiliares contables"},
        {"code": "accounting_audit", "label": "Auditoria financiera"},
        {"code": "accounting_alerts", "label": "Alertas y validaciones"},
        {"code": "accounting_monthly_close", "label": "Cierre mensual"},
        {"code": "accounting_portia", "label": "PORTIA contable"},
        {"code": "tax_center", "label": "Centro fiscal"},
        {"code": "tax_declarations", "label": "Declaraciones D150/D102"},
        {"code": "legal_library", "label": "Biblioteca legal"},
        {"code": "fixed_assets", "label": "Activos fijos"},
        {"code": "inventory", "label": "Inventarios"},
        {"code": "executive_reports", "label": "Reportes ejecutivos"},
        {"code": "reports_download", "label": "Reportes/descargas"},
        {"code": "admin", "label": "Administrar Finanzas"},
    ],
    "hhrre": [
        {"code": "view", "label": "Ver HHRR"},
        {"code": "payslips_view", "label": "Ver colillas"},
        {"code": "payslips_download", "label": "Descargar colillas"},
        {"code": "payroll_view", "label": "Ver Payroll"},
        {"code": "payroll_generate", "label": "Generar Payroll"},
        {"code": "requests_view", "label": "Ver solicitudes"},
        {"code": "requests_create", "label": "Crear solicitudes"},
        {"code": "requests_approve", "label": "Aprobar/rechazar solicitudes"},
        {"code": "hours_view", "label": "Ver horas"},
        {"code": "hours_register", "label": "Registrar horas"},
        {"code": "hours_approve", "label": "Aprobar horas"},
        {"code": "liquidations", "label": "Generar liquidaciones"},
        {"code": "employees_view", "label": "Ver empleados HHRR"},
        {"code": "employees_edit", "label": "Editar empleados HHRR"},
        {"code": "salary_calculator", "label": "Calculadora salarial"},
        {"code": "medical_network", "label": "Red medica"},
        {"code": "policies_view", "label": "Ver politicas"},
        {"code": "policies_edit", "label": "Crear/editar politicas"},
        {"code": "news_publish", "label": "Publicar noticias"},
    ],
    "comercial": [
        {"code": "view", "label": "Ver Comercial"},
        {"code": "quotes_view", "label": "Ver cotizaciones"},
        {"code": "quotes_edit", "label": "Crear/editar cotizaciones"},
        {"code": "prices_view", "label": "Ver precios"},
        {"code": "prices_edit", "label": "Editar precios"},
        {"code": "analytics_view", "label": "Analitica comercial"},
        {"code": "download", "label": "Exportar/descargar"},
    ],
    "informes": [
        {"code": "view", "label": "Ver Informes"},
        {"code": "generate", "label": "Generar informes"},
        {"code": "review", "label": "Revisar informes"},
        {"code": "edit", "label": "Editar informes"},
        {"code": "submit", "label": "Enviar a revision"},
        {"code": "approve", "label": "Aprobar/rechazar"},
        {"code": "download", "label": "Exportar/descargar"},
        {"code": "attachments", "label": "Adjuntos"},
        {"code": "draft_survey", "label": "Draft Survey"},
        {"code": "draft_survey_edit", "label": "Editar Draft Survey"},
        {"code": "draft_survey_export", "label": "Exportar Draft Survey"},
        {"code": "vessel_reports", "label": "Informes de buque"},
        {"code": "container_reports", "label": "Informes de contenedor"},
        {"code": "certificates", "label": "Certificados"},
        {"code": "ong_generate", "label": "Generar ONG"},
        {"code": "ong_review", "label": "Revisar ONG"},
        {"code": "ong_agenda", "label": "Agenda ONG"},
        {"code": "ong_agenda_edit", "label": "Editar agenda ONG"},
        {"code": "ong_agenda_export", "label": "Exportar agenda ONG"},
        {"code": "portia", "label": "PORTIA en informes"},
    ],
    "portia": [
        {"code": "view", "label": "Usar PORTIA"},
        {"code": "finance", "label": "PORTIA contable"},
        {"code": "reports", "label": "PORTIA informes"},
    ],
    "qa_som": [
        {"code": "view", "label": "Ver Q&A SOM"},
        {"code": "ask", "label": "Preguntar"},
    ],
    "admin_users": [
        {"code": "view", "label": "Ver Admin"},
        {"code": "users_create", "label": "Crear usuarios"},
        {"code": "users_permissions", "label": "Asignar permisos"},
        {"code": "users_disable", "label": "Inactivar usuarios"},
        {"code": "company_switch", "label": "Cambiar empresa"},
        {"code": "audit", "label": "Auditar cambios de usuarios"},
        {"code": "admin", "label": "Administrar usuarios"},
    ],
}


class UserAdminUI(tk.Frame):
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent, bg="white")
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back
        self.people = []
        self.users = []
        self.meta = {"modules": [], "actions": [], "module_actions": {}, "roles": [], "password_rules": []}
        self.permission_vars = {}
        self.selected_person = tk.StringVar()
        self.selected_user = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.role_var = tk.StringVar(value="user")
        self.active_var = tk.BooleanVar(value=True)
        self.permission_status_var = tk.StringVar(value="Selecciona un usuario para ver sus permisos.")
        self._build()
        self._load_data()

    def _build(self):
        header = tk.Frame(self, bg="white")
        header.pack(fill="x", padx=18, pady=(14, 8))
        tk.Label(header, text="Administracion de usuarios", bg="white", fg="#003A75",
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        if self.on_back:
            tk.Button(header, text="Volver", command=self.on_back).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=10)

        self.create_tab = tk.Frame(self.notebook, bg="white")
        self.permissions_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(self.create_tab, text="Crear usuario")
        self.notebook.add(self.permissions_tab, text="Permisos")

        self._build_create_tab()
        self._build_permissions_tab()

    def _build_create_tab(self):
        form = ttk.LabelFrame(self.create_tab, text="Nuevo usuario desde empleado/proveedor")
        form.pack(fill="x", padx=10, pady=10)

        ttk.Label(form, text="Persona base").grid(row=0, column=0, sticky="w", padx=8, pady=8)
        self.person_combo = ttk.Combobox(form, textvariable=self.selected_person, state="readonly", width=55)
        self.person_combo.grid(row=0, column=1, sticky="ew", padx=8, pady=8)
        self.person_combo.bind("<<ComboboxSelected>>", lambda _e: self._prefill_from_person())

        ttk.Label(form, text="Usuario").grid(row=1, column=0, sticky="w", padx=8, pady=8)
        ttk.Entry(form, textvariable=self.username_var, width=32).grid(row=1, column=1, sticky="w", padx=8, pady=8)

        ttk.Label(form, text="Contrasena").grid(row=2, column=0, sticky="w", padx=8, pady=8)
        ttk.Entry(form, textvariable=self.password_var, show="*", width=32).grid(row=2, column=1, sticky="w", padx=8, pady=8)

        ttk.Label(form, text="Rol base").grid(row=3, column=0, sticky="w", padx=8, pady=8)
        self.role_combo = ttk.Combobox(form, textvariable=self.role_var, state="readonly", width=30)
        self.role_combo.grid(row=3, column=1, sticky="w", padx=8, pady=8)

        ttk.Checkbutton(form, text="Activo", variable=self.active_var).grid(row=4, column=1, sticky="w", padx=8, pady=8)
        form.columnconfigure(1, weight=1)

        rules = ttk.LabelFrame(self.create_tab, text="Requisitos minimos de contrasena")
        rules.pack(fill="x", padx=10, pady=(0, 10))
        self.rules_label = tk.Label(rules, bg="white", justify="left", anchor="w")
        self.rules_label.pack(fill="x", padx=10, pady=8)

        tk.Label(self.create_tab, text="Permisos iniciales", bg="white", fg="#003A75",
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=12, pady=(8, 4))
        self.create_perm_frame = tk.Frame(self.create_tab, bg="white")
        self.create_perm_frame.pack(fill="both", expand=True, padx=10, pady=4)
        self.create_permission_vars = {}

        buttons = tk.Frame(self.create_tab, bg="white")
        buttons.pack(fill="x", padx=10, pady=10)
        tk.Button(buttons, text="Crear usuario", command=self._create_user).pack(side="right")

    def _build_permissions_tab(self):
        top = ttk.LabelFrame(self.permissions_tab, text="Usuario existente")
        top.pack(fill="x", padx=10, pady=10)
        ttk.Label(top, text="Usuario").pack(side="left", padx=8, pady=8)
        self.user_combo = ttk.Combobox(top, textvariable=self.selected_user, state="readonly", width=35)
        self.user_combo.pack(side="left", padx=8, pady=8)
        self.user_combo.bind("<<ComboboxSelected>>", lambda _e: self._load_selected_user_permissions())
        tk.Button(top, text="Recargar", command=self._load_data).pack(side="left", padx=8)
        tk.Button(top, text="Guardar permisos", command=self._save_permissions).pack(side="right", padx=8)

        tk.Label(
            self.permissions_tab,
            textvariable=self.permission_status_var,
            bg="white",
            fg="#003A75",
            anchor="w",
        ).pack(fill="x", padx=14, pady=(0, 4))

        self.permissions_matrix = tk.Frame(self.permissions_tab, bg="white")
        self.permissions_matrix.pack(fill="both", expand=True, padx=10, pady=4)

    def _load_data(self):
        try:
            self.meta = api_client.get_admin_users_meta_api()
            self.people = api_client.get_admin_people_api()
            self.users = api_client.get_admin_users_api()
        except Exception as exc:
            messagebox.showerror("Usuarios", f"No se pudieron cargar usuarios/permisos:\n{exc}", parent=self)
            return
        self.role_combo["values"] = self.meta.get("roles", ["user"])
        self.rules_label.configure(text="\n".join(f"- {r}" for r in self.meta.get("password_rules", [])))
        self.person_combo["values"] = [self._person_label(p) for p in self.people]
        self.user_combo["values"] = [u.get("usuario", "") for u in self.users]
        self._render_permission_matrix(self.create_perm_frame, self.create_permission_vars)
        self._render_permission_matrix(self.permissions_matrix, self.permission_vars)
        if self.selected_user.get():
            self._load_selected_user_permissions()

    def _person_label(self, person):
        kind = (person.get("source_type") or "").title()
        label = person.get("label") or ""
        return f"{kind}: {label}"

    def _selected_person_payload(self):
        label = self.selected_person.get()
        values = [self._person_label(p) for p in self.people]
        if label in values:
            return self.people[values.index(label)]
        return {}

    def _prefill_from_person(self):
        person = self._selected_person_payload()
        if not person:
            return
        existing_user = (person.get("usuario") or "").strip()
        if existing_user:
            self.username_var.set(existing_user)
            return
        base = ".".join(
            part for part in [
                str(person.get("nombre") or "").strip().split(" ")[0].lower(),
                str(person.get("apellido") or "").strip().split(" ")[0].lower(),
            ] if part
        )
        self.username_var.set(base.replace(" ", "."))

    def _render_permission_matrix(self, parent, var_store):
        for w in parent.winfo_children():
            w.destroy()
        var_store.clear()
        modules = self.meta.get("modules", [])
        module_actions = self.meta.get("module_actions") or LOCAL_MODULE_ACTIONS
        canvas = tk.Canvas(parent, bg="white", highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="white")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        inner_window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        def _wheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        def _bind_mousewheel(_event):
            canvas.bind_all("<MouseWheel>", _wheel)
        def _unbind_mousewheel(_event):
            canvas.unbind_all("<MouseWheel>")
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        inner.bind("<Enter>", _bind_mousewheel)
        inner.bind("<Leave>", _unbind_mousewheel)
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner_window, width=e.width))
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        row = 0
        for module in modules:
            module_code = module["code"]
            actions = module_actions.get(module_code) or self.meta.get("actions", [])
            section = ttk.LabelFrame(inner, text=module["label"])
            section.grid(row=row, column=0, sticky="ew", padx=8, pady=8)
            section.columnconfigure(0, weight=1)
            section.bind("<Enter>", _bind_mousewheel)
            section.bind("<Leave>", _unbind_mousewheel)
            for idx, action in enumerate(actions):
                var = tk.BooleanVar(value=False)
                var_store[(module_code, action["code"])] = var
                chk = ttk.Checkbutton(
                    section,
                    text=action["label"],
                    variable=var
                )
                chk.grid(row=idx // 3, column=idx % 3, sticky="w", padx=10, pady=4)
                chk.bind("<Enter>", _bind_mousewheel)
                chk.bind("<Leave>", _unbind_mousewheel)
            row += 1

    def _vars_to_permissions(self, var_store):
        permissions = {}
        for (module_code, action_code), var in var_store.items():
            if var.get():
                permissions.setdefault(module_code, []).append(action_code)
        return permissions

    def _set_vars_from_permissions(self, var_store, permissions):
        for var in var_store.values():
            var.set(False)
        for module_code, actions in (permissions or {}).items():
            for action_code in actions:
                var = var_store.get((module_code, action_code))
                if var:
                    var.set(True)

    def _all_matrix_permissions(self):
        permissions = {}
        for module_code, action_code in self.permission_vars.keys():
            permissions.setdefault(module_code, []).append(action_code)
        return permissions

    def _legacy_permissions_for_user(self, usuario):
        usuario_norm = (usuario or "").strip().lower()
        found = next((u for u in self.users if (u.get("usuario") or "").strip().lower() == usuario_norm), {})
        rol = (found.get("rol") or "").strip().lower()
        if rol in {"admin", "master"} or usuario_norm in {"admin", "aaron01", "gerencia1"}:
            return self._all_matrix_permissions(), "Acceso total por rol/usuario administrador."
        role_modules = {
            "accounting": {"finanzas", "qa_som"},
            "finance": {"dashboard", "finanzas", "qa_som"},
            "hr": {"dashboard", "hhrre", "qa_som"},
            "user": {"dashboard", "servicios", "informes", "qa_som"},
        }
        modules = role_modules.get(rol, set())
        if usuario_norm in {"surveyor01", "surveyor02", "surveyor03"}:
            modules = {"comercial", "hhrre", "informes", "qa_som"}
        permissions = {module_code: ["view"] for module_code in modules}
        if permissions:
            return permissions, f"Permisos heredados por rol '{rol or 'user'}'."
        return {}, "Sin permisos configurados."

    def _create_user(self):
        person = self._selected_person_payload()
        payload = {
            "usuario": self.username_var.get().strip(),
            "password": self.password_var.get(),
            "rol": self.role_var.get().strip() or "user",
            "source_type": person.get("source_type"),
            "source_id": person.get("source_id"),
            "nombre": person.get("nombre"),
            "apellido": person.get("apellido"),
            "email": person.get("email"),
            "activo": self.active_var.get(),
            "permissions": self._vars_to_permissions(self.create_permission_vars),
        }
        try:
            api_client.create_admin_user_api(payload)
            messagebox.showinfo("Usuarios", "Usuario creado correctamente.", parent=self)
            self.password_var.set("")
            self._load_data()
        except Exception as exc:
            messagebox.showerror("Usuarios", f"No se pudo crear el usuario:\n{exc}", parent=self)

    def _load_selected_user_permissions(self):
        usuario = self.selected_user.get()
        if not usuario:
            self._set_vars_from_permissions(self.permission_vars, {})
            return
        permissions = {}
        try:
            resp = api_client.get_admin_user_permissions_api(usuario)
            permissions = (resp.get("permissions") if isinstance(resp, dict) and "permissions" in resp else resp) or {}
        except Exception:
            found = next((u for u in self.users if u.get("usuario") == usuario), {})
            permissions = found.get("permissions") or {}
        status = "Permisos explicitos cargados desde backend."
        if not permissions:
            permissions, status = self._legacy_permissions_for_user(usuario)
        self._set_vars_from_permissions(self.permission_vars, permissions)
        total = sum(len(actions) for actions in permissions.values())
        self.permission_status_var.set(f"{status} Marcados: {total}.")

    def _save_permissions(self):
        usuario = self.selected_user.get()
        if not usuario:
            messagebox.showwarning("Usuarios", "Selecciona un usuario.", parent=self)
            return
        permissions = self._vars_to_permissions(self.permission_vars)
        try:
            api_client.save_admin_user_permissions_api(usuario, permissions)
            messagebox.showinfo("Usuarios", "Permisos guardados correctamente.", parent=self)
            self._load_data()
        except Exception as exc:
            messagebox.showerror("Usuarios", f"No se pudieron guardar permisos:\n{exc}", parent=self)
