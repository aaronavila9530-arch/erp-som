import tkinter as tk
from Modulos.Finanzas.sections.BankReconciliation.tabla_bank_reconciliation import (
    BankReconciliationUI
)


class BankReconciliationSection(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent)
        BankReconciliationUI(self).pack(fill="both", expand=True)
