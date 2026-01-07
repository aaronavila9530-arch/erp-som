import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_servicio_api,
    cerrar_operacion_api,
    generar_informe_api
)

from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker
from Modulos.Servicios.Popup_servicios.popup_editar_servicio import PopupEditarServicio


class PopupGenerarInforme(tk.Toplevel):

    def __init__(self, parent, consec, on_success=None):
        super().__init__(parent)
        self.parent = parent
        self.consec = consec
        self.on_success = on_success

        self.title("Generar Informe")
        self.geometry("520x520")
        self.config(bg="white")
        self.transient(parent)
        self.grab_set()

        self._cargar_datos()
        self._build_ui()

    # ============================================================
    # DATA
    # ============================================================
    def _cargar_datos(self):
        self.data = get_servicio_api(self.consec)

        if not self.data:
            messagebox.showerror(
                "Error",
                "No se pudo cargar la información del servicio."
            )
            self.destroy()

    # ============================================================
    # UI (SOLO VISTA)
    # ============================================================
    def _build_ui(self):

        self.frame = tk.Frame(self, bg="white")
        self.frame.pack(fill="both", expand=True, padx=20, pady=15)

        def row(label, value, r):
            ttk.Label(
                self.frame,
                text=label,
                font=("Segoe UI", 9)
            ).grid(row=r, column=0, sticky="w", pady=4)

            ttk.Label(
                self.frame,
                text=value if value not in (None, "") else "-",
                font=("Segoe UI", 9),
                foreground="black"
            ).grid(row=r, column=1, sticky="w", pady=4)

        # ===== DATOS EN VISTA =====
        row("Cliente:", self.data.get("cliente"), 0)
        row("Buque:", self.data.get("buque_contenedor"), 1)
        row("Operación:", self.data.get("operacion"), 2)
        row("Detalle:", self.data.get("detalle"), 3)
        row("Surveyor:", self.data.get("surveyor"), 4)
        row("Honorarios:", self.data.get("honorarios"), 5)
        row("Costo operativo:", self.data.get("costo_operativo"), 6)
        row("Fecha inicio:", self.data.get("fecha_inicio"), 7)
        row("Hora inicio:", self.data.get("hora_inicio"), 8)

        ttk.Separator(self.frame).grid(
            row=9, columnspan=2, sticky="ew", pady=12
        )

        # ===== BOTONES =====
        btns = tk.Frame(self.frame, bg="white")
        btns.grid(row=10, columnspan=2, pady=10, sticky="e")

        ttk.Button(
            btns,
            text="Editar",
            command=self._editar
        ).pack(side="left", padx=5)

        ttk.Button(
            btns,
            text="Generar informe",
            command=self._generar_informe
        ).pack(side="left", padx=5)

    # ============================================================
    # EDITAR
    # ============================================================
    def _editar(self):
        self.withdraw()

        def _refresh():
            self.deiconify()
            self.frame.destroy()
            self._cargar_datos()
            self._build_ui()

        PopupEditarServicio(
            self,
            self.consec,
            on_success=_refresh
        )

    # ============================================================
    # GENERAR INFORME
    # ============================================================
    def _generar_informe(self):

        # Validar obligatorios
        faltantes = []
        for campo in ("surveyor", "honorarios", "costo_operativo"):
            if not str(self.data.get(campo, "")).strip():
                faltantes.append(campo)

        if faltantes:
            messagebox.showerror(
                "Error",
                "No se puede generar el informe.\n\n"
                "Campos faltantes:\n- " + "\n- ".join(faltantes)
            )
            return

        if not messagebox.askyesno(
            "Confirmar",
            "¿Está seguro que desea generar el informe?\n\n"
            "Si continúa, el servicio no podrá modificarse."
        ):
            return

        self._pedir_fecha_fin()

    # ============================================================
    # FECHA / HORA FIN
    # ============================================================
    def _pedir_fecha_fin(self):

        self.top_fin = tk.Toplevel(self)
        self.top_fin.title("Finalizar Servicio")
        self.top_fin.geometry("300x220")
        self.top_fin.transient(self)
        self.top_fin.grab_set()

        tk.Label(self.top_fin, text="Fecha finalización").pack(pady=5)
        self.entry_fecha_fin = tk.Entry(self.top_fin)
        self.entry_fecha_fin.pack()

        tk.Button(
            self.top_fin,
            text="📅",
            command=lambda: DatePicker(self.top_fin, self.entry_fecha_fin)
        ).pack()

        tk.Label(self.top_fin, text="Hora finalización").pack(pady=5)
        self.entry_hora_fin = tk.Entry(self.top_fin)
        self.entry_hora_fin.pack()

        tk.Button(
            self.top_fin,
            text="⏰",
            command=lambda: TimePicker(self.top_fin, self.entry_hora_fin)
        ).pack()

        ttk.Button(
            self.top_fin,
            text="Confirmar",
            command=self._finalizar
        ).pack(pady=10)

    # ============================================================
    # FINALIZAR → BACKEND
    # ============================================================
    def _finalizar(self):

        fecha_fin = self.entry_fecha_fin.get().strip()
        hora_fin = self.entry_hora_fin.get().strip()

        if not fecha_fin or not hora_fin:
            messagebox.showerror(
                "Error",
                "Debe ingresar fecha y hora final."
            )
            return

        # 1️⃣ Cerrar operación
        resp = cerrar_operacion_api(
            self.consec,
            fecha_fin,
            hora_fin
        )
        if resp.get("status") != "ok":
            messagebox.showerror("Error", resp.get("error"))
            return

        # 2️⃣ Generar informe
        resp_inf = generar_informe_api(self.consec)
        if resp_inf.get("status") != "ok":
            messagebox.showerror("Error", resp_inf.get("error"))
            return

        # 3️⃣ Cerrar y mostrar informe
        self.top_fin.destroy()
        self.destroy()

        if self.on_success:
            self.on_success()

        from Modulos.Servicios.Popup_servicios.popup_vista_informe import PopupVistaInforme
        PopupVistaInforme(self.parent, self.consec)
