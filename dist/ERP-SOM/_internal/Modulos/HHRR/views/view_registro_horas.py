import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    hr_get_my_summary,
    hr_list_ot_logs,
    hr_delete_ot_log
)

from Modulos.HHRR.popups.popup_registro_horas import PopupRegistroHoras
from Modulos.HHRR.ui_lazy_table import TablaLazy


class VistaRegistroHoras(ttk.Frame):

    PAGE_SIZE = 50

    ESTADO_LABELS = {
        "PENDIENTE": "● Pendiente",
        "APROBADO": "● Aprobado",
        "RECHAZADO": "● Rechazado",
    }

    ESTADO_MAP_UI_TO_BACK = {
        "● Pendiente": "PENDIENTE",
        "● Aprobado": "APROBADO",
        "● Rechazado": "RECHAZADO"
    }

    def __init__(self, parent, usuario, rol, on_back):
        super().__init__(parent)

        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.read_only = (self.usuario or "").strip().lower() in ("surveyor01", "surveyor02")
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

        header = ttk.Frame(self)
        header.pack(fill="x", pady=5)

        ttk.Button(header, text="← Volver", command=self.on_back).pack(side="left")

        ttk.Label(
            header,
            text="Registro de Horas",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left", padx=10)

        # ================= SUMMARY =================
        self.frm_summary = ttk.LabelFrame(self, text="Resumen")
        self.frm_summary.pack(fill="x", padx=10, pady=10)

        self.lbl_summary = ttk.Label(
            self.frm_summary,
            text="Cargando...",
            font=("Segoe UI", 10)
        )
        self.lbl_summary.pack(anchor="w", padx=10, pady=5)

        # ================= BOTÓN REGISTRO =================
        if not self.read_only:
            ttk.Button(
                self,
                text="+ Registrar horas",
                command=self._open_registro_popup
            ).pack(anchor="e", padx=10, pady=5)

        # ================= FILTROS =================
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

        ttk.Label(filtros, text="Estado:").pack(side="left", padx=(10, 0))

        self.cmb_estado = ttk.Combobox(
            filtros,
            values=["", "● Pendiente", "● Aprobado", "● Rechazado"],
            width=15,
            state="readonly"
        )
        self.cmb_estado.pack(side="left", padx=5)

        # ================= TABLA =================
        self.columnas = [
            "id",
            "tipo",
            "fecha_inicio",
            "fecha_fin",
            "duracion_horas",
            "buque",
            "comentario",
            "estado"
        ]

        self.tabla = TablaLazy(
            self,
            columnas=self.columnas,
            alto=18
        )
        self.tabla.pack(fill="both", expand=True, padx=10, pady=5)

        # ================= ACCIONES =================
        acciones = ttk.Frame(self)
        acciones.pack(fill="x", padx=10, pady=5)

        self.btn_eliminar = ttk.Button(
            acciones,
            text="Eliminar seleccionado",
            command=self._eliminar
        )
        self.btn_eliminar.pack(side="left")

        # 🔒 RBAC FRONT
        if self.rol == "user" or self.read_only:
            self.btn_eliminar.state(["disabled"])

        self.lbl_paginacion = ttk.Label(acciones, text="")
        self.lbl_paginacion.pack(side="right")

        ttk.Button(acciones, text="◀", command=self._prev_page).pack(side="right")
        ttk.Button(acciones, text="▶", command=self._next_page).pack(side="right")

    # =========================================================
    # SUMMARY
    # =========================================================
    def _load_summary(self):
        try:
            data = hr_get_my_summary()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        emp = data.get("empleado", {})

        txt = (
            f"Empleado: {emp.get('nombre','')} {emp.get('apellidos','')} | "
            f"Jornada: {emp.get('jornada','')} | "
            f"Salario: {emp.get('salario','')} | "
            f"Pago: {emp.get('pago','')}\n"
            f"Horas contratadas: {data.get('horas_contratadas',0)} | "
            f"Horas registradas: {data.get('horas_registradas',0)} | "
            f"Horas pendientes: {data.get('horas_pendientes',0)}"
        )

        self.lbl_summary.config(text=txt)

    # =========================================================
    # TABLA
    # =========================================================
    def _load_table(self):

        try:
            tipo = (self.cmb_tipo.get() or "").strip().upper() or None
            estado_ui = self.cmb_estado.get()

            estado_backend = self.ESTADO_MAP_UI_TO_BACK.get(estado_ui)

            resp = hr_list_ot_logs(
                page=self.page,
                page_size=self.PAGE_SIZE,
                tipo=tipo,
                estado=estado_backend
            )

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        data = resp.get("data", [])
        self.total = resp.get("total", 0)

        # -------- NORMALIZACIÓN --------
        for row in data:
            raw_estado = (row.get("estado") or "").upper()
            row["estado"] = self.ESTADO_LABELS.get(raw_estado, "● Desconocido")

        self.tabla.cargar_datos(data)

        # -------- COLORES --------
        tree = self.tabla.tree

        tree.tag_configure("Pendiente", foreground="#D4A017")
        tree.tag_configure("Aprobado", foreground="#2E8B57")
        tree.tag_configure("Rechazado", foreground="#B22222")

        idx_estado = self.columnas.index("estado")

        for item in tree.get_children():
            values = tree.item(item, "values")
            estado_ui = values[idx_estado]

            if "Pendiente" in estado_ui:
                tree.item(item, tags=("Pendiente",))
            elif "Aprobado" in estado_ui:
                tree.item(item, tags=("Aprobado",))
            elif "Rechazado" in estado_ui:
                tree.item(item, tags=("Rechazado",))

        total_pages = max(1, (self.total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.lbl_paginacion.config(text=f"Página {self.page} de {total_pages}")

    # =========================================================
    # ACCIONES
    # =========================================================
    def _open_registro_popup(self):
        if self.read_only:
            messagebox.showwarning("Permiso", "Este usuario solo tiene permisos de consulta.")
            return
        PopupRegistroHoras(parent=self, on_success=self._reload)

    def _eliminar(self):

        if self.rol == "user" or self.read_only:
            messagebox.showwarning("Permiso", "No tienes permisos para eliminar.")
            return

        row = self.tabla.obtener_seleccionado()

        if not row or not row.get("id"):
            messagebox.showwarning("Selección", "Seleccione un registro válido.")
            return

        if not messagebox.askyesno("Confirmar", "¿Eliminar registro?"):
            return

        try:
            hr_delete_ot_log(row["id"])
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._reload()

    # =========================================================
    # PAGINACIÓN
    # =========================================================
    def _prev_page(self):
        if self.page > 1:
            self.page -= 1
            self._load_table()

    def _next_page(self):
        if self.page * self.PAGE_SIZE < self.total:
            self.page += 1
            self._load_table()

    def _reload(self):
        self.page = 1
        self._load_table()
        self._load_summary()
