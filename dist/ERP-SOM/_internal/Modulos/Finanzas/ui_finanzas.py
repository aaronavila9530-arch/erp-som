import tkinter as tk
from tkinter import ttk, messagebox


class FinanzasUI(tk.Frame):
    """
    Módulo FINANZAS
    Nivel 1: Procesos financieros
    Nivel 2: Secciones por proceso
    """

    def __init__(self, parent, on_back):
        super().__init__(parent, bg="white")
        self.on_back = on_back

        self.section_container = None
        self.submenu_container = None

        self._build_header()
        self._build_main_menu()
        self._build_body()

    # ============================================================
    # HEADER
    # ============================================================
    def _build_header(self):
        header = tk.Frame(self, bg="#f5f5f5", height=50)
        header.pack(fill="x")

        ttk.Button(
            header,
            text="← Volver",
            command=self._back_to_finance_home
        ).pack(side="left", padx=10, pady=10)

        ttk.Label(
            header,
            text="Finanzas",
            font=("Segoe UI", 14, "bold"),
            background="#f5f5f5"
        ).pack(side="left", padx=20)

    # ============================================================
    # MENÚ PRINCIPAL (NIVEL 1)
    # ============================================================
    def _build_main_menu(self):
        self.main_menu = tk.Frame(self, bg="white")
        self.main_menu.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Button(
            self.main_menu,
            text="Order To Cash",
            command=self.load_order_to_cash
        ).pack(side="left", padx=5)

        ttk.Button(
            self.main_menu,
            text="Invoice To Pay",
            command=self.load_invoice_to_pay
        ).pack(side="left", padx=5)

        ttk.Button(
            self.main_menu,
            text="Accounting",
            command=self.load_accounting
        ).pack(side="left", padx=5)

    # ============================================================
    # BODY
    # ============================================================
    def _build_body(self):

        # ---------- Submenú (SIN SCROLL) ----------
        self.submenu_wrapper = tk.Frame(self, bg="white")
        self.submenu_wrapper.pack(fill="x", padx=10, pady=(5, 5))

        self.submenu_canvas = tk.Canvas(
            self.submenu_wrapper,
            height=45,
            bg="white",
            highlightthickness=0
        )
        self.submenu_canvas.pack(fill="x", expand=True)

        self.submenu_container = tk.Frame(
            self.submenu_canvas,
            bg="white"
        )

        self.submenu_canvas.create_window(
            (0, 0),
            window=self.submenu_container,
            anchor="nw"
        )

        # ---------- Contenedor principal ----------
        self.section_container = tk.Frame(self, bg="white")
        self.section_container.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self._show_placeholder("Seleccione un proceso financiero")

    # ============================================================
    # UTILIDADES
    # ============================================================
    def _clear_section(self):
        for widget in self.section_container.winfo_children():
            widget.destroy()

    def _clear_submenu(self):
        for widget in self.submenu_container.winfo_children():
            widget.destroy()

    def _show_placeholder(self, text):
        self._clear_section()
        ttk.Label(
            self.section_container,
            text=text,
            font=("Segoe UI", 11),
            foreground="gray"
        ).pack(anchor="center", expand=True)

    def _safe_lazy_load(self, loader, placeholder_text):
        """
        Carga diferida real para evitar LAG en Tkinter
        """
        self.configure(cursor="watch")
        self.update_idletasks()

        def _execute():
            try:
                loader()
            except Exception as e:
                self._show_placeholder(placeholder_text)
                messagebox.showerror("Error", str(e))
            finally:
                self.configure(cursor="")

        # 🔥 Ejecutar en siguiente ciclo del mainloop
        self.after(1, _execute)

    def _back_to_finance_home(self):
        self._clear_submenu()
        self._clear_section()
        self._show_placeholder("Seleccione un proceso financiero")

    # ============================================================
    # ORDER TO CASH
    # ============================================================
    def load_order_to_cash(self):
        self._clear_submenu()
        self._clear_section()

        self.submenu_wrapper.pack(fill="x", padx=10, pady=(5, 5))

        buttons = [
            ("Invoicing & Billing", self.load_invoicing),
            ("Credit (Order Hold & Release)", self.load_credit_hold),
            ("Collections", self.load_collections),
            ("Bank Reconciliation", self.load_bank_reconciliation),
            ("Disputes", self.load_disputes),
        ]

        for text, command in buttons:
            ttk.Button(
                self.submenu_container,
                text=text,
                command=command
            ).pack(side="left", padx=5, pady=5)

        self._show_placeholder("Seleccione una sección de Order To Cash")

    # ============================================================
    # INVOICE TO PAY
    # ============================================================
    def load_invoice_to_pay(self):
        self._clear_submenu()
        self._clear_section()

        self.submenu_wrapper.pack_forget()

        def _load():
            from Modulos.Finanzas.sections.InvoiceToPay.invoice_to_pay_ui import InvoiceToPayUI
            InvoiceToPayUI(self.section_container).pack(fill="both", expand=True)

        self._safe_lazy_load(_load, "Error al cargar Invoice To Pay")

    # ============================================================
    # INVOICING & BILLING
    # ============================================================
    def load_invoicing(self):
        self._clear_section()

        def _load():
            notebook = ttk.Notebook(self.section_container)
            notebook.pack(fill="both", expand=True)

            tab_invoicing = tk.Frame(notebook, bg="white")
            notebook.add(tab_invoicing, text="Invoicing")

            from Modulos.Finanzas.sections.invoicing.ui_invoicing import InvoicingUI
            InvoicingUI(tab_invoicing).pack(fill="both", expand=True)

            tab_billing = tk.Frame(notebook, bg="white")
            notebook.add(tab_billing, text="Billing")

            from Modulos.Finanzas.Billing.ui_billing import BillingUI
            BillingUI(tab_billing).pack(fill="both", expand=True)

        self._safe_lazy_load(_load, "Error al cargar Invoicing & Billing")

    # ============================================================
    # CREDIT HOLD
    # ============================================================
    def load_credit_hold(self):
        self._clear_section()

        def _load():
            from Modulos.Finanzas.sections.credit_hold.ui_credit_control import CreditControlUI
            CreditControlUI(self.section_container).pack(fill="both", expand=True)

        self._safe_lazy_load(_load, "Error al cargar Credit Control")

    # ============================================================
    # COLLECTIONS
    # ============================================================
    def load_collections(self):
        self._clear_section()

        def _load():
            from Modulos.Finanzas.sections.Collections.ui_collections import CollectionsUI
            CollectionsUI(self.section_container).pack(fill="both", expand=True)

        self._safe_lazy_load(_load, "Error al cargar Collections")

    # ============================================================
    # BANK RECONCILIATION
    # ============================================================
    def load_bank_reconciliation(self):
        self._clear_section()

        def _load():
            from Modulos.Finanzas.sections.BankReconciliation.tabla_bank_reconciliation import (
                BankReconciliationUI
            )
            BankReconciliationUI(self.section_container).pack(fill="both", expand=True)

        self._safe_lazy_load(_load, "Error al cargar Bank Reconciliation")

    # ============================================================
    # DISPUTES
    # ============================================================
    def load_disputes(self):
        self._clear_section()

        def _load():
            from Modulos.Finanzas.sections.Disputes.dispute_management_ui import DisputeManagementUI
            DisputeManagementUI(self.section_container).pack(fill="both", expand=True)

        self._safe_lazy_load(_load, "Error al cargar Disputes")

    # ============================================================
    # ACCOUNTING
    # ============================================================
    def load_accounting(self):
        self._clear_submenu()
        self._clear_section()

        # Mostrar submenú (Accounting puede usarlo)
        self.submenu_wrapper.pack(fill="x", padx=10, pady=(5, 5))

        def _load():
            from Modulos.Finanzas.sections.Accounting.accounting_ui import AccountingUI
            AccountingUI(self.section_container).pack(fill="both", expand=True)

        self._safe_lazy_load(_load, "Error al cargar Accounting")
