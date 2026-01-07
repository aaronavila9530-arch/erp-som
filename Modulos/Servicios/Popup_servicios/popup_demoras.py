import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# Importar widgets personalizados
from Modulos.Servicios.widgets.date_picker import DatePicker
from Modulos.Servicios.widgets.time_picker import TimePicker


def calcular_diferencia(f1, h1, f2, h2):
    """Retorna la diferencia entre dos fechas en (dias, horas, minutos)."""
    inicio = datetime.strptime(f"{f1} {h1}", "%Y-%m-%d %H:%M")
    fin = datetime.strptime(f"{f2} {h2}", "%Y-%m-%d %H:%M")

    delta = fin - inicio
    total_min = int(delta.total_seconds() // 60)

    dias = total_min // (24 * 60)
    horas = (total_min % (24 * 60)) // 60
    minutos = total_min % 60

    return dias, horas, minutos


# ======================================================================
# LINEA DE DEMORA (usa tus DatePicker / TimePicker)
# ======================================================================
class LineaDemora:
    """Cada fila editable dentro del popup de demoras."""

    def __init__(self, parent, remove_callback):
        self.parent = parent
        self.remove_callback = remove_callback

        self.frame = tk.Frame(parent, bg="white")
        self.frame.pack(fill="x", pady=4)

        # =============================
        # FECHA INICIO
        # =============================
        tk.Label(self.frame, text="Fecha Inicio:", bg="white").grid(row=0, column=0)
        self.entry_f_ini = tk.Entry(self.frame, width=12)
        self.entry_f_ini.grid(row=0, column=1, padx=5)

        tk.Button(
            self.frame,
            text="📅",
            command=lambda: DatePicker(self.frame, self.entry_f_ini)
        ).grid(row=0, column=2)

        # =============================
        # HORA INICIO
        # =============================
        tk.Label(self.frame, text="Hora Inicio:", bg="white").grid(row=0, column=3)
        self.entry_h_ini = tk.Entry(self.frame, width=8)
        self.entry_h_ini.grid(row=0, column=4, padx=5)

        tk.Button(
            self.frame,
            text="⏰",
            command=lambda: TimePicker(self.frame, self.entry_h_ini)
        ).grid(row=0, column=5)

        # =============================
        # FECHA FIN
        # =============================
        tk.Label(self.frame, text="Fecha Fin:", bg="white").grid(row=1, column=0)
        self.entry_f_fin = tk.Entry(self.frame, width=12)
        self.entry_f_fin.grid(row=1, column=1, padx=5)

        tk.Button(
            self.frame,
            text="📅",
            command=lambda: DatePicker(self.frame, self.entry_f_fin)
        ).grid(row=1, column=2)

        # =============================
        # HORA FIN
        # =============================
        tk.Label(self.frame, text="Hora Fin:", bg="white").grid(row=1, column=3)
        self.entry_h_fin = tk.Entry(self.frame, width=8)
        self.entry_h_fin.grid(row=1, column=4, padx=5)

        tk.Button(
            self.frame,
            text="⏰",
            command=lambda: TimePicker(self.frame, self.entry_h_fin)
        ).grid(row=1, column=5)

        # =============================
        # Botón eliminar línea
        # =============================
        tk.Button(
            self.frame,
            text="X",
            bg="#F4CCCC",
            command=self.remove
        ).grid(row=0, column=6, rowspan=2, padx=10)

    def get_values(self):
        """Devuelve fecha inicio, hora inicio, fecha fin, hora fin."""
        return (
            self.entry_f_ini.get().strip(),
            self.entry_h_ini.get().strip(),
            self.entry_f_fin.get().strip(),
            self.entry_h_fin.get().strip(),
        )

    def remove(self):
        self.frame.destroy()
        self.remove_callback(self)


# ======================================================================
# POPUP COMPLETO
# ======================================================================
class PopupDemoras(tk.Toplevel):

    def __init__(self, parent, consec, on_success):
        super().__init__(parent)
        self.consec = consec
        self.on_success = on_success
        self.title(f"Demoras - Servicio {consec}")
        self.geometry("750x500")
        self.config(bg="white")

        self.lineas = []

        tk.Label(
            self,
            text=f"Registrar demoras para el servicio {consec}",
            bg="white",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=10)

        # Marco para líneas
        self.contenedor = tk.Frame(self, bg="white")
        self.contenedor.pack(fill="both", expand=True)

        # Botón agregar fila
        tk.Button(
            self,
            text="+ Añadir demora",
            command=self.add_linea,
            bg="#D9EAD3",
            font=("Segoe UI", 10, "bold")
        ).pack(pady=5)

        # Botón guardar
        tk.Button(
            self,
            text="Guardar",
            command=self.guardar,
            bg="#9FC5E8",
            font=("Segoe UI", 11, "bold"),
            padx=12,
            pady=5
        ).pack(pady=10)

        # Primera línea por defecto
        self.add_linea()

    # ============================================================
    # AGREGAR UNA LÍNEA
    # ============================================================
    def add_linea(self):
        linea = LineaDemora(self.contenedor, self._remove_line)
        self.lineas.append(linea)

    def _remove_line(self, linea):
        if linea in self.lineas:
            self.lineas.remove(linea)

    # ============================================================
    # GUARDAR → CALCULAR Y ENVIAR AL API
    # ============================================================
    def guardar(self):
        total_d = total_h = total_m = 0

        for linea in self.lineas:
            f1, h1, f2, h2 = linea.get_values()

            # Validación
            if not f1 or not h1 or not f2 or not h2:
                messagebox.showerror("Error", "Todas las fechas y horas son obligatorias.")
                return

            try:
                d, h, m = calcular_diferencia(f1, h1, f2, h2)
            except Exception:
                messagebox.showerror("Error", "Revise que las fechas y horas sean válidas.")
                return

            total_d += d
            total_h += h
            total_m += m

        # Normalizar tiempo (días / horas / minutos)
        total_h += total_m // 60
        total_m = total_m % 60
        total_d += total_h // 24
        total_h = total_h % 24

        # ---------- AQUÍ VIENE EL CAMBIO IMPORTANTE ----------
        # Convertimos el total a MINUTOS para grabar un número en SQL
        total_min = total_d * 24 * 60 + total_h * 60 + total_m
        total_str = str(total_min)  # se envía como string "150" etc.
        # -----------------------------------------------------

        # Enviar al API
        from api_client import actualizar_demoras_api
        resp = actualizar_demoras_api(self.consec, total_str)

        # Debug opcional para ver qué devuelve la API en consola
        print("DEBUG demoras → respuesta API:", resp)

        if resp.get("status") == "ok":
            messagebox.showinfo("OK", "Demoras registradas correctamente.")
            self.on_success()
            self.destroy()
        else:
            # Mostrar cualquier detalle que venga del backend
            msg = resp.get("error") or resp.get("detail") or str(resp)
            messagebox.showerror("Error", msg)
