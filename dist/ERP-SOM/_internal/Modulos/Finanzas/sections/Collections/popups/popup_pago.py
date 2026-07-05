import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from Modulos.Finanzas.date_utils import LONG_DATE_FORMAT, to_db_date, to_long_english_date
from Modulos.Servicios.widgets.date_picker import DatePicker
from api_client import (
    aplicar_pago_api,
    aplicar_nota_credito_api,
    api_request,
    BASE_URL
)


class PopupPago(tk.Toplevel):

    def __init__(self, parent, row_data, on_success=None):
        super().__init__(parent)

        self.row = row_data
        self.on_success = on_success
        self.notas_credito = []

        # ----------------- SALDOS -----------------
        self.total = self._to_float(self.row[10])
        self.saldo = self._calcular_saldo()

        self.title("Aplicar Pago / Nota de Crédito")
        self.geometry("540x620")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # ============================================================
    # HELPERS
    # ============================================================
    def _to_float(self, val):
        try:
            if val in (None, "", "None"):
                return 0.0
            return float(val)
        except Exception:
            return 0.0

    def _calcular_saldo(self):
        saldo_raw = self.row[11]
        saldo = self._to_float(saldo_raw)
        return saldo if saldo > 0 else self.total

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        container = tk.Frame(self)
        container.pack(fill="both", expand=True)

        # ================= HEADER =================
        tk.Label(
            container,
            text="Aplicar Pago / Nota de Crédito",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # ================= INFO FACTURA =================
        info = tk.LabelFrame(container, text="Factura")
        info.pack(fill="x", padx=15, pady=5)

        def info_row(lbl, val):
            r = tk.Frame(info)
            r.pack(fill="x", padx=8, pady=2)
            tk.Label(r, text=lbl, width=22, anchor="w").pack(side="left")
            tk.Label(r, text=val, anchor="w").pack(side="left")

        info_row("N° Factura:", self.row[4])
        info_row("Cliente:", self.row[1])
        info_row("Moneda:", self.row[9])
        info_row("Monto factura:", f"{self.total:.2f}")
        info_row("Saldo pendiente:", f"{self.saldo:.2f}")

        # ================= FORM =================
        form = tk.LabelFrame(container, text="Detalle de la Aplicación")
        form.pack(fill="x", padx=15, pady=10)

        tk.Label(form, text="Tipo de aplicación").pack(anchor="w", padx=8)

        self.tipo = tk.StringVar(value="PAGO")
        cbo_tipo = ttk.Combobox(
            form,
            textvariable=self.tipo,
            values=["PAGO", "NOTA_CREDITO"],
            state="readonly"
        )
        cbo_tipo.pack(fill="x", padx=8, pady=5)
        cbo_tipo.bind("<<ComboboxSelected>>", self._on_tipo_change)

        # ================= FRAME PAGO =================
        self.frm_pago = tk.Frame(form)

        tk.Label(self.frm_pago, text="Banco").pack(anchor="w", padx=8)
        self.banco = ttk.Entry(self.frm_pago)
        self.banco.pack(fill="x", padx=8, pady=5)

        tk.Label(self.frm_pago, text="Fecha de pago").pack(anchor="w", padx=8)
        fecha_row = tk.Frame(self.frm_pago)
        fecha_row.pack(fill="x", padx=8, pady=5)
        self.fecha_pago = ttk.Entry(fecha_row)
        self.fecha_pago.insert(0, to_long_english_date(date.today()))
        self.fecha_pago.pack(side="left", fill="x", expand=True)
        ttk.Button(
            fecha_row,
            text="📅",
            width=3,
            command=lambda: DatePicker(self, self.fecha_pago, output_format=LONG_DATE_FORMAT)
        ).pack(side="left", padx=(5, 0))

        tk.Label(self.frm_pago, text="Comisión").pack(anchor="w", padx=8)
        self.comision = ttk.Entry(self.frm_pago)
        self.comision.insert(0, "0")
        self.comision.pack(fill="x", padx=8, pady=5)

        tk.Label(self.frm_pago, text="Referencia").pack(anchor="w", padx=8)
        self.referencia = ttk.Entry(self.frm_pago)
        self.referencia.pack(fill="x", padx=8, pady=5)

        tk.Label(self.frm_pago, text="Monto a aplicar").pack(anchor="w", padx=8)
        self.monto = ttk.Entry(self.frm_pago)
        self.monto.pack(fill="x", padx=8, pady=5)

        self.frm_pago.pack(fill="x")

        # ================= FRAME NC =================
        self.frm_nc = tk.Frame(form)

        tk.Label(self.frm_nc, text="Nota de Crédito disponible").pack(anchor="w", padx=8)

        self.nc_var = tk.StringVar()
        self.cbo_nc = ttk.Combobox(
            self.frm_nc,
            textvariable=self.nc_var,
            state="readonly"
        )
        self.cbo_nc.pack(fill="x", padx=8, pady=5)

        # ================= ACTIONS =================
        actions = tk.Frame(container)
        actions.pack(fill="x", padx=15, pady=15)

        ttk.Button(actions, text="Cancelar", command=self.destroy).pack(side="right", padx=5)
        ttk.Button(actions, text="Aplicar", command=self._confirmar).pack(side="right")

    # ============================================================
    # EVENTS
    # ============================================================
    def _on_tipo_change(self, *_):

        if self.tipo.get() == "NOTA_CREDITO":
            self.frm_pago.pack_forget()
            self.frm_nc.pack(fill="x")
            self._cargar_notas_credito()
        else:
            self.frm_nc.pack_forget()
            self.frm_pago.pack(fill="x")

    def _cargar_notas_credito(self):

        try:
            r = api_request(
                "GET",
                f"{BASE_URL}/collections/search",
                params={
                    "cliente": str(self.row[0]).strip(),
                    "tipo_documento": "NOTA_CREDITO",
                    "estado_factura": "PENDIENTE_PAGO"
                },
                timeout=15
            )
            r.raise_for_status()

            data = r.json().get("data", [])

            self.notas_credito = data

            self.cbo_nc["values"] = [
                f'{d["numero_documento"]} | {float(d["total"]):.2f}'
                for d in self.notas_credito
            ]

            if self.cbo_nc["values"]:
                self.nc_var.set(self.cbo_nc["values"][0])

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudieron cargar las Notas de Crédito\n\n{e}"
            )

    # ============================================================
    # CONFIRMAR
    # ============================================================
    def _confirmar(self):

        try:
            numero_factura = str(self.row[4]).strip()
            codigo_cliente = str(self.row[0]).strip()
            nombre_cliente = str(self.row[1]).strip()

            # ====================================================
            # 🔥 VALIDAR SALDO REAL DESDE BACKEND (NO TREEVIEW)
            # ====================================================
            r = api_request(
                "GET",
                f"{BASE_URL}/collections/search",
                params={
                    "cliente": codigo_cliente,
                    "page": 1,
                    "page_size": 200
                },
                timeout=15
            )
            r.raise_for_status()

            data = r.json().get("data", []) or []

            factura_actual = next(
                (
                    f for f in data
                    if str(f.get("numero_documento")).strip().lstrip("0")
                    == numero_factura.lstrip("0")
                ),
                None
            )

            if not factura_actual:
                raise ValueError("Factura no encontrada")

            saldo_real = float(factura_actual.get("saldo_pendiente") or 0)

            if saldo_real <= 0:
                raise ValueError("La factura no tiene saldo pendiente")

            # Actualizamos saldo interno con valor real
            self.saldo = saldo_real

            # ===================== PAGO =====================
            if self.tipo.get() == "PAGO":

                try:
                    monto = float(self.monto.get())
                except Exception:
                    raise ValueError("Monto inválido")

                try:
                    comision = float(self.comision.get())
                except Exception:
                    comision = 0.0

                if monto <= 0:
                    raise ValueError("El monto debe ser mayor a cero")

                if monto > self.saldo:
                    raise ValueError("El monto excede el saldo pendiente")

                payload = {
                    "numero_documento": numero_factura,
                    "codigo_cliente": codigo_cliente,
                    "nombre_cliente": nombre_cliente,
                    "banco": self.banco.get().strip(),
                    "fecha_pago": to_db_date(self.fecha_pago.get().strip()),
                    "comision": comision,
                    "referencia": self.referencia.get().strip(),
                    "monto_pagado": monto,
                    "tipo_aplicacion": "PAGO"
                }

                aplicar_pago_api(payload)

            # ===================== NOTA DE CRÉDITO =====================
            else:

                if not self.nc_var.get():
                    raise ValueError("Seleccione una Nota de Crédito")

                idx = self.cbo_nc.current()
                if idx < 0:
                    raise ValueError("Nota de Crédito inválida")

                nc = self.notas_credito[idx]

                payload = {
                    "factura_numero": numero_factura,
                    "nota_credito_numero": nc["numero_documento"],
                    "codigo_cliente": codigo_cliente,
                    "nombre_cliente": nombre_cliente
                }

                aplicar_nota_credito_api(payload)

            messagebox.showinfo(
                "OK",
                "Aplicación registrada correctamente"
            )

            if self.on_success:
                self.on_success()

            self.destroy()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo aplicar\n\n{e}"
            )
