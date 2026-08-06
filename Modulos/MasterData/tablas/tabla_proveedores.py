import tkinter as tk
from tkinter import messagebox
from api_client import api_request
from session_context import get_company_code

from Modulos.MasterData.tablas.base_table import BasePaginatedTable
from Modulos.MasterData.popups.popup_proveedor import PopupProveedor


BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app"


def _company_prefix():
    return (get_company_code() or "MSL-CR").split("-")[0].strip().upper() or "MSL"


class TablaProveedoresUI(BasePaginatedTable):

    def __init__(self, parent, on_back):
        super().__init__(parent, title="Proveedores", on_back=on_back)

        # Definir columnas
        self.columns = [
            ("Codigo", "Código"),
            ("Nombre", "Nombre"),
            ("Apellidos", "Apellidos"),
            ("NombreComercial", "Nombre Comercial"),
            ("Cedula", "Cédula / VAT"),
            ("Pais", "País"),
            ("Provincia", "Provincia"),
            ("Canton", "Cantón"),
            ("Distrito", "Distrito"),
            ("DireccionExacta", "Dirección Exacta"),
            ("Prefijo", "Prefijo"),
            ("Telefono", "Teléfono"),
            ("Correo", "Correo"),
            ("TerminosPago", "Términos Pago"),
            ("Banco", "Banco"),
            ("CuentaIBAN", "IBAN"),
            ("SwiftCode", "Swift Code"),
            ("UID", "UID"),
            ("DireccionBanco", "Dirección Banco"),
            ("TipoProveeduria", "Tipo Proveeduría"),
            ("Comentarios", "Comentarios"),
        ]

        self._configurar_columnas()
        self.refresh()

        self.btn_ver.config(command=self.ver_registro)
        self.btn_editar.config(command=self.editar_registro)
        self.btn_eliminar.config(command=self.eliminar_registro)

    # ======================================================
    # Configurar columnas en tabla SAP
    # ======================================================
    def _configurar_columnas(self):
        self.table["columns"] = [c[0] for c in self.columns]
        for col, texto in self.columns:
            self.table.heading(col, text=texto)
            self.table.column(col, width=170, stretch=True)

    # ======================================================
    # Cargar datos paginados desde API
    # ======================================================
    def load_data(self):
        try:
            url = f"{BASE_URL}/proveedores?page={self.page}&page_size={self.page_size}"
            r = api_request("GET", url, timeout=15)
            data = r.json()

            self.total_items = data.get("total", 0)
            filas = data.get("data", [])

            # UI estado de paginación
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

    # ======================================================
    # Obtener selección
    # ======================================================
    def _get_codigo_seleccionado(self):
        sel = self.table.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un registro primero")
            return None
        return self.table.item(sel)["values"][0]


    # ======================================================
    # AGREGAR NUEVO PROVEEDOR (Popup con código incremental)
    # ======================================================
    def agregar_registro(self):
        from api_client import get_ultimo_codigo_proveedor

        # Obtener último consecutivo desde API
        try:
            ultimo = get_ultimo_codigo_proveedor()
        except Exception as e:
            print("❌ Error obteniendo consecutivo proveedor:", e)
            ultimo = 0

        # Crear el nuevo consecutivo
        nuevo_num = ultimo + 1
        codigo = f"{_company_prefix()}-{nuevo_num:04d}-P"

        # Abrir popup
        popup = PopupProveedor(self, codigo, self._guardar_nuevo)
        popup.title(f"Nuevo Proveedor — {codigo}")
        popup.grab_set()


    # ======================================================
    # VER — Popup solo lectura
    # ======================================================
    def ver_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo: return

        try:
            r = api_request("GET", f"{BASE_URL}/proveedores/{codigo}", timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Proveedor {codigo} no encontrado")
            return

        data = r.json()

        popup = tk.Toplevel(self)
        popup.title(f"Proveedor — {codigo}")
        popup.geometry("520x600")
        popup.configure(bg="white")
        popup.resizable(False, False)

        for i, (key, label) in enumerate(self.columns):
            tk.Label(popup, text=f"{label}:", bg="white").grid(row=i, column=0, padx=8, pady=4, sticky="e")
            entry = tk.Entry(popup, width=45, relief="flat", bg="#F2F2F2")
            entry.grid(row=i, column=1, padx=8, pady=4, sticky="w")
            entry.insert(0, data.get(key, ""))
            entry.config(state="readonly")

    # ==========================================================
    # EDITAR Registro - Rellena Popup con datos del API
    # ==========================================================
    def editar_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo:
            return

        # GET API
        url = f"{BASE_URL}/proveedores/{codigo}"
        try:
            r = api_request("GET", url, timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Proveedor {codigo} no encontrado")
            return

        data = r.json()

        # Abrir popup EXACTAMENTE igual que servicios
        popup = PopupProveedor(self, codigo, self._guardar_edicion)
        popup.title(f"Editar Proveedor — {codigo}")

        # Rellenar campos
        popup.Nombre.set(data.get("Nombre", ""))
        popup.Apellidos.set(data.get("Apellidos", ""))
        popup.NombreComercial.set(data.get("NombreComercial", ""))
        popup.Cedula.set(data.get("Cedula", ""))
        popup.Pais.set(data.get("Pais", ""))
        popup.Provincia.set(data.get("Provincia", ""))
        popup.Canton.set(data.get("Canton", ""))
        popup.Distrito.set(data.get("Distrito", ""))
        popup.DireccionExacta.set(data.get("DireccionExacta", ""))
        popup.Prefijo.set(data.get("Prefijo", ""))
        popup.Telefono.set(data.get("Telefono", ""))
        popup.Correo.set(data.get("Correo", ""))
        popup.TerminosPago.set(data.get("TerminosPago", ""))
        popup.Banco.set(data.get("Banco", ""))
        popup.CuentaIBAN.set(data.get("CuentaIBAN", ""))
        popup.SwiftCode.set(data.get("SwiftCode", ""))
        popup.UID.set(data.get("UID", ""))
        popup.DireccionBanco.set(data.get("DireccionBanco", ""))
        popup.TipoProveeduria.set(data.get("TipoProveeduria", ""))
        popup.Comentarios.set(data.get("Comentarios", ""))


    # ======================================================
    # Guardar actualización en API
    # ======================================================
    def _guardar_edicion(self, data):
        try:
            url = f"{BASE_URL}/proveedores/update"
            r = api_request("PUT", url, json=data, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Proveedor actualizado correctamente")
                self.refresh()  # refrescar tabla luego de guardar
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))


    # ======================================================
    # ELIMINAR
    # ======================================================
    def eliminar_registro(self):
        codigo = self._get_codigo_seleccionado()
        if not codigo: return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar proveedor {codigo}?"):
            return

        try:
            url = f"{BASE_URL}/proveedores/{codigo}"
            r = api_request("DELETE", url, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Proveedor eliminado")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))
