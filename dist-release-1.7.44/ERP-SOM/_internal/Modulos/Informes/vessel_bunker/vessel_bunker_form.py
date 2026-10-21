import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import PopupServicioDraftSelector
from tkcalendar import DateEntry

from api_client import (
    create_vessel_bunker_report_api,
    update_vessel_bunker_report_api,
    preview_vessel_bunker_excel_api   # ✅ NUEVO
)

from Modulos.Informes.informes_home_ui import InformesHomeUI




class VesselBunkerReportForm(ttk.Frame):
    """
    ERP-SOM — Vessel Bunker Report Form
    ON HIRE / OFF HIRE / SPOT BUNKER (Single Unified Report)

    UI ULTRA PRO:
    - 2 columnas (aprovecha pantalla)
    - Secciones estilo "certificado" con texto fijo + campos vacíos
    - Tanques dinámicos con botón "+"
    - Bunker Figures con selector de modo (Imagen 2 vs 3)
    - Alineado a tabla vessel_bunker_reports (20 tanques máximo)
    """

    MAX_TANKS = 20

    CERTIFICATE_OPTIONS = ["ON_HIRE", "OFF_HIRE", "SPOT"]

    # Bunker figures modes (según tus imágenes)
    FIGURES_MODE_DELIVERED = "Delivered / ROB / Plus Consumption (Imagen 2)"
    FIGURES_MODE_GENERATOR = "Generator / Departure / Totals (Imagen 3)"

    # =========================================================
    # INIT
    # =========================================================
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back

        # ✅ ID del reporte creado en backend (para luego hacer PUT)
        self.report_id = None

        self.pack(fill="both", expand=True)

        # Vars 1:1 con tabla (excepto tanques que son dinámicos)
        self.vars = {}

        # Tanks dynamic rows storage
        self.vlsfo_rows = []  # list[dict[str, tk.Variable]]
        self.mgo_rows = []
        self.bunker_figure_rows = []

        self._build_ui_ultra_pro()

    # =========================================================
    # UI ROOT (Scrollable)
    # =========================================================
    def _build_ui_ultra_pro(self):

        # =====================================================
        # HEADER BAR (Actions)
        # =====================================================
        topbar = ttk.Frame(self)
        topbar.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(
            topbar,
            text="ON/OFF/SPOT BUNKER SURVEY",
            font=("Segoe UI", 13, "bold")
        ).pack(side="left")

        btn_frame = ttk.Frame(topbar)
        btn_frame.pack(side="right")

        self.btn_select_report = ttk.Button(
            btn_frame,
            text="Seleccionar Reporte",
            command=self._select_draft_service
        )
        self.btn_select_report.pack(side="left", padx=4)

        self.btn_send_review = ttk.Button(
            btn_frame,
            text="Enviar a Revisión",
            command=self._send_to_review
        )
        self.btn_send_review.pack(side="left", padx=4)

        self.btn_edit = ttk.Button(
            btn_frame,
            text="Editar",
            command=self._enable_edit_mode
        )
        self.btn_edit.pack(side="left", padx=4)
        self.btn_edit.pack_forget()

        self.btn_save_changes = ttk.Button(
            btn_frame,
            text="Guardar Cambios",
            command=self._save_changes
        )
        self.btn_save_changes.pack(side="left", padx=4)
        self.btn_save_changes.pack_forget()

        self.btn_visualizar = ttk.Button(
            btn_frame,
            text="Visualizar",
            command=self._visualizar_excel
        )
        self.btn_visualizar.pack(side="left", padx=4)

        ttk.Button(
            btn_frame,
            text="Home",
            command=self._go_home_reports
        ).pack(side="left", padx=4)

        # =====================================================
        # Scrollable Area
        # =====================================================
        self._build_scrollable_area()

        # =====================================================
        # Main 2-column container inside scroll_frame
        # =====================================================
        self.main = ttk.Frame(self.scroll_frame)
        self.main.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)

        left = ttk.Frame(self.main)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.columnconfigure(0, weight=1)

        right = ttk.Frame(self.main)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)

        self._build_header_compact(left)
        self._build_certificate_text_section(left)
        self._build_delivery_point_and_figures(left)
        self._build_signatures_section(left)

        self._build_draft_and_totals(right)
        self._build_tanks_section(right, fuel="vlsfo")
        self._build_tanks_section(right, fuel="mgo")
        self._build_log_book_section(right)
        self._build_consumption_section(right)

        ttk.Label(self.scroll_frame, text="").grid(row=999, column=0, pady=10)


    # =========================================================
    # SCROLLABLE AREA (Vertical + Horizontal)
    # =========================================================
    def _build_scrollable_area(self):

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(container, highlightthickness=0)

        vbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(container, orient="horizontal", command=self.canvas.xview)

        self.canvas.configure(
            yscrollcommand=vbar.set,
            xscrollcommand=hbar.set
        )

        vbar.pack(side="right", fill="y")
        hbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll_frame = ttk.Frame(self.canvas)

        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        # Crear ventana UNA SOLA VEZ
        self._canvas_window_id = self.canvas.create_window(
            (0, 0),
            window=self.scroll_frame,
            anchor="nw"
        )

        # Mouse wheel vertical
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Shift + wheel = horizontal
        def _on_shift_mousewheel(event):
            self.canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

        self.canvas.bind_all("<Shift-MouseWheel>", _on_shift_mousewheel)


    # =========================================================
    # HELPERS (Vars / Widgets)
    # =========================================================
    def _v(self, key: str) -> tk.StringVar:
        if key not in self.vars:
            self.vars[key] = tk.StringVar()
        return self.vars[key]

    def _parse_decimal_for_formula(self, value):
        normalized = self._normalize_numeric_for_db(value)
        if normalized is None:
            return None
        try:
            return float(normalized)
        except Exception:
            return None

    def _refresh_tank_formula_fields(self, row_vars):
        volume = self._parse_decimal_for_formula(row_vars["vol"].get())
        temp_c = self._parse_decimal_for_formula(row_vars["tc"].get())
        density = self._parse_decimal_for_formula(row_vars["den"].get())

        if temp_c is None:
            row_vars["tf"].set("")
        else:
            row_vars["tf"].set(f"{(temp_c * 1.8 + 32):.2f}")

        if volume is None or temp_c is None or density is None:
            row_vars["w"].set("")
            return

        weight = volume * (density - (0.00063 * (temp_c - 15)))
        row_vars["w"].set(f"{round(weight, 2):.2f}")

    def _bind_tank_formula_fields(self, row_vars):
        def _refresh(*_):
            self._refresh_tank_formula_fields(row_vars)

        for key in ("vol", "tc", "den"):
            row_vars[key].trace_add("write", _refresh)

    def _entry(self, parent, label, var_key, row, col=0, width=26):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6, pady=3)
        e = ttk.Entry(parent, textvariable=self._v(var_key), width=width)
        e.grid(row=row, column=col + 1, sticky="ew", padx=6, pady=3)
        parent.columnconfigure(col + 1, weight=1)
        return e

    def _combo(self, parent, label, var_key, values, row, col=0, width=24, readonly=True):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=6, pady=3)
        state = "readonly" if readonly else "normal"
        cb = ttk.Combobox(parent, textvariable=self._v(var_key), values=values, width=width, state=state)
        cb.grid(row=row, column=col + 1, sticky="ew", padx=6, pady=3)
        parent.columnconfigure(col + 1, weight=1)
        return cb

    def _sep(self, parent, row, colspan=12):
        """
        Separador horizontal robusto.
        Usar colspan amplio para layouts con muchas columnas (horas/tablas).
        """
        ttk.Separator(parent).grid(
            row=row,
            column=0,
            columnspan=colspan,
            sticky="ew",
            pady=8
        )

    # =========================================================
    # LEFT: HEADER COMPACT
    # =========================================================
    def _build_header_compact(self, parent):

        box = ttk.LabelFrame(parent, text="Header")
        box.pack(fill="x", pady=(0, 10))

        # compact grid 2 columns
        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=8, pady=8)
        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        # Row 0
        self._entry(inner, "Cert No", "bunker_cert_no", row=0, col=0, width=24)
        self._combo(inner, "Type", "certificate", self.CERTIFICATE_OPTIONS, row=0, col=2, width=22)

        # Row 1
        self._entry(inner, "Ship Name", "ship_name", row=1, col=0, width=24)
        self._entry(inner, "Port of Registry", "port_of_registry", row=1, col=2, width=22)

        # Row 2
        self._entry(inner, "Gross Tonnage", "gross_tonnage", row=2, col=0, width=24)
        ttk.Label(inner, text="Report Date").grid(row=2, column=2, sticky="w", padx=6, pady=3)
        date_entry = DateEntry(
            inner,
            textvariable=self._v("report_date"),
            width=20,
            date_pattern="yyyy-mm-dd"
        )
        date_entry.grid(row=2, column=3, sticky="ew", padx=6, pady=3)

        date_entry.bind(
            "<FocusOut>",
            lambda e: self._format_date_long("report_date")
        )

        # Row 3
        self._entry(inner, "Client", "client", row=3, col=0, width=24)
        self._entry(inner, "Port / Country", "port", row=3, col=2, width=22)

        # Country in same row (small)
        ttk.Label(inner, text="").grid(row=4, column=0)  # spacer
        self._entry(inner, "Country", "country", row=4, col=2, width=22)

        # Report category (kept for future)
        self._entry(inner, "Report Category", "report_category", row=5, col=0, width=24)

    # =========================================================
    # LEFT: CERTIFICATE TEXT (Imagen 1)
    # =========================================================
    def _build_certificate_text_section(self, parent):

        box = ttk.LabelFrame(parent, text="Certificate Text (Fill the blanks)")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=8, pady=8)
        inner.columnconfigure(0, weight=1)

        # Fixed title depends on certificate type (we display, not stored)
        title = ttk.Label(inner, text="ON/OFF/Spot Hire Certificate", font=("Segoe UI", 11, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        # Text blocks with blank fields:
        # We'll map blanks to existing columns where possible.
        # If something doesn't exist in table, we store it in "remarks" later manually (you can extend schema later).

        # Request line
        line1 = ttk.Frame(inner)
        line1.grid(row=1, column=0, sticky="ew", pady=2)
        line1.columnconfigure(3, weight=1)

        ttk.Label(line1, text="At the request of").grid(row=0, column=0, sticky="w")
        ttk.Entry(line1, textvariable=self._v("client"), width=28).grid(row=0, column=1, sticky="w", padx=(6, 6))
        ttk.Label(line1, text=", the undersigned MSL Marine Surveyor, carried out a").grid(row=0, column=2, sticky="w")
        # Certificate combobox already exists, reuse
        ttk.Combobox(
            line1,
            textvariable=self._v("certificate"),
            values=self.CERTIFICATE_OPTIONS,
            state="readonly",
            width=12
        ).grid(row=0, column=3, sticky="w", padx=(6, 0))

        # In the vessel
        line2 = ttk.Frame(inner)
        line2.grid(row=2, column=0, sticky="ew", pady=2)
        ttk.Label(line2, text="Bunker Survey in the vessel").grid(row=0, column=0, sticky="w")
        ttk.Entry(line2, textvariable=self._v("ship_name"), width=26).grid(row=0, column=1, sticky="w", padx=(6, 0))

        self._sep(inner, row=3)

        # 1- ANTECEDENTS (simple fill lines, stored in remarks if needed)
        ttk.Label(inner, text="1- ANTECEDENTS", font=("Segoe UI", 10, "bold")).grid(row=4, column=0, sticky="w")

        a1 = ttk.Frame(inner)
        a1.grid(row=5, column=0, sticky="ew", pady=2)
        a1.columnconfigure(3, weight=1)
        ttk.Label(a1, text="1.1 Vessel arrived to").grid(row=0, column=0, sticky="w")
        ttk.Entry(a1, textvariable=self._v("antecedent_arrived_port"), width=22).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Label(a1, text="on").grid(row=0, column=2, sticky="w")

        arrived_entry = DateEntry(
            a1,
            textvariable=self._v("antecedent_arrived_dt"),
            width=18,
            date_pattern="yyyy-mm-dd"
        )
        arrived_entry.grid(row=0, column=3, sticky="w", padx=6)

        arrived_entry.bind(
             "<FocusOut>",
            lambda e: self._format_date_long("antecedent_arrived_dt")
        )

        a2 = ttk.Frame(inner)
        a2.grid(row=6, column=0, sticky="ew", pady=2)
        for c in range(12):
            a2.columnconfigure(c, weight=0)

        ttk.Label(a2, text="1.2 On").grid(row=0, column=0, sticky="w")

        survey_entry = DateEntry(
            a2,
            textvariable=self._v("antecedent_survey_date_from"),
            width=16,
            date_pattern="yyyy-mm-dd"
        )
        survey_entry.grid(row=0, column=1, sticky="w", padx=4)

        survey_entry.bind(
            "<FocusOut>",
            lambda e: self._format_date_long("antecedent_survey_date_from")
        )

        ttk.Label(a2, text="at").grid(row=0, column=2, sticky="w")

        ttk.Entry(
            a2,
            textvariable=self._v("antecedent_survey_hour_from"),
            width=4
        ).grid(row=0, column=3, sticky="w", padx=2)

        ttk.Label(a2, text=":").grid(row=0, column=4, sticky="w")

        ttk.Entry(
            a2,
            textvariable=self._v("antecedent_survey_minute_from"),
            width=4
        ).grid(row=0, column=5, sticky="w", padx=2)

        ttk.Label(a2, text="LT, survey until").grid(row=0, column=6, sticky="w", padx=(8,2))

        survey_until_entry = DateEntry(
            a2,
            textvariable=self._v("antecedent_survey_date_to"),
            width=16,
            date_pattern="yyyy-mm-dd"
        )
        survey_until_entry.grid(row=0, column=7, sticky="w", padx=4)

        survey_until_entry.bind(
            "<FocusOut>",
            lambda e: self._format_date_long("antecedent_survey_date_to")
        )

        ttk.Entry(
            a2,
            textvariable=self._v("antecedent_survey_hour_to"),
            width=4
        ).grid(row=0, column=8, sticky="w", padx=2)

        ttk.Label(a2, text=":").grid(row=0, column=9, sticky="w")

        ttk.Entry(
            a2,
            textvariable=self._v("antecedent_survey_minute_to"),
            width=4
        ).grid(row=0, column=10, sticky="w", padx=2)

        # 2- INSPECTION (checkbox-ish via combobox yes/no)
        ttk.Label(inner, text="2- INSPECTION", font=("Segoe UI", 10, "bold")).grid(row=8, column=0, sticky="w")

        ins = ttk.Frame(inner)
        ins.grid(row=9, column=0, sticky="ew", pady=2)
        ttk.Label(ins, text="2.1 Joint with").grid(row=0, column=0, sticky="w")
        ttk.Entry(ins, textvariable=self._v("inspection_with"), width=45).grid(row=0, column=1, sticky="w", padx=6)

        self._sep(inner, row=10)

        # 3- REMARK
        ttk.Label(
            inner,
            text="3- REMARK",
            font=("Segoe UI", 10, "bold")
        ).grid(row=11, column=0, sticky="w")

        self.remarks_box = tk.Text(inner, height=5, width=90)
        self.remarks_box.grid(row=12, column=0, sticky="ew", padx=6, pady=4)

        # -------------------------------------------------
        # REMARKS SYNC (FIXED)
        # -------------------------------------------------
        def sync_remarks(event=None):
            try:
                value = self.remarks_box.get("1.0", "end-1c")
                self._v("remarks").set(value.strip())
            except Exception:
                pass

        self.remarks_box.bind("<KeyRelease>", sync_remarks)


    # =========================================================
    # LEFT: DELIVERY POINT + BUNKER FIGURES
    # =========================================================
    def _build_delivery_point_and_figures(self, parent):

        box = ttk.LabelFrame(parent, text="4- DELIVERY POINT + Bunker Figures")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=8, pady=8)
        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)
        inner.columnconfigure(5, weight=1)

        # =====================================================
        # DELIVERY POINT
        # =====================================================

        ttk.Label(inner, text="4.1 DLOSP at").grid(row=0, column=0, sticky="w")
        ttk.Entry(
            inner,
            textvariable=self._v("dslop_port"),
            width=22
        ).grid(row=0, column=1, sticky="ew", padx=6)

        ttk.Label(inner, text="Country").grid(row=0, column=2, sticky="w")
        ttk.Entry(
            inner,
            textvariable=self._v("dslop_country"),
            width=18
        ).grid(row=0, column=3, sticky="ew", padx=6)

        # -------------------------
        # DLOSP DATE + TIME
        # -------------------------
        ttk.Label(inner, text="DLOSP Date").grid(row=1, column=0, sticky="w")

        dslop_entry = DateEntry(
            inner,
            textvariable=self._v("dslop_date"),
            width=18,
            date_pattern="yyyy-mm-dd"
        )
        dslop_entry.grid(row=1, column=1, sticky="w", padx=6)

        dslop_entry.bind(
            "<FocusOut>",
            lambda e: self._format_date_long("dslop_date")
        )

        ttk.Label(inner, text="HH").grid(row=1, column=2, sticky="w")

        ttk.Entry(
            inner,
            textvariable=self._v("dslop_hour"),
            width=4
        ).grid(row=1, column=3, sticky="w", padx=4)

        ttk.Label(inner, text="MM").grid(row=1, column=4, sticky="w")

        ttk.Entry(
            inner,
            textvariable=self._v("dslop_minute"),
            width=4
        ).grid(row=1, column=5, sticky="w", padx=4)


        # =====================================================
        # BUNKER FIGURES (Single Mode – Delivered Only)
        # =====================================================

        ttk.Label(
            inner,
            text="Bunker Figures",
            font=("Segoe UI", 10, "bold")
        ).grid(row=5, column=0, columnspan=6, sticky="w", pady=(4, 6))

        self.fig_delivered = ttk.Frame(inner)
        self.fig_delivered.grid(row=6, column=0, columnspan=6, sticky="ew")

        self._build_figures_delivered(self.fig_delivered)


        # OWNER / CHARTERERS
        self._sep(inner, row=7, colspan=6)

        ttk.Label(inner, text="Owner").grid(row=8, column=0, sticky="w")
        ttk.Entry(
            inner,
            textvariable=self._v("owner_name"),
            width=30
        ).grid(row=8, column=1, columnspan=2, sticky="ew", padx=6)

        ttk.Label(inner, text="Charterers").grid(row=8, column=3, sticky="w")
        ttk.Entry(
            inner,
            textvariable=self._v("charterers_name"),
            width=30
        ).grid(row=8, column=4, columnspan=2, sticky="ew", padx=6)



    def _build_figures_delivered(self, parent):

        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", pady=(0, 6))

        ttk.Label(toolbar, text="Bunker Figures").pack(side="left")

        ttk.Button(
            toolbar,
            text="+ Add",
            command=self._add_bunker_figure_row
        ).pack(side="right")

        table = ttk.Frame(parent)
        table.pack(fill="x")

        headers = ["Bunker Figure", "IFO (MT)", "VLSFO (MT)", "LSMGO (MT)"]

        for c, h in enumerate(headers):
            ttk.Label(
                table,
                text=h,
                font=("Segoe UI", 9, "bold")
            ).grid(row=0, column=c, sticky="w", padx=4, pady=2)
            table.columnconfigure(c, weight=1)

        self.bunker_figures_frame = table


    # =========================================================
    # LEFT: SIGNATURES (Imagen 4)
    # =========================================================
    def _build_signatures_section(self, parent):

        box = ttk.LabelFrame(parent, text="Signatures")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=8, pady=8)
        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        self._entry(inner, "Surveyor Name", "surveyor_name", row=0, col=0, width=22)
        self._entry(inner, "Master Name", "master_name", row=0, col=2, width=22)

        self._entry(inner, "C. Engineer", "chief_engineer_name", row=1, col=0, width=22)

        # These aren't in DB columns (yet). You can later add them.
        # Meanwhile they can be appended into remarks if desired.

    # =========================================================
    # RIGHT: DRAFT + TOTALS
    # =========================================================
    def _build_draft_and_totals(self, parent):

        box = ttk.LabelFrame(parent, text="Bunker Survey Calculations — Draft")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=8, pady=8)
        inner.columnconfigure(1, weight=1)
        inner.columnconfigure(3, weight=1)

        self._entry(inner, "FWD", "draft_fwd", row=0, col=0, width=12)
        self._entry(inner, "AFT", "draft_aft", row=0, col=2, width=12)

        self._entry(inner, "TRIM", "trim", row=1, col=0, width=12)
        self._entry(inner, "LIST", "list", row=1, col=2, width=12)

        # totals summary quick

    # =========================================================
    # RIGHT: TANKS (Dynamic +)
    # =========================================================
    def _build_tanks_section(self, parent, fuel: str):

        if fuel == "vlsfo":
            title = "FUEL OIL — Tanks (Dynamic)"
            rows_store = self.vlsfo_rows
            prefix = "vlsfo"
        else:
            title = "DIESEL / MGO — Tanks (Dynamic)"
            rows_store = self.mgo_rows
            prefix = "mgo"

        box = ttk.LabelFrame(parent, text=title)
        box.pack(fill="x", pady=(0, 10))

        # Toolbar
        toolbar = ttk.Frame(box)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))

        ttk.Label(
            toolbar,
            text=f"Add only the tanks you need (max {self.MAX_TANKS})."
        ).pack(side="left")

        ttk.Button(
            toolbar,
            text="+ Add Tank",
            command=lambda: self._add_tank_row(prefix)
        ).pack(side="right", padx=(6, 0))

        ttk.Button(
            toolbar,
            text="− Remove Last",
            command=lambda: self._remove_last_tank_row(prefix)
        ).pack(side="right")

        # Table header
        table = ttk.Frame(box)
        table.pack(fill="x", padx=8, pady=(0, 8))

        headers = ["Tank Name", "Dist (m)", "Gauge (m)", "Vol (m3)", "Temp °C", "Temp °F", "Density@15C", "Weight MT"]
        for c, h in enumerate(headers):
            ttk.Label(table, text=h, font=("Segoe UI", 9, "bold")).grid(row=0, column=c, sticky="w", padx=4, pady=2)
            table.columnconfigure(c, weight=1)

        # Rows container
        rows_frame = ttk.Frame(table)
        rows_frame.grid(row=1, column=0, columnspan=len(headers), sticky="ew")
        for c in range(len(headers)):
            rows_frame.columnconfigure(c, weight=1)

        if prefix == "vlsfo":
            self.vlsfo_rows_frame = rows_frame
        else:
            self.mgo_rows_frame = rows_frame

        # Start with 0 rows (as requested). User adds with "+"
        # rows_store holds dicts with vars and widget refs if needed.

    def _add_tank_row(self, prefix: str):

        rows_store = self.vlsfo_rows if prefix == "vlsfo" else self.mgo_rows
        rows_frame = self.vlsfo_rows_frame if prefix == "vlsfo" else self.mgo_rows_frame

        if len(rows_store) >= self.MAX_TANKS:
            messagebox.showwarning("Limit", f"Max {self.MAX_TANKS} tanks allowed for {prefix.upper()}.")
            return

        idx = len(rows_store) + 1  # 1-based for DB mapping

        # Map to DB columns
        keys = {
            "name": f"{prefix}_tank_{idx}_name",
            "dist": f"{prefix}_tank_{idx}_dist_mtrs",
            "gauge": f"{prefix}_tank_{idx}_gauge_mtrs",
            "vol": f"{prefix}_tank_{idx}_volume_m3",
            "tc": f"{prefix}_tank_{idx}_temp_c",
            "tf": f"{prefix}_tank_{idx}_temp_f",
            "den": f"{prefix}_tank_{idx}_density_15c",
            "w": f"{prefix}_tank_{idx}_weight_mt",
        }

        # Create vars
        row_vars = {k: self._v(vk) for k, vk in keys.items()}

        # Place widgets (grid row = idx)
        r = idx  # because header row is 0
        e_name = ttk.Entry(rows_frame, textvariable=row_vars["name"], width=16)
        e_name.grid(row=r, column=0, sticky="ew", padx=3, pady=2)

        e_dist = ttk.Entry(rows_frame, textvariable=row_vars["dist"], width=8)
        e_dist.grid(row=r, column=1, sticky="ew", padx=3, pady=2)

        e_gauge = ttk.Entry(rows_frame, textvariable=row_vars["gauge"], width=8)
        e_gauge.grid(row=r, column=2, sticky="ew", padx=3, pady=2)

        e_vol = ttk.Entry(rows_frame, textvariable=row_vars["vol"], width=10)
        e_vol.grid(row=r, column=3, sticky="ew", padx=3, pady=2)

        e_tc = ttk.Entry(rows_frame, textvariable=row_vars["tc"], width=8)
        e_tc.grid(row=r, column=4, sticky="ew", padx=3, pady=2)

        e_tf = ttk.Entry(rows_frame, textvariable=row_vars["tf"], width=8, state="readonly")
        e_tf.grid(row=r, column=5, sticky="ew", padx=3, pady=2)

        e_den = ttk.Entry(rows_frame, textvariable=row_vars["den"], width=10)
        e_den.grid(row=r, column=6, sticky="ew", padx=3, pady=2)

        e_w = ttk.Entry(rows_frame, textvariable=row_vars["w"], width=10, state="readonly")
        e_w.grid(row=r, column=7, sticky="ew", padx=3, pady=2)

        self._bind_tank_formula_fields(row_vars)

        # Store row record
        rows_store.append({
            "idx": idx,
            "vars": row_vars,
            "widgets": [e_name, e_dist, e_gauge, e_vol, e_tc, e_tf, e_den, e_w]
        })

    def _remove_last_tank_row(self, prefix: str):

        rows_store = self.vlsfo_rows if prefix == "vlsfo" else self.mgo_rows
        if not rows_store:
            return

        row = rows_store.pop()

        # Destroy widgets
        for w in row.get("widgets", []):
            try:
                w.destroy()
            except Exception:
                pass

        # Clear corresponding vars (avoid leaking old values)
        for k, v in row.get("vars", {}).items():
            try:
                v.set("")
            except Exception:
                pass

    # =========================================================
    # ENGINE LOG BOOK FIGURES — TABLA COMPLETA
    # =========================================================
    def _build_log_book_section(self, parent):

        box = ttk.LabelFrame(parent, text="ENGINE LOG BOOK FIGURES DECLARATION")
        box.pack(fill="both", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="both", padx=8, pady=8)

        headers = [
            "Event",
            "Date",
            "HH",
            "MM",
            "VLSFO",
            "HFSO",
            "MDO",
            "LSMGO"
        ]

        for c, h in enumerate(headers):
            ttk.Label(
                inner,
                text=h,
                font=("Segoe UI", 9, "bold")
            ).grid(row=0, column=c, padx=4, pady=3, sticky="w")
            inner.columnconfigure(c, weight=1)

        rows = [
            ("E.O.S.P", "log_eosp"),
            ("P.O.B", "log_pob"),
            ("F.W.E", "log_fwe"),
            ("BUNKER ON LOG BOOK FIGURES", "log_bunker"),
            ("LOG BOOK FIGURES AT SURVEY", "log_at_survey"),
        ]

        for r, (label, prefix) in enumerate(rows, start=1):

            ttk.Label(inner, text=label)\
                .grid(row=r, column=0, sticky="w", padx=4, pady=2)

            DateEntry(
                inner,
                textvariable=self._v(f"{prefix}_date"),
                width=14,
                date_pattern="yyyy-mm-dd"
            ).grid(row=r, column=1, padx=3, pady=2, sticky="ew")

            ttk.Entry(
                inner,
                textvariable=self._v(f"{prefix}_hour"),
                width=4
            ).grid(row=r, column=2, padx=3, pady=2)

            ttk.Entry(
                inner,
                textvariable=self._v(f"{prefix}_minute"),
                width=4
            ).grid(row=r, column=3, padx=3, pady=2)

            ttk.Entry(inner, textvariable=self._v(f"{prefix}_vlsfo"), width=10)\
                .grid(row=r, column=4, padx=3, pady=2)

            ttk.Entry(inner, textvariable=self._v(f"{prefix}_hfso"), width=10)\
                .grid(row=r, column=5, padx=3, pady=2)

            ttk.Entry(inner, textvariable=self._v(f"{prefix}_mdo"), width=10)\
                .grid(row=r, column=6, padx=3, pady=2)

            ttk.Entry(inner, textvariable=self._v(f"{prefix}_lsmgo"), width=10)\
                .grid(row=r, column=7, padx=3, pady=2)


    # =========================================================
    # RIGHT: CONSUMPTION (Imagen 10 fija)
    # =========================================================
    def _build_consumption_section(self, parent):

        box = ttk.LabelFrame(parent, text="CONSUMPTION (MT / DAY) — Declared")
        box.pack(fill="x", pady=(0, 10))

        inner = ttk.Frame(box)
        inner.pack(fill="x", padx=8, pady=8)

        headers = ["Events", "Condition", "VLSFO", "HFSO", "MDO", "LSMGO"]
        for c, h in enumerate(headers):
            ttk.Label(inner, text=h, font=("Segoe UI", 9, "bold")).grid(row=0, column=c, sticky="w", padx=4, pady=2)
            inner.columnconfigure(c, weight=1)

        # Rows fixed as in your image
        data_rows = [
            ("AT SEA", "LOADED", "cons_sea_loaded_vlsfo", "cons_sea_loaded_hfso", "cons_sea_loaded_mdo", "cons_sea_loaded_lsmgo"),
            ("AT SEA", "BALLAST", "cons_sea_ballast_vlsfo", "cons_sea_ballast_hfso", "cons_sea_ballast_mdo", "cons_sea_ballast_lsmgo"),
            ("AT PORT", "SHIP GEAR IN USE", "cons_port_ship_gear_vlsfo", "cons_port_ship_gear_hfso", "cons_port_ship_gear_mdo", "cons_port_ship_gear_lsmgo"),
            ("AT PORT", "SHORE GEAR IN USE", "cons_port_shore_gear_vlsfo", "cons_port_shore_gear_hfso", "cons_port_shore_gear_mdo", "cons_port_shore_gear_lsmgo"),
        ]

        for r, (ev, cond, k1, k2, k3, k4) in enumerate(data_rows, start=1):
            ttk.Label(inner, text=ev).grid(row=r, column=0, sticky="w", padx=4, pady=2)
            ttk.Label(inner, text=cond).grid(row=r, column=1, sticky="w", padx=4, pady=2)

            ttk.Entry(inner, textvariable=self._v(k1), width=10).grid(row=r, column=2, sticky="ew", padx=3, pady=2)
            ttk.Entry(inner, textvariable=self._v(k2), width=10).grid(row=r, column=3, sticky="ew", padx=3, pady=2)
            ttk.Entry(inner, textvariable=self._v(k3), width=10).grid(row=r, column=4, sticky="ew", padx=3, pady=2)
            ttk.Entry(inner, textvariable=self._v(k4), width=10).grid(row=r, column=5, sticky="ew", padx=3, pady=2)


    # =========================================================
    # BACK HANDLER
    # =========================================================
    def _handle_back(self):
        try:
            if callable(self.on_back):
                self.on_back()
        except Exception:
            pass
    # =========================================================
    # PAYLOAD (DB ALIGNED STRICT 1:1 WITH DATABASE)
    # =========================================================
    def get_payload(self) -> dict:

        try:
            self.update_idletasks()
        except Exception:
            pass

        # -------------------------------
        # Sync remarks (Text → var)
        # -------------------------------
        try:
            if hasattr(self, "remarks_box"):
                remarks_value = self.remarks_box.get("1.0", "end-1c")
                self._v("remarks").set((remarks_value or "").strip())
        except Exception:
            pass

        payload = {}

        for row in self.vlsfo_rows + self.mgo_rows:
            try:
                self._refresh_tank_formula_fields(row.get("vars", {}))
            except Exception:
                pass

        # =====================================================
        # 1) CAMPOS DIRECTOS (DB)
        # =====================================================
        static_columns = [

            # HEADER
            "bunker_cert_no",
            "ship_name",
            "port_of_registry",
            "gross_tonnage",
            "report_date",
            "certificate",
            "report_category",
            "client",
            "port",
            "country",

            # FECHAS
            "berthing_date",
            "commenced_date",
            "dslop_date",

            # DELIVERY
            "dslop_port",
            "dslop_country",

            # CALCULOS
            "bunker_delivery_declared",
            "rob_diff",
            "plus_consumption",
            "generator_until_aps",
            "cons_dept",
            "me_to_sea_buoy",

            # TEXTO
            "remarks",

            # DRAFT
            "draft",
            "draft_fwd",
            "draft_aft",
            "trim",
            "list",

            # ENGINE LOG
            "log_eosp_vlsfo",
            "log_eosp_hfso",
            "log_eosp_mdo",
            "log_eosp_lsmgo",

            "log_pob_vlsfo",
            "log_pob_hfso",
            "log_pob_mdo",
            "log_pob_lsmgo",

            "log_fwe_vlsfo",
            "log_fwe_hfso",
            "log_fwe_mdo",
            "log_fwe_lsmgo",

            "log_bunker_vlsfo",
            "log_bunker_hfso",
            "log_bunker_mdo",
            "log_bunker_lsmgo",

            "log_at_survey_vlsfo",
            "log_at_survey_hfso",
            "log_at_survey_mdo",
            "log_at_survey_lsmgo",

            # CONSUMPTION
            "cons_sea_loaded_vlsfo",
            "cons_sea_loaded_hfso",
            "cons_sea_loaded_mdo",
            "cons_sea_loaded_lsmgo",

            "cons_sea_ballast_vlsfo",
            "cons_sea_ballast_hfso",
            "cons_sea_ballast_mdo",
            "cons_sea_ballast_lsmgo",

            "cons_port_ship_gear_vlsfo",
            "cons_port_ship_gear_hfso",
            "cons_port_ship_gear_mdo",
            "cons_port_ship_gear_lsmgo",

            "cons_port_shore_gear_vlsfo",
            "cons_port_shore_gear_hfso",
            "cons_port_shore_gear_mdo",
            "cons_port_shore_gear_lsmgo",

            # WORKFLOW
            "workflow_status",
            "status",

            # ANTECEDENTS
            "antecedent_arrived_port",
            "antecedent_arrived_dt",
            "antecedent_survey_date_from",
            "antecedent_survey_date_to",
            "inspection_with",

            # SIGNATURES
            "surveyor_name",
            "master_name",
            "chief_engineer_name",
            "owner_name",
            "charterers_name",

            # LOG DATES
            "log_eosp_date",
            "log_pob_date",
            "log_fwe_date",
            "log_bunker_date",
            "log_at_survey_date",

            # HORAS
            "antecedent_survey_hour_from",
            "antecedent_survey_hour_to",
            "antecedent_survey_minute_from",
            "antecedent_survey_minute_to",

            "dslop_hour",
            "dslop_minute",

            "log_at_survey_hour",
            "log_at_survey_minute",

            "log_bunker_hour",
            "log_bunker_minute",

            "log_eosp_hour",
            "log_eosp_minute",

            "log_fwe_hour",
            "log_fwe_minute",

            "log_pob_hour",
            "log_pob_minute",

            "berthing_hour",
            "berthing_minute",
        ]

        for col in static_columns:
            payload[col] = self._get_var_value(col)

        # =====================================================
        # 2) TANQUES DINÁMICOS
        # =====================================================
        for i in range(1, self.MAX_TANKS + 1):
            for prefix in ("vlsfo", "mgo"):
                for suffix in (
                    "name",
                    "dist_mtrs",
                    "gauge_mtrs",
                    "volume_m3",
                    "temp_c",
                    "temp_f",
                    "density_15c",
                    "weight_mt"
                ):
                    key = f"{prefix}_tank_{i}_{suffix}"
                    payload[key] = self._get_var_value(key)

        # =====================================================
        # 3) BUNKER FIGURES
        # =====================================================
        for i in range(1, 11):
            payload[f"bunker_figure_{i}_name"] = self._get_var_value(f"bunker_figure_{i}_name")
            payload[f"bunker_figure_{i}_ifo"] = self._get_var_value(f"bunker_figure_{i}_ifo")
            payload[f"bunker_figure_{i}_vlsfo"] = self._get_var_value(f"bunker_figure_{i}_vlsfo")
            payload[f"bunker_figure_{i}_lsmgo"] = self._get_var_value(f"bunker_figure_{i}_lsmgo")

        # =====================================================
        # 4) NORMALIZAR HH/MM
        # =====================================================
        for k in payload:
            if "hour" in k:
                payload[k] = self._normalize_hhmm(payload[k], 23)
            if "minute" in k:
                payload[k] = self._normalize_hhmm(payload[k], 59)

        # =====================================================
        # 5) NORMALIZAR FECHAS
        # =====================================================
        for k in payload:
            if "date" in k:
                payload[k] = self._normalize_date_for_db(payload[k])

        # =====================================================
        # 6) NORMALIZAR NUMÉRICOS
        # =====================================================
        numeric_fields = {
            "gross_tonnage",
            "bunker_delivery_declared",
            "rob_diff",
            "plus_consumption",
            "generator_until_aps",
            "cons_dept",
            "me_to_sea_buoy",
            "draft",
            "draft_fwd",
            "draft_aft",
            "trim",
            "list",

            "log_eosp_vlsfo", "log_eosp_hfso", "log_eosp_mdo", "log_eosp_lsmgo",
            "log_pob_vlsfo", "log_pob_hfso", "log_pob_mdo", "log_pob_lsmgo",
            "log_fwe_vlsfo", "log_fwe_hfso", "log_fwe_mdo", "log_fwe_lsmgo",
            "log_bunker_vlsfo", "log_bunker_hfso", "log_bunker_mdo", "log_bunker_lsmgo",
            "log_at_survey_vlsfo", "log_at_survey_hfso", "log_at_survey_mdo", "log_at_survey_lsmgo",

            "cons_sea_loaded_vlsfo", "cons_sea_loaded_hfso", "cons_sea_loaded_mdo", "cons_sea_loaded_lsmgo",
            "cons_sea_ballast_vlsfo", "cons_sea_ballast_hfso", "cons_sea_ballast_mdo", "cons_sea_ballast_lsmgo",
            "cons_port_ship_gear_vlsfo", "cons_port_ship_gear_hfso", "cons_port_ship_gear_mdo", "cons_port_ship_gear_lsmgo",
            "cons_port_shore_gear_vlsfo", "cons_port_shore_gear_hfso", "cons_port_shore_gear_mdo", "cons_port_shore_gear_lsmgo",
        }

        for key in list(payload.keys()):
            if key in numeric_fields:
                payload[key] = self._normalize_numeric_for_db(payload[key])
                continue

            if key.startswith("vlsfo_tank_") or key.startswith("mgo_tank_"):
                if key.endswith((
                    "_volume_m3",
                    "_temp_c",
                    "_temp_f",
                    "_density_15c",
                    "_weight_mt",
                )):
                    payload[key] = self._normalize_numeric_for_db(payload[key])
                continue

            if key.startswith("bunker_figure_") and key.endswith(("_ifo", "_vlsfo", "_lsmgo")):
                payload[key] = self._normalize_numeric_for_db(payload[key])

        # =====================================================
        # 7) LIMPIEZA FINAL
        # =====================================================
        for k, v in payload.items():
            if isinstance(v, str):
                v = v.strip()
                payload[k] = v if v else None

        return payload


    # =========================================================
    # SAFE VAR GETTER
    # =========================================================
    def _get_var_value(self, key: str):
        try:
            if key not in self.vars:
                return None
            val = self.vars[key].get()
            if val is None:
                return None
            val = str(val).strip()
            return val if val else None
        except Exception:
            return None


    # =========================================================
    # NORMALIZE HH/MM
    # =========================================================
    def _normalize_hhmm(self, value, max_value):
        if value is None:
            return None
        s = str(value).strip()
        if not s.isdigit():
            return None
        n = int(s)
        if n < 0 or n > max_value:
            return None
        return f"{n:02d}"


    # =========================================================
    # NORMALIZE DATE
    # =========================================================
    def _normalize_date_for_db(self, value):
        if not value:
            return None

        value = str(value).strip()

        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except:
            pass

        try:
            return datetime.strptime(value, "%B %d, %Y").strftime("%Y-%m-%d")
        except:
            pass

        return value

    # =========================================================
    # NORMALIZE NUMERIC FOR DB
    # =========================================================
    def _normalize_numeric_for_db(self, value):
        """
        Normaliza numéricos para PostgreSQL:
        - "" -> None
        - "4,65" -> "4.65"
        - "1.234,56" -> "1234.56"
        - "1,234.56" -> "1234.56"
        - limpia espacios
        - si no es numérico válido, devuelve el valor original
        """
        if value is None:
            return None

        s = str(value).strip()
        if not s:
            return None

        s = s.replace(" ", "")

        # Si trae coma y punto, decidir cuál es decimal
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                # Formato europeo: 1.234,56
                s = s.replace(".", "")
                s = s.replace(",", ".")
            else:
                # Formato US: 1,234.56
                s = s.replace(",", "")
        elif "," in s:
            # Caso simple: 4,65 -> 4.65
            s = s.replace(",", ".")

        try:
            float(s)
            return s
        except Exception:
            return None


    # =========================================================
    # SET PAYLOAD (BLINDADO + DINÁMICOS)
    # =========================================================
    # =========================================================
    # SET PAYLOAD / LOAD RECORD
    # =========================================================
    def set_payload(self, data: dict, from_review: bool = False):

        data = data or {}

        try:
            rid = data.get("id")
            if rid is not None:
                self.report_id = int(rid)
        except Exception:
            pass

        for k, v in data.items():
            try:
                self._v(str(k)).set("" if v is None else str(v))
            except Exception:
                pass

        try:
            if hasattr(self, "remarks_box"):
                self.remarks_box.delete("1.0", "end")
                self.remarks_box.insert("1.0", self._v("remarks").get() or "")
        except Exception:
            pass

        self._rebuild_dynamic_tanks_from_data("vlsfo", data)
        self._rebuild_dynamic_tanks_from_data("mgo", data)
        self._rebuild_bunker_figures_from_data(data)

        if from_review:
            self._enter_review_mode()
        else:
            self._enable_edit_mode()


    # =========================================================
    # REVIEW / EDIT MODE
    # =========================================================
    def _enter_review_mode(self):

        try:
            self.btn_send_review.pack_forget()
        except Exception:
            pass

        try:
            self.btn_save_changes.pack_forget()
        except Exception:
            pass

        try:
            self.btn_edit.pack(side="left", padx=4)
        except Exception:
            pass

        self._set_form_locked_state(True)


    def _enable_edit_mode(self):

        try:
            self.btn_edit.pack_forget()
        except Exception:
            pass

        try:
            self.btn_send_review.pack_forget()
        except Exception:
            pass

        try:
            self.btn_save_changes.pack(side="left", padx=4)
        except Exception:
            pass

        self._set_form_locked_state(False)


    def _iter_form_widgets(self, parent):

        for child in parent.winfo_children():
            yield child
            yield from self._iter_form_widgets(child)


    def _set_form_locked_state(self, locked: bool):

        root = getattr(self, "scroll_frame", self)

        for widget in self._iter_form_widgets(root):

            if isinstance(widget, tk.Text):
                try:
                    widget.configure(state="disabled" if locked else "normal")
                except Exception:
                    pass
                continue

            try:
                widget_class = widget.winfo_class()
            except Exception:
                widget_class = ""

            if widget_class in ("TEntry", "TCombobox", "DateEntry"):
                try:
                    widget.configure(state="disabled" if locked else "normal")
                except Exception:
                    pass

        for btn_name in ("btn_select_report", "btn_visualizar", "btn_send_review"):
            try:
                getattr(self, btn_name).config(state="disabled" if locked else "normal")
            except Exception:
                pass


    # =========================================================
    # SAVE CHANGES
    # =========================================================
    def _save_changes(self):

        try:
            if not self.report_id:
                messagebox.showwarning(
                    "Guardar Cambios",
                    "No se encontró el ID del reporte."
                )
                return

            payload = self.get_payload()

            resp = update_vessel_bunker_report_api(
                self.report_id,
                payload
            )

            if not resp or not resp.get("success"):
                raise Exception(
                    resp.get("detail") or resp.get("error") or "No se pudo actualizar el reporte."
                )

            messagebox.showinfo(
                "Guardar Cambios",
                "Reporte actualizado correctamente."
            )

        except Exception as e:
            messagebox.showerror(
                "Guardar Cambios",
                str(e)
            )


    # =========================================================
    # REBUILD BUNKER FIGURES FROM DATA (NUEVO)
    # =========================================================
    def _rebuild_bunker_figures_from_data(self, data: dict):

        # limpiar filas existentes (deja header row=0 intacto)
        try:
            for w in list(self.bunker_figures_frame.winfo_children()):
                try:
                    info = w.grid_info() or {}
                    if int(info.get("row", 0)) >= 1:
                        w.destroy()
                except Exception:
                    pass
        except Exception:
            pass

        self.bunker_figure_rows = []

        # cuántas filas mostrar (hasta la última no vacía)
        max_rows = 10  # mismo máximo del backend
        last_idx = 0

        for i in range(1, max_rows + 1):
            n = str(data.get(f"bunker_figure_{i}_name", "") or "").strip()
            ifo = str(data.get(f"bunker_figure_{i}_ifo", "") or "").strip()
            vlsfo = str(data.get(f"bunker_figure_{i}_vlsfo", "") or "").strip()
            lsmgo = str(data.get(f"bunker_figure_{i}_lsmgo", "") or "").strip()
            if n or ifo or vlsfo or lsmgo:
                last_idx = i

        # crear filas y setear values
        for i in range(1, last_idx + 1):

            # crea fila (engancha vars)
            self._add_bunker_figure_row()

            for key in (
                f"bunker_figure_{i}_name",
                f"bunker_figure_{i}_ifo",
                f"bunker_figure_{i}_vlsfo",
                f"bunker_figure_{i}_lsmgo",
            ):
                try:
                    self._v(key).set("" if data.get(key) is None else str(data.get(key)))
                except Exception:
                    pass

    def _rebuild_dynamic_tanks_from_data(self, prefix: str, data: dict):

        # Clear current dynamic rows visually
        if prefix == "vlsfo":
            while self.vlsfo_rows:
                self._remove_last_tank_row("vlsfo")
        else:
            while self.mgo_rows:
                self._remove_last_tank_row("mgo")

        # Decide how many rows to show: up to last non-empty slot
        last_idx = 0
        for i in range(1, self.MAX_TANKS + 1):
            name = str(data.get(f"{prefix}_tank_{i}_name", "") or "").strip()
            vol = str(data.get(f"{prefix}_tank_{i}_volume_m3", "") or "").strip()
            wt = str(data.get(f"{prefix}_tank_{i}_weight_mt", "") or "").strip()
            if name or vol or wt:
                last_idx = i

        # Add rows up to last_idx
        for i in range(1, last_idx + 1):
            self._add_tank_row(prefix)

            # Now set values for slot i
            for suffix in ("name", "dist_mtrs", "gauge_mtrs", "volume_m3", "temp_c", "temp_f", "density_15c", "weight_mt"):
                key = f"{prefix}_tank_{i}_{suffix}"
                if key not in self.vars:
                    self.vars[key] = tk.StringVar()
                try:
                    self.vars[key].set(str(data.get(key, "") or ""))
                except Exception:
                    pass

            rows_store = self.vlsfo_rows if prefix == "vlsfo" else self.mgo_rows
            if rows_store:
                try:
                    self._refresh_tank_formula_fields(rows_store[-1].get("vars", {}))
                except Exception:
                    pass


    # =========================================================
    # SELECT DRAFT SERVICE (POPUP)
    # =========================================================
    def _select_draft_service(self):

        PopupServicioDraftSelector(
            self.parent,
            on_select=self._on_draft_selected
        )



    def _on_draft_selected(self, values):

        if not values:
            return

        (
            num_informe,
            buque,
            cliente,
            continente,
            pais,
            puerto,
            operacion,
            fecha_inicio
        ) = values

        # 🔹 Llenar campos principales
        self._v("bunker_cert_no").set(num_informe or "")
        self._v("report_category").set(operacion or "")
        self._v("ship_name").set(buque or "")
        self._v("client").set(cliente or "")
        self._v("port").set(puerto or "")
        self._v("country").set(pais or "")
        self._v("report_date").set(str(fecha_inicio)[:10] if fecha_inicio else "")

        # 🔹 Bloquear campos críticos
        readonly_fields = [
            "bunker_cert_no",
            "report_category",
            "ship_name",
            "client",
            "port",
            "country",
            "report_date"
        ]

        for field in readonly_fields:
            widget = self._find_widget_by_var(field)
            if widget:
                try:
                    if isinstance(widget, ttk.Entry):
                        widget.configure(state="readonly")
                    elif isinstance(widget, ttk.Combobox):
                        widget.configure(state="disabled")
                    elif isinstance(widget, DateEntry):
                        widget.configure(state="disabled")
                except Exception:
                    pass

    def _find_widget_by_var(self, var_key):

        target = str(self._v(var_key))

        def search(widget):
            for child in widget.winfo_children():

                try:
                    if isinstance(child, (ttk.Entry, ttk.Combobox, DateEntry)):
                        if str(child.cget("textvariable")) == target:
                            return child
                except Exception:
                    pass

                result = search(child)
                if result:
                    return result

            return None

        return search(self)

    def _format_date_long(self, var_key):

        value = self._v(var_key).get()
        if not value:
            return

        value = value.strip()

        # Si viene en ISO
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            self._v(var_key).set(dt.strftime("%B %d, %Y"))
            return
        except Exception:
            pass

        # Si ya está en formato largo válido
        try:
            datetime.strptime(value, "%B %d, %Y")
            return
        except Exception:
            pass


    def _add_bunker_figure_row(self):

        idx = len(self.bunker_figure_rows) + 1
        frame = self.bunker_figures_frame

        name_var = self._v(f"bunker_figure_{idx}_name")
        ifo_var = self._v(f"bunker_figure_{idx}_ifo")
        vlsfo_var = self._v(f"bunker_figure_{idx}_vlsfo")
        lsmgo_var = self._v(f"bunker_figure_{idx}_lsmgo")

        r = idx

        e_name = ttk.Entry(frame, textvariable=name_var, width=18)
        e_name.grid(row=r, column=0, sticky="ew", padx=3, pady=2)

        e_ifo = ttk.Entry(frame, textvariable=ifo_var, width=10)
        e_ifo.grid(row=r, column=1, sticky="ew", padx=3, pady=2)

        e_vlsfo = ttk.Entry(frame, textvariable=vlsfo_var, width=10)
        e_vlsfo.grid(row=r, column=2, sticky="ew", padx=3, pady=2)

        e_lsmgo = ttk.Entry(frame, textvariable=lsmgo_var, width=10)
        e_lsmgo.grid(row=r, column=3, sticky="ew", padx=3, pady=2)

        self.bunker_figure_rows.append({
            "widgets": [e_name, e_ifo, e_vlsfo, e_lsmgo]
        })



    def _normalize_hhmm(self, value: str, max_value: int):
        """
        Normaliza HH/MM:
        - "" -> None
        - "9" -> "09"
        - valida rango
        """
        if value is None:
            return None

        s = str(value).strip()
        if not s:
            return None

        if not s.isdigit():
            return None

        n = int(s)
        if n < 0 or n > max_value:
            return None

        return f"{n:02d}"

    # =========================================================
    # NAV: HOME INFORMES
    # =========================================================
    def _go_home_reports(self):
        """
        Abre InformesHomeUI en el mismo contenedor (parent).
        Sin rutas Windows hardcode.
        """
        try:
            # destruir el form actual
            try:
                self.destroy()
            except Exception:
                pass

            # cargar home
            InformesHomeUI(
                self.parent,
                usuario=self.usuario,
                rol=self.rol
            )

        except Exception as e:
            messagebox.showerror("Home", f"No se pudo abrir Informes Home.\n{e}")

    # =========================================================
    # SEND TO REVIEW (POST + luego PUT si ya existe)
    # =========================================================
    def _send_to_review(self):

        try:
            payload = self.get_payload()

            # estado workflow
            payload["workflow_status"] = "Pending Review"

            # status general de tabla (si lo usas)
            payload.setdefault("status", "Pending")

            # ✅ si ya existe report_id -> PUT, si no -> POST
            if True:
                resp = create_vessel_bunker_report_api(payload)
                if not resp or not resp.get("success"):
                    raise Exception(resp.get("detail") or resp.get("error") or "Error creating report")

                data = resp.get("data") or {}
                self.report_id = data.get("id")

            elif False:
                resp = update_vessel_bunker_report_api(self.report_id, payload)
                if not resp or not resp.get("success"):
                    raise Exception(resp.get("detail") or resp.get("error") or "Error updating report")

            messagebox.showinfo("Enviado", "Informe enviado a revisión.")

        except Exception as e:
            messagebox.showerror("Revisión", f"No se pudo enviar a revisión.\n{e}")


    # =========================================================
    # VISUALIZAR (PREVIEW — NO USA DB)
    # =========================================================
    def _visualizar_excel(self):

        try:
            # 🔥 TOMA DIRECTAMENTE LOS DATOS DEL FORM
            payload = self.get_payload()

            # Opcional: marcar como preview
            payload["workflow_status"] = "DRAFT PREVIEW"

            resp = preview_vessel_bunker_excel_api(payload)

            if not resp.get("success"):
                raise Exception(
                    resp.get("detail")
                    or resp.get("error")
                    or "Error generando Excel preview"
                )

            content = resp.get("content")

            if not content:
                raise Exception("No se recibió contenido del archivo.")

            # ---------------------------------------------
            # Guardar archivo temporal
            # ---------------------------------------------
            import tempfile
            import os

            tmp_dir = tempfile.mkdtemp(prefix="bunker_preview_")
            file_path = os.path.join(
                tmp_dir,
                "vessel_bunker_preview.xlsx"
            )

            with open(file_path, "wb") as f:
                f.write(content)

            # ---------------------------------------------
            # Abrir automáticamente
            # ---------------------------------------------
            os.startfile(file_path)

        except Exception as e:
            messagebox.showerror(
                "Visualizar",
                f"No se pudo generar el Excel preview.\n{e}"
            )


    # =========================================================
    # SAVE
    # =========================================================
    def _save_report(self):

        payload = self.get_payload()

        messagebox.showinfo("Guardar", "Payload listo para enviar al backend.")
        # Aquí conectas tu API create/update

