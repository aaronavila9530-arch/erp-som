import tkinter as tk
from tkinter import ttk, messagebox

import api_client


class UserAdminUI(tk.Frame):
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent, bg="white")
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back
        self.people = []
        self.users = []
        self.meta = {"modules": [], "actions": [], "roles": [], "password_rules": []}
        self.permission_vars = {}
        self.selected_person = tk.StringVar()
        self.selected_user = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.role_var = tk.StringVar(value="user")
        self.active_var = tk.BooleanVar(value=True)
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
        actions = self.meta.get("actions", [])
        canvas = tk.Canvas(parent, bg="white", highlightthickness=0)
        vsb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg="white")
        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        tk.Label(inner, text="Modulo", bg="white", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        for col, action in enumerate(actions, start=1):
            tk.Label(inner, text=action["label"], bg="white", font=("Segoe UI", 9, "bold")).grid(row=0, column=col, padx=6, pady=6)
        for row, module in enumerate(modules, start=1):
            tk.Label(inner, text=module["label"], bg="white").grid(row=row, column=0, sticky="w", padx=8, pady=4)
            for col, action in enumerate(actions, start=1):
                var = tk.BooleanVar(value=False)
                var_store[(module["code"], action["code"])] = var
                ttk.Checkbutton(inner, variable=var).grid(row=row, column=col, padx=6, pady=4)

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
        found = next((u for u in self.users if u.get("usuario") == usuario), {})
        self._set_vars_from_permissions(self.permission_vars, found.get("permissions") or {})

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
