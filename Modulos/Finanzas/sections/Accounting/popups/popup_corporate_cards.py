import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from api_client import (
    get_accounting_accounts_api,
    get_corporate_card_statements_api,
    get_corporate_card_match_candidates_api,
    get_corporate_card_transactions_api,
    get_accounting_bank_accounts_api,
    post_corporate_card_auto_match_api,
    post_corporate_card_daily_entries_api,
    post_corporate_card_history_api,
    post_corporate_card_match_itp_api,
    post_corporate_card_settlement_api,
    post_corporate_card_statement_pdf_api,
    put_corporate_card_statement_classify_api,
    put_corporate_card_transaction_classify_api,
)


def _fmt_money(value):
    try:
        return f"CRC {float(value or 0):,.2f}"
    except Exception:
        return "CRC 0.00"


EXPENSE_PRESETS = [
    ("Alimentacion", "550-001-000-050", "Alimentación", "DEDUCTIBLE"),
    ("Transporte", "500-001-001-050", "Transporte", "DEDUCTIBLE"),
    ("Combustible", "500-001-001-042", "Combustible", "DEDUCTIBLE"),
    ("Telefonos", "500-001-001-023", "Teléfonos", "DEDUCTIBLE"),
    ("Hospedaje", "500-001-001-043", "Hospedaje", "DEDUCTIBLE"),
    ("Viaticos", "500-001-001-044", "Viáticos", "DEDUCTIBLE"),
    ("Pasajes avion", "500-001-001-054", "Pasajes de avión", "DEDUCTIBLE"),
    ("Oficina", "500-001-001-036", "Papeleria y Utiles de Oficina", "DEDUCTIBLE"),
    ("Mantenimiento vehiculo", "500-001-001-038", "Mant. y Reparación Vehículos", "DEDUCTIBLE"),
    ("Gastos medicos", "550-001-000-059", "Gastos Médicos", "DEDUCTIBLE"),
    ("Servicios profesionales", "500-001-001-006", "Servicios Profesionales", "DEDUCTIBLE"),
    ("Otros gastos", "5.4", "Otros gastos", "DEDUCTIBLE"),
    ("No deducible", "5.4.99", "Gastos no deducibles", "NON_DEDUCTIBLE"),
]


