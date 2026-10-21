import tkinter as tk
from tkinter import ttk, messagebox
import requests

from api_client import BASE_URL
from Modulos.Finanzas.date_utils import to_long_english_date


STATUSES = [
    "New",
    "In process",
    "Process by Sales",
    "Process by RTR",
    "Process by Invoicing",
    "Process by Collections",
    "Process by Bank",
    "Process by Disputes",
    "Written Off",
    "Resolved"
]


class PopupDisputeManagement(tk.Toplevel):

    def __init__(self, parent, dispute_id, on_success=None):
        super().__init__(parent)

        self.dispute_id = dispute_id
        self.management_id = None
        self.on_success = on_success

        self.title("Dispute Management")
        self.geometry("560x520")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self._build_ui()
        self._load_or_create_management()
        self._load_history()

    # =====================================================
    # UI
    # =====================================================
    def _build_ui(self):

        frm = tk.Frame(self)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        self.lbl_title = tk.Label(
            frm,
            text=f"Dispute ID: {self.dispute_id}",
            font=("Segoe UI", 9, "bold")
        )
        self.lbl_title.pack(anchor="w", pady=(0, 8))

        # ---------------- STATUS ----------------
        tk.Label(frm, text="Status").pack(anchor="w")
        self.status = ttk.Combobox(
            frm,
            values=STATUSES,
            state="readonly"
        )
        self.status.pack(fill="x")

        # ---------------- HISTORY ----------------
        tk.Label(frm, text="Historial").pack(anchor="w", pady=(10, 0))
        self.history = tk.Text(
            frm,
            height=12,
            state="disabled",
            wrap="word"
        )
        self.history.pack(fill="both", expand=True)

        # ---------------- NEW COMMENT ----------------
        tk.Label(frm, text="Nuevo comentario").pack(anchor="w", pady=(10, 0))
        self.comment = tk.Text(frm, height=4, wrap="word")
        self.comment.pack(fill="x")

        # ---------------- SAVE ----------------
        ttk.Button(
            frm,
            text="Guardar cambios",
            command=self._save
        ).pack(fill="x", pady=10)

    # =====================================================
    # CREAR / OBTENER MANAGEMENT
    # =====================================================
    def _load_or_create_management(self):

        try:
            r = requests.post(
                f"{BASE_URL}/dispute-management/from-dispute/{self.dispute_id}",
                timeout=20
            )
            r.raise_for_status()
            data = r.json()

            self.management_id = data["management_id"]

            self.lbl_title.config(
                text=f"Dispute ID: {self.dispute_id} | Management ID: {self.management_id}"
            )

            if data.get("status"):
                self.status.set(data["status"])

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo inicializar la gestión de la disputa:\n{e}"
            )
            self.destroy()

    # =====================================================
    # HISTORY
    # =====================================================
    def _load_history(self):

        if not self.management_id:
            return

        try:
            r = requests.get(
                f"{BASE_URL}/dispute-management/{self.management_id}/history",
                timeout=15
            )
            r.raise_for_status()
            data = r.json()
        except Exception:
            return

        self.history.config(state="normal")
        self.history.delete("1.0", "end")

        for row in data:
            self.history.insert(
                "end",
                f"[{to_long_english_date(row['created_at'])}] {row.get('created_by', '')}:\n"
                f"{row['comentario']}\n\n"
            )

        self.history.config(state="disabled")

    # =====================================================
    # SAVE STATUS + COMMENT
    # =====================================================
    def _save(self):

        if not self.status.get():
            messagebox.showwarning(
                "Validación",
                "Seleccione un status"
            )
            return

        payload = {
            "status": self.status.get(),
            "comentario": self.comment.get("1.0", "end").strip(),
            "user": "ERP-USER"
        }

        try:
            r = requests.post(
                f"{BASE_URL}/dispute-management/{self.management_id}/status",
                json=payload,
                timeout=20
            )
            r.raise_for_status()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        if self.on_success:
            self.on_success()

        self.destroy()
