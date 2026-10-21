import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_comercial_precios_meta_api,
    put_comercial_precio_api
)


class PopupEditarPrecio(tk.Toplevel):
    """
    Popup para EDITAR un precio existente
    """

    def __init__(self, parent, precio_data: dict, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.precio_data = precio_data
        self.on_success = on_success

        self.title("Editar Precio")
        self.geometry("520x380")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._load_meta()
        self._load_data()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=14, pady=14)

        self.servicio_var = tk.StringVar()
        self.cliente_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()
        self.precio_var = tk.StringVar()
        self.activo_var = tk.BooleanVar(value=True)

        row = 0

        def field(label, var):
            nonlocal row
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=5)
            cb = ttk.Combobox(frame, textvariable=var, state="readonly", width=38)
            cb.grid(row=row, column=1, pady=5)
            row += 1
            return cb

        self.cb_servicio = field("Servicio", self.servicio_var)
        self.cb_cliente = field("Cliente", self.cliente_var)
        self.cb_continente = field("Continente", self.continente_var)
        self.cb_pais = field("País", self.pais_var)
        self.cb_puerto = field("Puerto", self.puerto_var)

        ttk.Label(frame, text="Precio").grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(frame, textvariable=self.precio_var, width=40).grid(
            row=row, column=1, pady=5
        )
        row += 1

        ttk.Checkbutton(
            frame,
            text="Activo",
            variable=self.activo_var
        ).grid(row=row, column=1, sticky="w", pady=5)
        row += 1

        # ---------------- BOTONES ----------------
        btns = ttk.Frame(frame)
        btns.grid(row=row, column=0, columnspan=2, pady=18)

        ttk.Button(btns, text="Guardar", command=self._guardar).pack(
            side="left", padx=6
        )
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(
            side="left", padx=6
        )

    # =========================================================
    # META
    # =========================================================
    def _load_meta(self):
        try:
            meta = get_comercial_precios_meta_api()

            self.cb_servicio["values"] = [
                f"{s['nombre']} ({s['codigo']})"
                for s in meta.get("servicios", [])
            ]
            self.cb_cliente["values"] = [
                f"{c['nombrejuridico']} ({c['codigo']})"
                for c in meta.get("clientes", [])
            ]

            self.cb_continente["values"] = sorted(
                {u["continente"] for u in meta.get("ubicaciones", [])}
            )
            self.cb_pais["values"] = sorted(
                {u["pais"] for u in meta.get("ubicaciones", [])}
            )
            self.cb_puerto["values"] = sorted(
                {u["puerto"] for u in meta.get("ubicaciones", [])}
            )

        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar catálogos:\n{e}")
            self.destroy()

    # =========================================================
    # LOAD DATA
    # =========================================================
    def _load_data(self):
        self.servicio_var.set(self.precio_data.get("servicio"))
        self.cliente_var.set(self.precio_data.get("cliente"))
        self.continente_var.set(self.precio_data.get("continente") or "")
        self.pais_var.set(self.precio_data.get("pais") or "")
        self.puerto_var.set(self.precio_data.get("puerto") or "")
        self.precio_var.set(f"{float(self.precio_data.get('precio', 0)):.2f}")
        self.activo_var.set(bool(self.precio_data.get("activo")))

    # =========================================================
    # SAVE
    # =========================================================
    def _guardar(self):

        try:
            precio = float(self.precio_var.get())
        except Exception:
            messagebox.showwarning("Validación", "Precio inválido")
            return

        payload = {
            "servicio": self.servicio_var.get(),
            "cliente": self.cliente_var.get(),
            "continente": self.continente_var.get() or None,
            "pais": self.pais_var.get() or None,
            "puerto": self.puerto_var.get() or None,
            "precio": precio,
            "activo": self.activo_var.get()
        }

        try:
            put_comercial_precio_api(
                self.precio_data["id"],
                payload
            )

            if callable(self.on_success):
                self.on_success()

            self.destroy()

        except Exception as e:
            messagebox.showerror("Error", str(e))
