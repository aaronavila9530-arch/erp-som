import tkinter as tk
from tkinter import ttk, messagebox
import requests
from api_client import api_request

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
            ("email", "Email"),
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
            ("direccion_banco", "Dirección Banco"),
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
            r = api_request("GET", url, timeout=15)
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
            r = api_request("GET", url, timeout=10)
            r.raise_for_status()
        except:
            messagebox.showerror("Error", f"Surveyor {codigo} no encontrado")
            return

        data = r.json()

        popup = PopupSurveyor(
            self,
            codigo=codigo,
            lista_operaciones=[],
            lista_puertos=[]
        )

        popup.title(f"Ver Surveyor — {codigo}")

        # 🔹 Cargar datos
        popup.nombre.set(data.get("nombre", ""))
        popup.apellidos.set(data.get("apellidos", ""))
        popup.email.set(data.get("email", ""))
        popup.estado_civil.set(data.get("estado_civil", ""))
        popup.genero.set(data.get("genero", ""))
        popup.nacionalidad.set(data.get("nacionalidad", ""))

        popup.prefijo.set(data.get("prefijo", ""))
        popup.telefono.set(data.get("telefono", ""))
        popup.provincia.set(data.get("provincia", ""))
        popup.canton.set(data.get("canton", ""))
        popup.distrito.set(data.get("distrito", ""))
        popup.direccion.set(data.get("direccion", ""))

        popup.jornada.set(data.get("jornada", ""))
        popup.operacion.set(data.get("operacion", ""))
        popup.honorario.set(data.get("honorario", ""))
        popup.frecuencia_pago.set(data.get("pago", ""))
        popup.banco.set(data.get("banco", ""))
        popup.direccion_banco.set(data.get("direccion_banco", ""))
        popup.cuenta_iban.set(data.get("cuenta_iban", ""))
        popup.moneda.set(data.get("moneda", ""))
        popup.swift.set(data.get("swift", ""))
        popup.uid.set(data.get("uid", ""))

        popup.enfermedades.set(data.get("enfermedades", ""))
        popup.contacto_emergencia.set(data.get("contacto_emergencia", ""))
        popup.telefono_emergencia.set(data.get("telefono_emergencia", ""))
        popup.puerto.set(data.get("puerto", ""))
        popup.set_tarifas(data.get("tarifas", []))

        # 🔹 Deshabilitar todo (modo solo lectura)
        self._disable_widgets_recursive(popup)


    # ==========================================================
    # EDITAR
    # ==========================================================
    def editar_registro(self):
        codigo = self._get_codigo()
        if not codigo:
            return
        try:
            url = f"{BASE_URL}/surveyores/{codigo}"
            r = api_request("GET", url, timeout=10)
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
        popup.set_tarifas(data.get("tarifas", []))

    # ==========================================================
    # GUARDAR EDICIÓN
    # ==========================================================
    def _guardar_edicion(self, data):
        try:
            url = f"{BASE_URL}/surveyores/update"
            r = api_request("PUT", url, json=data, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Surveyor actualizado correctamente")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))


    def _disable_widgets_recursive(self, widget):
        for child in widget.winfo_children():
            try:
                child.configure(state="disabled")
            except:
                pass
            self._disable_widgets_recursive(child)

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
            r = api_request("DELETE", url, timeout=15)
            if r.status_code == 200:
                messagebox.showinfo("OK", "Surveyor eliminado")
                self.refresh()
            else:
                messagebox.showerror("Error API", r.text)
        except Exception as e:
            messagebox.showerror("Error API", str(e))
