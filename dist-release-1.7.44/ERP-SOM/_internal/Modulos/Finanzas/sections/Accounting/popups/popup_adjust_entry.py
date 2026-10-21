import tkinter as tk
from tkinter import ttk, messagebox
from api_client import get_accounting_accounts_api, get_accounting_entry_api


class PopupAdjustEntry(tk.Toplevel):

    def __init__(self, parent, entry_id: int, on_success=None):
        super().__init__(parent)

        self.parent = parent
        self.entry_id = entry_id
        self.on_success = on_success

        # 🔒 Inicializaciones OBLIGATORIAS
        self.catalog_map = {}
        self.accounts = []
        self.cmb_account = None

        self.title(f"Ajustar asiento #{entry_id}")
        self.geometry("780x520")
        self.transient(parent)
        self.grab_set()

        # ORDEN CORRECTO
        self._build_ui()
        self._load_catalog()
        self._load_entry()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Cuenta contable").grid(row=0, column=0, sticky="w")

        self.cmb_account = ttk.Combobox(
            frm,
            state="readonly",
            width=45
        )
        self.cmb_account.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(frm, text="Debe").grid(row=1, column=0, sticky="w")
        self.ent_debit = ttk.Entry(frm, width=20)
        self.ent_debit.grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Haber").grid(row=2, column=0, sticky="w")
        self.ent_credit = ttk.Entry(frm, width=20)
        self.ent_credit.grid(row=2, column=1, sticky="w")

        ttk.Label(frm, text="Detalle").grid(row=3, column=0, sticky="nw")
        self.txt_detail = tk.Text(frm, height=3, width=60)
        self.txt_detail.grid(row=3, column=1, sticky="w")

        ttk.Button(
            frm,
            text="➕ Agregar línea",
            command=self._add_line
        ).grid(row=4, column=1, sticky="w", pady=8)

        self.tree = ttk.Treeview(
            frm,
            columns=("account", "debit", "credit", "detail"),
            show="headings",
            height=8
        )

        self.tree.heading("account", text="Cuenta")
        self.tree.heading("debit", text="Debe")
        self.tree.heading("credit", text="Haber")
        self.tree.heading("detail", text="Detalle")

        self.tree.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=10)

        ttk.Button(
            frm,
            text="💾 Guardar ajuste",
            command=self._save_adjustment
        ).grid(row=6, column=1, sticky="e")

    # ============================================================
    # CATÁLOGO CONTABLE
    # ============================================================
    def _load_catalog(self):
        try:
            accounts = get_accounting_accounts_api()

            self.catalog_map = {
                f"{a['account_code']} - {a['account_name']}": a
                for a in accounts
            }

            self.cmb_account["values"] = list(self.catalog_map.keys())

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el catálogo contable:\n{e}"
            )

    # ============================================================
    # CARGAR ASIENTO ORIGINAL
    # ============================================================
    def _load_entry(self):
        data = get_accounting_entry_api(self.entry_id)

        for ln in data.get("lines", []):
            acc = f"{ln['account_code']} - {ln['account_name']}"
            self.tree.insert(
                "",
                "end",
                values=(
                    acc,
                    f"{ln['debit']:.2f}" if ln["debit"] else "",
                    f"{ln['credit']:.2f}" if ln["credit"] else "",
                    ln.get("line_description", "")
                )
            )

    # ============================================================
    # ACTIONS
    # ============================================================
    def _add_line(self):
        acc = self.cmb_account.get()
        if not acc:
            messagebox.showwarning("Validación", "Seleccione una cuenta")
            return

        debit = self.ent_debit.get() or "0"
        credit = self.ent_credit.get() or "0"
        detail = self.txt_detail.get("1.0", "end").strip()

        self.tree.insert(
            "",
            "end",
            values=(acc, debit, credit, detail)
        )

        self.ent_debit.delete(0, "end")
        self.ent_credit.delete(0, "end")
        self.txt_detail.delete("1.0", "end")

    def _save_adjustment(self):
        messagebox.showinfo(
            "OK",
            "Aquí se creará el asiento de ajuste (no se modifica el original)"
        )
        self.destroy()
        if self.on_success:
            self.on_success()
