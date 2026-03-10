import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from api_client import (
    hr_get_my_summary,
    hr_list_ot_logs,
    hr_create_ot_log,
    hr_delete_ot_log
)

from Modulos.HHRR.popups.popup_registro_horas import PopupRegistroHoras
from Modulos.HHRR.ui_lazy_table import TablaLazy


class VistaRegistroHoras(ttk.Frame):
    """
    View Registro de Horas (OT LOG)

    ✔ Respeta RBAC
    ✔ Summary superior
    ✔ Tabla paginada
    ✔ Popup de registro
    """

    PAGE_SIZE = 50

    # =========================================================
    # MAPA DE ESTADOS (BACKEND → UI)
    # =========================================================
    ESTADO_LABELS = {
        "PENDIENTE": "● Pendiente",
        "APROBADO": "● Aprobado",
        "RECHAZADO": "● Rechazado",
    }

    def __init__(self, parent, usuario, rol, on_back):
        super().__init__(parent)

        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        self.page = 1
        self.total = 0

        self._build_ui()
        self._load_summary()
        self._load_table()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # -------------------------------
        # Header
        # -------------------------------
        header = ttk.Frame(self)
        header.pack(fill="x", pady=5)

        ttk.Button(
            header,
            text="← Volver",
            command=self.on_back
        ).pack(side="left")

        ttk.Label(
            header,
            text="Registro de Horas",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=10)

        # -------------------------------
        # Summary
        # -------------------------------
        self.frm_summary = ttk.LabelFrame(self, text="Resumen")
        self.frm_summary.pack(fill="x", padx=10, pady=10)

        self.lbl_summary = ttk.Label(
            self.frm_summary,
            text="Cargando información...",
            font=("Segoe UI", 10)
        )
        self.lbl_summary.pack(anchor="w", padx=10, pady=5)

        # -------------------------------
        # Botón registrar
        # -------------------------------
        ttk.Button(
            self,
            text="+ Registrar horas",
            command=self._open_registro_popup
        ).pack(anchor="e", padx=10, pady=5)

        # -------------------------------
        # Filtros
        # -------------------------------
        filtros = ttk.Frame(self)
        filtros.pack(fill="x", padx=10, pady=5)

        ttk.Label(filtros, text="Tipo:").pack(side="left")

        self.cmb_tipo = ttk.Combobox(
            filtros,
            values=["", "OPERACION", "INFORME"],
            width=15,
            state="readonly"
        )
        self.cmb_tipo.pack(side="left", padx=5)

        # -----------------------------------
        # NUEVO FILTRO ESTADO
        # -----------------------------------
        ttk.Label(filtros, text="Estado:").pack(side="left", padx=(10, 0))

        self.cmb_estado = ttk.Combobox(
            filtros,
            values=[
                "",
                "● Pendiente",
                "● Aprobado",
                "● Rechazado"
            ],
            width=15,
            state="readonly"
        )
        self.cmb_estado.pack(side="left", padx=5)

        # -------------------------------
        # Tabla
        # -------------------------------
        columnas = [
            "id",
            "tipo",
            "fecha_inicio",
            "fecha_fin",
            "duracion_horas",
            "buque",
            "comentario",
            "estado"            # ← SOLO SE AGREGA ESTA
        ]

        self.tabla = TablaLazy(
            self,
            columnas=columnas,
            alto=18
        )
        self.tabla.pack(fill="both", expand=True, padx=10, pady=5)

        # -------------------------------
        # Acciones tabla
        # -------------------------------
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", padx=10, pady=5)

        ttk.Button(
            acciones,
            text="Eliminar seleccionado",
            command=self._eliminar
        ).pack(side="left")

        # -------------------------------
        # Paginación
        # -------------------------------
        self.lbl_paginacion = ttk.Label(acciones, text="")
        self.lbl_paginacion.pack(side="right")

        ttk.Button(
            acciones,
            text="◀",
            command=self._prev_page
        ).pack(side="right")

        ttk.Button(
            acciones,
            text="▶",
            command=self._next_page
        ).pack(side="right")

    # =========================================================
    # DATA
    # =========================================================
    def _load_summary(self):
        try:
            data = hr_get_my_summary()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        emp = data["empleado"]

        txt = (
            f"Empleado: {emp['nombre']} {emp['apellidos']} | "
            f"Jornada: {emp['jornada']} | "
            f"Salario: {emp['salario']} | "
            f"Pago: {emp['pago']}\n"
            f"Horas contratadas: {data['horas_contratadas']} | "
            f"Horas registradas: {data['horas_registradas']} | "
            f"Horas pendientes: {data['horas_pendientes']}"
        )

        self.lbl_summary.config(text=txt)

    def _load_table(self):
        try:

            # -------------------------------------------------
            # CONVERTIR ESTADO VISUAL A ESTADO REAL BACKEND
            # -------------------------------------------------
            estado_map = {
                "● Pendiente": "PENDIENTE",
                "● Aprobado": "APROBADO",
                "● Rechazado": "RECHAZADO"
            }

            estado_backend = estado_map.get(
                self.cmb_estado.get(),
                None
            )

            estado_backend = estado_map.get(self.cmb_estado.get())

            resp = hr_list_ot_logs(
                page=self.page,
                page_size=self.PAGE_SIZE,
                tipo=self.cmb_tipo.get() or None,
                estado=estado_backend
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        # -------- FORMATEO VISUAL DE ESTADO --------
        for row in resp["data"]:

            raw_estado = (row.get("estado") or "").upper()

            row["estado"] = self.ESTADO_LABELS.get(
                raw_estado,
                "● Desconocido"
            )


        self.total = resp["total"]
        self.tabla.cargar_datos(resp["data"])

        # =====================================================
        # COLORES POR ESTADO — PINTAR FILA COMPLETA (HORAS)
        # =====================================================
        tree = self.tabla.tree

        tree.tag_configure(
            "Pendiente",
            foreground="#D4A017"  # amarillo
        )
        tree.tag_configure(
            "Aprobado",
            foreground="#2E8B57"  # verde
        )
        tree.tag_configure(
            "Rechazado",
            foreground="#B22222"  # rojo
        )

        for item in tree.get_children():
            values = tree.item(item, "values")

            # estado es la ÚLTIMA columna (índice 7)
            estado_ui = values[7]

            if "Pendiente" in estado_ui:
                tree.item(item, tags=("Pendiente",))
            elif "Aprobado" in estado_ui:
                tree.item(item, tags=("Aprobado",))
            elif "Rechazado" in estado_ui:
                tree.item(item, tags=("Rechazado",))

        total_pages = max(
            1,
            (self.total + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        )
        self.lbl_paginacion.config(
            text=f"Página {self.page} de {total_pages}"
        )

    def _reload(self):
        self.page = 1
        self._load_table()
        self._load_summary()

    # =========================================================
    # ACCIONES
    # =========================================================
    def _open_registro_popup(self):
        PopupRegistroHoras(
            parent=self,
            on_success=self._reload
        )

    def _eliminar(self):
        row = self.tabla.obtener_seleccionado()
        if not row:
            messagebox.showwarning("Selección", "Seleccione un registro.")
            return

        if not messagebox.askyesno(
            "Confirmar",
            "Esta acción es irreversible. ¿Desea continuar?"
        ):
            return

        try:
            hr_delete_ot_log(row["id"])
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._reload()

    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._load_table()

    def _next_page(self):
        if self.page * self.PAGE_SIZE < self.total:
            self.page += 1
            self._load_table()
