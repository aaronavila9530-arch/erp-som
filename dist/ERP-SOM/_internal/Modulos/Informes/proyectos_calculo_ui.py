# ============================================================
# INFORMES — PROYECTOS CALCULO UI
# Tabla + Filtros + Paginado
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_proyectos_calculo_api,
    get_proyecto_calculo_by_nombre_api,
    update_proyecto_calculo_api,
    delete_proyecto_calculo_api
)

from Modulos.Informes.popup.popup_proyecto_calculadora import (
    PopupProyectoCalculadora
)


class ProyectosCalculoUI(ttk.Frame):

    PAGE_SIZE = 50

    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.page = 1
        self.data_all = []

        self._build_ui()

    # ============================================================
    # UI STRUCTURE
    # ============================================================
    def _build_ui(self):

        self.pack(fill="both", expand=True)
        self.parent.grid_rowconfigure(0, weight=1)
        self.parent.grid_columnconfigure(0, weight=1)

        # --------------------------------------------------------
        # HEADER
        # --------------------------------------------------------
        header = ttk.Frame(self)
        header.pack(fill="x", padx=10, pady=8)

        ttk.Label(
            header,
            text="📊 Proyectos — Cálculo",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="⬅ Volver",
            command=self._go_back
        ).pack(side="right")

        # --------------------------------------------------------
        # FILTERS
        # --------------------------------------------------------
        filters = ttk.LabelFrame(self, text="Filtros")
        filters.pack(fill="x", padx=10, pady=5)

        ttk.Label(filters, text="Nombre proyecto:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )

        self.var_nombre = tk.StringVar()

        self.cmb_nombre = ttk.Combobox(
            filters,
            textvariable=self.var_nombre,
            width=38,
            state="readonly"
        )
        self.cmb_nombre.grid(row=0, column=1, padx=5, pady=5)

        self.cmb_nombre.bind(
            "<Button-1>",
            lambda e: self._load_nombre_proyectos()
        )

        ttk.Button(
            filters,
            text="🔍 Buscar",
            command=self._buscar
        ).grid(row=0, column=2, padx=10)

        # --------------------------------------------------------
        # ACTION BUTTONS
        # --------------------------------------------------------
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            actions,
            text="➕ Nuevo Proyecto",
            command=self._nuevo_proyecto
        ).pack(side="left")

        ttk.Button(
            actions,
            text="👁 Ver",
            command=self._ver_proyecto
        ).pack(side="left", padx=5)


        ttk.Button(
            actions,
            text="✏ Editar",
            command=self._editar_proyecto
        ).pack(side="left", padx=5)

        ttk.Button(
            actions,
            text="🗑 Eliminar",
            command=self._eliminar_proyecto
        ).pack(side="left", padx=5)

        # --------------------------------------------------------
        # TABLE
        # --------------------------------------------------------
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
            "nombre_proyecto",
            "moneda",
            "precio",
            "utilidad",
            "creado_el"
        )

        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings"
        )

        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=150, anchor="center")

        self.tree.column("nombre_proyecto", width=300, anchor="w")

        vsb = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.tree.yview
        )
        hsb = ttk.Scrollbar(
            table_frame,
            orient="horizontal",
            command=self.tree.xview
        )

        self.tree.configure(
            yscrollcommand=vsb.set,
            xscrollcommand=hsb.set
        )

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # --------------------------------------------------------
        # PAGINATION
        # --------------------------------------------------------
        pager = ttk.Frame(self)
        pager.pack(fill="x", padx=10, pady=5)

        self.lbl_page = ttk.Label(pager, text="Página 1")
        self.lbl_page.pack(side="left")

        ttk.Button(
            pager,
            text="◀ Anterior",
            command=self._prev_page
        ).pack(side="right", padx=5)

        ttk.Button(
            pager,
            text="Siguiente ▶",
            command=self._next_page
        ).pack(side="right")

    # ============================================================
    # ACTIONS
    # ============================================================
    def _buscar(self):
        try:
            response = get_proyectos_calculo_api()
            rows = response.get("data", [])

            filtro = self.var_nombre.get().strip()

            if filtro and filtro != "ALL":
                filtro = filtro.lower()
                rows = [
                    r for r in rows
                    if filtro in (r.get("nombre_proyecto") or "").lower()
                ]

            self.data_all = rows
            self.page = 1
            self._render_page()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _render_page(self):
        self.tree.delete(*self.tree.get_children())

        start = (self.page - 1) * self.PAGE_SIZE
        end = start + self.PAGE_SIZE

        for row in self.data_all[start:end]:
            self.tree.insert(
                "",
                "end",
                values=(
                    row.get("nombre_proyecto"),
                    row.get("moneda"),
                    row.get("precio"),
                    row.get("utilidad"),
                    row.get("creado_el"),
                )
            )

        total_pages = max(
            1,
            (len(self.data_all) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        )

        self.lbl_page.config(
            text=f"Página {self.page} de {total_pages}"
        )

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._render_page()

    def _next_page(self):
        total_pages = max(
            1,
            (len(self.data_all) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        )
        if self.page < total_pages:
            self.page += 1
            self._render_page()

    def _get_selected_nombre(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0])["values"][0]

    # ============================================================
    # CRUD ACTIONS
    # ============================================================
    def _nuevo_proyecto(self):
        popup = PopupProyectoCalculadora(self)
        self.wait_window(popup)
        self._buscar()

    def _editar_proyecto(self):
        nombre_proyecto = self._get_selected_nombre()
        if not nombre_proyecto:
            messagebox.showwarning("Seleccionar", "Seleccione un proyecto")
            return

        try:
            response = get_proyecto_calculo_by_nombre_api(nombre_proyecto)
            data = response.get("data", {})

            popup = PopupProyectoCalculadora(self)

            header = data.get("header", {})
            personas = data.get("personas", [])

            # ---------------- HEADER ----------------
            popup.var_nombre_proyecto.set(header.get("nombre_proyecto"))
            popup.var_moneda.set(header.get("moneda"))
            popup.var_margen.set(str(header.get("margen", 0)))

            popup.var_precio.set(header.get("precio", 0))
            popup.var_utilidad.set(header.get("utilidad", 0))

            # ---------------- TIEMPO ----------------
            tiempo = float(header.get("tiempo", 0))
            popup.var_horas.set(int(tiempo))
            popup.var_minutos.set(int((tiempo % 1) * 60))

            # ---------------- PERSONAL ----------------
            for w in popup.personal_frame.winfo_children():
                w.destroy()
            popup.personal_costos.clear()

            for p in personas:
                popup._add_personal_row()
                popup.personal_costos[-1].set(p.get("costo", 0))

            # ---------------- GASTOS ----------------
            popup.var_gasto_alimentacion.set(header.get("gasto_alimentacion", 0))
            popup.var_gasto_comunicacion.set(header.get("gasto_comunicacion", 0))
            popup.var_gasto_transporte.set(header.get("gasto_transporte", 0))

            # ---------------- SAVE OVERRIDE ----------------
            popup._guardar_proyecto = lambda: self._guardar_edicion(
                nombre_proyecto, popup
            )

            popup._recalculate()

            popup.wait_window()
            self._buscar()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _ver_proyecto(self):
        nombre_proyecto = self._get_selected_nombre()
        if not nombre_proyecto:
            messagebox.showwarning(
                "Seleccionar",
                "Seleccione un proyecto"
            )
            return

        try:
            response = get_proyecto_calculo_by_nombre_api(nombre_proyecto)
            data = response.get("data", {})

            popup = PopupProyectoCalculadora(self)

            header = data.get("header", {})
            personas = data.get("personas", [])

            # ---------------- HEADER ----------------
            popup.var_nombre_proyecto.set(header.get("nombre_proyecto"))
            popup.var_moneda.set(header.get("moneda"))
            popup.var_margen.set(str(header.get("margen", 0)))

            popup.var_precio.set(header.get("precio", 0))
            popup.var_utilidad.set(header.get("utilidad", 0))

            # ---------------- TIEMPO ----------------
            tiempo = float(header.get("tiempo", 0))
            popup.var_horas.set(int(tiempo))
            popup.var_minutos.set(int((tiempo % 1) * 60))

            # ---------------- PERSONAL ----------------
            for w in popup.personal_frame.winfo_children():
                w.destroy()
            popup.personal_costos.clear()

            for p in personas:
                popup._add_personal_row()
                popup.personal_costos[-1].set(p.get("costo", 0))

            # ---------------- GASTOS ----------------
            popup.var_gasto_alimentacion.set(header.get("gasto_alimentacion", 0))
            popup.var_gasto_comunicacion.set(header.get("gasto_comunicacion", 0))
            popup.var_gasto_transporte.set(header.get("gasto_transporte", 0))

            popup._lock_precio = True
            popup._lock_utilidad = True

            popup._recalculate()

            self._set_popup_readonly(popup)

            popup.wait_window()

        except Exception as e:
            messagebox.showerror("Error", str(e))


    def _guardar_edicion(self, nombre_proyecto, popup):
        payload = {
            "moneda": popup.var_moneda.get(),
            "margen": float(popup.var_margen.get()),
            "precio": round(popup.var_precio.get(), 2),
            "utilidad": round(popup.var_utilidad.get(), 2),
        }

        try:
            update_proyecto_calculo_api(nombre_proyecto, payload)
            popup.destroy()
            messagebox.showinfo("Éxito", "Proyecto actualizado")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _eliminar_proyecto(self):
        nombre_proyecto = self._get_selected_nombre()
        if not nombre_proyecto:
            messagebox.showwarning("Seleccionar", "Seleccione un proyecto")
            return

        if not messagebox.askyesno(
            "Confirmar", "¿Eliminar el proyecto seleccionado?"
        ):
            return

        try:
            delete_proyecto_calculo_api(nombre_proyecto)
            self._buscar()

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _load_nombre_proyectos(self):
        try:
            response = get_proyectos_calculo_api()
            rows = response.get("data", [])

            nombres = sorted({
                r.get("nombre_proyecto")
                for r in rows
                if r.get("nombre_proyecto")
            })

            self.cmb_nombre["values"] = ["ALL"] + nombres

            # default
            if not self.var_nombre.get():
                self.var_nombre.set("ALL")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar los proyectos\n{e}"
            )

    def _set_popup_readonly(self, popup):

        # Deshabilitar inputs
        for child in popup.winfo_children():
            self._disable_recursive(child)

        # Ocultar botón Guardar
        for widget in popup.winfo_children():
            if isinstance(widget, ttk.Frame):
                for btn in widget.winfo_children():
                    if isinstance(btn, ttk.Button) and "Guardar" in btn.cget("text"):
                        btn.destroy()

    def _disable_recursive(self, widget):
        try:
            if isinstance(widget, ttk.Button):
                if "Cerrar" in widget.cget("text"):
                    return
                widget.configure(state="disabled")
            else:
                widget.configure(state="disabled")
        except Exception:
            pass

        for child in widget.winfo_children():
            self._disable_recursive(child)



    def _go_back(self):
        if callable(self.on_back):
            self.on_back()
