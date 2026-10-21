import tkinter as tk
from tkinter import ttk
from api_client import get_container_report_by_id_api
from api_client import update_container_report_api


class PopupContainerReportPreview(tk.Toplevel):
    """
    Preview 1:1 del Container Inspection Report
    (alineado exactamente al ContainerReportForm)
    """

    def __init__(self, parent, report: dict):
        super().__init__(parent)

        self.report_id = report.get("id")
        self.report = {}

        self.title("Container Inspection Report — Preview")
        self.geometry("1200x850")
        self.minsize(900, 600)

        self.resizable(True, True)
        self.state("normal")

        self._build_ui()
        self._load_report()

    # =========================================================
    # UI BASE
    # =========================================================
    def _build_ui(self):

        header = ttk.Frame(self)
        header.pack(fill="x", padx=12, pady=10)

        ttk.Label(
            header,
            text="Container Inspection Report — Preview",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        ttk.Button(
            header,
            text="✏ Edit",
            command=self._enable_edit
        ).pack(side="right", padx=5)

        ttk.Button(
            header,
            text="💾 Save",
            command=self._save_changes
        ).pack(side="right", padx=5)

        canvas = tk.Canvas(self)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        self.body = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=self.body, anchor="nw")

        self.body.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        self._sec_report_link()
        self._sec_general_information()
        self._sec_container_description()
        self._sec_cause_of_inspection()
        self._sec_goods_and_packages()
        self._sec_package_type()
        self._sec_qty_packages()
        self._sec_narratives()
        self._sec_collected_documents()
        self._sec_quality()
        self._sec_inspected_container()
        self._sec_general_details()
        self._sec_transfer_to_container()
        self._sec_scope_of_inspection()
        self._sec_persons()

    # =========================================================
    # HELPERS
    # =========================================================
    def _entry(self, parent, label, key, row, col=0, width=30, readonly=True):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6, pady=3)
        e = ttk.Entry(parent, width=width)
        e.grid(row=row, column=col + 1, sticky="w", padx=6, pady=3)
        if readonly:
            e.configure(state="readonly")
        setattr(self, f"f_{key}", e)

    def _text(self, parent, title, key, height=4, readonly=True):
        frm = ttk.LabelFrame(parent, text=title)
        frm.pack(fill="x", padx=12, pady=8)
        t = tk.Text(frm, height=height, wrap="word")
        t.pack(fill="x", padx=6, pady=6)
        if readonly:
            t.configure(state="disabled")
        setattr(self, f"t_{key}", t)

    def _check(self, parent, label, key):
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(parent, text=label, variable=var, state="disabled")
        cb.pack(side="left", padx=10)
        setattr(self, f"c_{key}", var)
        setattr(self, f"cb_{key}", cb)

    # =========================================================
    # SECTIONS
    # =========================================================
    def _sec_report_link(self):
        frm = ttk.LabelFrame(self.body, text="Report Link")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Report Number", "linked_report_number", 0)
        self._entry(grid, "Container Type", "container_type_text", 1)

    def _sec_general_information(self):
        frm = ttk.LabelFrame(self.body, text="General Information")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "No.", "report_no", 0)
        self._entry(grid, "B / L", "bl", 1)
        self._entry(grid, "Seals", "seals", 2)
        self._entry(grid, "Appointment", "appointment", 3)
        self._entry(grid, "Shippers", "shippers", 4)

        self._entry(grid, "Inspection Place", "inspection_place", 0, 2, 40)
        self._entry(grid, "Contact Person", "contact_person", 1, 2, 40)
        self._entry(grid, "On Behalf Of", "on_behalf_of", 3, 2, 40)
        self._entry(grid, "Consignee / Notify", "consignee_notify", 4, 2, 40)

        self._entry(grid, "Vessel", "vessel", 0, 4)
        self._entry(grid, "Contact D/Time", "contact_datetime", 1, 4)
        self._entry(grid, "Init Insp. D/Time", "init_inspection_datetime", 2, 4)
        self._entry(grid, "Init To", "init_to", 2, 6)
        self._entry(grid, "Final Insp. D/Time", "final_inspection_datetime", 3, 4)
        self._entry(grid, "Final To", "final_to", 3, 6)

    def _sec_container_description(self):
        frm = ttk.LabelFrame(self.body, text="Container Description")
        frm.pack(fill="x", padx=12, pady=8)

        row = ttk.Frame(frm)
        row.pack(fill="x", pady=4)
        self._check(row, "20 Foot", "container_size_20")
        self._check(row, "40 Foot", "container_size_40")

        row = ttk.Frame(frm)
        row.pack(fill="x", pady=4)
        self._check(row, "Dry", "container_type_dry")
        self._check(row, "Reefer", "container_type_reefer")
        self._check(row, "ISO Tank", "container_type_iso")
        self._check(row, "Flat Rack", "container_type_flat_rack")

        row = ttk.Frame(frm)
        row.pack(fill="x", pady=4)
        self._check(row, "FCL", "container_load_fcl")
        self._check(row, "LCL", "container_load_lcl")

    def _sec_cause_of_inspection(self):
        frm = ttk.LabelFrame(self.body, text="Cause of Inspection")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=6)

        for lbl, key in [
            ("Seals ≠ BL", "cause_seals_bl"),
            ("Change Seals", "cause_change_seals"),
            ("Customs", "cause_customs"),
            ("Transfer", "cause_transfer"),
            ("Leaking", "cause_leaking"),
            ("Damage", "cause_damage"),
            ("Stuff / D Condition", "cause_stuff_condition"),
        ]:
            self._check(grid, lbl, key)

        self._text(frm, "Detail of Cause", "cause_detail", 3)

    def _sec_goods_and_packages(self):
        frm = ttk.LabelFrame(self.body, text="Goods & Packages")
        frm.pack(fill="x", padx=12, pady=8)

        self._text(frm, "Goods Description", "goods_description", 3)
        self._text(frm, "Package & Marking Description", "package_marking", 3)
        self._text(frm, "Goods Condition", "goods_condition", 3)

    def _sec_package_type(self):
        frm = ttk.LabelFrame(self.body, text="Type of Package")
        frm.pack(fill="x", padx=12, pady=8)

        row = ttk.Frame(frm)
        row.pack(fill="x")

        for key in [
            "package_carton","package_bags","package_boxes","package_drums",
            "package_pallets","package_bulk","package_bales","package_crates","package_other"
        ]:
            self._check(row, key.replace("package_", "").title(), key)

    def _sec_qty_packages(self):
        frm = ttk.LabelFrame(self.body, text="Qty Of Packages")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        for i in range(1, 4):
            self._entry(grid, f"{i}st Left", f"qty_{i}_left", i - 1)
            self._entry(grid, f"{i}st Right", f"qty_{i}_right", i - 1, 2)


    def _sec_narratives(self):
        self._text(self.body, "Details of Damage / Shortage", "damage_details", 5)
        self._text(self.body, "Remarks", "remarks", 5)
        self._text(self.body, "Conclusion", "conclusion", 5)
        self._text(self.body, "Picture Link", "picture_link", 2)

    def _sec_collected_documents(self):
        frm = ttk.LabelFrame(self.body, text="Collected Documents")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack()

        for lbl, key in [
            ("B/L", "doc_bl"),
            ("Packing List", "doc_packing_list"),
            ("Shipping Invoice", "doc_shipping_invoice"),
            ("Cargo Manifest", "doc_cargo_manifest"),
            ("Commercial Invoice", "doc_commercial_invoice"),
            ("Delivery Record", "doc_delivery_record"),
            ("Notice of Loss", "doc_notice_loss"),
            ("Insurance Policy", "doc_insurance_policy"),
            ("Other", "doc_other"),
        ]:
            self._check(grid, lbl, key)

    def _sec_quality(self):
        frm = ttk.LabelFrame(self.body, text="Quality")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack()

        for key in [
            "quality_packing_exam","quality_un_witness","quality_visual_exam",
            "quality_product_exam","quality_documents","quality_sanitary_cert",
            "quality_phytosanitary_cert","quality_factory_cert","quality_origin_cert"
        ]:
            self._check(grid, key.replace("quality_", "").replace("_", " ").title(), key)

    def _sec_inspected_container(self):
        frm = ttk.LabelFrame(self.body, text="Inspected Container")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Manuf. Nº", "ic_manuf", 0)
        self._entry(grid, "CSC Saf. Apr.", "ic_csc", 1)
        self._entry(grid, "Max Gross Weight", "ic_max_gw", 2)
        self._entry(grid, "Tare", "ic_tare", 3)

    def _sec_general_details(self):
        frm = ttk.LabelFrame(self.body, text="General Details")
        frm.pack(fill="x", padx=12, pady=8)

        # --- Checkboxes (pack) ---
        checks = ttk.Frame(frm)
        checks.pack(fill="x", padx=6, pady=4)

        self._check(checks, "New Commodity", "new_commodity")
        self._check(checks, "Used Commodity", "used_commodity")

        # --- Entries (grid) ---
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Net Weight", "net_weight", 0)
        self._entry(grid, "Gross Weight", "gross_weight", 1)
        self._entry(grid, "Volume", "volume", 2)

    def _sec_transfer_to_container(self):
        frm = ttk.LabelFrame(self.body, text="Transfer To Container")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Number", "tr_number", 0)
        self._entry(grid, "Manuf. Nº", "tr_manuf", 1)
        self._entry(grid, "CSC Saf. Apr.", "tr_csc", 2)
        self._entry(grid, "Seal Nº", "tr_seal", 3)
        self._entry(grid, "Max Gross Weight", "tr_max_gw", 4)
        self._entry(grid, "Tare", "tr_tare", 5)

    def _sec_scope_of_inspection(self):
        frm = ttk.LabelFrame(self.body, text="Scope of Inspection")
        frm.pack(fill="x", padx=12, pady=8)

        # --- Checkboxes (pack) ---
        checks = ttk.Frame(frm)
        checks.pack(fill="x", padx=6, pady=4)

        self._check(checks, "100%", "scope_100")
        self._check(checks, "Random", "scope_random")

        # --- Entries (grid) ---
        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Nº Items", "scope_items", 0)

    def _sec_persons(self):
        frm = ttk.LabelFrame(self.body, text="Persons Present at Survey")
        frm.pack(fill="x", padx=12, pady=8)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", padx=6, pady=4)

        self._entry(grid, "Person 1 Name", "person_1_name", 0, width=60)
        self._entry(grid, "Person 1 Position", "person_1_position", 1, width=60)
        self._entry(grid, "Person 2 Name", "person_2_name", 2, width=60)
        self._entry(grid, "Person 2 Position", "person_2_position", 3, width=60)
        self._entry(grid, "Person 3 Name", "person_3_name", 4, width=60)
        self._entry(grid, "Person 3 Position", "person_3_position", 5, width=60)

    # =========================================================
    # LOGIC
    # =========================================================
    def _enable_edit(self):
        for attr in dir(self):
            if attr.startswith("f_"):
                getattr(self, attr).configure(state="normal")
            elif attr.startswith("t_"):
                getattr(self, attr).configure(state="normal")
            elif attr.startswith("cb_"):
                getattr(self, attr).configure(state="normal")

    def _save_changes(self):
        payload = {}

        # -----------------------------
        # Entries
        # -----------------------------
        for attr in dir(self):
            if attr.startswith("f_"):
                key = attr.replace("f_", "")
                val = getattr(self, attr).get().strip()
                if val != "":
                    payload[key] = val

        # -----------------------------
        # Text fields
        # -----------------------------
        for attr in dir(self):
            if attr.startswith("t_"):
                key = attr.replace("t_", "")
                txt = getattr(self, attr).get("1.0", "end").strip()
                if txt != "":
                    payload[key] = txt

        # -----------------------------
        # Checkboxes
        # -----------------------------
        for attr in dir(self):
            if attr.startswith("c_"):
                key = attr.replace("c_", "")
                payload[key] = bool(getattr(self, attr).get())

        # -----------------------------
        # Guardar en backend
        # -----------------------------
        update_container_report_api(
            self.report.get("id"),
            payload
        )

        # -----------------------------
        # Volver a modo preview
        # -----------------------------
        for attr in dir(self):
            if attr.startswith("f_"):
                getattr(self, attr).configure(state="readonly")
            elif attr.startswith("t_"):
                getattr(self, attr).configure(state="disabled")
            elif attr.startswith("cb_"):
                getattr(self, attr).configure(state="disabled")

    def _fill(self):
        for k, v in self.report.items():
            if hasattr(self, f"f_{k}"):
                e = getattr(self, f"f_{k}")
                e.configure(state="normal")
                e.delete(0, "end")
                e.insert(0, v or "")
                e.configure(state="readonly")
            if hasattr(self, f"t_{k}"):
                t = getattr(self, f"t_{k}")
                t.configure(state="normal")
                t.delete("1.0", "end")
                t.insert("1.0", v or "")
                t.configure(state="disabled")
            if hasattr(self, f"c_{k}"):
                getattr(self, f"c_{k}").set(bool(v))


    def _load_report(self):
        try:
            resp = get_container_report_by_id_api(self.report_id)

            # Backend devuelve {"data": {...}}
            self.report = resp.get("data", {})

            self._fill()

        except Exception as e:
            tk.messagebox.showerror(
                "Error",
                f"Error loading report:\n{e}"
            )

