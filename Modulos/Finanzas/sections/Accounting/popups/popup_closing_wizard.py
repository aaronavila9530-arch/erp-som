import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import requests
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from tkinter import filedialog
from api_client import get_closing_period_status


from api_client import (
    post_close_period_api,
    post_closing_gl_preview_api,
    post_closing_gl_post_api,
    post_closing_tb_preview_api,
    post_closing_tb_post_api,
    post_closing_pnl_post_api,
    post_closing_fs_post_api,
    post_closing_fy_open_api,
)


class PopupClosingWizard(tk.Toplevel):
    """
    Wizard de Cierre Contable (SAP-like REAL)
    """

    def __init__(self, parent, company_code: str, ledger: str):
        super().__init__(parent)

        self.parent = parent
        self.company_code = company_code
        self.ledger = ledger

        self.fiscal_year = None
        self.period = None
        self.period_closed = False
        self.current_step = 0
        self.last_batch_id = None

        # =========================
        # PREVIEW EXPORT STATE
        # =========================
        self.last_preview_data = None
        self.last_preview_type = None  # "GL", "TB", "FS"


        self.steps = [
            "Cerrar Período",
            "Libro Mayor (Preview)",
            "Libro Mayor (Posteo)",
            "Balance de Comprobación",
            "Cierre de Resultados",
            "Estados Financieros",
            "Apertura Nuevo Ejercicio"
        ]

        self.title("Cierre Contable – ERP SOM")
        self.geometry("1100x700")
        self.resizable(True, True)
        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._show_step(0)

        self.fs_can_post = False  # solo true si no hay descuadre


    # ==========================================================
    # UI
    # ==========================================================
    def _build_ui(self):
        header = tk.Frame(self, bg="#003A75")
        header.pack(fill="x")

        tk.Label(
            header,
            text="Wizard de Cierre Contable",
            fg="white",
            bg="#003A75",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor="w", padx=15, pady=10)

        body = tk.Frame(self, bg="white")
        body.pack(fill="both", expand=True)

        sidebar = tk.Frame(body, width=260, bg="#F4F6F8")
        sidebar.pack(side="left", fill="y")

        self.step_labels = []
        for i, step in enumerate(self.steps):
            lbl = tk.Label(
                sidebar,
                text=f"{i}. {step}",
                anchor="w",
                bg="#F4F6F8",
                font=("Segoe UI", 10)
            )
            lbl.pack(fill="x", padx=10, pady=6)
            self.step_labels.append(lbl)

        self.content = tk.Frame(body, bg="white")
        self.content.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        footer = tk.Frame(self, bg="#EFEFEF")
        footer.pack(fill="x")

        self.btn_prev = ttk.Button(footer, text="◀ Anterior", command=self._prev_step)
        self.btn_prev.pack(side="left", padx=10, pady=8)

        self.btn_next = ttk.Button(footer, text="Siguiente ▶", command=self._next_step)
        self.btn_next.pack(side="right", padx=10, pady=8)

        ttk.Button(footer, text="Cerrar", command=self.destroy).pack(side="right", padx=5)

    # ==========================================================
    # Navegación
    # ==========================================================
    def _show_step(self, step_index: int):
        for w in self.content.winfo_children():
            w.destroy()

        self.current_step = step_index

        for i, lbl in enumerate(self.step_labels):
            lbl.configure(
                bg="#D0E3FF" if i == step_index else "#F4F6F8",
                font=("Segoe UI", 10, "bold" if i == step_index else "normal")
            )

        steps_map = {
            0: self._step_close_period,
            1: self._step_gl_preview,
            2: self._step_gl_post,
            3: self._step_tb,
            4: self._step_pnl,
            5: self._step_fs,
            6: self._step_open_fy
        }

        steps_map[step_index]()

        self.btn_prev["state"] = "normal" if step_index > 0 else "disabled"
        self.btn_next["state"] = "normal" if step_index > 0 and step_index < len(self.steps) - 1 else "disabled"


    def _next_step(self):
        self._show_step(self.current_step + 1)

    def _prev_step(self):
        self._show_step(self.current_step - 1)

    # ==========================================================
    # STEP 0 – Cerrar Período
    # ==========================================================
    def _step_close_period(self):
        frame = self._base_step("Cerrar Período Contable")

        # Selector automático de año / período
        self._period_selector(frame)

        # Estado del período (DEBE existir antes de consultar)
        self.lbl_status = ttk.Label(frame, text="Estado: CARGANDO…")
        self.lbl_status.pack(anchor="w", pady=5)

        # Botón cerrar período
        self.btn_close_period = ttk.Button(
            frame,
            text="🔒 Cerrar Período",
            command=self._do_close_period
        )
        self.btn_close_period.pack(pady=10)

        # Cargar estado REAL desde backend
        self._load_period_status()

        # Habilitar / deshabilitar botón según estado del período
        if self.period_closed:
            self.btn_close_period.config(state="disabled")
        else:
            self.btn_close_period.config(state="normal")



    def _do_close_period(self):
        try:
            post_close_period_api(
                company_code=self.company_code,
                fiscal_year=self.fiscal_year,
                period=self.period,
                ledger=self.ledger,
                closed_by=self._posted_by()
            )

            self.period_closed = True
            self.lbl_status.configure(text="Estado: CERRADO ✅")
            self.btn_close_period.config(state="disabled")

            messagebox.showinfo("OK", "Período cerrado correctamente.")
            self._show_step(1)

        except Exception as e:
            messagebox.showerror(
                "Error al cerrar período",
                str(e) if str(e) else "Error desconocido al cerrar período"
            )

    # ==========================================================
    # STEP 1 – GL Preview
    # ==========================================================
    def _step_gl_preview(self):
        frame = self._base_step("Libro Mayor – Preview")
        ttk.Button(frame, text="🔍 Generar Preview", command=self._do_gl_preview).pack(pady=10)
        self._export_buttons(frame)
        self.txt_preview = self._preview_box(frame)

    def _do_gl_preview(self):
        try:
            self._validate_period()
        except ValueError as e:
            messagebox.showerror("Validación", str(e))
            return

        if not self.period_closed:
            messagebox.showwarning(
                "Validación",
                "Debe cerrar el período antes de generar el preview."
            )
            return

        data = post_closing_gl_preview_api(
            company_code=self.company_code,
            fiscal_year=self.fiscal_year,
            period=self.period,
            ledger=self.ledger
        )

        self.last_preview_data = data
        self.last_preview_type = "GL"

        self._render_preview(self.txt_preview, data)

    # ==========================================================
    # STEP 2 – GL Post (MANEJA 409)
    # ==========================================================
    def _step_gl_post(self):
        frame = self._base_step("Libro Mayor – Posteo")
        ttk.Button(frame, text="📘 Postear Cierre GL", command=self._do_gl_post).pack(pady=20)

    def _do_gl_post(self):
        try:
            self._validate_period()
        except ValueError as e:
            messagebox.showerror("Validación", str(e))
            return

        if not messagebox.askyesno(
            "Confirmación",
            "El cierre del Libro Mayor es irreversible.\n¿Desea continuar?"
        ):
            return

        try:
            result = post_closing_gl_post_api(
                company_code=self.company_code,
                fiscal_year=self.fiscal_year,
                period=self.period,
                posted_by=self._posted_by(),
                ledger=self.ledger
            )

            self.last_batch_id = result.get("batch_id")
            messagebox.showinfo("GL", "Libro Mayor cerrado correctamente.")
            self._show_step(3)

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                messagebox.showinfo(
                    "GL",
                    "El Libro Mayor ya estaba cerrado.\nContinuando proceso."
                )
                self._show_step(3)
            else:
                messagebox.showerror("GL", str(e))

    # ==========================================================
    # STEP 3 – TB (ÚNICA MODIFICACIÓN: SCROLL V + H)
    # ==========================================================
    def _step_tb(self):
        frame = self._base_step("Balance de Comprobación")

        ttk.Button(frame, text="📊 Preview", command=self._do_tb_preview).pack(anchor="w")

        # ---- ÚNICA MODIFICACIÓN: Text con scroll vertical y horizontal ----
        container = tk.Frame(frame, bg="white")
        container.pack(fill="both", expand=True, pady=5)

        v_scroll = ttk.Scrollbar(container, orient="vertical")
        h_scroll = ttk.Scrollbar(container, orient="horizontal")

        self.txt_tb = tk.Text(
            container,
            height=18,
            wrap="none",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )

        v_scroll.config(command=self.txt_tb.yview)
        h_scroll.config(command=self.txt_tb.xview)

        self.txt_tb.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.txt_tb.configure(state="disabled")
        # -----------------------------------------------------------------

        ttk.Button(frame, text="✔ Postear TB", command=self._do_tb_post).pack(pady=10)

    def _do_tb_post(self):
        try:
            post_closing_tb_post_api(
                company_code=self.company_code,
                fiscal_year=self.fiscal_year,
                period=self.period,
                posted_by=self._posted_by(),
                ledger=self.ledger
            )
            messagebox.showinfo("TB", "Balance de Comprobación posteado.")

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                messagebox.showinfo(
                    "TB ya posteado",
                    "El Balance de Comprobación ya fue posteado previamente.\nContinuando el proceso."
                )
            else:
                messagebox.showerror("TB", str(e))
                return  # NO avanzar si es otro error

        self._show_step(4)

    # ==========================================================
    # STEP 4 – P&L
    # ==========================================================
    def _step_pnl(self):
        frame = self._base_step("Cierre Estado de Resultados")
        ttk.Button(frame, text="📉 Cerrar P&L", command=self._do_pnl_post).pack(pady=10)

    def _do_pnl_post(self):
        try:
            post_closing_pnl_post_api(
                company_code=self.company_code,
                fiscal_year=self.fiscal_year,
                period=self.period,
                equity_account_code="3-RESULT",
                equity_account_name="Resultado del Ejercicio",
                posted_by=self._posted_by(),
                ledger=self.ledger
            )
            messagebox.showinfo("P&L", "Estado de Resultados cerrado.")

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                messagebox.showinfo(
                    "P&L ya cerrado",
                    "El Estado de Resultados ya fue cerrado previamente.\nContinuando el proceso."
                )
            else:
                messagebox.showerror("P&L", str(e))
                return  # NO avanzar si es otro error

        self._show_step(5)

    # ==========================================================
    # STEP 5 – FS
    # ==========================================================
    def _step_fs(self):
        frame = self._base_step("Estados Financieros")

        ttk.Button(
            frame,
            text="📄 Previsualizar EEFF",
            command=self._do_fs_preview
        ).pack(anchor="w", pady=5)

        # 👉 BOTONES DE EXPORTACIÓN (AQUÍ)
        self._export_buttons(frame)
        # ==========================
        # Tabs EEFF
        # ==========================
        notebook = ttk.Notebook(frame)
        notebook.pack(fill="both", expand=True, pady=5)

        tab_bs = tk.Frame(notebook, bg="white")
        tab_pnl = tk.Frame(notebook, bg="white")
        tab_cf = tk.Frame(notebook, bg="white")

        notebook.add(tab_bs, text="Situación Financiera")
        notebook.add(tab_pnl, text="Estado de Resultados")
        notebook.add(tab_cf, text="Flujo de Efectivo")

        self.txt_bs = self._text_with_scroll(tab_bs)
        self.txt_pnl = self._text_with_scroll(tab_pnl)
        self.txt_cf = self._text_with_scroll(tab_cf)

        self.btn_post_fs = ttk.Button(
            frame,
            text="✔ Postear EEFF",
            command=self._do_fs_post,
            state="disabled"
        )
        self.btn_post_fs.pack(pady=10)

    def _do_fs_post(self):
        if not self.fs_can_post:
            messagebox.showerror(
                "EEFF",
                "No se pueden postear los Estados Financieros.\nExiste un descuadre contable."
            )
            return

        try:
            post_closing_fs_post_api(
                company_code=self.company_code,
                fiscal_year=self.fiscal_year,
                period=self.period,
                posted_by=self._posted_by(),
                ledger=self.ledger
            )
            messagebox.showinfo("EEFF", "Estados Financieros posteados correctamente.")

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                messagebox.showinfo(
                    "EEFF ya posteados",
                    "Los Estados Financieros ya fueron posteados previamente.\nContinuando el proceso."
                )
            else:
                messagebox.showerror("EEFF", str(e))
                return  # NO avanzar si es otro error

        self._show_step(6)

    # ==========================================================
    # STEP 6 – Open FY
    # ==========================================================
    def _step_open_fy(self):
        frame = self._base_step("Apertura Nuevo Ejercicio")
        ttk.Button(frame, text="🚀 Abrir Ejercicio", command=self._do_open_fy).pack(pady=10)

    def _do_open_fy(self):
        try:
            post_closing_fy_open_api(
                company_code=self.company_code,
                fiscal_year=self.fiscal_year + 1,
                source_fiscal_year=self.fiscal_year,
                posted_by=self._posted_by(),
                ledger=self.ledger
            )
            messagebox.showinfo("OK", "Nuevo ejercicio abierto.")

        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 409:
                messagebox.showinfo(
                    "Ejercicio ya abierto",
                    "El nuevo ejercicio ya fue abierto previamente."
                )
            else:
                messagebox.showerror("FY", str(e))
                return

        self.destroy()

    # ==========================================================
    # EEFF – PREVIEW
    # ==========================================================
    def _do_fs_preview(self):
        try:
            self._validate_period()
        except ValueError as e:
            messagebox.showerror("Validación", str(e))
            return

        if not self.period_closed:
            messagebox.showwarning(
                "Validación",
                "Debe cerrar el período antes de generar EEFF."
            )
            return

        tb = post_closing_tb_preview_api(
            company_code=self.company_code,
            fiscal_year=self.fiscal_year,
            period=self.period,
            ledger=self.ledger
        )

        rows = tb.get("data", [])

        self.last_preview_data = tb
        self.last_preview_type = "FS"

        activos = []
        pasivos = []
        patrimonio = []
        ingresos = []
        gastos = []

        for r in rows:
            debe = float(r.get("debit", 0))
            haber = float(r.get("credit", 0))
            saldo = debe - haber
            code = r["account_code"]

            if code.startswith("1"):
                activos.append((r["account_name"], saldo))
            elif code.startswith("2"):
                pasivos.append((r["account_name"], abs(saldo)))
            elif code.startswith("3"):
                patrimonio.append((r["account_name"], abs(saldo)))
            elif code.startswith("4"):
                ingresos.append((r["account_name"], abs(saldo)))
            elif code.startswith("5"):
                gastos.append((r["account_name"], abs(saldo)))

        total_ing = sum(v for _, v in ingresos)
        total_gas = sum(v for _, v in gastos)

        utilidad = total_ing - total_gas
        isr = round(utilidad * 0.30, 2)
        utilidad_neta = utilidad - isr

        pasivos.append(("Impuesto sobre la renta por pagar", isr))

        self._render_pnl_preview(
            ingresos, gastos,
            total_ing, total_gas,
            utilidad, isr, utilidad_neta
        )

        total_act = sum(v for _, v in activos)
        total_pas = sum(v for _, v in pasivos)
        total_pat = sum(v for _, v in patrimonio) + utilidad_neta

        diff = round(total_act - (total_pas + total_pat), 2)

        self._render_bs_preview(
            activos, pasivos, patrimonio,
            utilidad_neta,
            total_act, total_pas, total_pat,
            diff
        )

        self._render_cf_preview(utilidad, rows)

        if diff == 0:
            self.fs_can_post = True
            self.btn_post_fs.config(state="normal")
        else:
            self.fs_can_post = False
            self.btn_post_fs.config(state="disabled")
    # ==========================================================
    # RENDER – ESTADO DE RESULTADOS
    # ==========================================================
    def _render_pnl_preview(
        self, ingresos, gastos, total_ing, total_gas,
        utilidad, isr, utilidad_neta
    ):
        t = self.txt_pnl
        t.configure(state="normal")
        t.delete("1.0", "end")

        t.insert("end", "ESTADO DE RESULTADOS\n" + "-" * 70 + "\n")

        for n, v in ingresos:
            t.insert("end", f"{n:<45}{v:>15,.2f}\n")
        t.insert("end", f"{'TOTAL INGRESOS':<45}{total_ing:>15,.2f}\n\n")

        for n, v in gastos:
            t.insert("end", f"{n:<45}{v:>15,.2f}\n")
        t.insert("end", f"{'TOTAL GASTOS':<45}{total_gas:>15,.2f}\n")

        t.insert("end", "-" * 70 + "\n")
        t.insert(
            "end",
            f"{'Resultado del Periodo (utilidad neta)':<45}{utilidad_neta:>15,.2f}\n"
        )

        t.insert("end", f"{'IMPUESTO RENTA 30%':<45}{isr:>15,.2f}\n")
        t.insert("end", f"{'UTILIDAD NETA':<45}{utilidad_neta:>15,.2f}\n")

        t.configure(state="disabled")

    # ==========================================================
    # RENDER – BALANCE GENERAL
    # ==========================================================
    def _render_bs_preview(
        self, activos, pasivos, patrimonio,
        utilidad_neta, total_act, total_pas, total_pat, diff
    ):
        t = self.txt_bs
        t.configure(state="normal")
        t.delete("1.0", "end")

        t.insert("end", "ESTADO DE SITUACIÓN FINANCIERA\n" + "-" * 70 + "\n")

        # ---------------- ACTIVOS ----------------
        for n, v in activos:
            t.insert("end", f"{n:<45}{v:>15,.2f}\n")
        t.insert("end", f"{'TOTAL ACTIVOS':<45}{total_act:>15,.2f}\n\n")

        # ---------------- PASIVOS ----------------
        for n, v in pasivos:
            t.insert("end", f"{n:<45}{v:>15,.2f}\n")
        t.insert("end", f"{'TOTAL PASIVOS':<45}{total_pas:>15,.2f}\n\n")

        # ---------------- PATRIMONIO ----------------
        for n, v in patrimonio:
            t.insert("end", f"{n:<45}{v:>15,.2f}\n")

        t.insert(
            "end",
            f"{'Resultado del Periodo (utilidad neta)':<45}{utilidad_neta:>15,.2f}\n"
        )

        t.insert("end", f"{'TOTAL PATRIMONIO':<45}{total_pat:>15,.2f}\n")

        # ---------------- VALIDACIÓN ----------------
        t.insert("end", "-" * 70 + "\n")
        t.insert(
            "end",
            f"{'PASIVO + PATRIMONIO':<45}{(total_pas + total_pat):>15,.2f}\n"
        )

        if diff == 0:
            t.insert("end", "\nVALIDACIÓN: ACTIVO = PASIVO + PATRIMONIO ✔\n")
        else:
            t.insert("end", f"\n⚠ DESCUADRE CONTABLE: {diff:,.2f}\n")

        t.configure(state="disabled")

    # ==========================================================
    # RENDER – FLUJO DE EFECTIVO
    # ==========================================================
    def _render_cf_preview(self, utilidad, rows):
        t = self.txt_cf
        t.configure(state="normal")
        t.delete("1.0", "end")

        t.insert("end", "ESTADO DE FLUJO DE EFECTIVO (MÉTODO INDIRECTO)\n" + "-" * 80 + "\n")
        t.insert("end", f"Utilidad antes de impuestos: {utilidad:>15,.2f}\n")
        t.insert("end", f"Impuesto sobre la renta (30%): {-(utilidad * 0.30):>18,.2f}\n")
        t.insert("end", f"Utilidad neta: {(utilidad * 0.70):>24,.2f}\n")

        dep = sum(
            abs(float(r["debit"]) - float(r["credit"]))
            for r in rows if "depreci" in r["account_name"].lower()
        )
        t.insert("end", f"Depreciación: {dep:>32,.2f}\n")

        t.insert("end", "-" * 80 + "\n")
        t.insert("end", "Efectivo neto de actividades de operación\n")

        t.configure(state="disabled")




    # ==========================================================
    # Helpers
    # ==========================================================
    def _base_step(self, title):
        frame = tk.Frame(self.content, bg="white")
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=title, font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Separator(frame).pack(fill="x", pady=5)
        return frame

    def _period_selector(self, parent):
        frm = tk.Frame(parent, bg="white")
        frm.pack(anchor="w", pady=10)

        # -----------------------------
        # Año y período AUTOMÁTICOS
        # -----------------------------
        self.var_year = tk.IntVar(value=date.today().year)
        self.var_period = tk.IntVar(value=date.today().month)

        ttk.Label(frm, text="Año:").grid(row=0, column=0, padx=5)
        ttk.Entry(
            frm,
            textvariable=self.var_year,
            width=8,
            state="readonly"   # 🔒 NO editable
        ).grid(row=0, column=1)

        ttk.Label(frm, text="Periodo:").grid(row=0, column=2, padx=5)
        ttk.Entry(
            frm,
            textvariable=self.var_period,
            width=5,
            state="readonly"   # 🔒 NO editable
        ).grid(row=0, column=3)

        # -----------------------------
        # Sincronizar variables internas
        # -----------------------------
        self.fiscal_year = self.var_year.get()
        self.period = self.var_period.get()

        # -----------------------------
        # Cargar estado REAL del período
        # -----------------------------
        if hasattr(self, "lbl_status"):
            self._load_period_status()

    def _preview_box(self, parent):
        txt = tk.Text(parent, height=18, wrap="none")
        txt.pack(fill="both", expand=True)
        txt.configure(state="disabled")
        return txt

    def _render_preview(self, widget, data):
        widget.configure(state="normal")
        widget.delete("1.0", "end")

        widget.insert("end", "Libro Mayor – Preview\n", "title")
        widget.insert("end", f"Empresa: {data['company_code']}\n")
        widget.insert("end", f"Año Fiscal: {data['fiscal_year']}   Periodo: {data['period']}\n")
        widget.insert("end", "-" * 95 + "\n")

        widget.insert(
            "end",
            f"{'Cuenta':<12}{'Descripción':<40}{'Debe':>18}{'Haber':>18}\n"
        )
        widget.insert("end", "-" * 95 + "\n")

        total_debe = 0.0
        total_haber = 0.0

        for r in data.get("data", []):
            debe = float(r.get("debit", 0))
            haber = float(r.get("credit", 0))

            total_debe += debe
            total_haber += haber

            widget.insert(
                "end",
                f"{r['account_code']:<12}"
                f"{r['account_name']:<40}"
                f"{debe:>18,.2f}"
                f"{haber:>18,.2f}\n"
            )

        widget.insert("end", "-" * 95 + "\n")
        widget.insert(
            "end",
            f"{'TOTAL':<52}{total_debe:>18,.2f}{total_haber:>18,.2f}\n"
        )

        diff = round(total_debe - total_haber, 2)
        widget.insert("end", "-" * 95 + "\n")
        widget.insert("end", f"Diferencia: {diff:,.2f}\n")
        widget.insert(
            "end",
            f"Estado: {'BALANCEADO' if diff == 0 else 'DESBALANCEADO'}\n"
        )

        widget.configure(state="disabled")

    def _render_tb_sap(self, widget, data):
        widget.configure(state="normal")
        widget.delete("1.0", "end")

        widget.insert("end", "BALANCE DE COMPROBACIÓN\n")
        widget.insert("end", f"Empresa: {data['company_code']}\n")
        widget.insert("end", f"Año Fiscal: {data['fiscal_year']}   Periodo: {data['period']}\n")
        widget.insert("end", "-" * 110 + "\n")

        widget.insert(
            "end",
            f"{'Cuenta':<12}{'Descripción':<40}"
            f"{'Debe':>16}{'Haber':>16}"
            f"{'Saldo Deudor':>18}{'Saldo Acreedor':>18}\n"
        )

        widget.insert("end", "-" * 110 + "\n")

        total_sd = 0.0
        total_sa = 0.0

        for r in data.get("data", []):
            debe = float(r.get("debit", 0))
            haber = float(r.get("credit", 0))
            saldo = round(debe - haber, 2)

            saldo_deudor = saldo if saldo > 0 else 0
            saldo_acreedor = abs(saldo) if saldo < 0 else 0

            total_sd += saldo_deudor
            total_sa += saldo_acreedor

            widget.insert(
                "end",
                f"{r['account_code']:<12}"
                f"{r['account_name']:<40}"
                f"{debe:>16,.2f}"
                f"{haber:>16,.2f}"
                f"{saldo_deudor:>18,.2f}"
                f"{saldo_acreedor:>18,.2f}\n"
            )

        widget.insert("end", "-" * 110 + "\n")
        widget.insert(
            "end",
            f"{'TOTALES':<68}"
            f"{total_sd:>18,.2f}{total_sa:>18,.2f}\n"
        )

        widget.insert("end", "-" * 110 + "\n")
        widget.insert(
            "end",
            f"Estado: {'BALANCEADO' if round(total_sd - total_sa, 2) == 0 else 'REVISAR'}\n"
        )

        widget.configure(state="disabled")


    def _text_with_scroll(self, parent):
        container = tk.Frame(parent, bg="white")
        container.pack(fill="both", expand=True)

        v = ttk.Scrollbar(container, orient="vertical")
        h = ttk.Scrollbar(container, orient="horizontal")

        txt = tk.Text(
            container,
            wrap="none",
            yscrollcommand=v.set,
            xscrollcommand=h.set
        )

        v.config(command=txt.yview)
        h.config(command=txt.xview)

        txt.grid(row=0, column=0, sticky="nsew")
        v.grid(row=0, column=1, sticky="ns")
        h.grid(row=1, column=0, sticky="ew")

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        txt.configure(state="disabled")
        return txt


    def _export_buttons(self, parent):
        bar = tk.Frame(parent, bg="white")
        bar.pack(fill="x", pady=5)

        ttk.Button(
            bar,
            text="📊 Exportar Excel",
            command=self._export_excel
        ).pack(side="right", padx=5)

        ttk.Button(
            bar,
            text="📄 Exportar PDF",
            command=self._export_pdf
        ).pack(side="right")


    def _do_tb_preview(self):
        try:
            self._validate_period()
        except ValueError as e:
            messagebox.showerror("Validación", str(e))
            return

        if not self.period_closed:
            messagebox.showwarning(
                "Validación",
                "Debe cerrar el período antes de generar el Balance de Comprobación."
            )
            return

        data = post_closing_tb_preview_api(
            company_code=self.company_code,
            fiscal_year=self.fiscal_year,
            period=self.period,
            ledger=self.ledger
        )

        self.last_preview_data = data
        self.last_preview_type = "TB"

        self._render_tb_sap(self.txt_tb, data)

    def _posted_by(self):
        """
        Retorna el usuario logeado.
        Por ahora usa 'system', luego se conecta al login real.
        """
        return "system"



    def _export_excel(self):
        if not self.last_preview_data:
            messagebox.showwarning("Exportar", "No hay preview para exportar.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not path:
            return

        try:
            # =============================
            # GL / TB
            # =============================
            if self.last_preview_type in ("GL", "TB"):
                df = pd.DataFrame(self.last_preview_data.get("data", []))
                df = df[[
                    "account_code",
                    "account_name",
                    "debit",
                    "credit"
                ]]
                df.to_excel(path, index=False, sheet_name=self.last_preview_type)

            # =============================
            # FS (EEFF) – 3 HOJAS REALES
            # =============================
            elif self.last_preview_type == "FS":
                rows = self.last_preview_data.get("data", [])

                activos, pasivos, patrimonio = [], [], []
                ingresos, gastos = [], []

                for r in rows:
                    saldo = float(r["debit"]) - float(r["credit"])
                    code = r["account_code"]

                    if code.startswith("1"):
                        activos.append([r["account_name"], saldo])
                    elif code.startswith("2"):
                        pasivos.append([r["account_name"], abs(saldo)])
                    elif code.startswith("3"):
                        patrimonio.append([r["account_name"], abs(saldo)])
                    elif code.startswith("4"):
                        ingresos.append([r["account_name"], abs(saldo)])
                    elif code.startswith("5"):
                        gastos.append([r["account_name"], abs(saldo)])

                with pd.ExcelWriter(path, engine="openpyxl") as writer:
                    pd.DataFrame(activos, columns=["Cuenta", "Monto"]).to_excel(
                        writer, sheet_name="Balance - Activos", index=False
                    )
                    pd.DataFrame(pasivos, columns=["Cuenta", "Monto"]).to_excel(
                        writer, sheet_name="Balance - Pasivos", index=False
                    )
                    pd.DataFrame(patrimonio, columns=["Cuenta", "Monto"]).to_excel(
                        writer, sheet_name="Balance - Patrimonio", index=False
                    )
                    pd.DataFrame(ingresos, columns=["Cuenta", "Monto"]).to_excel(
                        writer, sheet_name="Resultados - Ingresos", index=False
                    )
                    pd.DataFrame(gastos, columns=["Cuenta", "Monto"]).to_excel(
                        writer, sheet_name="Resultados - Gastos", index=False
                    )

            messagebox.showinfo("Exportar", "Archivo Excel generado correctamente.")

        except Exception as e:
            messagebox.showerror("Exportar", f"Error al generar Excel:\n{str(e)}")


    def _export_pdf(self):
        if not self.last_preview_data:
            messagebox.showwarning("Exportar", "No hay preview para exportar.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return

        try:
            c = canvas.Canvas(path, pagesize=A4)
            width, height = A4

            def new_page(title):
                c.showPage()
                c.setFont("Helvetica-Bold", 11)
                c.drawString(40, height - 40, title)
                c.setFont("Helvetica", 9)

            y = height - 60
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, f"ERP SOM – {self.last_preview_type} Preview")
            y -= 20
            c.setFont("Helvetica", 9)

            # =============================
            # GL / TB
            # =============================
            if self.last_preview_type in ("GL", "TB"):
                headers = ["Cuenta", "Descripción", "Debe", "Haber"]
                c.drawString(40, y, " | ".join(headers))
                y -= 15

                for r in self.last_preview_data.get("data", []):
                    line = f"{r['account_code']} | {r['account_name']} | {r['debit']:,.2f} | {r['credit']:,.2f}"
                    if y < 50:
                        new_page("Continuación")
                        y = height - 60
                    c.drawString(40, y, line[:120])
                    y -= 12

            # =============================
            # FS (EEFF)
            # =============================
            elif self.last_preview_type == "FS":
                rows = self.last_preview_data.get("data", [])

                secciones = {
                    "ACTIVOS": [],
                    "PASIVOS": [],
                    "PATRIMONIO": [],
                    "INGRESOS": [],
                    "GASTOS": []
                }

                for r in rows:
                    saldo = float(r["debit"]) - float(r["credit"])
                    code = r["account_code"]

                    if code.startswith("1"):
                        secciones["ACTIVOS"].append((r["account_name"], saldo))
                    elif code.startswith("2"):
                        secciones["PASIVOS"].append((r["account_name"], abs(saldo)))
                    elif code.startswith("3"):
                        secciones["PATRIMONIO"].append((r["account_name"], abs(saldo)))
                    elif code.startswith("4"):
                        secciones["INGRESOS"].append((r["account_name"], abs(saldo)))
                    elif code.startswith("5"):
                        secciones["GASTOS"].append((r["account_name"], abs(saldo)))

                for titulo, items in secciones.items():
                    if not items:
                        continue

                    if y < 100:
                        new_page(titulo)
                        y = height - 60

                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(40, y, titulo)
                    y -= 15
                    c.setFont("Helvetica", 9)

                    for n, v in items:
                        if y < 50:
                            new_page(titulo)
                            y = height - 60
                        c.drawString(50, y, f"{n}: {v:,.2f}")
                        y -= 12

            c.save()
            messagebox.showinfo("Exportar", "Archivo PDF generado correctamente.")

        except Exception as e:
            messagebox.showerror("Exportar", f"Error al generar PDF:\n{str(e)}")


    def _load_period_status(self):
        """
        Consulta a la API si el período ya está cerrado
        y sincroniza el estado visual y lógico.
        """
        try:
            status = get_closing_period_status(
                company_code=self.company_code,
                fiscal_year=self.fiscal_year,
                period=self.period,
                ledger=self.ledger
            )

            self.period_closed = bool(status.get("period_closed", False))

            if self.period_closed:
                self.lbl_status.config(text="Estado: CERRADO ✅")
                if hasattr(self, "btn_close_period"):
                    self.btn_close_period.config(state="disabled")
            else:
                self.lbl_status.config(text="Estado: ABIERTO")
                if hasattr(self, "btn_close_period"):
                    self.btn_close_period.config(state="normal")

        except requests.HTTPError as e:
            self.period_closed = False
            self.lbl_status.config(text="Estado: ERROR API ⚠")
            messagebox.showerror(
                "Error API",
                f"Error consultando estado del período:\n"
                f"{e.response.text if e.response else str(e)}"
            )

        except Exception as e:
            self.period_closed = False
            self.lbl_status.config(text="Estado: ERROR ⚠")
            messagebox.showerror(
                "Error",
                f"Error inesperado al consultar estado:\n{str(e)}"
            )
