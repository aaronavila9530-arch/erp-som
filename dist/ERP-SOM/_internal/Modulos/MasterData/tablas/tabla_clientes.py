import tkinter as tk
from tkinter import ttk, messagebox
import requests

from Modulos.MasterData.tablas.base_table import BasePaginatedTable
from Modulos.MasterData.popups.popup_cliente import PopupCliente
from Modulos.MasterData.date_utils import to_long_english_date

BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"



class TablaClientesUI(BasePaginatedTable):

    def __init__(self, parent, on_back):
        super().__init__(parent, title="Clientes", on_back=on_back)

        # Definir TODAS las columnas que vienen de API-SQL
        self.columns = [
            ("codigo",             "Código"),
            ("nombrejuridico",     "Nombre Jurídico"),
            ("nombrecomercial",    "Nombre Comercial"),
            ("pais",               "País"),
            ("correo",             "Correo"),
            ("telefono",           "Teléfono"),
            ("cedulajuridicavat",  "Cédula Jurídica / VAT"),
            ("actividad_economica","Actividad Económica"),
            ("comentarios",        "Comentarios"),
            ("provincia",          "Provincia"),
            ("canton",             "Cantón"),
            ("distrito",           "Distrito"),
            ("direccionexacta",    "Dirección Exacta"),
            ("fecha_pago",         "Fecha de Pago"),
            ("prefijo",            "Prefijo"),
            ("contacto_principal", "Contacto Principal"),
            ("contacto_secundario","Contacto Secundario"),
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
            url = f"{BASE_URL}/clientes?page={self.page}&page_size={self.page_size}"
            r = requests.get(url, timeout=15)
            data = r.json()

            self.total_items = data.get("total", 0)
            filas = data.get("data", [])

            total_pages = max(1, (self.total_items + self.page_size - 1) // self.page_size)
            self.lbl_page.config(text=f"Página {self.page} / {total_pages}")

            for item in self.table.get_children():
                self.table.delete(item)

            for row in filas:
                vals = [
                    to_long_english_date(row.get(col, "")) if col == "fecha_pago" else row.get(col, "")
                    for col, _ in self.columns
                ]
                self.table.insert("", "end", values=vals)

        except Exception as e:
            messagebox.showerror("Error API", str(e))

    # ==========================================================
    # Helper para obtener código
    # ==========================================================
    def _get_codigo_seleccionado(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un registro")
            return None

        vals = self.table.item(sel)["values"]
        return vals[0]

    # =================== VER REGISTRO ======================
    def ver_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo: return

        try:
            url = f"{BASE_URL}/clientes/{codigo}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Cliente {codigo} no encontrado")
            return

        data = r.json()

        popup = tk.Toplevel(self)
        popup.title(f"Ver Cliente — {codigo}")
        popup.geometry("400x300")
        popup.configure(bg="white")
        popup.resizable(False, False)

        for i, (key, label) in enumerate(self.columns):
            tk.Label(popup, text=f"{label}:", bg="white").grid(
                row=i, column=0, padx=10, pady=6, sticky="e"
            )

            entry = tk.Entry(popup, width=35, relief="flat", bg="#F2F2F2")
            entry.grid(row=i, column=1, padx=10, pady=6, sticky="w")
            value = to_long_english_date(data.get(key, "")) if key == "fecha_pago" else data.get(key, "")
            entry.insert(0, value)
            entry.config(state="readonly",
                        readonlybackground="#F2F2F2",
                        foreground="black")

    # =================== EDITAR ============================
    def editar_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo:
            return

        try:
            url = f"{BASE_URL}/clientes/{codigo}"
            r = requests.get(url, timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Cliente {codigo} no encontrado")
            return

        data = r.json()

        popup = PopupCliente(self, codigo=codigo, on_save=self._guardar_edicion)

        # CAMBIAMOS todos a minúsculas (igual que en row.get de load_data)
        popup.NombreJuridico.set(data.get("nombrejuridico", ""))
        popup.NombreComercial.set(data.get("nombrecomercial", ""))
        popup.Pais.set(data.get("pais", ""))
        popup.CedulaJuridicaVAT.set(data.get("cedulajuridicavat", ""))
        popup.Provincia.set(data.get("provincia", ""))
        popup.Canton.set(data.get("canton", ""))
        popup.Distrito.set(data.get("distrito", ""))
        popup.DireccionExacta.set(data.get("direccionexacta", ""))
        popup.FechaDePago.set(to_long_english_date(data.get("fecha_pago", "")))
        popup.Correo.set(data.get("correo", ""))
        popup.Prefijo.set(data.get("prefijo", ""))
        popup.Telefono.set(data.get("telefono", ""))
        popup.ContactoPrincipal.set(data.get("contacto_principal", ""))
        popup.ContactoSecundario.set(data.get("contacto_secundario", ""))
        popup.Comentarios.set(data.get("comentarios", ""))

    # =================== GUARDAR EDICIÓN ===================
    def _guardar_edicion(self, data):
        try:
            url = f"{BASE_URL}/clientes/update"
            r = requests.put(url, json=data, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Cliente actualizado correctamente")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))

    # =================== ELIMINAR ==========================
    def eliminar_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo: return

        if not messagebox.askyesno("Confirmar", f"¿Eliminar el cliente {codigo}?"):
            return

        try:
            url = f"{BASE_URL}/clientes/{codigo}"
            r = requests.delete(url, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Cliente eliminado")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))
