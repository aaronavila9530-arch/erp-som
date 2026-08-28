import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    get_vessel_grain_sampling_by_id_api,
    update_vessel_grain_sampling_api
)


class PopupVesselGrainSamplingPreview(tk.Toplevel):

    def __init__(self, parent, report_id: int):
        super().__init__(parent)

        self.report_id = report_id
        self.report = {}
        self.edit_mode = False

        self.title("Vessel Grain Sampling — Preview")
        self.geometry("1200x900")
        self.minsize(1000, 700)

        self._build_ui()
        self._load_report()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        header = ttk.Frame(self)
        header.pack(fill="x", padx=12, pady=10)

        ttk.Label(
            header,
            text="Vessel Grain Sampling Report — Preview",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        self.btn_edit = ttk.Button(header, text="✏ Edit", command=self._enable_edit)
        self.btn_edit.pack(side="right", padx=5)

        self.btn_save = ttk.Button(header, text="💾 Save", command=self._save_changes, state="disabled")
        self.btn_save.pack(side="right", padx=5)

        canvas = tk.Canvas(self)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        self.body = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        self._bind_mousewheel(canvas)

        self._sec_header()
        self._sec_main()
        self._sec_ship()
        self._sec_times()
        self._sec_products()
        self._sec_sampling()
        self._sec_supervision()
        self._sec_conclusion()

    # =========================================================
    # HELPER
    # =========================================================
    def _entry(self, parent, label, key, row):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=6, pady=3)
        e = ttk.Entry(parent, width=40, state="readonly")
        e.grid(row=row, column=1, sticky="w", padx=6, pady=3)
        setattr(self, f"f_{key}", e)

    # =========================================================
    # SECTIONS
    # =========================================================
    def _sec_header(self):
        frm = ttk.LabelFrame(self.body, text="Report Header")
        frm.pack(fill="x", padx=12, pady=8)
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Cert Nº", "cert_no", 0)
        self._entry(grid, "Place Date", "place_date", 1)

    def _sec_main(self):
        frm = ttk.LabelFrame(self.body, text="Main Information")
        frm.pack(fill="x", padx=12, pady=8)
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Vessel", "vessel_name", 0)
        self._entry(grid, "Requested By", "requested_by", 1)
        self._entry(grid, "Captain", "captain", 2)
        self._entry(grid, "Chief Officer", "chief_officer", 3)

    def _sec_ship(self):
        frm = ttk.LabelFrame(self.body, text="Ship Data")
        frm.pack(fill="x", padx=12, pady=8)
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Flag", "ship_flag", 0)
        self._entry(grid, "GRT", "ship_grt", 1)
        self._entry(grid, "NRT", "ship_nrt", 2)
        self._entry(grid, "IMO", "ship_imo", 3)
        self._entry(grid, "Year Built", "ship_year", 4)

    def _sec_times(self):
        frm = ttk.LabelFrame(self.body, text="Operational Times")
        frm.pack(fill="x", padx=12, pady=8)
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        fields = [
            "arrival_buoy_time",
            "nor_tendered_time",
            "holds_opening_time",
            "surveyors_onboard_time",
            "seals_verification_time",
            "sampling_start_time",
            "sampling_end_time",
            "surveyors_disembark_time"
        ]

        for i, f in enumerate(fields):
            self._entry(grid, f.replace("_", " ").title(), f, i)

    # =========================================================
    # PRODUCTS (5 FIJOS)
    # =========================================================
    def _sec_products(self):

        frm = ttk.LabelFrame(self.body, text="Products")
        frm.pack(fill="x", padx=12, pady=8)

        ttk.Label(frm, text="Products Total").grid(row=0, column=0, sticky="w", padx=6)
        self.f_products_total = ttk.Entry(frm, width=20, state="readonly")
        self.f_products_total.grid(row=0, column=1, padx=6)

        self.hold_entries = []

        for i in range(1, 6):
            ttk.Label(frm, text=f"Hold {i} Product").grid(row=i, column=0, sticky="w", padx=6)
            prod = ttk.Entry(frm, width=25, state="readonly")
            prod.grid(row=i, column=1, padx=6)

            ttk.Label(frm, text=f"Hold {i}").grid(row=i, column=2, sticky="w", padx=6)
            hold = ttk.Entry(frm, width=8, state="readonly")
            hold.grid(row=i, column=3, padx=6)

            ttk.Label(frm, text=f"Hold {i} Tonnage").grid(row=i, column=4, sticky="w", padx=6)
            ton = ttk.Entry(frm, width=15, state="readonly")
            ton.grid(row=i, column=5, padx=6)

            self.hold_entries.append((prod, hold, ton))

    # =========================================================
    # SAMPLING (3 BLOQUES)
    # =========================================================
    def _sec_sampling(self):

        frm = ttk.LabelFrame(self.body, text="Sampling Points")
        frm.pack(fill="x", padx=12, pady=8)

        self.sample_entries = []

        positions = [
            "hold",
            "proa_babor",
            "proa_estribor",
            "centro",
            "popa_babor",
            "popa_estribor"
        ]

        for s in range(1, 6):

            ttk.Label(frm, text=f"Sample {s}", font=("Segoe UI", 10, "bold")).grid(row=(s-1)*7, column=0, pady=(10,2))

            entries = {}

            for i, pos in enumerate(positions):
                ttk.Label(frm, text=pos.replace("_", " ").title()).grid(row=(s-1)*7 + i + 1, column=0, sticky="w", padx=6)
                e = ttk.Entry(frm, width=25, state="readonly")
                e.grid(row=(s-1)*7 + i + 1, column=1, padx=6)
                entries[pos] = e

            self.sample_entries.append(entries)

    def _sec_supervision(self):
        frm = ttk.LabelFrame(self.body, text="Supervision")
        frm.pack(fill="x", padx=12, pady=8)
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Supervision", "supervision", 0)

    def _sec_conclusion(self):
        frm = ttk.LabelFrame(self.body, text="Conclusion")
        frm.pack(fill="both", expand=True, padx=12, pady=8)

        self.conclusion = tk.Text(
            frm,
            height=6,
            wrap="word",
            bg="white",
            fg="black",
            relief="solid",
            borderwidth=1
        )
        self.conclusion.pack(fill="both", expand=True, padx=6, pady=6)

        # Iniciar como solo lectura sin usar disabled
        self.conclusion.bind("<Key>", lambda e: "break")

    # =========================================================
    # ENABLE EDIT
    # =========================================================
    def _enable_edit(self):

        self.edit_mode = True
        self.btn_save.config(state="normal")

        for attr in dir(self):
            if attr.startswith("f_"):
                getattr(self, attr).configure(state="normal")

        for prod, hold, ton in self.hold_entries:
            prod.configure(state="normal")
            hold.configure(state="normal")
            ton.configure(state="normal")

        for sample in self.sample_entries:
            for e in sample.values():
                e.configure(state="normal")

        # habilitar edición en conclusion
        self.conclusion.unbind("<Key>")

    # =========================================================
    # SAVE
    # =========================================================
    def _save_changes(self):

        payload = {}

        # campos simples
        for attr in dir(self):
            if attr.startswith("f_"):
                key = attr.replace("f_", "")
                payload[key] = getattr(self, attr).get().strip()

        # holds
        for i, (prod, hold, ton) in enumerate(self.hold_entries, start=1):
            payload[f"hold{i}_product"] = prod.get().strip()
            payload[f"hold{i}_hold"] = hold.get().strip()
            payload[f"hold{i}_tonnage"] = ton.get().strip()

        # sampling
        for s_index, sample in enumerate(self.sample_entries, start=1):
            for key, entry in sample.items():
                payload[f"sample{s_index}_{key}"] = entry.get().strip()

        payload["conclusion"] = self.conclusion.get("1.0", "end").strip()

        try:
            update_vessel_grain_sampling_api(self.report_id, payload)
            messagebox.showinfo("Success", "Report updated successfully.")
            self.edit_mode = False
            self.btn_save.config(state="disabled")
            self._load_report()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # FILL
    # =========================================================
    def _fill(self):

        for k, v in self.report.items():
            if hasattr(self, f"f_{k}"):
                e = getattr(self, f"f_{k}")
                e.configure(state="normal")
                e.delete(0, "end")
                e.insert(0, v or "")
                e.configure(state="readonly")

        # holds
        for i, (prod, hold, ton) in enumerate(self.hold_entries, start=1):
            prod.configure(state="normal")
            prod.delete(0, "end")
            prod.insert(0, self.report.get(f"hold{i}_product") or "")
            prod.configure(state="readonly")

            hold.configure(state="normal")
            hold.delete(0, "end")
            hold.insert(0, self.report.get(f"hold{i}_hold") or str(i))
            hold.configure(state="readonly")

            ton.configure(state="normal")
            ton.delete(0, "end")
            ton.insert(0, self.report.get(f"hold{i}_tonnage") or "")
            ton.configure(state="readonly")

        # sampling
        for s_index, sample in enumerate(self.sample_entries, start=1):
            for key, entry in sample.items():
                entry.configure(state="normal")
                entry.delete(0, "end")
                entry.insert(0, self.report.get(f"sample{s_index}_{key}") or "")
                entry.configure(state="readonly")

        # conclusion
        self.conclusion.unbind("<Key>")
        self.conclusion.delete("1.0", "end")
        self.conclusion.insert("1.0", self.report.get("conclusion") or "")
        self.conclusion.bind("<Key>", lambda e: "break")

    # =========================================================
    # LOAD
    # =========================================================
    def _load_report(self):
        try:
            resp = get_vessel_grain_sampling_by_id_api(self.report_id)
            self.report = resp.get("data", {})
            self._fill()
        except Exception as e:
            messagebox.showerror("Error", f"Error loading report:\n{e}")

    def _bind_mousewheel(self, canvas):

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind(_):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind(_):
            canvas.unbind_all("<MouseWheel>")

        self.body.bind("<Enter>", _bind)
        self.body.bind("<Leave>", _unbind)
