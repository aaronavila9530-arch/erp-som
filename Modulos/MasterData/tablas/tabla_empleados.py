import tkinter as tk
from tkinter import ttk, messagebox
import requests
from api_client import api_request

from Modulos.MasterData.tablas.base_table import BasePaginatedTable
from Modulos.MasterData.popups.popup_empleado import PopupEmpleado

BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"


class TablaEmpleadosUI(BasePaginatedTable):

    def __init__(self, parent, on_back):
        super().__init__(parent, title="Empleados", on_back=on_back)

        # Columnas alineadas 1:1 con SQL y con el JSON del router
        self.columns = [
            ("codigo", "Código"),
            ("nombre", "Nombre"),
            ("apellidos", "Apellidos"),
            ("estado_civil", "Estado Civil"),
            ("genero", "Género"),
            ("nacionalidad", "Nacionalidad"),
            ("prefijo", "Prefijo"),
            ("telefono", "Teléfono"),
            ("provincia", "Provincia"),
            ("canton", "Cantón"),
            ("distrito", "Distrito"),
            ("direccion", "Dirección"),
            ("jornada", "Jornada"),
            ("salario", "Salario"),
            ("horas_contratadas", "Horas Contratadas"),
            ("horas_tope_ordinario", "Primer Aviso"),
            ("horas_tope_maximo", "Segundo Aviso"),
            ("tarifa_hora_extra", "Tarifa H. Extra"),
            ("pago_minimo_garantizado", "Pago Mínimo"),
            ("pago", "Método Pago"),
            ("banco", "Banco"),
            ("cuenta_iban", "Cuenta IBAN"),
            ("moneda", "Moneda"),
            ("enfermedades", "Enfermedades"),
            ("contacto_emergencia", "Contacto Emergencia"),
            ("telefono_emergencia", "Tel. Emergencia"),
            ("activo1", "Activo 1"),
            ("marca1", "Marca 1"),
            ("serial1", "Serial 1"),
            ("activo2", "Activo 2"),
            ("marca2", "Marca 2"),
            ("serial2", "Serial 2"),
            ("activo3", "Activo 3"),
            ("marca3", "Marca 3"),
            ("serial3", "Serial 3"),
        ]

        self._configurar_columnas()
        self.refresh()

        # Eventos botones
        self.btn_ver.config(command=self.ver_registro)
        self.btn_editar.config(command=self.editar_registro)
        self.btn_eliminar.config(command=self.eliminar_registro)

    # ==========================================================
    # Configurar columnas de la tabla
    # ==========================================================
    def _configurar_columnas(self):
        # Solo los keys (para el Treeview)
        self.table["columns"] = [c[0] for c in self.columns]

        for col, texto in self.columns:
            self.table.heading(col, text=texto)
            self.table.column(col, width=140, stretch=True)

    # ==========================================================
    # Cargar datos desde API
    # ==========================================================
    def load_data(self):
        try:
            url = f"{BASE_URL}/empleados?page={self.page}&page_size={self.page_size}"
            r = api_request("GET", url, timeout=15)
            r.raise_for_status()  # ← si hay 500/404, lanza excepción clara
            data = r.json()

            self.total_items = data.get("total", 0)
            filas = data.get("data", [])

            total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
            self.lbl_page.config(text=f"Página {self.page} / {total_pages}")

            # Limpiar tabla
            self.table.delete(*self.table.get_children())

            # Insertar filas
            for row in filas:
                vals = [row.get(col, "") for col, _ in self.columns]
                self.table.insert("", "end", values=vals)

        except Exception as e:
            messagebox.showerror("Error API", str(e))

    # ==========================================================
    # Selección
    # ==========================================================
    def _get_codigo(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un registro")
            return None
        vals = self.table.item(sel)["values"]
        # Primer valor = código
        return vals[0] if vals else None

    # ==========================================================
    # VER
    # ==========================================================
    def ver_registro(self):
        codigo = self._get_codigo()
        if not codigo:
            return

        try:
            url = f"{BASE_URL}/empleados/{codigo}"
            r = api_request("GET", url, timeout=10)
            r.raise_for_status()
            data = r.json()
        except Exception:
            messagebox.showerror("Error", f"Empleado {codigo} no encontrado")
            return

        popup = tk.Toplevel(self)
        popup.title(f"Ver Empleado — {codigo}")
        popup.geometry("600x700")
        popup.configure(bg="white")
        popup.resizable(False, False)

        for i, (key, label) in enumerate(self.columns):
            tk.Label(popup, text=f"{label}:", bg="white").grid(
                row=i, column=0, padx=10, pady=4, sticky="e"
            )
            entry = tk.Entry(popup, width=45, bg="#F2F2F2", relief="flat")
            entry.grid(row=i, column=1, padx=10, pady=4, sticky="w")
            entry.insert(0, data.get(key, ""))
            entry.config(state="readonly", readonlybackground="#F2F2F2")

    # ==========================================================
    # EDITAR
    # ==========================================================
    def editar_registro(self):
        codigo = self._get_codigo()
        if not codigo:
            return

        try:
            url = f"{BASE_URL}/empleados/{codigo}"
            r = api_request("GET", url, timeout=15)
            r.raise_for_status()
            data = r.json()
        except Exception:
            messagebox.showerror("Error", f"Empleado {codigo} no encontrado")
            return

        popup = PopupEmpleado(self, codigo=codigo, on_save=self._guardar_edicion)

        # Cargar valores en el popup
        for col, _ in self.columns:
            if hasattr(popup, col):
                value = data.get(col, "")
                if col == "pago_minimo_garantizado":
                    value = str(value or "").strip().lower() in {"1", "true", "t", "yes", "si", "sí", "y"}
                getattr(popup, col).set(value)
            else:
                try:
                    getattr(popup, f"entry_{col}").delete(0, tk.END)
                    getattr(popup, f"entry_{col}").insert(0, data.get(col, ""))
                except Exception:
                    pass

    # ==========================================================
    # GUARDAR EDICIÓN
    # ==========================================================
    def _guardar_edicion(self, data):
        try:
            url = f"{BASE_URL}/empleados/update"
            r = api_request("PUT", url, json=data, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Empleado actualizado ✔")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))

    # ==========================================================
    # ELIMINAR
    # ==========================================================
    def eliminar_registro(self):
        codigo = self._get_codigo()
        if not codigo:
            return

        if not messagebox.askyesno("Confirmar", f"¿Eliminar al empleado {codigo}?"):
            return

        try:
            url = f"{BASE_URL}/empleados/{codigo}"
            r = api_request("DELETE", url, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Empleado eliminado")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))
