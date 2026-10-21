import tkinter as tk
from tkinter import ttk, messagebox


class PopupEstadoCuenta(tk.Toplevel):
    """
    Popup para seleccionar idioma (ES/EN), formato (WORD/PDF)
    e ingresar datos bancarios.
    El popup SOLO se cierra si el documento se genera correctamente.
    """

    def __init__(self, parent, on_confirm=None):
        super().__init__(parent)

        self.parent = parent
        self.on_confirm = on_confirm

        self.title("Estado de Cuenta - Datos Bancarios")
        self.geometry("520x470")
        self.resizable(False, False)

        # Modal
        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self._build_ui()

    # ============================================================
    # UI
    # ============================================================
    def _build_ui(self):

        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(
            container,
            text="Generar Estado de Cuenta",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 10))

        # ================= IDIOMA =================
        lang_frame = tk.LabelFrame(container, text="Idioma / Language")
        lang_frame.pack(fill="x", pady=(0, 10))

        self.idioma = tk.StringVar(value="ES")

        row_lang = tk.Frame(lang_frame)
        row_lang.pack(fill="x", padx=10, pady=10)

        tk.Label(row_lang, text="Idioma:").pack(side="left")
        ttk.Combobox(
            row_lang,
            textvariable=self.idioma,
            state="readonly",
            values=["ES", "EN"],
            width=10
        ).pack(side="left", padx=10)

        # ================= FORMATO =================
        format_frame = tk.LabelFrame(container, text="Formato de salida")
        format_frame.pack(fill="x", pady=(0, 10))

        self.formato = tk.StringVar(value="WORD")

        row_format = tk.Frame(format_frame)
        row_format.pack(fill="x", padx=10, pady=10)

        ttk.Radiobutton(
            row_format,
            text="Word (.docx)",
            variable=self.formato,
            value="WORD"
        ).pack(side="left", padx=5)

        ttk.Radiobutton(
            row_format,
            text="PDF",
            variable=self.formato,
            value="PDF"
        ).pack(side="left", padx=15)

        # ================= DATOS BANCARIOS =================
        bank_frame = tk.LabelFrame(
            container,
            text="Datos bancarios (se insertan en el documento)"
        )
        bank_frame.pack(fill="both", expand=True)

        self.var_banco = tk.StringVar()
        self.var_dir_banco = tk.StringVar()
        self.var_moneda = tk.StringVar()
        self.var_swift = tk.StringVar()
        self.var_uid = tk.StringVar()
        self.var_iban = tk.StringVar()

        def field(parent, label, var):
            r = tk.Frame(parent)
            r.pack(fill="x", padx=10, pady=5)
            tk.Label(r, text=label, width=18, anchor="w").pack(side="left")
            ttk.Entry(r, textvariable=var).pack(
                side="left", fill="x", expand=True
            )

        field(bank_frame, "Banco", self.var_banco)
        field(bank_frame, "Dirección", self.var_dir_banco)
        field(bank_frame, "Moneda", self.var_moneda)
        field(bank_frame, "SWIFT Code", self.var_swift)
        field(bank_frame, "UID", self.var_uid)
        field(bank_frame, "IBAN", self.var_iban)

        # ================= BOTONES =================
        actions = tk.Frame(container)
        actions.pack(fill="x", pady=(12, 0))

        ttk.Button(actions, text="Cancelar", command=self._cancelar).pack(side="right")
        ttk.Button(actions, text="Continuar", command=self._confirmar).pack(
            side="right", padx=8
        )

    # ============================================================
    # ACTIONS
    # ============================================================
    def _cancelar(self):
        self.grab_release()
        self.destroy()

    def _confirmar(self):

        if not self.var_banco.get().strip():
            messagebox.showwarning("Validación", "Debe indicar el Banco.")
            return

        # ✅ SOLO datos bancarios reales
        datos_bancarios = {
            "Banco": self.var_banco.get().strip(),
            "Direccion del Banco": self.var_dir_banco.get().strip(),
            "Moneda": self.var_moneda.get().strip(),
            "SWIFT Code": self.var_swift.get().strip(),
            "UID": self.var_uid.get().strip(),
            "IBAN": self.var_iban.get().strip()
        }

        idioma = self.idioma.get().strip()
        formato = self.formato.get()

        if not self.on_confirm:
            messagebox.showerror(
                "Error",
                "No hay acción definida para generar el documento."
            )
            return

        try:
            generado = self.on_confirm(
                idioma,
                formato,
                datos_bancarios
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo generar el estado de cuenta\n\n{e}"
            )
            return

        if generado is True:
            self.grab_release()
            self.destroy()
