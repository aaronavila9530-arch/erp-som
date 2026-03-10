# ============================================================
# POPUP — AGREGAR PRECIO (SERVICIO / CLIENTE / UBICACIÓN)
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_comercial_precios_meta_api,
    post_comercial_precio_api
)


class PopupAgregarPrecio(tk.Toplevel):
    """
    Popup para agregar un nuevo precio por:
    Servicio + Cliente + Continente / País / Puerto
    """

    def __init__(self, parent, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.on_success = on_success

        self.meta = {}
        self.servicios = []
        self.clientes = []
        self.ubicaciones = []

        self.title("Agregar Precio")
        self.geometry("520x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._load_meta()
        self._build_ui()

    # =========================================================
    # DATA
    # =========================================================
    def _load_meta(self):
        try:
            resp = get_comercial_precios_meta_api()
            self.servicios = resp.get("servicios", [])
            self.clientes = resp.get("clientes", [])
            self.ubicaciones = resp.get("ubicaciones", [])
        except Exception as e:
            messagebox.showerror("Precios", str(e))
            self.destroy()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # ================= VARIABLES =================
        self.servicio_var = tk.StringVar()
        self.cliente_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()
        self.precio_var = tk.StringVar()

        # ================= FORM =================
        row = 0

        ttk.Label(container, text="Servicio").grid(row=row, column=0, sticky="w", pady=6)
        self.cb_servicio = ttk.Combobox(
            container,
            textvariable=self.servicio_var,
            values=[s["nombre"] for s in self.servicios],
            state="readonly",
            width=40
        )
        self.cb_servicio.grid(row=row, column=1, pady=6)
        row += 1

        ttk.Label(container, text="Cliente").grid(row=row, column=0, sticky="w", pady=6)
        self.cb_cliente = ttk.Combobox(
            container,
            textvariable=self.cliente_var,
            values=[c["nombrejuridico"] for c in self.clientes],
            state="readonly",
            width=40
        )
        self.cb_cliente.grid(row=row, column=1, pady=6)
        row += 1

        ttk.Label(container, text="Continente").grid(row=row, column=0, sticky="w", pady=6)
        self.cb_continente = ttk.Combobox(
            container,
            textvariable=self.continente_var,
            values=self._unique_continentes(),
            state="readonly",
            width=40
        )
        self.cb_continente.grid(row=row, column=1, pady=6)
        self.cb_continente.bind("<<ComboboxSelected>>", self._on_continente_change)
        row += 1

        ttk.Label(container, text="País").grid(row=row, column=0, sticky="w", pady=6)
        self.cb_pais = ttk.Combobox(
            container,
            textvariable=self.pais_var,
            state="readonly",
            width=40
        )
        self.cb_pais.grid(row=row, column=1, pady=6)
        self.cb_pais.bind("<<ComboboxSelected>>", self._on_pais_change)
        row += 1

        ttk.Label(container, text="Puerto").grid(row=row, column=0, sticky="w", pady=6)
        self.cb_puerto = ttk.Combobox(
            container,
            textvariable=self.puerto_var,
            state="readonly",
            width=40
        )
        self.cb_puerto.grid(row=row, column=1, pady=6)
        row += 1

        ttk.Label(container, text="Precio").grid(row=row, column=0, sticky="w", pady=6)
        ttk.Entry(
            container,
            textvariable=self.precio_var,
            width=42
        ).grid(row=row, column=1, pady=6)
        row += 1

        # ================= BUTTONS =================
        btns = ttk.Frame(container)
        btns.grid(row=row, column=0, columnspan=2, pady=20)

        ttk.Button(btns, text="Guardar", command=self._save).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancelar", command=self.destroy).pack(side="left", padx=6)

    # =========================================================
    # DEPENDENT COMBOS
    # =========================================================
    def _unique_continentes(self):
        return sorted({u["continente"] for u in self.ubicaciones})

    def _on_continente_change(self, event=None):
        cont = self.continente_var.get()
        paises = sorted({
            u["pais"] for u in self.ubicaciones
            if u["continente"] == cont
        })
        self.pais_var.set("")
        self.puerto_var.set("")
        self.cb_pais["values"] = paises
        self.cb_puerto["values"] = []

    def _on_pais_change(self, event=None):
        cont = self.continente_var.get()
        pais = self.pais_var.get()
        puertos = sorted({
            u["puerto"] for u in self.ubicaciones
            if u["continente"] == cont and u["pais"] == pais
        })
        self.puerto_var.set("")
        self.cb_puerto["values"] = puertos

    # =========================================================
    # SAVE
    # =========================================================
    def _save(self):

        if not self.servicio_var.get():
            return messagebox.showwarning("Precios", "Seleccione un servicio")

        if not self.cliente_var.get():
            return messagebox.showwarning("Precios", "Seleccione un cliente")

        try:
            precio = float(self.precio_var.get())
            if precio <= 0:
                raise ValueError
        except Exception:
            return messagebox.showwarning("Precios", "Precio inválido")

        payload = {
            "servicio": self.servicio_var.get(),
            "cliente": self.cliente_var.get(),
            "continente": self.continente_var.get() or None,
            "pais": self.pais_var.get() or None,
            "puerto": self.puerto_var.get() or None,
            "precio": precio
        }

        try:
            post_comercial_precio_api(payload)
        except Exception as e:
            messagebox.showerror("Precios", str(e))
            return

        if self.on_success:
            self.on_success()

        self.destroy()
