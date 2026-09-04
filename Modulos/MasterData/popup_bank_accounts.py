import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from api_client import (
    create_masterdata_bank_account_api,
    delete_masterdata_bank_account_api,
    get_masterdata_bank_accounts_api,
    unlock_masterdata_bank_accounts_api,
    update_masterdata_bank_account_api,
)


COLOR_MENU = "#003A75"
COLOR_BG = "white"


class PopupBankAccounts(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Datos bancarios protegidos")
        self.configure(bg=COLOR_BG)
        self.geometry("1080x620")
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.access_token = ""
        self.rows = []
        self.selected_id = None
        self.vars = {
            "bank_name": tk.StringVar(),
            "currency": tk.StringVar(value="CRC"),
            "swift_code": tk.StringVar(),
            "bank_address": tk.StringVar(),
            "uid": tk.StringVar(),
            "beneficiary_name": tk.StringVar(),
        }

        self._build()
        self.after(100, self._unlock)

    def _build(self):
        top = tk.Frame(self, bg=COLOR_BG, padx=12, pady=10)
        top.pack(fill="x")

        tk.Label(
            top,
            text="Datos bancarios protegidos por revalidación Microsoft Authenticator",
            bg=COLOR_BG,
            fg=COLOR_MENU,
            font=("Arial", 12, "bold"),
        ).pack(side="left")

        tk.Button(top, text="Revalidar", command=self._unlock, bg=COLOR_MENU, fg="white", width=12).pack(side="right")

        columns = ("bank_name", "currency", "swift_code", "bank_address", "uid", "beneficiary_name", "updated_by")
        labels = {
            "bank_name": "Banco",
            "currency": "Moneda",
            "swift_code": "Swift Code",
            "bank_address": "Dirección",
            "uid": "UID",
            "beneficiary_name": "Beneficiario",
            "updated_by": "Actualizado por",
        }
        widths = {
            "bank_name": 180,
            "currency": 80,
            "swift_code": 120,
            "bank_address": 260,
            "uid": 130,
            "beneficiary_name": 220,
            "updated_by": 120,
        }

        table_frame = tk.Frame(self, bg=COLOR_BG, padx=12)
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        for col in columns:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        form = tk.LabelFrame(self, text="Agregar / modificar", bg=COLOR_BG, fg=COLOR_MENU, padx=12, pady=10)
        form.pack(fill="x", padx=12, pady=10)
        fields = [
            ("Nombre del banco", "bank_name", 0, 0),
            ("Moneda", "currency", 0, 2),
            ("Swift Code", "swift_code", 1, 0),
            ("UID", "uid", 1, 2),
            ("Nombre del beneficiario", "beneficiary_name", 2, 0),
            ("Dirección", "bank_address", 3, 0),
        ]
        for label, key, row, col in fields:
            tk.Label(form, text=label, bg=COLOR_BG).grid(row=row, column=col, sticky="w", padx=5, pady=4)
            if key == "currency":
                widget = ttk.Combobox(form, textvariable=self.vars[key], values=["CRC", "USD", "EUR"], state="readonly", width=16)
            else:
                width = 80 if key in {"bank_address", "beneficiary_name"} else 32
                widget = tk.Entry(form, textvariable=self.vars[key], width=width)
            widget.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=4)
        form.grid_columnconfigure(1, weight=1)

        actions = tk.Frame(self, bg=COLOR_BG, padx=12, pady=8)
        actions.pack(fill="x")
        tk.Button(actions, text="Nuevo", width=12, command=self._clear).pack(side="left", padx=(0, 6))
        tk.Button(actions, text="Guardar", width=12, bg=COLOR_MENU, fg="white", command=self._save).pack(side="left", padx=6)
        tk.Button(actions, text="Eliminar", width=12, command=self._delete).pack(side="left", padx=6)
        tk.Button(actions, text="Cerrar", width=12, command=self.destroy).pack(side="right")

    def _unlock(self):
        code = simpledialog.askstring(
            "Microsoft Authenticator",
            "Digite el código actual de Microsoft Authenticator:",
            parent=self,
            show="*",
        )
        if not code:
            if not self.access_token:
                self.destroy()
            return
        try:
            payload = unlock_masterdata_bank_accounts_api(code)
            self.access_token = payload.get("access_token") or ""
            if not self.access_token:
                raise ValueError("No se recibió token de acceso.")
            self._load()
        except Exception as exc:
            messagebox.showerror("Datos bancarios", f"No se pudo revalidar:\n{exc}", parent=self)
            if not self.access_token:
                self.destroy()

    def _load(self):
        try:
            self.rows = get_masterdata_bank_accounts_api(self.access_token)
            self.tree.delete(*self.tree.get_children())
            for row in self.rows:
                iid = str(row.get("id"))
                self.tree.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(
                        row.get("bank_name") or "",
                        row.get("currency") or "",
                        row.get("swift_code") or "",
                        row.get("bank_address") or "",
                        row.get("uid") or "",
                        row.get("beneficiary_name") or "",
                        row.get("updated_by") or "",
                    ),
                )
        except Exception as exc:
            messagebox.showerror("Datos bancarios", f"No se pudieron cargar datos:\n{exc}", parent=self)

    def _on_select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.selected_id = int(selected[0])
        row = next((item for item in self.rows if int(item.get("id")) == self.selected_id), {})
        for key, var in self.vars.items():
            var.set(row.get(key) or "")

    def _clear(self):
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())
        for key, var in self.vars.items():
            var.set("CRC" if key == "currency" else "")

    def _payload(self):
        return {
            "bank_name": self.vars["bank_name"].get().strip(),
            "currency": self.vars["currency"].get().strip(),
            "swift_code": self.vars["swift_code"].get().strip(),
            "bank_address": self.vars["bank_address"].get().strip(),
            "uid": self.vars["uid"].get().strip(),
            "beneficiary_name": self.vars["beneficiary_name"].get().strip(),
        }

    def _save(self):
        if not self.access_token:
            self._unlock()
            if not self.access_token:
                return
        try:
            payload = self._payload()
            if self.selected_id:
                update_masterdata_bank_account_api(self.selected_id, payload, self.access_token)
            else:
                create_masterdata_bank_account_api(payload, self.access_token)
            self._clear()
            self._load()
            messagebox.showinfo("Datos bancarios", "Guardado correctamente.", parent=self)
        except Exception as exc:
            messagebox.showerror("Datos bancarios", f"No se pudo guardar:\n{exc}", parent=self)

    def _delete(self):
        if not self.selected_id:
            messagebox.showwarning("Datos bancarios", "Seleccione un registro.", parent=self)
            return
        if not messagebox.askyesno("Datos bancarios", "¿Eliminar este dato bancario?", parent=self):
            return
        try:
            delete_masterdata_bank_account_api(self.selected_id, self.access_token)
            self._clear()
            self._load()
        except Exception as exc:
            messagebox.showerror("Datos bancarios", f"No se pudo eliminar:\n{exc}", parent=self)
