import tkinter as tk
from tkinter import ttk, messagebox

from api_client import filter_servicios_vessel_truck_api


class PopupServicioSelector(tk.Toplevel):

    def __init__(self, parent, on_select=None):
        super().__init__(parent)

        self.parent = parent
        self.on_select = on_select

        self.title("Buscar Servicio")
        self.geometry("1100x620")
        self.transient(parent)
        self.grab_set()

        self._build_filters()
        self._build_table()
        self._build_actions()

        self._refresh_filters()   # solo filtros

    # =========================================================
    # FILTERS
    # =========================================================

    def _build_filters(self):

        frm = ttk.LabelFrame(self, text="Filtros")
        frm.pack(fill="x", padx=10, pady=10)

        self.year_cb = self._combo(frm, "Año", 0, 0)
        self.month_cb = self._combo(frm, "Mes", 0, 2)

        self.continent_cb = self._combo(frm, "Continente", 1, 0)
        self.country_cb = self._combo(frm, "País", 1, 2)
        self.port_cb = self._combo(frm, "Puerto", 1, 4)

        self.client_cb = self._combo(frm, "Cliente", 2, 0)
        self.vessel_cb = self._combo(frm, "Buque", 2, 2)
        self.operacion_cb = self._combo(frm, "Operación", 2, 4)

        ttk.Button(frm, text="Buscar", command=self._search)\
            .grid(row=3, column=5, pady=10, sticky="e")

        ttk.Button(frm, text="Limpiar", command=self._clear_filters)\
            .grid(row=3, column=4, pady=10, sticky="e")

    def _combo(self, parent, text, row, col):

        ttk.Label(parent, text=text).grid(row=row, column=col, padx=5, sticky="w")

        cb = ttk.Combobox(parent, width=18, state="readonly")
        cb.grid(row=row, column=col+1, padx=5)
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_filters())

        return cb

    # =========================================================
    # REFRESH FILTERS (BLINDADO)
    # =========================================================

    def _refresh_filters(self):

        try:
            resp = filter_servicios_vessel_truck_api(
                {
                    "continente": self._val(self.continent_cb),
                    "pais": self._val(self.country_cb),
                    "puerto": self._val(self.port_cb),
                    "cliente": self._val(self.client_cb),
                    "buque_contenedor": self._val(self.vessel_cb),
                    "operacion": self._val(self.operacion_cb),
                    "anio": self._val_int(self.year_cb),
                    "mes": self._val_int(self.month_cb),
                }
            )

            filters = resp.get("filters", {})

            self._set_combo(self.year_cb, filters.get("years"))
            self._set_combo(self.month_cb, filters.get("months"))
            self._set_combo(self.continent_cb, filters.get("continentes"))
            self._set_combo(self.country_cb, filters.get("paises"))
            self._set_combo(self.port_cb, filters.get("puertos"))
            self._set_combo(self.client_cb, filters.get("clientes"))
            self._set_combo(self.vessel_cb, filters.get("buques"))
            self._set_combo(self.operacion_cb, filters.get("operaciones"))

        except Exception as e:
            messagebox.showerror("Error Filtros", str(e))

    # =========================================================
    # SET COMBO VALUES (NO BORRA SELECCION VALIDA)
    # =========================================================

    def _set_combo(self, combo, values):

        current = combo.get()

        if not values:
            combo["values"] = [""]
            combo.set("")
            return

        str_values = sorted([str(v) for v in values if v])

        combo["values"] = [""] + str_values

        if current in str_values:
            combo.set(current)
        else:
            combo.set("")

    # =========================================================
    # SEARCH
    # =========================================================

    def _search(self):

        try:
            resp = filter_servicios_vessel_truck_api(
                {
                    "continente": self._val(self.continent_cb),
                    "pais": self._val(self.country_cb),
                    "puerto": self._val(self.port_cb),
                    "cliente": self._val(self.client_cb),
                    "buque_contenedor": self._val(self.vessel_cb),
                    "operacion": self._val(self.operacion_cb),
                    "anio": self._val_int(self.year_cb),
                    "mes": self._val_int(self.month_cb),
                }
            )

            rows = resp.get("data", [])

            self.tree.delete(*self.tree.get_children())

            if not rows:
                messagebox.showinfo("Sin resultados", "No se encontraron servicios.")
                return

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
                        r.get("puerto"),
                        r.get("anio"),
                        r.get("mes"),
                        r.get("operacion"),
                    )
                )

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # TABLE
    # =========================================================

    def _build_table(self):

        columns = (
            "num_informe",
            "buque",
            "cliente",
            "continente",
            "pais",
            "puerto",
            "anio",
            "mes",
            "operacion"
        )

        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=15)

        for col in columns:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=120)

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    # =========================================================
    # ACTIONS
    # =========================================================

    def _build_actions(self):

        frm = ttk.Frame(self)
        frm.pack(fill="x", pady=10)

        ttk.Button(frm, text="Seleccionar",
                   command=self._confirm_selection)\
            .pack(side="right", padx=10)

    def _confirm_selection(self):

        item = self.tree.focus()
        if not item:
            messagebox.showwarning("Warning", "Seleccione un servicio.")
            return

        values = self.tree.item(item)["values"]

        if self.on_select:
            self.on_select(values)

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

    def _clear_filters(self):

        for cb in [
            self.year_cb, self.month_cb, self.continent_cb,
            self.country_cb, self.port_cb, self.client_cb,
            self.vessel_cb, self.operacion_cb
        ]:
            cb.set("")

        self.tree.delete(*self.tree.get_children())
        self._refresh_filters()
