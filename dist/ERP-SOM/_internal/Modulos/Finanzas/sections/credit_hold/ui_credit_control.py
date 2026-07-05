import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL
from Modulos.Finanzas.sections.credit_hold.PopupEditarCreditoCliente import PopupEditarCreditoCliente
from Modulos.Finanzas.sections.credit_hold.ui_credit_control_popup import CreditControlPopup




class CreditControlUI(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg="white")

        self.selected_cliente = tk.StringVar()
        self.termino_pago = tk.StringVar()
        self.limite_credito = tk.StringVar()
        self.moneda = tk.StringVar()
        self.estado = tk.StringVar()

        # -------- NUEVO (EXPOSICIÓN) --------
        self.total_facturado = tk.StringVar()
        self.disponible = tk.StringVar()
        self.exposicion = tk.StringVar()
        self.avg_days = tk.StringVar()
        self.payment_trend = tk.StringVar()

        self.modo = "view"
        self.clientes_loaded = False

        self._build_ui()
        self._set_form_state("disabled")

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):
        ttk.Label(
            self,
            text="Credit Control",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", padx=20, pady=10)

        # -------- CLIENTE + BUSCAR --------
        top = tk.Frame(self, bg="white")
        top.pack(fill="x", padx=20)

        ttk.Label(top, text="Cliente:", width=15).pack(side="left")

        self.cbo_cliente = ttk.Combobox(
            top,
            textvariable=self.selected_cliente,
            state="readonly",
            width=40
        )
        self.cbo_cliente.pack(side="left", padx=5)
        self.cbo_cliente.bind("<Button-1>", self._load_clientes)

        ttk.Button(
            top,
            text="Buscar",
            command=self._buscar_cliente
        ).pack(side="left", padx=10)

        # -------- FORM CREDIT --------
        form = tk.Frame(self, bg="white")
        form.pack(fill="x", padx=20, pady=15)

        self._field(form, "Término de pago:", self.termino_pago, 0)
        self._field(form, "Límite de crédito:", self.limite_credito, 1)
        self._field(form, "Moneda:", self.moneda, 2)
        self._field(form, "Estado:", self.estado, 3)

        ttk.Label(form, text="Observaciones:").grid(
            row=4, column=0, sticky="nw", pady=5
        )

        self.txt_obs = tk.Text(form, height=4, width=50)
        self.txt_obs.grid(row=4, column=1, pady=5, sticky="w")

        # -------- NUEVO: EXPOSICIÓN CREDITICIA --------
        exposure = ttk.LabelFrame(
            self,
            text="Exposición Crediticia",
            padding=10
        )
        exposure.pack(fill="x", padx=20, pady=10)

        self._info_field(exposure, "Total facturado:", self.total_facturado, 0)
        self._info_field(exposure, "Disponible:", self.disponible, 1)
        self._info_field(exposure, "Exposición:", self.exposicion, 2)
        self._info_field(exposure, "Avg días de pago:", self.avg_days, 3)
        self._info_field(exposure, "Payment trend:", self.payment_trend, 4)

        self.lbl_semaforo = tk.Label(
            exposure,
            text="",
            width=20,
            font=("Segoe UI", 10, "bold")
        )
        self.lbl_semaforo.grid(row=0, column=2, rowspan=3, padx=20)

        # -------- ACTIONS --------
        actions = tk.Frame(self, bg="white")
        actions.pack(fill="x", padx=20, pady=10)

        self.btn_edit = ttk.Button(
            actions,
            text="Editar",
            command=self._editar
        )
        self.btn_edit.pack(side="left")

        self.btn_delete = ttk.Button(
            actions,
            text="Eliminar",
            command=self._eliminar
        )
        self.btn_delete.pack(side="left", padx=10)

        self.btn_edit["state"] = "disabled"
        self.btn_delete["state"] = "disabled"

    def _field(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=5
        )
        ttk.Entry(parent, textvariable=variable, width=30).grid(
            row=row, column=1, sticky="w", pady=5
        )

    def _info_field(self, parent, label, variable, row):
        ttk.Label(parent, text=label).grid(
            row=row, column=0, sticky="w", pady=3
        )
        ttk.Label(parent, textvariable=variable).grid(
            row=row, column=1, sticky="w", pady=3
        )

    # ============================================================
    # DATA
    # ============================================================
    def _load_clientes(self, *_):
        if self.clientes_loaded:
            return
        try:
            r = requests.get(f"{BASE_URL}/clientes", timeout=15)
            r.raise_for_status()
            data = r.json().get("data", [])

            values = [
                f"{c['codigo']} - {c.get('nombrecomercial') or c.get('nombrejuridico')}"
                for c in data
            ]

            self.cbo_cliente["values"] = values
            self.clientes_loaded = True

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _buscar_cliente(self):
        if not self.selected_cliente.get():
            messagebox.showwarning("Atención", "Seleccione un cliente")
            return

        codigo = self.selected_cliente.get().split(" - ")[0]

        # -------- CREDIT CONFIG --------
        try:
            r = requests.get(
                f"{BASE_URL}/cliente-credito/{codigo}",
                timeout=15
            )
            r.raise_for_status()
            resp = r.json()

            self._clear_form()

            if not resp.get("exists"):
                messagebox.showinfo(
                    "Información",
                    "Este cliente no tiene términos crediticios asignados."
                )
                CreditControlPopup(self, codigo, on_save=self._buscar_cliente)
                return

            data = resp["data"]

            self.termino_pago.set(data.get("termino_pago", ""))
            self.limite_credito.set(data.get("limite_credito", ""))
            self.moneda.set(data.get("moneda", ""))
            self.estado.set(data.get("estado", "ACTIVE"))
            self.txt_obs.insert("1.0", data.get("observaciones") or "")

            self.btn_edit["state"] = "normal"
            self.btn_delete["state"] = "normal"
            self._set_form_state("disabled")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        # -------- NUEVO: CREDIT EXPOSURE --------
        try:
            r = requests.get(
                f"{BASE_URL}/cliente-credito/exposure/{codigo}",
                timeout=15
            )
            r.raise_for_status()
            exp = r.json()

            self.total_facturado.set(exp["total_facturado"])
            self.disponible.set(exp["disponible"])
            self.exposicion.set(exp["exposicion"])

            trend = exp["payment_trend"]
            self.avg_days.set(trend.get("avg_days_to_pay"))
            self.payment_trend.set(trend.get("trend"))

            # -------- SEMÁFORO --------
            sem = exp["semaforo"]

            if sem == "VERDE":
                self.lbl_semaforo.config(
                    text="🟢 DISPONIBLE",
                    bg="#d4edda",
                    fg="#155724"
                )
            elif sem == "AMARILLO":
                self.lbl_semaforo.config(
                    text="🟡 CRÍTICO",
                    bg="#fff3cd",
                    fg="#856404"
                )
            else:
                self.lbl_semaforo.config(
                    text="🔴 SOBREGIRADO",
                    bg="#f8d7da",
                    fg="#721c24"
                )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo calcular exposición crediticia:\n{e}"
            )

    # ============================================================
    # ACTIONS
    # ============================================================
    def _editar(self):

        if not self.selected_cliente.get():
            messagebox.showwarning(
                "Atención",
                "Debe seleccionar un cliente primero"
            )
            return

        codigo_cliente = self.selected_cliente.get().split(" - ")[0]

        PopupEditarCreditoCliente(
            parent=self,
            codigo_cliente=codigo_cliente,
            on_save=self._buscar_cliente
        )

    def _guardar_edicion(self):
        codigo = self.selected_cliente.get().split(" - ")[0]

        payload = {
            "termino_pago": int(self.termino_pago.get()),
            "limite_credito": float(self.limite_credito.get() or 0),
            "estado_credito": self.estado.get(),
            "observaciones": self.txt_obs.get("1.0", "end").strip()
        }

        try:
            r = requests.put(
                f"{BASE_URL}/cliente-credito/{codigo}",
                json=payload,
                timeout=15
            )
            r.raise_for_status()

            messagebox.showinfo(
                "Éxito",
                "Configuración crediticia actualizada correctamente"
            )

            self.btn_save.destroy()
            self.modo = "view"
            self._set_form_state("disabled")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _eliminar(self):
        codigo = self.selected_cliente.get().split(" - ")[0]

        if not messagebox.askyesno(
            "Confirmar",
            "¿Eliminar configuración crediticia de este cliente?"
        ):
            return

        try:
            r = requests.delete(
                f"{BASE_URL}/cliente-credito/{codigo}",
                timeout=15
            )
            r.raise_for_status()

            messagebox.showinfo("OK", "Configuración eliminada")
            self._clear_form()
            self.btn_edit["state"] = "disabled"
            self.btn_delete["state"] = "disabled"

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ============================================================
    # UTIL
    # ============================================================
    def _clear_form(self):
        self.termino_pago.set("")
        self.limite_credito.set("")
        self.moneda.set("")
        self.estado.set("")
        self.total_facturado.set("")
        self.disponible.set("")
        self.exposicion.set("")
        self.avg_days.set("")
        self.payment_trend.set("")
        self.lbl_semaforo.config(text="", bg="white")
        self.txt_obs.delete("1.0", "end")

    def _set_form_state(self, state):
        for child in self.winfo_children():
            if isinstance(child, ttk.Entry):
                child["state"] = state
        self.txt_obs["state"] = state
