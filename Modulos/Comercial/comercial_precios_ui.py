# ============================================================
# COMERCIAL — PRECIOS UI
# Archivo: Modulos/Comercial/comercial_precios_ui.py
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import csv
import pandas as pd
from Modulos.Comercial.popup.popup_agregar_precio import PopupAgregarPrecio
from Modulos.Comercial.popup.popup_editar_precio import PopupEditarPrecio

from api_client import (
    get_comercial_precios_meta_api,
    get_comercial_precios_api,
    post_comercial_precio_api,
    put_comercial_precio_api,
    delete_comercial_precio_api
)


class ComercialPreciosUI(ttk.Frame):
    """
    COMERCIAL — PRECIOS
    Gestión de precios por Servicio / Cliente / Ubicación
    """

    PAGE_SIZE = 50

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        # =========================
        # STATE
        # =========================
        self.data_all = []
        self.page = 1

        # =========================
        # META DATA
        # =========================
        self.servicios = []
        self.clientes = []
        self.ubicaciones = []

        self.pack(fill="both", expand=True)
        self._setup_style()
        self._build_ui()
        self._load_meta()  # SOLO combos, NO data

    # =========================================================
    # STYLE
    # =========================================================
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", font=("Segoe UI", 9), rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))


    # =========================================================
    # AUTO RESIZE COMBO BASED ON VALUES
    # =========================================================
    def _auto_resize_combo(self, combo, values):
        """
        Ajusta el width del Combobox basado en el texto más largo.
        """
        if not values:
            return

        max_len = max(len(str(v)) for v in values)

        # margen extra para que no quede pegado
        combo.configure(width=min(max_len + 3, 80))



    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # ---------------- HEADER ----------------
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=6)

        ttk.Label(
            header,
            text="Precios por Servicio",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="Volver",
            command=self._go_back
        ).pack(side="right")

        # ---------------- FILTER BAR ----------------
        filter_bar = ttk.LabelFrame(self, text="Filtros")
        filter_bar.pack(fill="x", padx=10, pady=6)

        self.servicio_var = tk.StringVar()
        self.cliente_var = tk.StringVar()
        self.continente_var = tk.StringVar()
        self.pais_var = tk.StringVar()
        self.puerto_var = tk.StringVar()

        col = 0

        def _combo(lbl, var, width=30):
            nonlocal col

            ttk.Label(filter_bar, text=lbl).grid(row=0, column=col, padx=4)

            cb = ttk.Combobox(
                filter_bar,
                textvariable=var,
                state="readonly",
                width=width
            )

            cb.grid(row=1, column=col, padx=4, sticky="w")

            # 🔹 Expande visualmente el dropdown
            cb.configure(font=("Segoe UI", 9))

            # Permite que el popup desplegable tenga mayor ancho
           

            col += 1
            return cb

        self.cb_servicio = _combo("Servicio", self.servicio_var)
        self.cb_cliente = _combo("Cliente", self.cliente_var)
        self.cb_continente = _combo("Continente", self.continente_var)
        self.cb_pais = _combo("País", self.pais_var)
        self.cb_puerto = _combo("Puerto", self.puerto_var)

        ttk.Button(
            filter_bar,
            text="Buscar",
            command=self._buscar
        ).grid(row=1, column=col, padx=10)

        ttk.Button(
            filter_bar,
            text="Limpiar",
            command=self._limpiar
        ).grid(row=1, column=col + 1)

        # ---------------- ACTION BAR ----------------
        action_bar = ttk.Frame(self)
        action_bar.pack(fill="x", padx=10, pady=4)

        ttk.Button(action_bar, text="Agregar Precio", command=self._agregar).pack(side="left", padx=4)
        ttk.Button(action_bar, text="Editar Precio", command=self._editar).pack(side="left", padx=4)
        ttk.Button(action_bar, text="Eliminar Precio", command=self._eliminar).pack(side="left", padx=4)
        ttk.Button(action_bar, text="Exportar", command=self._exportar).pack(side="right")

        # ---------------- TABLE ----------------
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=6)

        cols = (
            "id", "servicio", "cliente",
            "continente", "pais", "puerto",
            "precio", "activo"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings"
        )

        headers = {
            "id": "ID",
            "servicio": "Servicio",
            "cliente": "Cliente",
            "continente": "Continente",
            "pais": "País",
            "puerto": "Puerto",
            "precio": "Precio",
            "activo": "Activo"
        }

        for c in cols:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=140, anchor="center")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # ---------------- PAGINATION ----------------
        self.pagination_lbl = ttk.Label(self, text="0 resultados")
        self.pagination_lbl.pack(anchor="e", padx=12, pady=(0, 6))

    # =========================================================
    # DATA
    # =========================================================
    def _load_meta(self):
        try:
            meta = get_comercial_precios_meta_api()

            self.servicios = sorted(
                [f"{s['nombre']} ({s['codigo']})" for s in meta.get("servicios", [])]
            )
            self.clientes = sorted(
                [f"{c['nombrejuridico']} ({c['codigo']})" for c in meta.get("clientes", [])]
            )

            continentes = sorted({u["continente"] for u in meta.get("ubicaciones", [])})
            paises = sorted({u["pais"] for u in meta.get("ubicaciones", [])})
            puertos = sorted({u["puerto"] for u in meta.get("ubicaciones", [])})

            self.cb_servicio["values"] = self.servicios
            self.cb_cliente["values"] = self.clientes
            self.cb_continente["values"] = continentes
            self.cb_pais["values"] = paises
            self.cb_puerto["values"] = puertos

            # 🔹 Forzar ancho REAL del dropdown
            def _attach_dropdown_resize(combo):
                combo.configure(
                    postcommand=lambda: self._force_dropdown_width(combo)
                )

            for cb in (
                self.cb_servicio,
                self.cb_cliente,
                self.cb_continente,
                self.cb_pais,
                self.cb_puerto
            ):
                _attach_dropdown_resize(cb)


            # 🔹 Auto resize dinámico
            self._auto_resize_combo(self.cb_servicio, self.servicios)
            self._auto_resize_combo(self.cb_cliente, self.clientes)
            self._auto_resize_combo(self.cb_continente, continentes)
            self._auto_resize_combo(self.cb_pais, paises)
            self._auto_resize_combo(self.cb_puerto, puertos)


        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar meta:\n{e}")

    def _buscar(self):
        try:
            resp = get_comercial_precios_api()
            self.data_all = resp.get("data", [])
            self.page = 1
            self._render_page()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _render_page(self):
        self.tree.delete(*self.tree.get_children())

        start = (self.page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for r in self.data_all[start:end]:
            self.tree.insert("", "end", values=(
                r.get("id"),
                r.get("servicio"),
                r.get("cliente"),
                r.get("continente"),
                r.get("pais"),
                r.get("puerto"),
                f"{float(r.get('precio', 0)):,.2f}",
                "✔" if r.get("activo") else ""
            ))

        total = len(self.data_all)
        self.pagination_lbl.config(
            text=f"Mostrando {min(end, total)} de {total} registros"
        )


    # =========================================================
    # FORCE DROPDOWN WIDTH (REAL FIX FOR ttk.Combobox)
    # =========================================================
    def _force_dropdown_width(self, combo):
        """
        Ajusta el ancho REAL del dropdown del Combobox (popdown listbox).
        """
        try:
            combo.update_idletasks()

            popdown = combo.tk.call("ttk::combobox::PopdownWindow", combo)

            values = combo["values"]
            if not values:
                return

            max_len = max(len(str(v)) for v in values)

            # Ajusta ancho real del listbox interno
            combo.tk.call(f"{popdown}.f.l", "configure", "-width", max_len + 5)

        except Exception:
            pass


    # =========================================================
    # ACTIONS
    # =========================================================
    def _agregar(self):
        """
        Abre el popup para agregar un nuevo precio.
        """

        PopupAgregarPrecio(
            self,
            on_success=self._on_precio_guardado
        )

    def _editar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Editar", "Seleccione un registro")
            return

        item = self.tree.item(sel[0])
        precio_id = item["values"][0]

        precio_data = next(
            (r for r in self.data_all if r.get("id") == precio_id),
            None
        )
        if not precio_data:
            return

        PopupEditarPrecio(
            self,
            precio_data=precio_data,
            on_success=self._buscar
        )

    def _eliminar(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Eliminar", "Seleccione un registro")
            return

        item = self.tree.item(sel[0])
        precio_id = item["values"][0]
        servicio = item["values"][1]
        cliente = item["values"][2]

        if not messagebox.askyesno(
            "Confirmar eliminación",
            f"¿Desea eliminar el precio?\n\nServicio: {servicio}\nCliente: {cliente}"
        ):
            return

        try:
            delete_comercial_precio_api(precio_id)
            messagebox.showinfo("Eliminar", "Precio eliminado correctamente")
            self._buscar()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _exportar(self):
        if not self.data_all:
            messagebox.showwarning("Exportar", "No hay datos")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )
        if not path:
            return

        df = pd.DataFrame(self.data_all)
        if path.endswith(".csv"):
            df.to_csv(path, index=False)
        else:
            df.to_excel(path, index=False)

        messagebox.showinfo("Exportar", "Archivo generado correctamente")

    def _limpiar(self):
        for v in (
            self.servicio_var,
            self.cliente_var,
            self.continente_var,
            self.pais_var,
            self.puerto_var
        ):
            v.set("")

        self.data_all = []
        self.tree.delete(*self.tree.get_children())
        self.pagination_lbl.config(text="0 resultados")

    def _on_precio_guardado(self):
        """
        Callback ejecutado cuando se guarda un precio desde el popup.
        Refresca el listado SIN recrear la UI.
        """
        self._buscar()


    def _go_back(self):
        if callable(self.on_back):
            self.on_back()
