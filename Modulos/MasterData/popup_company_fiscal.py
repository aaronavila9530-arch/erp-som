import tkinter as tk
from tkinter import messagebox
from tkinter import ttk

from api_client import get_current_company_profile_api, update_company_profile_api
from session_context import get_company_code, get_company_name


COLOR_BG = "white"
COLOR_MENU = "#003A75"


FIELDS = [
    ("company_name", "Razon social"),
    ("legal_name", "Nombre legal"),
    ("trade_name", "Nombre comercial"),
    ("tax_id", "Cedula juridica / VAT"),
    ("economic_activity", "Actividad economica"),
    ("phone", "Telefono"),
    ("billing_email", "Correo facturacion"),
    ("email", "Correo general"),
    ("country", "Pais"),
    ("province", "Provincia"),
    ("canton", "Canton"),
    ("district", "Distrito"),
    ("address", "Direccion exacta"),
    ("notes", "Notas"),
]


class PopupCompanyFiscal(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Datos fiscales de empresa")
        self.configure(bg=COLOR_BG)
        self.geometry("760x560")
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self.vars = {}
        self.company_code = get_company_code() or "MSL-CR"

        self._build()
        self.after(100, self._load)

    def _build(self):
        header = tk.Frame(self, bg=COLOR_MENU, padx=16, pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Ficha fiscal de empresa",
            bg=COLOR_MENU,
            fg="white",
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text=f"{self.company_code} | {get_company_name()}",
            bg=COLOR_MENU,
            fg="white",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(self, bg=COLOR_BG, padx=16, pady=14)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)

        for idx, (key, label) in enumerate(FIELDS):
            ttk.Label(body, text=label, background=COLOR_BG).grid(row=idx, column=0, sticky="w", padx=(0, 10), pady=5)
            var = tk.StringVar()
            self.vars[key] = var
            if key in {"address", "notes"}:
                entry = tk.Text(body, height=3, wrap="word")
                entry.grid(row=idx, column=1, sticky="ew", pady=5)
                entry.bind("<KeyRelease>", lambda _event, field=key, widget=entry: self.vars[field].set(widget.get("1.0", "end").strip()))
                self.vars[f"_{key}_widget"] = entry
            else:
                ttk.Entry(body, textvariable=var).grid(row=idx, column=1, sticky="ew", pady=5)

        actions = tk.Frame(self, bg=COLOR_BG, padx=16, pady=12)
        actions.pack(fill="x")
        tk.Button(actions, text="Cerrar", width=12, command=self.destroy).pack(side="right", padx=(6, 0))
        tk.Button(actions, text="Guardar", width=12, bg=COLOR_MENU, fg="white", command=self._save).pack(side="right")

    def _set_value(self, key, value):
        value = "" if value is None else str(value)
        self.vars[key].set(value)
        widget = self.vars.get(f"_{key}_widget")
        if widget:
            widget.delete("1.0", "end")
            widget.insert("1.0", value)

    def _load(self):
        try:
            data = get_current_company_profile_api()
        except Exception as exc:
            messagebox.showwarning(
                "Datos fiscales",
                f"No se pudo cargar desde el servidor. Puede editar y guardar de nuevo.\n{exc}",
                parent=self,
            )
            data = {
                "company_code": self.company_code,
                "company_name": get_company_name(),
                "legal_name": get_company_name(),
                "country": "Costa Rica",
            }

        self.company_code = data.get("company_code") or self.company_code
        for key, _label in FIELDS:
            self._set_value(key, data.get(key, ""))

    def _payload(self):
        data = {}
        for key, _label in FIELDS:
            widget = self.vars.get(f"_{key}_widget")
            if widget:
                data[key] = widget.get("1.0", "end").strip()
            else:
                data[key] = self.vars[key].get().strip()
        return data

    def _save(self):
        payload = self._payload()
        if not payload.get("company_name") and not payload.get("legal_name"):
            messagebox.showwarning("Datos fiscales", "Indique la razon social o nombre legal.", parent=self)
            return

        try:
            saved = update_company_profile_api(self.company_code, payload)
            for key, _label in FIELDS:
                self._set_value(key, saved.get(key, ""))
            messagebox.showinfo("Datos fiscales", "Ficha fiscal guardada correctamente.", parent=self)
        except Exception as exc:
            messagebox.showerror("Datos fiscales", f"No se pudo guardar:\n{exc}", parent=self)
