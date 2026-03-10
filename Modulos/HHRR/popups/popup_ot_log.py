import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# =========================================================
# API CLIENT REAL (EXISTE)
# =========================================================
from api_client import crear_ot_log


class PopupRegistroHoras(tk.Toplevel):
    """
    Popup para registro de horas trabajadas (OT LOG).
    - NO precarga datos
    - SOLO guarda cuando el usuario presiona GUARDAR
    - El backend obtiene el usuario real vía auth
    """

    def __init__(self, parent, usuario, on_success=None):
        super().__init__(parent)

        self.usuario = usuario  # Solo informativo (NO se envía al backend)
        self.on_success = on_success

        self.title("Registro de Horas Trabajadas")
        self.geometry("420x520")
        self.resizable(False, False)

        # Modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self._construir_ui()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        cont = ttk.Frame(self, padding=20)
        cont.pack(fill="both", expand=True)

        # -------------------------------
        # Tipo
        # -------------------------------
        ttk.Label(cont, text="Tipo de actividad").pack(anchor="w")
        self.var_tipo = tk.StringVar(value="OPERACION")

        ttk.Combobox(
            cont,
            textvariable=self.var_tipo,
            values=["OPERACION", "INFORME"],
            state="readonly"
        ).pack(fill="x", pady=5)

        # -------------------------------
        # Fecha inicio
        # -------------------------------
        ttk.Label(
            cont,
            text="Fecha y hora de inicio (YYYY-MM-DD HH:MM)"
        ).pack(anchor="w")

        self.var_inicio = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_inicio).pack(fill="x", pady=5)

        # -------------------------------
        # Fecha fin
        # -------------------------------
        ttk.Label(
            cont,
            text="Fecha y hora de fin (YYYY-MM-DD HH:MM)"
        ).pack(anchor="w")

        self.var_fin = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_fin).pack(fill="x", pady=5)

        # -------------------------------
        # Buque (opcional)
        # -------------------------------
        ttk.Label(cont, text="Buque (opcional)").pack(anchor="w")
        self.var_buque = tk.StringVar()
        ttk.Entry(cont, textvariable=self.var_buque).pack(fill="x", pady=5)

        # -------------------------------
        # Comentario
        # -------------------------------
        ttk.Label(cont, text="Comentario").pack(anchor="w")
        self.txt_comentario = tk.Text(cont, height=4)
        self.txt_comentario.pack(fill="x", pady=5)

        # -------------------------------
        # Botones
        # -------------------------------
        cont_btn = ttk.Frame(cont)
        cont_btn.pack(fill="x", pady=15)

        ttk.Button(
            cont_btn,
            text="Guardar registro",
            command=self._guardar
        ).pack(side="right")

        ttk.Button(
            cont_btn,
            text="Cancelar",
            command=self.destroy
        ).pack(side="right", padx=5)

    # =========================================================
    # LÓGICA
    # =========================================================
    def _guardar(self):

        # -------------------------------
        # Validación de fechas
        # -------------------------------
        try:
            inicio = datetime.strptime(
                self.var_inicio.get().strip(), "%Y-%m-%d %H:%M"
            )
            fin = datetime.strptime(
                self.var_fin.get().strip(), "%Y-%m-%d %H:%M"
            )
        except ValueError:
            messagebox.showerror(
                "Formato inválido",
                "Las fechas deben tener el formato YYYY-MM-DD HH:MM"
            )
            return

        if fin <= inicio:
            messagebox.showerror(
                "Error de tiempo",
                "La fecha/hora de fin debe ser mayor a la de inicio"
            )
            return

        duracion = round(
            (fin - inicio).total_seconds() / 3600,
            2
        )

        if duracion <= 0:
            messagebox.showerror(
                "Duración inválida",
                "La duración calculada no es válida"
            )
            return

        # -------------------------------
        # Payload EXACTO para el backend
        # -------------------------------
        data = {
            "tipo": self.var_tipo.get(),
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "duracion_horas": duracion,
            "buque": self.var_buque.get().strip() or None,
            "comentario": self.txt_comentario.get("1.0", "end").strip() or None
        }

        try:
            crear_ot_log(data)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar el registro:\n{e}"
            )
            return

        messagebox.showinfo(
            "Registro guardado",
            "Las horas fueron registradas correctamente."
        )

        if callable(self.on_success):
            self.on_success()

        self.destroy()
