import tkinter as tk
from tkinter import ttk, messagebox
import requests

from Modulos.MasterData.tablas.base_table import BasePaginatedTable
from Modulos.MasterData.popups.popup_servicio import PopupServicio

BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"


class TablaServiciosUI(BasePaginatedTable):

    def __init__(self, parent, on_back):
        super().__init__(parent, title="Servicios", on_back=on_back)

        # Definir columnas exactas
        self.columns = [
            ("codigo", "Código"),
            ("codigo_prod", "Código Producto"),
            ("nombre", "Nombre del Servicio"),
            ("costo", "Costo"),
        ]

        self._configurar_columnas()
        self.refresh()  # Cargar página 1

        # Acciones
        self.btn_ver.config(command=self.ver_registro)
        self.btn_editar.config(command=self.editar_registro)
        self.btn_eliminar.config(command=self.eliminar_registro)

    # ==========================================================
    # Configurar columnas
    # ==========================================================
    def _configurar_columnas(self):
        # Borrar columnas previas
        self.table["columns"] = [c[0] for c in self.columns]

        for col, texto in self.columns:
            self.table.heading(col, text=texto)
            self.table.column(col, width=150, stretch=True)

    # ==========================================================
    # Carga datos del API
    # ==========================================================
    def load_data(self):
        try:
            url = f"{BASE_URL}/servicios_md?page={self.page}&page_size={self.page_size}"
            r = requests.get(url, timeout=15)
            data = r.json()

            self.total_items = data.get("total", 0)
            filas = data.get("data", [])

            # Update label page
            total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
            self.lbl_page.config(text=f"Página {self.page} / {total_pages}")

            # Limpiar tabla
            for item in self.table.get_children():
                self.table.delete(item)

            # Insertar filas
            for row in filas:
                vals = [row.get(col, "") for col, _ in self.columns]
                self.table.insert("", "end", values=vals)

        except Exception as e:
            messagebox.showerror("Error API", str(e))

    # ==========================================================
    # Helpers para obtener código seleccionado
    # ==========================================================
    def _get_codigo_seleccionado(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un registro primero")
            return None

        vals = self.table.item(sel)["values"]
        return vals[0]  # Código es la primera columna

    # =================== VER REGISTRO ======================
    def ver_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo:
            return

        # API GET
        try:
            url = f"{BASE_URL}/servicios_md/{codigo}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Servicio {codigo} no encontrado")
            return

        data = r.json()

        popup = tk.Toplevel(self)
        popup.title(f"Ver Servicio — {codigo}")
        popup.geometry("370x210")
        popup.configure(bg="white")
        popup.resizable(False, False)

        for i, (key, label) in enumerate(self.columns):
            tk.Label(popup, text=f"{label}:", bg="white").grid(
                row=i, column=0, padx=10, pady=6, sticky="e"
            )

            entry = tk.Entry(
                popup,
                width=30,
                relief="flat",
                bg="#F2F2F2"
            )
            entry.grid(row=i, column=1, padx=10, pady=6, sticky="w")
            entry.insert(0, data.get(key, ""))
            entry.config(
                state="readonly",
                readonlybackground="#F2F2F2",
                foreground="black"
            )

    # ==========================================================
    # EDITAR
    # ==========================================================
    def editar_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo: return

        try:
            # Obtener datos del API
            url = f"{BASE_URL}/servicios_md/{codigo}"
            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                messagebox.showerror("Error API", r.text)
                return

            data = r.json()

            # Crear popup de edición con datos precargados
            popup = PopupServicio(self, codigo=data["codigo"], on_save=self._guardar_edicion)
            popup.entry_codigo_prod.insert(0, data.get("codigo_prod", ""))
            popup.entry_nombre.insert(0, data.get("nombre", ""))
            popup.entry_costo.insert(0, data.get("costo", ""))

        except Exception as e:
            messagebox.showerror("Error API", str(e))

    def _guardar_edicion(self, data):
        try:
            url = f"{BASE_URL}/servicios_md/update"
            r = requests.put(url, json=data, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Servicio actualizado correctamente")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))

    # ==========================================================
    # ELIMINAR
    # ==========================================================
    def eliminar_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo: return

        if not messagebox.askyesno("Confirmar", f"¿Eliminar el servicio {codigo}?"):
            return

        try:
            url = f"{BASE_URL}/servicios_md/{codigo}"
            r = requests.delete(url, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Servicio eliminado")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))
