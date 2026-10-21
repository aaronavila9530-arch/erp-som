import tkinter as tk
import requests

from api_client import BASE_URL


class DisputesKPIs(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg="white")
        self._build_ui()

    # =====================================================
    # UI
    # =====================================================
    def _build_ui(self):

        self.cards = {}

        container = tk.Frame(self, bg="white")
        container.pack(fill="x", padx=5, pady=5)

        # KPI definitions (color aligned to MSL style)
        kpis = [
            ("ADO", "ADO", "#005A9E"),              # Azul oscuro
            ("DDO", "DDO", "#0078D4"),              # Azul
            ("IncomingVolume", "Incoming", "#00A3C4"),  # Cyan
            ("DisputedAmount", "Disputed", "#00B294")   # Verde
        ]

        for key, label, color in kpis:
            self._create_card(container, key, label, color)

    def _create_card(self, parent, key, label, bg_color):

        card = tk.Frame(
            parent,
            bg=bg_color,
            width=220,
            height=80
        )
        card.pack(side="left", padx=4, fill="both", expand=True)
        card.pack_propagate(False)  # 🔑 mantener tamaño fijo

        # Title
        tk.Label(
            card,
            text=label,
            bg=bg_color,
            fg="white",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="n", pady=(8, 0))

        # Value
        value = tk.Label(
            card,
            text="—",
            bg=bg_color,
            fg="white",
            font=("Segoe UI", 22, "bold")
        )
        value.pack(expand=True)

        self.cards[key] = value

    # =====================================================
    # LOAD KPIs (EXPLICIT CALL)
    # =====================================================
    def load_kpis(self):

        try:
            r = requests.get(
                f"{BASE_URL}/dispute-management/kpis/summary",
                timeout=20
            )
            r.raise_for_status()
            data = r.json()
        except Exception:
            return

        self.cards["ADO"].config(
            text=f"{int(data.get('ADO', 0))}"
        )

        self.cards["DDO"].config(
            text=f"{int(data.get('DDO', 0))}"
        )

        self.cards["IncomingVolume"].config(
            text=str(data.get("IncomingVolume", 0))
        )

        self.cards["DisputedAmount"].config(
            text=f"${data.get('DisputedAmount', 0):,.2f}"
        )
