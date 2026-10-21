import tkinter as tk
from tkinter import ttk, messagebox

from api_client import filter_servicios_draft_api
from Modulos.Informes.Vessel_Draft_Survey.draft_survey_form import DraftSurveyForm


class PopupServicioDraftSelector(tk.Toplevel):

    def __init__(self, parent, on_select=None):
        super().__init__(parent)

        self.parent = parent
        self.on_select = on_select

        self.title("Buscar Servicio - Draft Survey")
        self.geometry("1150x620")
        self.transient(parent)
        self.grab_set()

        self._build_filters()
        self._build_table()
        self._build_actions()

        self._load_initial_data()

    # =========================================================
    # FILTERS
    # =========================================================

    def _build_filters(self):

        frm = ttk.LabelFrame(self, text="Filtros")
        frm.pack(fill="x", padx=10, pady=10)

        # Año
        ttk.Label(frm, text="Año").grid(row=0, column=0, padx=5, sticky="w")
        self.year_cb = ttk.Combobox(frm, width=10, state="readonly")
        self.year_cb.grid(row=0, column=1, padx=5)

        # Mes
        ttk.Label(frm, text="Mes").grid(row=0, column=2, padx=5, sticky="w")
        self.month_cb = ttk.Combobox(frm, width=8, state="readonly")
        self.month_cb.grid(row=0, column=3, padx=5)
        self.month_cb["values"] = [""] + [f"{i:02d}" for i in range(1, 13)]

        # Continente
        ttk.Label(frm, text="Continente").grid(row=0, column=4, padx=5, sticky="w")
        self.continente_cb = ttk.Combobox(frm, width=15, state="readonly")
        self.continente_cb.grid(row=0, column=5, padx=5)

        # País
        ttk.Label(frm, text="País").grid(row=1, column=0, padx=5, sticky="w")
        self.pais_cb = ttk.Combobox(frm, width=15, state="readonly")
        self.pais_cb.grid(row=1, column=1, padx=5)

        # Puerto
        ttk.Label(frm, text="Puerto").grid(row=1, column=2, padx=5, sticky="w")
        self.puerto_cb = ttk.Combobox(frm, width=15, state="readonly")
        self.puerto_cb.grid(row=1, column=3, padx=5)

        # Cliente
        ttk.Label(frm, text="Cliente").grid(row=1, column=4, padx=5, sticky="w")
        self.cliente_cb = ttk.Combobox(frm, width=20, state="readonly")
        self.cliente_cb.grid(row=1, column=5, padx=5)

        # Operación
        ttk.Label(frm, text="Operación").grid(row=2, column=0, padx=5, sticky="w")
        self.operacion_cb = ttk.Combobox(frm, width=20, state="readonly")
        self.operacion_cb.grid(row=2, column=1, padx=5)

        # Botones
        ttk.Button(frm, text="Buscar", command=self._search)\
            .grid(row=2, column=4, padx=10)

        ttk.Button(frm, text="Limpiar", command=self._clear_filters)\
            .grid(row=2, column=5, padx=5)

        # ==============================
        # BINDS CASCADA
        # ==============================

        self.year_cb.bind("<<ComboboxSelected>>", lambda e: self._update_cascade())
        self.month_cb.bind("<<ComboboxSelected>>", lambda e: self._update_cascade())
        self.continente_cb.bind("<<ComboboxSelected>>", lambda e: self._update_cascade())
        self.pais_cb.bind("<<ComboboxSelected>>", lambda e: self._update_cascade())
        self.puerto_cb.bind("<<ComboboxSelected>>", lambda e: self._update_cascade())
        self.cliente_cb.bind("<<ComboboxSelected>>", lambda e: self._update_cascade())
        self.operacion_cb.bind("<<ComboboxSelected>>", lambda e: self._update_cascade())

    # =========================================================
    # INITIAL LOAD
    # =========================================================

    def _load_initial_data(self):
        self._update_cascade()

    # =========================================================
    # SEARCH
    # =========================================================

    def _search(self):

        try:
            resp = filter_servicios_draft_api(
                year=int(self.year_cb.get()) if self.year_cb.get() else None,
                month=int(self.month_cb.get()) if self.month_cb.get() else None,
                continente=self.continente_cb.get() or None,
                pais=self.pais_cb.get() or None,
                puerto=self.puerto_cb.get() or None,
                operacion=self.operacion_cb.get() or None
            )

            if not resp.get("success"):
                messagebox.showerror("Error", "Error consultando servicios.")
                return

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
                        r.get("operacion"),
                        r.get("fecha_inicio"),
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
            "operacion",
            "fecha_inicio"
        )

        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            height=15
        )

        headers = {
            "num_informe": "No. Informe",
            "buque": "Buque",
            "cliente": "Cliente",
            "continente": "Continente",
            "pais": "País",
            "puerto": "Puerto",
            "operacion": "Operación",
            "fecha_inicio": "Fecha Inicio"
        }

        for col in columns:
            self.tree.heading(col, text=headers[col])
            self.tree.column(col, width=140, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    # =========================================================
    # ACTIONS
    # =========================================================

    def _build_actions(self):

        frm = ttk.Frame(self)
        frm.pack(fill="x", pady=10)

        ttk.Button(
            frm,
            text="Seleccionar",
            command=self._confirm_selection
        ).pack(side="right", padx=10)

    # =========================================================
    # CONFIRM SELECTION — ABRE FORM Y DISPARA GET AUTOMÁTICO
    # =========================================================
    def _confirm_selection(self):

        item = self.tree.focus()

        if not item:
            messagebox.showwarning("Advertencia", "Seleccione un servicio.")
            return

        values = self.tree.item(item)["values"]

        if not values:
            messagebox.showwarning("Advertencia", "Registro inválido.")
            return

        # 🔥 Solo devolver datos al form
        if self.on_select:
            self.on_select(values)

        self.destroy()

    # =========================================================
    # CASCADE UPDATE (PROFESIONAL)
    # =========================================================

    def _update_cascade(self):

        try:
            # Guardar selección actual
            selected = {
                "year": self.year_cb.get(),
                "month": self.month_cb.get(),
                "continente": self.continente_cb.get(),
                "pais": self.pais_cb.get(),
                "puerto": self.puerto_cb.get(),
                "cliente": self.cliente_cb.get(),
                "operacion": self.operacion_cb.get(),
            }

            resp = filter_servicios_draft_api(
                year=int(selected["year"]) if selected["year"] else None,
                month=int(selected["month"]) if selected["month"] else None,
                continente=selected["continente"] or None,
                pais=selected["pais"] or None,
                puerto=selected["puerto"] or None,
                operacion=selected["operacion"] or None
            )

            if not resp.get("success"):
                return

            rows = resp.get("data", [])

            # Crear sets dinámicos
            years = set()
            continentes = set()
            paises = set()
            puertos = set()
            clientes = set()
            operaciones = set()

            for r in rows:
                fecha = r.get("fecha_inicio")
                if fecha:
                    years.add(str(fecha)[:4])

                if r.get("continente"):
                    continentes.add(r["continente"])

                if r.get("pais"):
                    paises.add(r["pais"])

                if r.get("puerto"):
                    puertos.add(r["puerto"])

                if r.get("cliente"):
                    clientes.add(r["cliente"])

                if r.get("operacion"):
                    operaciones.add(r["operacion"])

            # Actualizar combos
            self.year_cb["values"] = [""] + sorted(years, reverse=True)
            self.continente_cb["values"] = [""] + sorted(continentes)
            self.pais_cb["values"] = [""] + sorted(paises)
            self.puerto_cb["values"] = [""] + sorted(puertos)
            self.cliente_cb["values"] = [""] + sorted(clientes)
            self.operacion_cb["values"] = [""] + sorted(operaciones)

            # Restaurar selección si aún existe
            for key, combo in [
                ("year", self.year_cb),
                ("month", self.month_cb),
                ("continente", self.continente_cb),
                ("pais", self.pais_cb),
                ("puerto", self.puerto_cb),
                ("cliente", self.cliente_cb),
                ("operacion", self.operacion_cb),
            ]:
                if selected[key] in combo["values"]:
                    combo.set(selected[key])
                else:
                    combo.set("")

        except Exception as e:
            print("Cascade error:", e)

    # =========================================================
    # CLEAR
    # =========================================================

    def _clear_filters(self):

        self.year_cb.set("")
        self.month_cb.set("")
        self.continente_cb.set("")
        self.pais_cb.set("")
        self.puerto_cb.set("")
        self.cliente_cb.set("")
        self.operacion_cb.set("")

        self.tree.delete(*self.tree.get_children())
