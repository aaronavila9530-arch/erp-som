import tkinter as tk
from tkinter import ttk, messagebox

from api_client import get_services_for_grain_sampling_api


class PopupGrainServiceSelector(tk.Toplevel):

    def __init__(self, parent, on_select=None):
        super().__init__(parent)

        self.parent = parent
        self.on_select = on_select
        self.selected_data = None

        self.title("Select Service Report")
        self.geometry("950x550")
        self.transient(parent)
        self.grab_set()

        self._build_filters()
        self._build_table()
        self._build_actions()

        # Cargar datos iniciales
        self._refresh_filters()

    # =========================================================
    # FILTERS
    # =========================================================
    def _build_filters(self):

        frm = ttk.LabelFrame(self, text="Filters")
        frm.pack(fill="x", padx=10, pady=10)

        # ===== AÑO
        ttk.Label(frm, text="Año").grid(row=0, column=0, sticky="w", padx=5)
        self.year_cb = ttk.Combobox(frm, width=10, state="readonly")
        self.year_cb.grid(row=0, column=1, padx=5)
        self.year_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        # ===== MES
        ttk.Label(frm, text="Mes").grid(row=0, column=2, sticky="w", padx=5)
        self.month_cb = ttk.Combobox(frm, width=10, state="readonly")
        self.month_cb.grid(row=0, column=3, padx=5)
        self.month_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        # ===== RESTO FILTROS
        ttk.Label(frm, text="Continente").grid(row=1, column=0, sticky="w", padx=5)
        self.continent_cb = ttk.Combobox(frm, width=18, state="readonly")
        self.continent_cb.grid(row=1, column=1, padx=5)
        self.continent_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        ttk.Label(frm, text="País").grid(row=1, column=2, sticky="w", padx=5)
        self.country_cb = ttk.Combobox(frm, width=18, state="readonly")
        self.country_cb.grid(row=1, column=3, padx=5)
        self.country_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        ttk.Label(frm, text="Puerto").grid(row=1, column=4, sticky="w", padx=5)
        self.port_cb = ttk.Combobox(frm, width=18, state="readonly")
        self.port_cb.grid(row=1, column=5, padx=5)
        self.port_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        ttk.Label(frm, text="Cliente").grid(row=2, column=0, sticky="w", padx=5)
        self.client_cb = ttk.Combobox(frm, width=18, state="readonly")
        self.client_cb.grid(row=2, column=1, padx=5)
        self.client_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        ttk.Label(frm, text="Buque").grid(row=2, column=2, sticky="w", padx=5)
        self.vessel_cb = ttk.Combobox(frm, width=18, state="readonly")
        self.vessel_cb.grid(row=2, column=3, padx=5)
        self.vessel_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        ttk.Label(frm, text="Operación").grid(row=2, column=4, sticky="w", padx=5)
        self.operacion_cb = ttk.Combobox(frm, width=18, state="readonly")
        self.operacion_cb.grid(row=2, column=5, padx=5)
        self.operacion_cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        # ===== BOTONES
        ttk.Button(
            frm,
            text="Buscar",
            command=self._search
        ).grid(row=3, column=5, pady=8, sticky="e")

        ttk.Button(
            frm,
            text="Limpiar Filtros",
            command=self._clear_filters
        ).grid(row=3, column=4, pady=8, sticky="e")

    # =========================================================
    # LIMPIAR FILTROS (NUEVO)
    # =========================================================
    def _clear_filters(self):

        try:
            combos = [
                self.year_cb,
                self.month_cb,
                self.continent_cb,
                self.country_cb,
                self.port_cb,
                self.client_cb,
                self.vessel_cb,
                self.operacion_cb
            ]

            for cb in combos:
                cb.set("")

            # Limpiar tabla
            for i in self.tree.get_children():
                self.tree.delete(i)

            # Recargar filtros iniciales
            self._refresh_filters()

        except Exception as e:
            messagebox.showerror("Clear Error", str(e))

    # =========================================================
    # REFRESH FILTERS
    # =========================================================
    def _refresh_filters(self):

        try:
            resp = get_services_for_grain_sampling_api(
                continente=self._val(self.continent_cb),
                pais=self._val(self.country_cb),
                puerto=self._val(self.port_cb),
                cliente=self._val(self.client_cb),
                buque=self._val(self.vessel_cb),
                operacion=self._val(self.operacion_cb),
                year=self._val_int(self.year_cb),
                month=self._val_int(self.month_cb)
            )

            filters = resp.get("filters", {})

            self.year_cb["values"] = [""] + filters.get("years", [])
            self.month_cb["values"] = [""] + filters.get("months", [])
            self.continent_cb["values"] = [""] + filters.get("continentes", [])
            self.country_cb["values"] = [""] + filters.get("paises", [])
            self.port_cb["values"] = [""] + filters.get("puertos", [])
            self.client_cb["values"] = [""] + filters.get("clientes", [])
            self.vessel_cb["values"] = [""] + filters.get("buques", [])
            self.operacion_cb["values"] = [""] + filters.get("operaciones", [])

        except Exception as e:
            messagebox.showerror("Filter Error", str(e))

    # =========================================================
    # TABLE
    # =========================================================
    def _build_table(self):

        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=10)

        columns = (
            "num_informe",
            "buque",
            "cliente",
            "continente",
            "pais",
            "puerto"
        )

        self.tree = ttk.Treeview(
            frm,
            columns=columns,
            show="headings",
            height=15
        )

        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=130, anchor="center")

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select_row)

    # =========================================================
    # SEARCH
    # =========================================================
    def _search(self):

        try:
            resp = get_services_for_grain_sampling_api(
                continente=self._val(self.continent_cb),
                pais=self._val(self.country_cb),
                puerto=self._val(self.port_cb),
                cliente=self._val(self.client_cb),
                buque=self._val(self.vessel_cb),
                operacion=self._val(self.operacion_cb),
                year=self._val_int(self.year_cb),
                month=self._val_int(self.month_cb)
            )

            rows = resp.get("data", [])

            for i in self.tree.get_children():
                self.tree.delete(i)

            for r in rows:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        r.get("num_informe"),
                        r.get("buque_contenedor"),
                        r.get("cliente"),
                        r.get("continente"),
                        r.get("pais"),
                        r.get("puerto")
                    )
                )

        except Exception as e:
            messagebox.showerror("Search Error", str(e))

    # =========================================================
    # ROW SELECT
    # =========================================================
    def _on_select_row(self, event):

        item = self.tree.focus()
        if not item:
            return

        values = self.tree.item(item)["values"]

        self.selected_data = {
            "num_informe": values[0],
            "buque": values[1],
            "cliente": values[2],
            "continente": values[3],
            "pais": values[4],
            "puerto": values[5]
        }

    # =========================================================
    # ACTIONS
    # =========================================================
    def _build_actions(self):

        frm = ttk.Frame(self)
        frm.pack(fill="x", pady=10)

        ttk.Button(
            frm,
            text="Seleccionar Reporte",
            command=self._confirm_selection
        ).pack(side="right", padx=10)

    def _confirm_selection(self):

        if not self.selected_data:
            messagebox.showwarning("Warning", "Seleccione un reporte.")
            return

        if self.on_select:
            self.on_select(self.selected_data)

        self.destroy()

    # =========================================================
    # HELPERS
    # =========================================================
    def _val(self, cb):
        v = cb.get()
        return v if v else None

    def _val_int(self, cb):
        v = cb.get()
        if not v:
            return None
        try:
            return int(v)
        except:
            return None
