import tkinter as tk
from tkinter import ttk, messagebox

from api_client import create_proyecto_calculo_api


class PopupProyectoCalculadora(tk.Toplevel):
    """
    Popup Calculadora de Proyecto
    Margen y Precio EDITABLES
    Rentabilidad SOLO LECTURA
    Honorarios = SUM(costos) * TIEMPO
    """

    MAX_HOURS = 4000
    MAX_MINUTES = 59

    def __init__(self, parent):
        super().__init__(parent)

        self.title("Calculadora de Proyecto")
        self.geometry("900x680")
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        # ================= ESTADO =================
        self.personal_costos = []

        self.var_precio = tk.DoubleVar(value=0.0)
        self.var_utilidad = tk.DoubleVar(value=0.0)

        self._lock_calculo = False

        self._build_ui()
        self._add_personal_row()
        self._recalculate()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        # ---------------- PROYECTO ----------------
        header = ttk.LabelFrame(container, text="Proyecto")
        header.pack(fill="x", pady=5)

        ttk.Label(header, text="Nombre del Proyecto:").grid(row=0, column=0, padx=5)
        self.var_nombre_proyecto = tk.StringVar()
        ttk.Entry(header, textvariable=self.var_nombre_proyecto, width=50).grid(
            row=0, column=1, padx=5
        )

        # ---------------- CONFIG ----------------
        top = ttk.LabelFrame(container, text="Configuración General")
        top.pack(fill="x", pady=5)

        ttk.Label(top, text="Moneda:").grid(row=0, column=0)
        self.var_moneda = tk.StringVar(value="USD")
        ttk.Combobox(
            top,
            textvariable=self.var_moneda,
            values=["USD", "CRC", "EUR"],
            state="readonly",
            width=10
        ).grid(row=0, column=1)

        ttk.Label(top, text="Tiempo total (HH:MM):").grid(row=0, column=2, padx=20)

        self.var_horas = tk.IntVar(value=1)
        self.var_minutos = tk.IntVar(value=0)

        ttk.Spinbox(
            top, from_=0, to=self.MAX_HOURS,
            textvariable=self.var_horas,
            width=5, command=self._recalculate
        ).grid(row=0, column=3)

        ttk.Label(top, text=":").grid(row=0, column=4)

        ttk.Spinbox(
            top, from_=0, to=self.MAX_MINUTES,
            increment=10,
            textvariable=self.var_minutos,
            width=5, command=self._recalculate
        ).grid(row=0, column=5)

        # ---------------- PERSONAL ----------------
        personal = ttk.LabelFrame(container, text="Personal de Trabajo")
        personal.pack(fill="x", pady=5)

        self.personal_frame = ttk.Frame(personal)
        self.personal_frame.pack(fill="x")

        ttk.Button(
            personal,
            text="➕ Agregar Persona",
            command=self._add_personal_row
        ).pack(anchor="w", pady=5)

        # ---------------- GASTOS ----------------
        gastos = ttk.LabelFrame(container, text="Gastos")
        gastos.pack(fill="x", pady=5)

        self.var_gasto_alimentacion = tk.DoubleVar(value=0)
        self.var_gasto_comunicacion = tk.DoubleVar(value=0)
        self.var_gasto_transporte = tk.DoubleVar(value=0)

        self._gasto_row(gastos, "Alimentación:", self.var_gasto_alimentacion, 0)
        self._gasto_row(gastos, "Comunicación:", self.var_gasto_comunicacion, 1)
        self._gasto_row(gastos, "Transporte:", self.var_gasto_transporte, 2)

        # ---------------- RESULTADOS ----------------
        results = ttk.LabelFrame(container, text="Resultados")
        results.pack(fill="x", pady=10)

        ttk.Label(results, text="Margen %:").grid(row=0, column=0)
        self.var_margen = tk.StringVar(value="20")
        ttk.Combobox(
            results,
            textvariable=self.var_margen,
            values=["10", "20", "30", "40", "50", "60", "70", "80", "90", "100"],
            width=10
        ).grid(row=0, column=1)

        self.lbl_honorarios = self._result_label(results, "Total Honorarios:", 1)
        self.lbl_gastos = self._result_label(results, "Total Gastos:", 2)

        ttk.Label(results, text="Precio:").grid(row=3, column=0, padx=5)
        ttk.Entry(results, textvariable=self.var_precio, width=15).grid(
            row=3, column=1, sticky="w"
        )

        ttk.Label(results, text="Rentabilidad %:").grid(row=4, column=0, padx=5)
        ttk.Label(
            results,
            textvariable=self.var_utilidad,
            font=("Segoe UI", 10, "bold")
        ).grid(row=4, column=1, sticky="w")

        self.var_margen.trace_add("write", lambda *_: self._recalculate())
        self.var_precio.trace_add("write", lambda *_: self._precio_editado())

        # ---------------- ACTIONS ----------------
        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=10)

        ttk.Button(
            actions,
            text="💾 Guardar Proyecto",
            command=self._guardar_proyecto
        ).pack(side="right")

        ttk.Button(
            actions,
            text="Cerrar",
            command=self.destroy
        ).pack(side="right", padx=5)

    # ============================================================
    # HELPERS
    # ============================================================
    def _add_personal_row(self):
        row = len(self.personal_costos)
        var = tk.DoubleVar(value=0)

        ttk.Label(self.personal_frame, text=f"Persona {row + 1}").grid(
            row=row, column=0, padx=5
        )
        ttk.Entry(
            self.personal_frame,
            textvariable=var,
            width=15
        ).grid(row=row, column=1)

        var.trace_add("write", lambda *_: self._recalculate())
        self.personal_costos.append(var)

    def _gasto_row(self, parent, label, var, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, padx=5)
        ttk.Entry(parent, textvariable=var, width=15).grid(row=row, column=1)
        var.trace_add("write", lambda *_: self._recalculate())

    def _result_label(self, parent, label, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, padx=5)
        lbl = ttk.Label(parent, text="0.00", font=("Segoe UI", 10, "bold"))
        lbl.grid(row=row, column=1, sticky="w")
        return lbl

    # ============================================================
    # LOGIC
    # ============================================================
    def _recalculate(self):
        if self._lock_calculo:
            return

        self._lock_calculo = True
        try:
            tiempo = self.var_horas.get() + self.var_minutos.get() / 60

            costo_hora_total = sum(c.get() for c in self.personal_costos)
            honorarios = costo_hora_total * tiempo

            gastos = (
                self.var_gasto_alimentacion.get()
                + self.var_gasto_comunicacion.get()
                + self.var_gasto_transporte.get()
            )

            costo_total = honorarios + gastos
            margen = float(self.var_margen.get()) / 100

            precio = costo_total / (1 - margen) if margen < 1 else 0
            utilidad = ((precio - costo_total) / precio) * 100 if precio else 0

            self.lbl_honorarios.config(text=f"{honorarios:,.2f}")
            self.lbl_gastos.config(text=f"{gastos:,.2f}")

            self.var_precio.set(round(precio, 2))
            self.var_utilidad.set(round(utilidad, 2))

        finally:
            self._lock_calculo = False

    def _precio_editado(self):
        if self._lock_calculo:
            return

        self._lock_calculo = True
        try:
            precio = self.var_precio.get()

            tiempo = self.var_horas.get() + self.var_minutos.get() / 60
            honorarios = sum(c.get() for c in self.personal_costos) * tiempo
            gastos = (
                self.var_gasto_alimentacion.get()
                + self.var_gasto_comunicacion.get()
                + self.var_gasto_transporte.get()
            )

            costo = honorarios + gastos
            utilidad = ((precio - costo) / precio) * 100 if precio else 0

            self.var_utilidad.set(round(utilidad, 2))

        finally:
            self._lock_calculo = False

    # ============================================================
    # SAVE
    # ============================================================
    def _guardar_proyecto(self):

        nombre = self.var_nombre_proyecto.get().strip()
        if not nombre:
            messagebox.showwarning(
                "Validación",
                "Debe ingresar el nombre del proyecto"
            )
            return

        # --------------------------------------------------------
        # 1) Construir lista de costos por persona (OBLIGATORIO)
        # --------------------------------------------------------
        personal_costos = []
        for var in self.personal_costos:
            try:
                val = float(var.get())
            except Exception:
                val = 0.0

            # si quieres permitir 0, quita este if
            if val > 0:
                personal_costos.append(val)

        if not personal_costos:
            messagebox.showwarning(
                "Validación",
                "Debe ingresar al menos 1 costo de personal (> 0)"
            )
            return

        # --------------------------------------------------------
        # 2) Totales (solo para enviar consistencia al backend)
        # --------------------------------------------------------
        tiempo = self.var_horas.get() + self.var_minutos.get() / 60

        costo_hora_total = sum(personal_costos)
        total_honorarios = round(costo_hora_total * tiempo, 2)

        total_gastos = round(
            self.var_gasto_alimentacion.get()
            + self.var_gasto_comunicacion.get()
            + self.var_gasto_transporte.get(),
            2
        )

        # margen es % (ej: "60") -> float
        try:
            margen = float(self.var_margen.get())
        except Exception:
            margen = 0.0

        payload = {
            "nombre_proyecto": nombre,
            "personal_costos": personal_costos,              # ✅ CLAVE
            "moneda": self.var_moneda.get(),
            "tiempo": round(tiempo, 2),

            # Estos campos se duplican en cada fila (backend)
            "total_honorarios": total_honorarios,
            "gasto_alimentacion": float(self.var_gasto_alimentacion.get()),
            "gasto_comunicacion": float(self.var_gasto_comunicacion.get()),
            "gasto_transporte": float(self.var_gasto_transporte.get()),
            "total_gastos": total_gastos,
            "margen": margen,
            "precio": round(float(self.var_precio.get()), 2),
            "utilidad": round(float(self.var_utilidad.get()), 2),
            "comentarios": None
        }

        try:
            create_proyecto_calculo_api(payload)
            messagebox.showinfo("Éxito", "Proyecto guardado correctamente")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))
