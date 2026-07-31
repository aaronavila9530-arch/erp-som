import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    hr_listar_empleados,
    hr_crear_empleado,
    hr_actualizar_empleado
)

from Modulos.HHRR.popups.popup_empleado import PopupEmpleado
from Modulos.HHRR.date_utils import to_long_english_date


class VistaEmpleadosHHRR(ttk.Frame):
    """
    Vista administrativa de EMPLEADOS (HHRR)
    Roles permitidos: admin / master
    """

    def __init__(self, parent, rol_usuario):
        super().__init__(parent)

        self.rol_usuario = (rol_usuario or "").lower()

        if self.rol_usuario not in ("admin", "master"):
            ttk.Label(
                self,
                text="Acceso restringido",
                foreground="red",
                font=("Segoe UI", 11, "bold")
            ).pack(pady=30)
            return

        self.page = 1
        self.page_size = 50
        self.total = 0

        # =====================================================
        # CACHE COMPLETO DEL GET (NO EXISTÍA)
        # =====================================================
        self._empleados_cache = []

        self._construir_ui()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(10, 5))

        ttk.Label(header, text="Empleados", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(header, text="Gestión administrativa de colaboradores", font=("Segoe UI", 9)).pack(anchor="w")

        # ---------------- FILTROS ----------------
        filtros = ttk.LabelFrame(self, text="Filtros")
        filtros.pack(fill="x", padx=5, pady=5)

        self.filtro_nombre = ttk.Combobox(filtros, width=25)
        self.filtro_codigo = ttk.Combobox(filtros, width=18)
        self.filtro_estado = ttk.Combobox(
            filtros,
            values=["", "Activo", "Inactivo"],
            state="readonly",
            width=15
        )
        self.filtro_usuario = ttk.Combobox(filtros, width=18)

        ttk.Label(filtros, text="Nombre").grid(row=0, column=0, padx=5, pady=5)
        self.filtro_nombre.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filtros, text="Código").grid(row=0, column=2, padx=5, pady=5)
        self.filtro_codigo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filtros, text="Estado").grid(row=0, column=4, padx=5, pady=5)
        self.filtro_estado.grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(filtros, text="Usuario").grid(row=0, column=6, padx=5, pady=5)
        self.filtro_usuario.grid(row=0, column=7, padx=5, pady=5)

        # ---------------- BOTONES ----------------
        botones = ttk.Frame(self)
        botones.pack(fill="x", padx=5)

        ttk.Button(botones, text="Buscar", command=self._on_buscar).pack(side="left", padx=5)
        ttk.Button(botones, text="Limpiar", command=self._on_limpiar).pack(side="left", padx=5)
        ttk.Button(botones, text="Nuevo empleado", command=self._on_nuevo).pack(side="right", padx=5)

        # ---------------- TABLA ----------------
        tabla_frame = ttk.Frame(self)
        tabla_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.columnas = [
            "id", "codigo", "nombre", "apellidos", "cedula_id", "usuario",
            "estado", "jornada", "salario", "pago", "banco", "moneda",
            "fecha_ingreso", "horas_contratadas", "activo1", "activo2", "activo3"
        ]

        self.tabla = ttk.Treeview(tabla_frame, columns=self.columnas, show="headings")

        for col in self.columnas:
            self.tabla.heading(col, text=col.replace("_", " ").title())
            self.tabla.column(col, width=120, anchor="center")

        self.tabla.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tabla.yview)
        scroll_x = ttk.Scrollbar(tabla_frame, orient="horizontal", command=self.tabla.xview)

        self.tabla.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        tabla_frame.rowconfigure(0, weight=1)
        tabla_frame.columnconfigure(0, weight=1)

        # ---------------- BOTONES VER / EDITAR ----------------
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Button(acciones, text="Ver", command=self._on_ver_btn).pack(side="left", padx=5)
        ttk.Button(acciones, text="Editar", command=self._on_editar_btn).pack(side="left", padx=5)

        # ---------------- PAGINACIÓN ----------------
        pag = ttk.Frame(self)
        pag.pack(fill="x", pady=5)

        self.lbl_pagina = ttk.Label(pag, text="Página 1")
        self.lbl_pagina.pack(side="left", padx=10)

        ttk.Button(pag, text="«", command=self._on_primera).pack(side="right", padx=2)
        ttk.Button(pag, text="‹", command=self._on_anterior).pack(side="right", padx=2)
        ttk.Button(pag, text="›", command=self._on_siguiente).pack(side="right", padx=2)

    # =========================================================
    # ACCIONES
    # =========================================================
    def _on_buscar(self):
        filtros = self._get_filtros()

        try:
            resp = hr_listar_empleados(
                page=self.page,
                page_size=self.page_size,
                **filtros
            )
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        data = resp.get("data", [])
        self.total = resp.get("total", 0)

        # =====================================================
        # GUARDAR GET COMPLETO EN MEMORIA (NUEVO)
        # =====================================================
        self._empleados_cache = data

        self._cargar_tabla(data)
        self._alimentar_filtros(data)

        total_pages = max(1, (self.total + self.page_size - 1) // self.page_size)
        self.lbl_pagina.config(text=f"Página {self.page} de {total_pages}")

    def _cargar_tabla(self, data):
        self.tabla.delete(*self.tabla.get_children())
        for row in data:
            values = []
            for col in self.columnas:
                value = row.get(col)
                if col == "fecha_ingreso":
                    value = to_long_english_date(value)
                values.append(value)
            self.tabla.insert("", "end", values=values)

    def _alimentar_filtros(self, data):
        self.filtro_nombre["values"] = sorted({d["nombre"] for d in data if d.get("nombre")})
        self.filtro_codigo["values"] = sorted({d["codigo"] for d in data if d.get("codigo")})
        self.filtro_usuario["values"] = sorted({d["usuario"] for d in data if d.get("usuario")})

    def _on_limpiar(self):
        self.filtro_nombre.set("")
        self.filtro_codigo.set("")
        self.filtro_usuario.set("")
        self.filtro_estado.set("")
        self.page = 1
        self.tabla.delete(*self.tabla.get_children())
        self.lbl_pagina.config(text="Página 1")
        self._empleados_cache = []

    # =========================================================
    # POPUPS
    # =========================================================
    def _on_nuevo(self):
        PopupEmpleado(
            parent=self,
            modo="nuevo",
            on_save=self._guardar_empleado
        )

    def _on_ver_btn(self):
        empleado = self._get_empleado_seleccionado()
        if not empleado:
            return

        PopupEmpleado(
            parent=self,
            modo="ver",
            empleado=empleado
        )

    def _on_editar_btn(self):
        empleado = self._get_empleado_seleccionado()
        if not empleado:
            return

        PopupEmpleado(
            parent=self,
            modo="editar",
            empleado=empleado,
            on_save=self._guardar_empleado
        )

    # =========================================================
    # GUARDADO
    # =========================================================
    def _guardar_empleado(self, modo, empleado_id, payload):

        if modo == "nuevo":
            hr_crear_empleado(payload)

        elif modo == "editar":
            hr_actualizar_empleado(empleado_id, payload)

        self._on_buscar()

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _on_primera(self):
        self.page = 1
        self._on_buscar()

    def _on_anterior(self):
        if self.page > 1:
            self.page -= 1
            self._on_buscar()

    def _on_siguiente(self):
        if self.page * self.page_size < self.total:
            self.page += 1
            self._on_buscar()

    # =========================================================
    # UTILIDADES BLINDADAS
    # =========================================================
    def _get_filtros(self):
        return {
            "nombre": self.filtro_nombre.get() or None,
            "codigo": self.filtro_codigo.get() or None,
            "estado": self.filtro_estado.get() or None,
            "usuario": self.filtro_usuario.get() or None
        }

    def _get_empleado_seleccionado(self):
        item = self.tabla.focus()
        if not item:
            messagebox.showwarning("Atención", "Seleccione un empleado")
            return None

        try:
            index = self.tabla.index(item)
            return self._empleados_cache[index]
        except Exception:
            messagebox.showerror("Error", "No se pudo leer el empleado seleccionado")
            return None
