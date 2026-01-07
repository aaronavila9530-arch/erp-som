import tkinter as tk
from tkinter import ttk, messagebox
import requests

from Modulos.MasterData.tablas.base_table import BasePaginatedTable
from Modulos.MasterData.popups.popup_surveyor import PopupSurveyor

BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"


class TablaSurveyoresUI(BasePaginatedTable):

    def __init__(self, parent, on_back):
        super().__init__(parent, title="Surveyores", on_back=on_back)

        # Columnas alineadas con API-SQL
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
            ("operacion", "Operación"),
            ("honorario", "Honorario"),
            ("pago", "Método Pago"),
            ("banco", "Banco"),
            ("cuenta_iban", "Cuenta IBAN"),
            ("moneda", "Moneda"),
            ("swift", "SWIFT"),
            ("uid", "UID"),
            ("enfermedades", "Enfermedades"),
            ("contacto_emergencia", "Contacto Emergencia"),
            ("telefono_emergencia", "Tel. Emergencia"),
            ("puerto", "Puerto"),
        ]

        self._configurar_columnas()
        self.refresh()

        # Acciones
        self.btn_ver.config(command=self.ver_registro)
        self.btn_editar.config(command=self.editar_registro)
        self.btn_eliminar.config(command=self.eliminar_registro)

    # ==========================================================
    # Configurar columnas
    # ==========================================================
    def _configurar_columnas(self):
        self.table["columns"] = [c[0] for c in self.columns]

        for col, texto in self.columns:
            self.table.heading(col, text=texto)
            self.table.column(col, width=150, stretch=True)

    # ==========================================================
    # Cargar datos desde API
    # ==========================================================
    def load_data(self):
        try:
            url = f"{BASE_URL}/surveyores?page={self.page}&page_size={self.page_size}"
            r = requests.get(url, timeout=15)
            data = r.json()

            self.total_items = data.get("total", 0)
            filas = data.get("data", [])

            total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
            self.lbl_page.config(text=f"Página {self.page} / {total_pages}")

            self.table.delete(*self.table.get_children())

            for row in filas:
                vals = [row.get(col, "") for col, _ in self.columns]
                self.table.insert("", "end", values=vals)

        except Exception as e:
            messagebox.showerror("Error API", str(e))

    # ==========================================================
    # Helper para selección
    # ==========================================================
    def _get_codigo(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un registro")
            return None
        vals = self.table.item(sel)["values"]
        return vals[0]

    # ==========================================================
    # VER
    # ==========================================================
    def ver_registro(self):
        codigo = self._get_codigo()
        if not codigo:
            return
        try:
            url = f"{BASE_URL}/surveyores/{codigo}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Surveyor {codigo} no encontrado")
            return

        data = r.json()

        popup = tk.Toplevel(self)
        popup.title(f"Ver Surveyor — {codigo}")
        popup.geometry("550x650")
        popup.configure(bg="white")
        popup.resizable(False, False)

        for i, (key, label) in enumerate(self.columns):
            tk.Label(popup, text=f"{label}:", bg="white").grid(
                row=i, column=0, padx=10, pady=4, sticky="e"
            )

            entry = tk.Entry(popup, width=40, relief="flat", bg="#F2F2F2")
            entry.grid(row=i, column=1, padx=10, pady=4, sticky="w")
            entry.insert(0, data.get(key, ""))
            entry.config(state="readonly",
                         readonlybackground="#F2F2F2",
                         foreground="black")

    # ==========================================================
    # EDITAR
    # ==========================================================
    def editar_registro(self):
        codigo = self._get_codigo()
        if not codigo:
            return
        try:
            url = f"{BASE_URL}/surveyores/{codigo}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Surveyor {codigo} no encontrado")
            return

        data = r.json()

        popup = PopupSurveyor(self, codigo=codigo, on_save=self._guardar_edicion)

        # Cargar valores al popup
        for col, _ in self.columns:
            if hasattr(popup, col):
                # Si existiera StringVar:
                getattr(popup, col).set(data.get(col, ""))
            else:
                # Si existiera Entry:
                try:
                    getattr(popup, f"entry_{col}").insert(0, data.get(col, ""))
                except:
                    pass

    # ==========================================================
    # GUARDAR EDICIÓN
    # ==========================================================
    def _guardar_edicion(self, data):
        try:
            url = f"{BASE_URL}/surveyores/update"
            r = requests.put(url, json=data, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Surveyor actualizado correctamente")
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

        if not messagebox.askyesno("Confirmar", f"¿Eliminar el surveyor {codigo}?"):
            return
        try:
            url = f"{BASE_URL}/surveyores/{codigo}"
            r = requests.delete(url, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Surveyor eliminado")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))