class PopupCorporateCards(tk.Toplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Tarjetas corporativas")
        self.geometry("1320x760")
        try:
            self.state("zoomed")
        except Exception:
            pass
        self.statements = []
        self.transactions = []
        self.selected_statement_id = None
        self.bank_accounts = []
        self.accounts = []
        self.pending_changes = {}
        self.expense_preset_map = {
            f"{label} | {code} {name}": {
                "fiscal_category": label,
                "expense_account_code": code,
                "expense_account_name": name,
                "deductible_status": status,
            }
            for label, code, name, status in EXPENSE_PRESETS
        }
        self._build_ui()
        self._load_expense_options()
        self._load()

    def _build_ui(self):
        toolbar = tk.Frame(self, bg="#ececec")
        toolbar.pack(fill="x", padx=8, pady=8)
        ttk.Button(toolbar, text="Importar PDF BAC", command=self._import_pdf).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Actualizar", command=self._load).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Auto cruzar ITP", command=self._auto_match).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Contabilizar cargos", command=self._post_daily).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Liquidar tarjeta día 15", command=self._post_settlement).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Contabilizar historial 2025-2026", command=self._post_history).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Cerrar", command=self.destroy).pack(side="right", padx=4)

        summary = tk.Frame(self, bg="#f7f7f7", bd=1, relief="solid")
        summary.pack(fill="x", padx=8, pady=(0, 8))
        self.lbl_rule = tk.Label(
            summary,
            text="Regla: factura electrónica + cargo de tarjeta = factura pagada por tarjeta; la tarjeta queda por pagar al día 15 del mes siguiente.",
            bg="#f7f7f7",
            anchor="w",
            font=("Segoe UI", 10, "bold"),
        )
        self.lbl_rule.pack(fill="x", padx=10, pady=8)
        self.lbl_totals = tk.Label(summary, text="Sin estado seleccionado.", bg="#f7f7f7", anchor="w")
        self.lbl_totals.pack(fill="x", padx=10, pady=(0, 8))

        panes = ttk.Panedwindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8, pady=4)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=3)

        tk.Label(left, text="Estados de cuenta BAC", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.tree_statements = ttk.Treeview(left, columns=("period", "card", "due", "crc", "usd", "tx", "status"), show="headings", height=18)
        for col, label, width in (
            ("period", "Periodo", 80),
            ("card", "Tarjeta", 80),
            ("due", "Pago 15", 95),
            ("crc", "Contado CRC", 115),
            ("usd", "Contado USD", 105),
            ("tx", "Cargos", 70),
            ("status", "Estado", 95),
        ):
            self.tree_statements.heading(col, text=label)
            self.tree_statements.column(col, width=width, anchor="w")
        self.tree_statements.pack(fill="both", expand=True, pady=(4, 0))
        self.tree_statements.bind("<<TreeviewSelect>>", self._on_statement_select)

        tk.Label(right, text="Movimientos por usuario / ITP", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        action_frame = tk.Frame(right)
        action_frame.pack(fill="x", pady=(4, 4))
        ttk.Label(action_frame, text="Rubro/cuenta:").pack(side="left", padx=(0, 3))
        self.cmb_expense = ttk.Combobox(
            action_frame,
            values=list(self.expense_preset_map.keys()),
            width=44,
            state="readonly",
        )
        self.cmb_expense.pack(side="left", padx=3)
        if self.cmb_expense["values"]:
            self.cmb_expense.current(0)
        ttk.Button(action_frame, text="Aplicar rubro", command=self._apply_expense_preset).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Marcar deducible", command=lambda: self._classify_selected("DEDUCTIBLE")).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Marcar no deducible", command=lambda: self._classify_selected("NON_DEDUCTIBLE")).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Requiere factura", command=lambda: self._classify_selected("PENDING_REVIEW", True)).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Cruzar factura ITP", command=self._match_itp).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Cuenta gasto", command=self._set_expense_account).pack(side="left", padx=3)
        ttk.Button(action_frame, text="Guardar cambios", command=self._save_changes).pack(side="right", padx=3)

        columns = ("date", "user", "card", "merchant", "currency", "amount", "account", "match", "deductible", "entry", "notes")
        self.tree_tx = ttk.Treeview(right, columns=columns, show="headings", height=24)
        self.tree_tx.config(selectmode="extended")
        headings = {
            "date": "Fecha",
            "user": "Usuario",
            "card": "Tarjeta",
            "merchant": "Comercio / detalle",
            "currency": "Moneda",
            "amount": "Monto",
            "account": "Cuenta gasto",
            "match": "Cruce",
            "deductible": "Fiscal",
            "entry": "Asiento",
            "notes": "Notas",
        }
        widths = {"date": 90, "user": 105, "card": 70, "merchant": 320, "currency": 65, "amount": 120, "account": 260, "match": 115, "deductible": 135, "entry": 80, "notes": 200}
        for col in columns:
            self.tree_tx.heading(col, text=headings[col])
            self.tree_tx.column(col, width=widths[col], anchor="w")
        self.tree_tx.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(self, textvariable=self.status_var, anchor="w", bg="#e8e8e8").pack(fill="x", side="bottom")

    def _load(self):
        try:
            self.statements = (get_corporate_card_statements_api() or {}).get("items", [])
            self.tree_statements.delete(*self.tree_statements.get_children())
            for row in self.statements:
                sid = str(row.get("id"))
                self.tree_statements.insert("", "end", iid=sid, values=(
                    row.get("statement_period") or "",
                    row.get("card_last4") or "",
                    row.get("payment_due_date") or "",
                    _fmt_money(row.get("cash_payment_crc")),
                    f"USD {float(row.get('cash_payment_usd') or 0):,.2f}",
                    row.get("transaction_count") or 0,
                    row.get("status") or "",
                ))
            if self.statements and not self.selected_statement_id:
                first = str(self.statements[0].get("id"))
                self.tree_statements.selection_set(first)
                self._load_transactions(int(first))
            self.status_var.set("Estados de cuenta actualizados.")
        except Exception as exc:
            messagebox.showerror("Tarjetas corporativas", f"No se pudo cargar:\n{exc}")

    def _on_statement_select(self, _event=None):
        selection = self.tree_statements.selection()
        if not selection:
            return
        self._load_transactions(int(selection[0]))

    def _load_transactions(self, statement_id):
        self.selected_statement_id = statement_id
        self.pending_changes = {}
        data = get_corporate_card_transactions_api(statement_id) or {}
        self.transactions = data.get("items", [])
        self.tree_tx.delete(*self.tree_tx.get_children())
        total = 0.0
        matched = 0
        pending = 0
        for row in self.transactions:
            total += float(row.get("amount_crc") or row.get("amount_original") or 0)
            if row.get("match_status") == "MATCHED_ITP":
                matched += 1
            if row.get("deductible_status") == "PENDING_REVIEW":
                pending += 1
            self.tree_tx.insert("", "end", iid=str(row.get("id")), values=(
                row.get("transaction_date") or "",
                row.get("user_name") or "",
                row.get("card_last4") or "",
                row.get("merchant") or row.get("description") or "",
                row.get("currency") or "",
                _fmt_money(row.get("amount_crc") or row.get("amount_original")),
                self._account_label(row),
                row.get("match_status") or "",
                row.get("deductible_status") or "",
                row.get("accounting_entry_id") or "",
                row.get("notes") or "",
            ))
        self.lbl_totals.config(
            text=f"Movimientos: {len(self.transactions)} | Cruzados ITP: {matched} | Pendientes fiscal: {pending} | Total visible: {_fmt_money(total)}"
        )

    def _account_label(self, row):
        code = str(row.get("expense_account_code") or "").strip()
        name = str(row.get("expense_account_name") or "").strip()
        category = str(row.get("fiscal_category") or "").strip()
        if code or name:
            return f"{code} {name}".strip()
        if category:
            return category
        return "Sin clasificar"

    def _row_by_id(self, tx_id):
        return next((row for row in self.transactions if int(row.get("id") or 0) == int(tx_id)), None)

    def _update_tx_visual(self, tx_id, patch):
        tx_id = int(tx_id)
        row = self._row_by_id(tx_id)
        if row is not None:
            row.update(patch)
        self.pending_changes.setdefault(tx_id, {"transaction_id": tx_id}).update(patch)
        values = list(self.tree_tx.item(str(tx_id), "values"))
        if values:
            merged = dict(row or {})
            merged.update(self.pending_changes.get(tx_id) or {})
            values[6] = self._account_label(merged)
            values[8] = merged.get("deductible_status") or ""
            values[10] = merged.get("notes") or ""
            self.tree_tx.item(str(tx_id), values=values)
            self.tree_tx.item(str(tx_id), tags=("changed",))
            self.tree_tx.tag_configure("changed", background="#fff7d6")
        self.status_var.set(f"Cambios pendientes: {len(self.pending_changes)}. Pulsa Guardar cambios para ajustar asientos.")

    def _selected_tx_id(self):
        selection = self.tree_tx.selection()
        if not selection:
            messagebox.showwarning("Tarjetas corporativas", "Selecciona un movimiento.")
            return None
        return int(selection[0])

    def _selected_tx_ids(self):
        selection = self.tree_tx.selection()
        if not selection:
            messagebox.showwarning("Tarjetas corporativas", "Selecciona uno o varios movimientos.")
            return []
        return [int(item) for item in selection]

    def _load_expense_options(self):
        try:
            self.accounts = get_accounting_accounts_api() or []
        except Exception:
            self.accounts = []
        existing_codes = {
            preset["expense_account_code"]
            for preset in self.expense_preset_map.values()
            if preset.get("expense_account_code")
        }
        for account in self.accounts:
            code = str(account.get("account_code") or "").strip()
            name = str(account.get("account_name") or "").strip()
            if not code or not name or code in existing_codes:
                continue
            if not (code.startswith("5") or code.startswith("6")):
                continue
            if account.get("active") is False or account.get("accepts_posting") is False:
                continue
            status = "NON_DEDUCTIBLE" if code == "5.4.99" else "DEDUCTIBLE"
            label = f"Catalogo | {code} {name}"
            self.expense_preset_map[label] = {
                "fiscal_category": name,
                "expense_account_code": code,
                "expense_account_name": name,
                "deductible_status": status,
            }
        try:
            values = list(self.expense_preset_map.keys())
            self.cmb_expense.config(values=values)
            if values and not self.cmb_expense.get():
                self.cmb_expense.current(0)
        except Exception:
            pass

    def _import_pdf(self):
        path = filedialog.askopenfilename(
            title="Seleccionar estado de cuenta BAC",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")],
        )
        if not path:
            return
        try:
            result = post_corporate_card_statement_pdf_api(path)
            messagebox.showinfo("Tarjetas corporativas", f"PDF importado. Movimientos nuevos: {result.get('transactions_inserted', 0)}")
            self.selected_statement_id = None
            self._load()
        except Exception as exc:
            messagebox.showerror("Tarjetas corporativas", f"No se pudo importar:\n{exc}")

    def _auto_match(self):
        if not self.selected_statement_id:
            return
        try:
            result = post_corporate_card_auto_match_api(self.selected_statement_id)
            self._load_transactions(self.selected_statement_id)
            messagebox.showinfo("Auto cruce ITP", f"Cruces aplicados: {result.get('matched', 0)}")
        except Exception as exc:
            messagebox.showerror("Auto cruce ITP", str(exc))

    def _classify_selected(self, status, requires_invoice=None):
        tx_id = self._selected_tx_id()
        if not tx_id:
            return
        payload = {"deductible_status": status}
        if requires_invoice is not None:
            payload["requires_invoice"] = requires_invoice
        try:
            self._update_tx_visual(tx_id, payload)
            self.status_var.set("Clasificacion lista. Pulsa Guardar cambios para actualizar el asiento.")
        except Exception as exc:
            messagebox.showerror("Clasificar", str(exc))

    def _apply_expense_preset(self):
        tx_ids = self._selected_tx_ids()
        if not tx_ids:
            return
        selected = self.cmb_expense.get()
        preset = self.expense_preset_map.get(selected)
        if not preset:
            messagebox.showwarning("Rubro/cuenta", "Selecciona un rubro contable.")
            return
        payload = dict(preset)
        payload["requires_invoice"] = False if payload.get("deductible_status") == "NON_DEDUCTIBLE" else True
        for tx_id in tx_ids:
            self._update_tx_visual(tx_id, payload)

    def _match_itp(self):
        tx_id = self._selected_tx_id()
        if not tx_id:
            return
        obligation_id = self._pick_itp_obligation(tx_id)
        if not obligation_id:
            return
        try:
            result = post_corporate_card_match_itp_api(tx_id, obligation_id)
            self._load_transactions(self.selected_statement_id)
            if result.get("blocked_reason"):
                messagebox.showwarning("Cruzar factura ITP", result["blocked_reason"])
            else:
                messagebox.showinfo("Cruzar factura ITP", "Factura cruzada y asiento de pago por tarjeta actualizado.")
        except Exception as exc:
            messagebox.showerror("Cruzar factura ITP", str(exc))

    def _pick_itp_obligation(self, tx_id):
        row = self._row_by_id(tx_id) or {}
        try:
            candidates = (get_corporate_card_match_candidates_api(tx_id) or {}).get("items", [])
        except Exception as exc:
            messagebox.showerror("Cruzar factura ITP", f"No se pudieron cargar obligaciones ITP:\n{exc}")
            return None

        win = tk.Toplevel(self)
        win.title("Cruzar factura ITP")
        win.geometry("1100x520")
        win.transient(self)
        win.grab_set()
        selected_id = tk.IntVar(value=0)

        header = tk.Frame(win, bg="#f7f7f7", bd=1, relief="solid")
        header.pack(fill="x", padx=10, pady=10)
        tx_text = (
            f"Tarjeta: {row.get('transaction_date') or ''} | "
            f"{row.get('merchant') or row.get('description') or ''} | "
            f"{row.get('currency') or ''} {_fmt_money(row.get('amount_crc') or row.get('amount_original'))}"
        )
        tk.Label(header, text=tx_text, bg="#f7f7f7", anchor="w", font=("Segoe UI", 10, "bold")).pack(fill="x", padx=10, pady=6)
        tk.Label(
            header,
            text="Selecciona una obligación pendiente de ITP. La diferencia ayuda a detectar montos que no calzan exacto.",
            bg="#f7f7f7",
            anchor="w",
        ).pack(fill="x", padx=10, pady=(0, 6))

        columns = ("score", "issue", "due", "payee", "reference", "currency", "total", "balance", "delta", "status", "type")
        tree = ttk.Treeview(win, columns=columns, show="headings", height=15)
        headings = {
            "score": "Score",
            "issue": "Fecha",
            "due": "Vence",
            "payee": "Proveedor / comercio",
            "reference": "Documento",
            "currency": "Moneda",
            "total": "Total",
            "balance": "Saldo",
            "delta": "Diferencia",
            "status": "Estado",
            "type": "Tipo",
        }
        widths = {"score": 65, "issue": 90, "due": 90, "payee": 250, "reference": 160, "currency": 70, "total": 115, "balance": 115, "delta": 115, "status": 90, "type": 120}
        for col in columns:
            tree.heading(col, text=headings[col])
            tree.column(col, width=widths[col], anchor="w")
        tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        for item in candidates:
            oid = str(item.get("id"))
            tree.insert("", "end", iid=oid, values=(
                item.get("score") or 0,
                item.get("issue_date") or "",
                item.get("due_date") or "",
                item.get("payee_name") or "",
                item.get("reference") or "",
                item.get("currency") or "",
                _fmt_money(item.get("total")),
                _fmt_money(item.get("balance")),
                _fmt_money(item.get("amount_delta")),
                item.get("status") or "",
                item.get("obligation_type") or item.get("payee_type") or "",
            ))

        if candidates:
            tree.selection_set(str(candidates[0].get("id")))
        else:
            tree.insert("", "end", iid="none", values=("", "", "", "No hay obligaciones ITP pendientes sugeridas.", "", "", "", "", "", "", ""))

        manual = tk.Frame(win)
        manual.pack(fill="x", padx=10, pady=(0, 8))
        tk.Label(manual, text="ID manual:").pack(side="left")
        manual_id = ttk.Entry(manual, width=12)
        manual_id.pack(side="left", padx=6)

        def accept():
            manual_text = manual_id.get().strip()
            if manual_text:
                try:
                    selected_id.set(int(manual_text))
                    win.destroy()
                    return
                except Exception:
                    messagebox.showwarning("Cruzar factura ITP", "El ID manual debe ser numerico.", parent=win)
                    return
            sel = tree.selection()
            if not sel or sel[0] == "none":
                messagebox.showwarning("Cruzar factura ITP", "Selecciona una obligación o escribe un ID manual.", parent=win)
                return
            selected_id.set(int(sel[0]))
            win.destroy()

        tree.bind("<Double-1>", lambda _e: accept())
        buttons = tk.Frame(win)
        buttons.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(buttons, text="Cruzar seleccionada", command=accept).pack(side="right", padx=4)
        ttk.Button(buttons, text="Cancelar", command=win.destroy).pack(side="right", padx=4)

        self.wait_window(win)
        return selected_id.get() or None

    def _set_expense_account(self):
        tx_id = self._selected_tx_id()
        if not tx_id:
            return
        code = simpledialog.askstring("Cuenta gasto", "Codigo de cuenta contable:", parent=self)
        if not code:
            return
        name = simpledialog.askstring("Cuenta gasto", "Nombre de cuenta:", parent=self) or code
        try:
            self._update_tx_visual(tx_id, {
                "fiscal_category": name.strip(),
                "deductible_status": "DEDUCTIBLE",
                "expense_account_code": code.strip(),
                "expense_account_name": name.strip(),
            })
        except Exception as exc:
            messagebox.showerror("Cuenta gasto", str(exc))

    def _save_changes(self):
        if not self.selected_statement_id:
            return
        if not self.pending_changes:
            self.status_var.set("No hay cambios pendientes.")
            return
        payload = {
            "items": list(self.pending_changes.values()),
            "force_closed_periods": True,
        }
        if not messagebox.askyesno(
            "Guardar cambios",
            "Esto guardara la cuenta/rubro fiscal y ajustara los asientos de tarjeta correspondientes, incluso si el periodo esta cerrado. Continuar?",
            parent=self,
        ):
            return
        try:
            result = put_corporate_card_statement_classify_api(self.selected_statement_id, payload)
            self.pending_changes = {}
            self._load_transactions(self.selected_statement_id)
            blocked = result.get("blocked") or []
            msg = f"Movimientos guardados: {result.get('updated', 0)}\nAsientos actualizados: {result.get('posted', 0)}"
            if blocked:
                msg += f"\nPendientes/bloqueados: {len(blocked)}"
            messagebox.showinfo("Guardar cambios", msg)
        except Exception as exc:
            messagebox.showerror("Guardar cambios", str(exc))

    def _post_daily(self):
        if not self.selected_statement_id:
            return
        if not messagebox.askyesno(
            "Contabilizar cargos",
            "Esto genera asientos diarios: factura ITP pagada por tarjeta o gasto contra tarjeta por pagar. Continuar?",
        ):
            return
        try:
            result = post_corporate_card_daily_entries_api(self.selected_statement_id)
            self._load_transactions(self.selected_statement_id)
            messagebox.showinfo("Contabilizar cargos", f"Asientos generados/actualizados: {result.get('posted', 0)}")
        except Exception as exc:
            messagebox.showerror("Contabilizar cargos", str(exc))

    def _post_settlement(self):
        if not self.selected_statement_id:
            return
        try:
            if not self.bank_accounts:
                self.bank_accounts = get_accounting_bank_accounts_api() or []
        except Exception:
            self.bank_accounts = []
        default_bank = ""
        default_name = ""
        if self.bank_accounts:
            row = self.bank_accounts[0]
            default_bank = row.get("account_code") or ""
            default_name = row.get("account_name") or default_bank
        code = simpledialog.askstring("Banco", "Cuenta banco para pagar tarjeta:", initialvalue=default_bank, parent=self)
        if not code:
            return
        name = simpledialog.askstring("Banco", "Nombre cuenta banco:", initialvalue=default_name or code, parent=self) or code
        try:
            result = post_corporate_card_settlement_api(self.selected_statement_id, {
                "bank_account_code": code.strip(),
                "bank_account_name": name.strip(),
            })
            self._load()
            messagebox.showinfo("Liquidar tarjeta", f"Asiento de pago creado: {result.get('entry_id')}")
        except Exception as exc:
            messagebox.showerror("Liquidar tarjeta", str(exc))

    def _post_history(self):
        if not messagebox.askyesno(
            "Historial tarjetas",
            "Esto contabiliza todos los estados BAC 2025-2026 importados, liquida todos menos el mas reciente y deja el ultimo pendiente. Continuar?",
        ):
            return
        try:
            result = post_corporate_card_history_api({
                "years": [2025, 2026],
                "settle_previous": True,
                "leave_latest_pending": True,
                "latest_pending_per_card": True,
                "force_closed_periods": True,
            })
            self._load()
            messagebox.showinfo(
                "Historial tarjetas",
                f"Estados: {result.get('statements', 0)}\nCargos contabilizados: {result.get('posted', 0)}\nEstados pagados: {result.get('settled', 0)}",
            )
        except Exception as exc:
            messagebox.showerror("Historial tarjetas", str(exc))
