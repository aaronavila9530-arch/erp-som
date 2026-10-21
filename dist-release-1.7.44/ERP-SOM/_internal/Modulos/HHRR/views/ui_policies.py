import tkinter as tk
from tkinter import ttk, messagebox

from api_client import listar_politicas_hr, eliminar_politica_hr
from session_context import get_rol

from Modulos.HHRR.popups.popup_lector_politica import PopupLectorPolitica
from Modulos.HHRR.popups.popup_politica_crud import PopupPoliticaCRUD


class VistaPoliticasHHRR(ttk.Frame):
    """
    Vista de Políticas de la Empresa (HHRR)

    - Carga bajo demanda (NO auto load)
    - Filtro por categoría
    - Tabla con scroll horizontal y vertical
    - Paginación de 50 registros
    - Botón VER para todos
    - CRUD solo Admin / Master
    """

    PAGE_SIZE = 50

    def __init__(self, parent):
        super().__init__(parent)

        self.rol_usuario = (get_rol() or "").lower()
        self.pagina_actual = 1
        self.total_registros = 0
        self.data_actual = []

        self._construir_ui()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        # ---------------------------
        # Título
        # ---------------------------
        ttk.Label(
            self,
            text="Políticas de la Empresa",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=10)

        # ---------------------------
        # Filtros
        # ---------------------------
        frame_filtros = ttk.Frame(self)
        frame_filtros.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_filtros, text="Categoría:").pack(side="left")

        self.var_categoria = tk.StringVar()

        self.combo_categoria = ttk.Combobox(
            frame_filtros,
            textvariable=self.var_categoria,
            width=28,
            state="readonly"
        )
        self.combo_categoria.pack(side="left", padx=5)

        ttk.Button(
            frame_filtros,
            text="Cargar",
            command=self._cargar_datos
        ).pack(side="left", padx=5)

        ttk.Button(
            frame_filtros,
            text="Limpiar",
            command=self._limpiar
        ).pack(side="left", padx=5)

        # ---------------------------
        # Botones de acción
        # ---------------------------
        frame_botones = ttk.Frame(self)
        frame_botones.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            frame_botones,
            text="Ver",
            command=self._ver_politica
        ).pack(side="left", padx=5)

        if self.rol_usuario in ("admin", "master"):
            ttk.Button(
                frame_botones,
                text="Agregar",
                command=self._agregar_politica
            ).pack(side="left", padx=5)

            ttk.Button(
                frame_botones,
                text="Editar",
                command=self._editar_politica
            ).pack(side="left", padx=5)

            ttk.Button(
                frame_botones,
                text="Eliminar",
                command=self._eliminar_politica
            ).pack(side="left", padx=5)

        # ---------------------------
        # Tabla
        # ---------------------------
        frame_tabla = ttk.Frame(self)
        frame_tabla.pack(fill="both", expand=True, padx=10, pady=5)

        columnas = (
            "id",
            "categoria",
            "titulo",
            "articulo_ref",
            "activo"
        )

        self.tree = ttk.Treeview(
            frame_tabla,
            columns=columnas,
            show="headings"
        )

        for col in columnas:
            self.tree.heading(col, text=col.upper())
            self.tree.column(col, width=150, anchor="w")

        self.tree.pack(side="left", fill="both", expand=True)

        # Scroll vertical
        scroll_y = ttk.Scrollbar(
            frame_tabla,
            orient="vertical",
            command=self.tree.yview
        )
        scroll_y.pack(side="right", fill="y")

        # Scroll horizontal
        scroll_x = ttk.Scrollbar(
            self,
            orient="horizontal",
            command=self.tree.xview
        )
        scroll_x.pack(fill="x")

        self.tree.configure(
            yscrollcommand=scroll_y.set,
            xscrollcommand=scroll_x.set
        )

        # ---------------------------
        # Paginación
        # ---------------------------
        frame_paginacion = ttk.Frame(self)
        frame_paginacion.pack(fill="x", pady=5)

        ttk.Button(
            frame_paginacion,
            text="<< Anterior",
            command=self._pagina_anterior
        ).pack(side="left", padx=5)

        self.lbl_pagina = ttk.Label(
            frame_paginacion,
            text="Página 1"
        )
        self.lbl_pagina.pack(side="left", padx=10)

        ttk.Button(
            frame_paginacion,
            text="Siguiente >>",
            command=self._pagina_siguiente
        ).pack(side="left", padx=5)

    # =========================================================
    # ACCIONES
    # =========================================================
    def _limpiar(self):
        self.var_categoria.set("")
        self.pagina_actual = 1
        self._limpiar_tabla()

    def _cargar_datos(self):
        categoria = self.var_categoria.get().strip() or None

        resp = listar_politicas_hr(
            categoria=categoria,
            solo_activas=True
        )

        self.data_actual = resp.get("data", [])
        self.total_registros = len(self.data_actual)
        self.pagina_actual = 1

        self._refrescar_tabla()

    def _refrescar_tabla(self):
        self._limpiar_tabla()

        inicio = (self.pagina_actual - 1) * self.PAGE_SIZE
        fin = inicio + self.PAGE_SIZE

        for row in self.data_actual[inicio:fin]:
            self.tree.insert(
                "",
                "end",
                values=(
                    row["id"],
                    row["categoria"],
                    row["titulo"],
                    row.get("articulo_ref"),
                    "Sí" if row["activo"] else "No"
                )
            )

        total_paginas = max(
            1,
            (self.total_registros + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        )

        self.lbl_pagina.config(
            text=f"Página {self.pagina_actual} de {total_paginas}"
        )

    def _limpiar_tabla(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _pagina_anterior(self):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self._refrescar_tabla()

    def _pagina_siguiente(self):
        max_pagina = (
            (self.total_registros + self.PAGE_SIZE - 1)
            // self.PAGE_SIZE
        )
        if self.pagina_actual < max_pagina:
            self.pagina_actual += 1
            self._refrescar_tabla()

    # =========================================================
    # CRUD / POPUPS
    # =========================================================
    def _ver_politica(self):
        sel = self.tree.selection()
        if not sel:
            return

        idx = self.tree.index(sel[0])
        row = self.data_actual[idx]

        PopupLectorPolitica(
            self,
            titulo=row["titulo"],
            categoria=row["categoria"],
            articulo_ref=row.get("articulo_ref") or "",
            contenido=row["contenido"]
        )

    def _agregar_politica(self):
        PopupPoliticaCRUD(
            self,
            modo="crear",
            on_success=self._cargar_datos
        )

    def _editar_politica(self):
        sel = self.tree.selection()
        if not sel:
            return

        idx = self.tree.index(sel[0])
        row = self.data_actual[idx]

        PopupPoliticaCRUD(
            self,
            modo="editar",
            data=row,
            on_success=self._cargar_datos
        )

    def _eliminar_politica(self):
        sel = self.tree.selection()
        if not sel:
            return

        idx = self.tree.index(sel[0])
        row = self.data_actual[idx]

        if not messagebox.askyesno(
            "Confirmar eliminación",
            "¿Desea desactivar esta política?\n\nEsta acción no la elimina definitivamente."
        ):
            return

        try:
            eliminar_politica_hr(row["id"])
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No fue posible eliminar la política.\n\n{e}"
            )
            return

        messagebox.showinfo(
            "Éxito",
            "Política desactivada correctamente."
        )

        self._cargar_datos()
