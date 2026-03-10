import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None


class DraftSurveyForm(ttk.Frame):
    """
    ERP-SOM — Draft Survey Form

    Ubicación del módulo (relativa al proyecto):
    Modulos\\Informes\\Vessel_Draft_Survey\\draft_survey_form.py

    ✅ Tabs:
      - General
      - Draft
      - Ballast
      - Word Report

    🔗 Listo para backend:
      - self.get_payload() -> dict completo (inputs)
      - self.set_payload(data) -> carga datos
    """
    # =========================================================
    # INIT
    # =========================================================
    def __init__(
        self,
        parent,
        usuario=None,
        rol=None,
        on_back=None,
        mode="create",
        draft_report_number=None
    ):

        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.on_back = on_back

        # =========================================================
        # MODE CONTROL (CREATE / EDIT)
        # =========================================================
        self.mode = mode
        self.draft_report_number = draft_report_number
        self._edit_mode = False

        # Referencia al botón editar (la definiremos luego)
        self.btn_editar = None

        # Map de widgets: key -> widget (Entry/DateEntry/Text)
        self.fields = {}
        self.vars = {}

        # =========================================================
        # SAP HEADER META (READONLY - NO PAYLOAD)
        # =========================================================
        self.meta_vars = {
            "anio": tk.StringVar(value=""),
            "mes": tk.StringVar(value=""),
            "continente": tk.StringVar(value=""),  # 🔥 AGREGAR
            "pais": tk.StringVar(value=""),
            "puerto": tk.StringVar(value=""),
            "cliente": tk.StringVar(value=""),
            "num_informe": tk.StringVar(value="")
        }

        # =========================================================
        # SAP STYLE (GRIS CORPORATIVO)
        # =========================================================
        self._sap_bg = "#E9ECEF"
        self._sap_font_label = ("Segoe UI", 8, "bold")
        self._sap_font_value = ("Segoe UI", 8)

        self.grid(row=0, column=0, sticky="nsew")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

        # =========================================================
        # DB AUTOLOAD FLAG (solo si entró a editar desde un draft real)
        # =========================================================
        self._db_autoload_enabled = bool(self.mode == "edit" and self.draft_report_number)

        # =========================================================
        # INITIAL MODE LOGIC
        # =========================================================
        if self.mode == "edit" and self.draft_report_number:
            self._load_existing_draft()
        else:
            if self.btn_editar:
                self.btn_editar.config(state="disabled")


    # =========================================================
    # HEADER
    # =========================================================
    def _build_header(self):

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))

        # 3 columnas:
        # 0 -> título
        # 1 -> botón back
        # 2 -> botones acción
        header.grid_columnconfigure(0, weight=1)

        # ---------------- TÍTULO ----------------
        ttk.Label(
            header,
            text="Vessel Draft Survey",
            font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, sticky="w")

        # ---------------- BACK ----------------
        if self.on_back:
            ttk.Button(
                header,
                text="← Back",
                command=self.on_back
            ).grid(row=0, column=1, padx=(10, 0))

        # ---------------- BOTONES ACCIÓN ----------------
        actions = ttk.Frame(header)
        actions.grid(row=0, column=2, sticky="e")

        ttk.Button(
            actions,
            text="Seleccionar Reporte",
            command=self._open_servicio_selector
        ).grid(row=0, column=0, padx=(0, 8))

        ttk.Button(
            actions,
            text="Visualizar Draft",
            command=self._visualizar_draft
        ).grid(row=0, column=1, padx=(0, 8))

        self.btn_editar = ttk.Button(
            actions,
            text="Editar",
            command=self._editar
        )
        self.btn_editar.grid(row=0, column=2, padx=(0, 8))

        # ✅ NUEVO: Guardar (MISMO FLUJO que Enviar a revisión)
        ttk.Button(
            actions,
            text="Guardar",
            command=self._guardar
        ).grid(row=0, column=3, padx=(0, 8))

        ttk.Button(
            actions,
            text="Enviar a revisión",
            command=self._enviar_revision
        ).grid(row=0, column=4)

    # =========================================================
    # BODY (NOTEBOOK + SCROLL)
    # =========================================================
    def _build_body(self):

        container = ttk.Frame(self)
        container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(container)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Tabs
        self.tab_general = ttk.Frame(self.notebook)
        self.tab_draft = ttk.Frame(self.notebook)
        self.tab_ballast = ttk.Frame(self.notebook)
        self.tab_word = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_general, text="General")
        self.notebook.add(self.tab_draft, text="Draft")
        self.notebook.add(self.tab_ballast, text="Ballast")
        self.notebook.add(self.tab_word, text="Word Report")

        # Scrollable bodies (UNA SOLA VEZ)
        self.general_body = self._make_scrollable(self.tab_general)
        self.draft_body = self._make_scrollable(self.tab_draft)
        self.ballast_body = self._make_scrollable(self.tab_ballast)
        self.word_body = self._make_scrollable(self.tab_word)

        # Build content
        self._build_general_tab(self.general_body)
        self._build_draft_tab(self.draft_body)
        self._build_ballast_tab(self.ballast_body)
        self._build_word_tab(self.word_body)

    def _make_scrollable(self, parent):

        outer = ttk.Frame(parent)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        sb.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=sb.set)

        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            # Ajustar ancho del frame interno al ancho del canvas
            canvas.itemconfigure(inner_id, width=event.width)

        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        return inner

    # =========================================================
    # SAP METADATA HEADER (READONLY, GRIS, 4 TABS)
    # =========================================================
    def _build_sap_metadata_header(self, parent):

        lf = tk.LabelFrame(
            parent,
            text="Draft Information",
            bg=self._sap_bg,
            fg="#333333",
            font=("Segoe UI", 8, "bold"),
            bd=1,
            relief="groove",
            padx=8,
            pady=6
        )
        lf.pack(fill="x", padx=8, pady=(8, 10))

        # Grid responsive
        for c in range(12):
            lf.grid_columnconfigure(c, weight=1)

        # -----------------------------------------------------
        # Helpers internos
        # -----------------------------------------------------
        def _label(row, col, text):
            tk.Label(
                lf,
                text=text,
                bg=self._sap_bg,
                fg="#333333",
                font=self._sap_font_label
            ).grid(row=row, column=col, sticky="w", padx=(2, 6), pady=(0, 2))

        def _value(row, col, var, width=18):
            e = ttk.Entry(
                lf,
                textvariable=var,
                width=width,
                state="readonly"
            )
            e.grid(row=row, column=col, sticky="w", padx=(0, 12), pady=(0, 2))
            return e

        # -----------------------------------------------------
        # Row 0
        # -----------------------------------------------------
        _label(0, 0, "Año")
        _value(0, 1, self.meta_vars["anio"], width=10)

        _label(0, 2, "Mes")
        _value(0, 3, self.meta_vars["mes"], width=10)

        _label(0, 4, "País")
        _value(0, 5, self.meta_vars["pais"], width=20)

        _label(0, 6, "Puerto")
        _value(0, 7, self.meta_vars["puerto"], width=20)

        # -----------------------------------------------------
        # Row 1
        # -----------------------------------------------------
        _label(1, 0, "Cliente")
        _value(1, 1, self.meta_vars["cliente"], width=35)

        _label(1, 4, "Núm. Informe")
        _value(1, 5, self.meta_vars["num_informe"], width=22)

        ttk.Separator(parent).pack(fill="x", padx=8, pady=(0, 10))

    # =========================================================
    # BUILD: GENERAL TAB (IMAGEN 1)
    # =========================================================
    def _build_general_tab(self, parent):

        # ================= SAP HEADER =================
        self._build_sap_metadata_header(parent)

        # ---------------- Vessel / Survey ----------------
        lf_vessel = ttk.LabelFrame(parent, text="Vessel / Survey")
        lf_vessel.pack(fill="x", pady=8)

        self._row_2cols(
            lf_vessel, 0,
            left=("vessel_mv", "Vessel MV", 34),
            right=("survey_no", "Survey no", 24)
        )
        self._row_2cols(
            lf_vessel, 1,
            left=("call_letters", "Call letters", 24),
            right=("vessel_previous_names", "Vessel previous name/s", 34)
        )
        self._row_2cols(
            lf_vessel, 2,
            left=("flag", "Flag", 24),
            right=("registry", "Registry", 24)
        )
        self._row_2cols(
            lf_vessel, 3,
            left=("built_year", "Built year", 10),
            right=("by", "By", 34)
        )

        # ---------------- People / Witness / Parties ----------------
        lf_people = ttk.LabelFrame(parent, text="People / Parties")
        lf_people.pack(fill="x", pady=8)

        self._row_2cols(
            lf_people, 0,
            left=("master", "Master", 34),
            right=("initial_surveyors", "Initial Surveyor/s", 34)
        )
        self._row_2cols(
            lf_people, 1,
            left=("chief_officer", "Chief Officer", 34),
            right=("final_surveyors", "Final Surveyor/s", 34)
        )
        self._row_2cols(
            lf_people, 2,
            left=("chief_engineer", "Chief Engineer", 34),
            right=("survey_requested_by", "Survey requested by", 34)
        )
        self._row_2cols(
            lf_people, 3,
            left=("witness_draughts", "Witness draughts", 34),
            right=("on_account_of", "On the account of", 34)
        )
        self._row_2cols(
            lf_people, 4,
            left=("witness_sounding", "Witness sounding", 34),
            right=("attended_also_by", "Attended also by", 34)
        )

        # ---------------- Locations ----------------
        lf_locations = ttk.LabelFrame(parent, text="Locations")
        lf_locations.pack(fill="x", pady=8)

        self._row_2cols(
            lf_locations, 0,
            left=("init_ships_location", "Init Ship's location", 34),
            right=("final_ships_location", "Final Ship's location", 34)
        )

        # ---------------- Dimensions ----------------
        lf_dims = ttk.LabelFrame(parent, text="Ship Dimensions")
        lf_dims.pack(fill="x", pady=8)

        self._row_2cols(lf_dims, 0, left=("length_overall", "Length overall", 18),
                       right=("length_between_pp", "Length between p.p.", 18))
        self._row_2cols(lf_dims, 1, left=("extreme_breadth", "Extreme breadth", 18),
                       right=("moulded_breadth", "Moulded breadth", 18))
        self._row_2cols(lf_dims, 2, left=("depth_overall_incl_keel_plate", "Depth overall incl. keel plate", 18),
                       right=("moulded_depth", "Moulded depth", 18))
        self._row_2cols(lf_dims, 3, left=("summer_draught", "Summer draught", 18),
                       right=("summer_freeboard", "Summer freeboard", 18))

        # ---------------- Constants / Displacement ----------------
        lf_constants = ttk.LabelFrame(parent, text="Constants / Displacement")
        lf_constants.pack(fill="x", pady=8)

        self._row_2cols(lf_constants, 0, left=("constant_declared", "Constant declared", 18),
                       right=("constant_calculated", "Constant calculated", 18))
        self._row_2cols(lf_constants, 1, left=("light_displacement", "Light displacement", 18),
                       right=("light_shipweight_plan", "Light shipweight (plan)", 18))
        self._row_2cols(lf_constants, 2, left=("summer_displacement", "Summer displacement", 18),
                       right=("summer_deadweight", "Summer deadweight", 18))
        self._row_2cols(lf_constants, 3, left=("net_register_tons", "Net register tons", 18),
                       right=("gross_register_tons", "Gross register tons", 18))

        # ---------------- Hydrostatic / Tables ----------------
        lf_hydro = ttk.LabelFrame(parent, text="Hydrostatic / Tables")
        lf_hydro.pack(fill="x", pady=8)

        self._row_1col(lf_hydro, 0, key="hydro_tables_issued", label="Ship's approved hydrostatic tables and lightship information issued by and dated", width=70)

        # Print options (YES/NO)
        row = ttk.Frame(lf_hydro)
        row.grid(row=1, column=0, sticky="ew", padx=8, pady=6)
        row.grid_columnconfigure(1, weight=1)

        ttk.Label(row, text="Range of trim correction tables available").grid(row=0, column=0, sticky="w")
        yes_var = tk.BooleanVar(value=True)
        no_var = tk.BooleanVar(value=False)

        # Guardamos como fields para payload
        self.fields["trim_tables_yes"] = yes_var
        self.fields["trim_tables_no"] = no_var

        cb_yes = ttk.Checkbutton(row, text="YES", variable=yes_var,
                                command=lambda: self._toggle_yes_no(yes_var, no_var))
        cb_no = ttk.Checkbutton(row, text="NO", variable=no_var,
                               command=lambda: self._toggle_yes_no(no_var, yes_var))

        cb_yes.grid(row=0, column=1, sticky="w", padx=(10, 0))
        cb_no.grid(row=0, column=2, sticky="w", padx=(10, 0))

        self._row_1col(lf_hydro, 2, key="hydrometer_no", label="Hydrometer no", width=30)

        # Padding grid config
        for i in range(4):
            lf_hydro.grid_columnconfigure(i, weight=1)

        # Spacer bottom
        ttk.Label(parent, text="").pack(pady=5)


    # =========================================================
    # BUILD: DRAFT TAB (ALINEADO 1:1 CON EXCEL)
    # =========================================================
    def _build_draft_tab(self, parent):

        # ================= SAP HEADER =================
        self._build_sap_metadata_header(parent)

        # ================= TOP BLOCK (NUEVO) =================
        self._draft_top_block(parent)

        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, pady=8)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        lf_initial = ttk.LabelFrame(container, text="INITIAL SURVEY")
        lf_final = ttk.LabelFrame(container, text="FINAL SURVEY")

        lf_initial.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        lf_final.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        # ================= INITIAL =================
        self._draft_header_block(lf_initial, prefix="init")
        self._draft_readings_block(lf_initial, prefix="init")
        self._draft_extra_block(lf_initial, prefix="init")
        self._draft_liquids_block(lf_initial, prefix="init")
        self._draft_bl_block(lf_initial, prefix="init")

        # ================= FINAL =================
        self._draft_header_block(lf_final, prefix="final", include_cargo_ports=False)
        self._draft_readings_block(lf_final, prefix="final")
        self._draft_extra_block(lf_final, prefix="final")
        self._draft_liquids_block(lf_final, prefix="final")
        self._draft_bl_block(lf_final, prefix="final")

        # ================= SIGNATURES =================
        self._draft_signatures_block(parent)

        # ================= HYDROSTATIC =================
        # 🔒 SOLO INITIAL — SE ELIMINA FINAL
        self._draft_hydro_block(parent, prefix="init")

        ttk.Label(parent, text="").pack(pady=5)

    # =========================================================
    # TOP BLOCK (GLOBAL CARGO + INITIAL / FINAL TIMES)
    # =========================================================
    def _draft_top_block(self, parent):

        block = ttk.LabelFrame(parent, text="Survey Overview")
        block.pack(fill="x", padx=8, pady=(8, 10))
        block.grid_columnconfigure(0, weight=1)

        # =====================================================
        # GLOBAL ROW
        # =====================================================
        global_row = ttk.Frame(block)
        global_row.grid(row=0, column=0, sticky="ew", padx=8, pady=6)

        col = 0

        # ---------------- CARGO ----------------
        ttk.Label(global_row, text="Cargo").grid(row=0, column=col, padx=(0, 4))
        col += 1
        cargo = ttk.Entry(global_row, width=24)
        cargo.grid(row=0, column=col, padx=4)
        self.fields["cargo"] = cargo
        col += 1

        # ---------------- PORT FROM ----------------
        ttk.Label(global_row, text="From").grid(row=0, column=col, padx=(20, 4))
        col += 1
        port_from = ttk.Entry(global_row, width=20)
        port_from.grid(row=0, column=col, padx=4)
        self.fields["port_from"] = port_from
        col += 1

        # ---------------- PORT TO ----------------
        ttk.Label(global_row, text="To").grid(row=0, column=col, padx=(15, 4))
        col += 1
        port_to = ttk.Entry(global_row, width=20)
        port_to.grid(row=0, column=col, padx=4)
        self.fields["port_to"] = port_to
        col += 1

        # =====================================================
        # OPERATION TYPE (MUTUAMENTE EXCLUSIVO)
        # =====================================================
        loading_var = tk.BooleanVar(value=True)
        unloading_var = tk.BooleanVar(value=False)

        def toggle_loading():
            if loading_var.get():
                unloading_var.set(False)
            elif not unloading_var.get():
                loading_var.set(True)

        def toggle_unloading():
            if unloading_var.get():
                loading_var.set(False)
            elif not loading_var.get():
                unloading_var.set(True)

        self.fields["loading"] = loading_var
        self.fields["unloading"] = unloading_var

        ttk.Checkbutton(
            global_row,
            text="Loading",
            variable=loading_var,
            command=toggle_loading
        ).grid(row=0, column=col, padx=(20, 4))

        col += 1

        ttk.Checkbutton(
            global_row,
            text="Unloading",
            variable=unloading_var,
            command=toggle_unloading
        ).grid(row=0, column=col, padx=4)

        # =====================================================
        # INITIAL
        # =====================================================
        self._draft_time_row(block, row_index=1, prefix="init", title="INITIAL")

        # =====================================================
        # FINAL
        # =====================================================
        self._draft_time_row(block, row_index=2, prefix="final", title="FINAL")



    # =========================================================
    # HEADER BLOCK (SIN DATE - YA ESTÁ EN TOP BLOCK)
    # =========================================================
    def _draft_header_block(self, parent, prefix: str, include_cargo_ports: bool = True):

        block = ttk.LabelFrame(parent, text="Header")
        block.pack(fill="x", padx=8, pady=(8, 6))

        # Este bloque queda vacío por ahora
        # Si luego agregas más campos específicos, van aquí
        pass


    # =========================================================
    # TIME ROW (INITIAL / FINAL)
    # =========================================================
    def _draft_time_row(self, parent, row_index, prefix: str, title: str):

        frm = ttk.Frame(parent)
        frm.grid(row=row_index, column=0, sticky="ew", padx=8, pady=6)

        col = 0

        # TITLE
        ttk.Label(
            frm,
            text=title,
            font=("Segoe UI", 10, "bold")
        ).grid(row=0, column=col, padx=6)

        col += 1

        # DATE
        ttk.Label(frm, text="Date").grid(row=0, column=col, padx=(20, 4))
        col += 1

        if DateEntry:
            date = DateEntry(frm, width=12, date_pattern="dd-mm-yyyy")
        else:
            date = ttk.Entry(frm, width=12)

        date.grid(row=0, column=col, padx=4)
        self.fields[f"{prefix}_date"] = date
        col += 1

        # FROM TIME
        ttk.Label(frm, text="From").grid(row=0, column=col, padx=(20, 4))
        col += 1

        self._time_widget(frm, f"{prefix}_time_from", 0, col)
        self.fields[f"{prefix}_time_from"] = self.vars[f"{prefix}_time_from"]

        col += 1

        # TO TIME
        ttk.Label(frm, text="To").grid(row=0, column=col, padx=(15, 4))
        col += 1

        self._time_widget(frm, f"{prefix}_time_to", 0, col)
        self.fields[f"{prefix}_time_to"] = self.vars[f"{prefix}_time_to"]

    # =========================================================
    # DRAFT READINGS + TRIM
    # =========================================================
    def _draft_readings_block(self, parent, prefix: str):

        block = ttk.LabelFrame(parent, text="Draft Readings")
        block.pack(fill="x", padx=8, pady=6)

        headers = ["", "PORT", "STB", "MARKS"]
        for c, h in enumerate(headers):
            ttk.Label(block, text=h, font=("Segoe UI", 10, "bold")).grid(
                row=0, column=c, sticky="w", padx=6, pady=(6, 2)
            )

        rows = [
            ("FWD", f"{prefix}_draft_fwd_port", f"{prefix}_draft_fwd_stb", f"{prefix}_draft_fwd_marks"),
            ("MID", f"{prefix}_draft_mid_port", f"{prefix}_draft_mid_stb", f"{prefix}_draft_mid_marks"),
            ("AFT", f"{prefix}_draft_aft_port", f"{prefix}_draft_aft_stb", f"{prefix}_draft_aft_marks"),
        ]

        for i, (label, k1, k2, k3) in enumerate(rows, start=1):
            ttk.Label(block, text=label).grid(row=i, column=0, sticky="w", padx=6, pady=4)
            self._entry(block, key=k1, row=i, col=1, width=10)
            self._entry(block, key=k2, row=i, col=2, width=10)
            self._entry(block, key=k3, row=i, col=3, width=10)

        r = len(rows) + 2

        ttk.Label(block, text="S.G").grid(row=r, column=0, sticky="w", padx=6)
        self._entry(block, key=f"{prefix}_sg", row=r, col=1, width=10)

        ttk.Label(block, text="LPP").grid(row=r, column=2, sticky="w", padx=6)
        self._entry(block, key=f"{prefix}_lpp", row=r, col=3, width=10)

    # =========================================================
    # LIQUIDS
    # =========================================================
    def _draft_liquids_block(self, parent, prefix: str):

        block = ttk.LabelFrame(parent, text="Liquids / Deductions")
        block.pack(fill="x", padx=8, pady=(6, 8))

        items = [
            ("Ballast", f"{prefix}_ballast"),
            ("F. Water", f"{prefix}_fresh_water"),
            ("Fuel Oil", f"{prefix}_fuel_oil"),
            ("Diesel Oil", f"{prefix}_diesel_oil"),
            ("Lub Oil", f"{prefix}_lub_oil"),
            ("Slop", f"{prefix}_slop"),
            ("Swimming Pool", f"{prefix}_swimming_pool"),
            ("Others", f"{prefix}_others"),
        ]

        for r, (label, key) in enumerate(items):
            ttk.Label(block, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=4)
            self._entry(block, key=key, row=r, col=1, width=14)

    def _draft_bl_block(self, parent, prefix: str):

        block = ttk.LabelFrame(parent, text="B/L Figure")
        block.pack(fill="x", padx=8, pady=6)

        ttk.Label(block, text="B/L Figure").grid(row=0, column=0, sticky="w", padx=6)
        self._entry(block, key=f"{prefix}_bl_figure", row=0, col=1, width=14)

    # =========================================================
    # EXTRA (TPC + B/L FIGURE)
    # =========================================================
    def _draft_extra_block(self, parent, prefix: str):

        block = ttk.LabelFrame(parent, text="Figures")
        block.pack(fill="x", padx=8, pady=6)

        ttk.Label(block, text="TPC - P").grid(row=0, column=0, sticky="w", padx=6)
        self._entry(block, key=f"{prefix}_tpc_p", row=0, col=1, width=10)

        ttk.Label(block, text="TPC - S").grid(row=0, column=2, sticky="w", padx=6)
        self._entry(block, key=f"{prefix}_tpc_s", row=0, col=3, width=10)

    # =========================================================
    # SIGNATURES
    # =========================================================
    def _draft_signatures_block(self, parent):

        block = ttk.LabelFrame(parent, text="Signatures")
        block.pack(fill="x", padx=8, pady=(10, 6))

        self._row_1col(block, 0, "chief_officer", "Chief Officer", 28)
        self._row_1col(block, 1, "master", "Master", 28)
        self._row_1col(block, 2, "msl_surveyor", "MSL Surveyor", 28)


    # =========================================================
    # HYDROSTATIC DATA (4 FILAS EXACTAS POR CUADRO)
    # =========================================================
    def _draft_hydro_block(self, parent, prefix: str):

        main_block = ttk.LabelFrame(
            parent,
            text=f"{prefix.upper()} - Hydrostatic Data"
        )
        main_block.pack(fill="x", padx=8, pady=8)

        # =====================================================
        # CUADRO 1
        # =====================================================
        frame1 = ttk.LabelFrame(main_block, text="Hydrostatic Table 1")
        frame1.pack(fill="x", padx=8, pady=6)

        # ---- Headers fila 1/2 ----
        headers_top = ["Draft", "Disp", "TPC", "LCF"]
        for col, h in enumerate(headers_top):
            ttk.Label(
                frame1,
                text=h,
                font=("Segoe UI", 9, "bold")
            ).grid(row=0, column=col, padx=6, pady=4)

        # Fila 1
        self._entry(frame1, f"{prefix}_hydro1_draft_1", 1, 0, 10)
        self._entry(frame1, f"{prefix}_hydro1_disp_1",  1, 1, 10)
        self._entry(frame1, f"{prefix}_hydro1_tpc_1",   1, 2, 10)
        self._entry(frame1, f"{prefix}_hydro1_lcf_1",   1, 3, 10)

        # Fila 2
        self._entry(frame1, f"{prefix}_hydro1_draft_2", 2, 0, 10)
        self._entry(frame1, f"{prefix}_hydro1_disp_2",  2, 1, 10)
        self._entry(frame1, f"{prefix}_hydro1_tpc_2",   2, 2, 10)
        self._entry(frame1, f"{prefix}_hydro1_lcf_2",   2, 3, 10)

        # ---- Headers fila 3/4 ----
        headers_bottom = ["Draft", "MTC+50", "MTC-50"]
        for col, h in enumerate(headers_bottom):
            ttk.Label(
                frame1,
                text=h,
                font=("Segoe UI", 9, "bold")
            ).grid(row=3, column=col, padx=6, pady=(10, 4))

        # Fila 3
        self._entry(frame1, f"{prefix}_hydro1_draft_mtc", 4, 0, 10)
        self._entry(frame1, f"{prefix}_hydro1_mtc_p50_1", 4, 1, 10)
        self._entry(frame1, f"{prefix}_hydro1_mtc_m50_1", 4, 2, 10)

        # Fila 4
        self._entry(frame1, f"{prefix}_hydro1_mtc_p50_2", 5, 1, 10)
        self._entry(frame1, f"{prefix}_hydro1_mtc_m50_2", 5, 2, 10)

        # =====================================================
        # CUADRO 2
        # =====================================================
        frame2 = ttk.LabelFrame(main_block, text="Hydrostatic Table 2")
        frame2.pack(fill="x", padx=8, pady=6)

        # ---- Headers fila 1/2 ----
        for col, h in enumerate(headers_top):
            ttk.Label(
                frame2,
                text=h,
                font=("Segoe UI", 9, "bold")
            ).grid(row=0, column=col, padx=6, pady=4)

        # Fila 1
        self._entry(frame2, f"{prefix}_hydro2_draft_1", 1, 0, 10)
        self._entry(frame2, f"{prefix}_hydro2_disp_1",  1, 1, 10)
        self._entry(frame2, f"{prefix}_hydro2_tpc_1",   1, 2, 10)
        self._entry(frame2, f"{prefix}_hydro2_lcf_1",   1, 3, 10)

        # Fila 2
        self._entry(frame2, f"{prefix}_hydro2_draft_2", 2, 0, 10)
        self._entry(frame2, f"{prefix}_hydro2_disp_2",  2, 1, 10)
        self._entry(frame2, f"{prefix}_hydro2_tpc_2",   2, 2, 10)
        self._entry(frame2, f"{prefix}_hydro2_lcf_2",   2, 3, 10)

        # ---- Headers fila 3/4 ----
        for col, h in enumerate(headers_bottom):
            ttk.Label(
                frame2,
                text=h,
                font=("Segoe UI", 9, "bold")
            ).grid(row=3, column=col, padx=6, pady=(10, 4))

        # Fila 3
        self._entry(frame2, f"{prefix}_hydro2_draft_mtc", 4, 0, 10)
        self._entry(frame2, f"{prefix}_hydro2_mtc_p50_1", 4, 1, 10)
        self._entry(frame2, f"{prefix}_hydro2_mtc_m50_1", 4, 2, 10)

        # Fila 4
        self._entry(frame2, f"{prefix}_hydro2_mtc_p50_2", 5, 1, 10)
        self._entry(frame2, f"{prefix}_hydro2_mtc_m50_2", 5, 2, 10)




    # =========================================================
    # TIME WIDGET (HH:MM) — CORREGIDO
    # =========================================================
    def _time_widget(self, parent, key, row, col):

        frame = ttk.Frame(parent)
        frame.grid(row=row, column=col, sticky="w")

        hour = tk.StringVar(value="00")
        minute = tk.StringVar(value="00")

        # 🔥 Guardamos referencias separadas
        self.vars[f"{key}_hour"] = hour
        self.vars[f"{key}_minute"] = minute

        # Variable final que irá al payload
        self.vars[key] = tk.StringVar()

        spin_h = tk.Spinbox(
            frame,
            from_=0,
            to=23,
            width=3,
            format="%02.0f",
            textvariable=hour
        )
        spin_h.pack(side="left")

        ttk.Label(frame, text=":").pack(side="left")

        spin_m = tk.Spinbox(
            frame,
            from_=0,
            to=59,
            width=3,
            format="%02.0f",
            textvariable=minute
        )
        spin_m.pack(side="left")

        def update_time(*args):
            self.vars[key].set(f"{hour.get()}:{minute.get()}")

        hour.trace("w", update_time)
        minute.trace("w", update_time)

        update_time()

    # =========================================================
    # WIDGET HELPERS (BLINDADO PARA MULTI-WIDGET POR KEY)
    # =========================================================

    def _register_field(self, key, widget):
        """
        Permite múltiples widgets bajo la misma key.
        Si la key ya existe:
            - Si es widget único → lo convierte en lista
            - Si ya es lista → agrega el nuevo
        """
        if key in self.fields:
            if isinstance(self.fields[key], list):
                self.fields[key].append(widget)
            else:
                self.fields[key] = [self.fields[key], widget]
        else:
            self.fields[key] = widget

    def _entry(self, parent, key: str, row: int, col: int, width: int = 24):
        e = ttk.Entry(parent, width=width)
        e.grid(row=row, column=col, sticky="w", padx=6, pady=2)

        self._register_field(key, e)
        return e

    def _row_1col(self, parent, row: int, key: str, label: str, width: int = 40):
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        frm.grid_columnconfigure(1, weight=1)

        ttk.Label(frm, text=label).grid(row=0, column=0, sticky="w")

        e = ttk.Entry(frm, width=width)
        e.grid(row=0, column=1, sticky="w", padx=(10, 0))

        self._register_field(key, e)
        return e

    def _row_2cols(self, parent, row: int, left: tuple, right: tuple):
        """
        left = (key, label, width)
        right = (key, label, width)
        """
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        frm.grid_columnconfigure(1, weight=1)
        frm.grid_columnconfigure(3, weight=1)

        lk, ll, lw = left
        rk, rl, rw = right

        ttk.Label(frm, text=ll).grid(row=0, column=0, sticky="w")
        le = ttk.Entry(frm, width=lw)
        le.grid(row=0, column=1, sticky="w", padx=(10, 20))
        self._register_field(lk, le)

        ttk.Label(frm, text=rl).grid(row=0, column=2, sticky="w")
        re = ttk.Entry(frm, width=rw)
        re.grid(row=0, column=3, sticky="w", padx=(10, 0))
        self._register_field(rk, re)

        return le, re

    def _row_date(self, parent, row: int, key: str, label: str):
        frm = ttk.Frame(parent)
        frm.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
        frm.grid_columnconfigure(1, weight=1)

        ttk.Label(frm, text=label).grid(row=0, column=0, sticky="w")

        if DateEntry:
            w = DateEntry(frm, width=15, date_pattern="dd-mm-yyyy")
            w.grid(row=0, column=1, sticky="w", padx=(10, 0))
        else:
            w = ttk.Entry(frm, width=15)
            w.grid(row=0, column=1, sticky="w", padx=(10, 0))
            w.insert(0, "dd-mm-yyyy")

        self._register_field(key, w)
        return w

    def _toggle_yes_no(self, active_var: tk.BooleanVar, other_var: tk.BooleanVar):
        if active_var.get():
            other_var.set(False)
        else:
            # Evita que ambos queden en False
            other_var.set(True)



    # =========================================================
    # LOCK / UNLOCK FIELDS (ERP CONTROL MODE)
    # =========================================================
    def _lock_fields(self, keys: list):
        """
        Bloquea campos tipo Entry / Combobox.
        No afecta BooleanVar ni StringVar.
        """
        for key in keys:
            widget = self.fields.get(key)
            if not widget:
                continue

            try:
                if isinstance(widget, ttk.Entry):
                    widget.config(state="readonly")
                elif isinstance(widget, ttk.Combobox):
                    widget.config(state="readonly")
            except Exception:
                pass


    def _unlock_fields(self, keys: list):
        """
        Desbloquea campos.
        """
        for key in keys:
            widget = self.fields.get(key)
            if not widget:
                continue

            try:
                if isinstance(widget, ttk.Entry):
                    widget.config(state="normal")
                elif isinstance(widget, ttk.Combobox):
                    widget.config(state="normal")
            except Exception:
                pass

    # =========================================================
    # EDIT MODE HELPERS (EDITAR / GUARDAR)
    # =========================================================
    def _set_edit_mode(self, enabled: bool):
        """
        enabled=True  -> desbloquea campos editables
        enabled=False -> vuelve a bloquear los campos editables
        NOTA: Los campos controlados por servicio (self._non_editable_keys)
              se mantienen bloqueados siempre.
        """
        self._edit_mode = bool(enabled)

        for key, widget in self.fields.items():

            # No tocar boolean vars ni string vars internas (times, totals, etc.)
            if isinstance(widget, (tk.BooleanVar, tk.StringVar)):
                continue

            # Nunca permitir edición de campos controlados por servicio
            if key in getattr(self, "_non_editable_keys", []):
                try:
                    if isinstance(widget, ttk.Entry):
                        widget.config(state="readonly")
                    elif isinstance(widget, ttk.Combobox):
                        widget.config(state="readonly")
                except Exception:
                    pass
                continue

            # Resto: editable o readonly según modo
            try:
                if isinstance(widget, ttk.Entry):
                    widget.config(state="normal" if enabled else "readonly")
                elif isinstance(widget, ttk.Combobox):
                    widget.config(state="readonly" if not enabled else "readonly")
                    # (Combobox normalmente lo quieres readonly siempre para evitar texto libre)
            except Exception:
                pass

    def _editar(self):

        if self.mode != "edit":
            messagebox.showwarning(
                "Aviso",
                "Debe cargar un Draft existente para poder editar."
            )
            return

        self._set_edit_mode(not self._edit_mode)

        if self._edit_mode:
            messagebox.showinfo("Editar", "Modo edición habilitado.")
        else:
            messagebox.showinfo("Editar", "Modo edición deshabilitado.")


    def _guardar(self):
        """
        ✅ Guardar = MISMO flujo que 'Enviar a revisión' (idéntico).
        """
        # Llama exactamente el mismo método
        self._enviar_revision()

        # Opcional: al terminar, volver a modo lectura (no rompe si falló)
        try:
            self._set_edit_mode(False)
        except Exception:
            pass


    # =========================================================
    # PUBLIC: GET / SET PAYLOAD
    # =========================================================
    def get_payload(self) -> dict:
        """
        Devuelve SOLO INPUTS del form + metadata header
        + Dynamic Ballast structure.
        Listo para POST/PUT.
        """

        def _get_value(widget):
            if widget is None:
                return ""

            # Boolean
            if isinstance(widget, tk.BooleanVar):
                return bool(widget.get())

            # DateEntry
            if DateEntry and isinstance(widget, DateEntry):
                return widget.get()

            # Entry
            if isinstance(widget, ttk.Entry):
                return widget.get().strip()

            # StringVar (times, totals, etc.)
            if isinstance(widget, tk.StringVar):
                return widget.get().strip()

            # Fallback seguro
            try:
                return str(widget.get()).strip()
            except Exception:
                return ""

        data = {}

        # ============================================
        # 1️⃣ CAMPOS NORMALES DEL FORM
        # ============================================
        for key, w in self.fields.items():
            try:
                data[key] = _get_value(w)
            except Exception:
                data[key] = ""

        # ============================================
        # 2️⃣ HEADER META (CRÍTICO)
        # ============================================
        try:
            data["year"] = self.meta_vars["anio"].get()
            data["month"] = self.meta_vars["mes"].get()
            data["continent"] = self.meta_vars["continente"].get()
            data["country"] = self.meta_vars["pais"].get()
            data["port"] = self.meta_vars["puerto"].get()
            data["client"] = self.meta_vars["cliente"].get()
            data["draft_report_number"] = self.meta_vars["num_informe"].get()
        except Exception:
            pass

        # ============================================
        # 3️⃣ NORMALIZAR TRIM TABLES
        # ============================================
        if "trim_tables_yes" in self.fields and "trim_tables_no" in self.fields:
            try:
                data["trim_tables_available"] = bool(
                    self.fields["trim_tables_yes"].get()
                )
            except Exception:
                data["trim_tables_available"] = False

        # ============================================
        # 4️⃣ 🔥 DYNAMIC BALLAST (CRÍTICO)
        # ============================================
        if hasattr(self, "dynamic_ballast") and isinstance(self.dynamic_ballast, dict):

            data["ballast"] = {
                "init": [],
                "final": []
            }

            for prefix in ["init", "final"]:

                tank_list = self.dynamic_ballast.get(prefix, [])

                if not isinstance(tank_list, list):
                    continue

                for tank in tank_list:

                    try:
                        tank_name = tank["tank_name"].get().strip()
                    except Exception:
                        tank_name = ""

                    # Saltar filas sin tanque seleccionado
                    if not tank_name:
                        continue

                    try:
                        sounding = tank["sounding"].get().strip()
                    except Exception:
                        sounding = ""

                    try:
                        volume = tank["volume"].get().strip()
                    except Exception:
                        volume = ""

                    try:
                        density = tank["density"].get().strip()
                    except Exception:
                        density = ""

                    data["ballast"][prefix].append({
                        "tank_name": tank_name,
                        "sounding": sounding,
                        "volume": volume,
                        "density": density
                    })

        return data

    def set_payload(self, data: dict):
        """
        Carga datos al form.

        BLINDADO:
        - Soporta wrapper UNIFIED:
            { "success": True, "draft_report_number": "...", "data": { ... } }
        - Soporta dict plano directo.
        - Soporta múltiples widgets por misma key.
        - Respeta estado readonly.
        - Soporta DateEntry, Entry, Combobox, BooleanVar, StringVar.
        """

        if not isinstance(data, dict):
            return

        # =====================================================
        # 0️⃣ UNWRAP SEGURO
        # =====================================================
        payload = data

        if isinstance(data.get("data"), dict):
            payload = data.get("data") or {}
        elif isinstance(data.get("payload"), dict):
            payload = data.get("payload") or {}

        if not isinstance(payload, dict):
            return

        # =====================================================
        # 1️⃣ HEADER META (SAP)
        # =====================================================
        try:
            self.meta_vars["anio"].set(str(payload.get("year", "") or ""))
            self.meta_vars["mes"].set(str(payload.get("month", "") or ""))
            self.meta_vars["continente"].set(payload.get("continent", "") or "")
            self.meta_vars["pais"].set(payload.get("country", "") or "")
            self.meta_vars["puerto"].set(payload.get("port", "") or "")
            self.meta_vars["cliente"].set(payload.get("client", "") or "")
            self.meta_vars["num_informe"].set(
                payload.get("draft_report_number", "") or ""
            )
        except Exception:
            pass

        # =====================================================
        # 2️⃣ HELPERS
        # =====================================================
        def _set_entry(entry: ttk.Entry, value):
            try:
                original_state = entry.cget("state")
                entry.config(state="normal")
                entry.delete(0, "end")
                entry.insert(0, "" if value is None else str(value))
                entry.config(state=original_state)
            except Exception:
                pass

        def _apply(widget, value):
            """
            Aplica valor a:
            - Widget único
            - Lista de widgets
            """

            # 🔥 Soporte multi-widget por misma key
            if isinstance(widget, list):
                for w in widget:
                    _apply(w, value)
                return

            # ================= BOOLEAN =================
            if isinstance(widget, tk.BooleanVar):
                try:
                    if isinstance(value, str):
                        widget.set(
                            value.strip().lower()
                            in ["true", "1", "yes", "y", "si", "sí"]
                        )
                    else:
                        widget.set(bool(value))
                except Exception:
                    pass
                return

            # ================= STRINGVAR =================
            if isinstance(widget, tk.StringVar):
                try:
                    widget.set("" if value is None else str(value))
                except Exception:
                    pass
                return

            # ================= DATEENTRY =================
            if DateEntry and isinstance(widget, DateEntry):
                try:
                    if isinstance(value, str) and value:
                        raw = value.split(" ")[0].strip()

                        if len(raw.split("-")[0]) == 4:
                            dt = datetime.strptime(raw, "%Y-%m-%d")
                        else:
                            dt = datetime.strptime(raw, "%d-%m-%Y")

                        widget.set_date(dt)
                except Exception:
                    pass
                return

            # ================= COMBOBOX =================
            if isinstance(widget, ttk.Combobox):
                try:
                    widget.set("" if value is None else str(value))
                except Exception:
                    pass
                return

            # ================= ENTRY =================
            if isinstance(widget, ttk.Entry):
                _set_entry(widget, value)
                return

            # ================= FALLBACK =================
            try:
                if hasattr(widget, "set"):
                    widget.set("" if value is None else str(value))
                elif hasattr(widget, "delete") and hasattr(widget, "insert"):
                    _set_entry(widget, value)
            except Exception:
                pass

        # =====================================================
        # 3️⃣ SET FIELDS
        # =====================================================
        for key, value in payload.items():

            widget = self.fields.get(key)
            if not widget:
                continue

            # ================= TIME (HH:MM) =================
            if key.endswith("_time_from") or key.endswith("_time_to"):
                if isinstance(value, str) and ":" in value:
                    try:
                        parts = value.strip().split(":")
                        hh = parts[0].zfill(2)
                        mm = parts[1].zfill(2)

                        if f"{key}_hour" in self.vars:
                            self.vars[f"{key}_hour"].set(hh)

                        if f"{key}_minute" in self.vars:
                            self.vars[f"{key}_minute"].set(mm)

                        if key in self.vars:
                            self.vars[key].set(f"{hh}:{mm}")

                    except Exception:
                        pass
                continue

            _apply(widget, value)

        # =====================================================
        # 4️⃣ TRIM TABLES
        # =====================================================
        if (
            "trim_tables_available" in payload
            and "trim_tables_yes" in self.fields
            and "trim_tables_no" in self.fields
        ):
            try:
                yes = bool(payload.get("trim_tables_available"))
                self.fields["trim_tables_yes"].set(yes)
                self.fields["trim_tables_no"].set(not yes)
            except Exception:
                pass




    # =========================================================
    # LOAD EXISTING DRAFT (SOLO EN MODO EDIT + AUTLOAD ENABLED)
    # =========================================================
    def _load_existing_draft(self):

        # 🔒 HARD BLOCK: si no está habilitado el autoload, NUNCA consultar DB
        if not getattr(self, "_db_autoload_enabled", False):
            return

        # 🔒 SOLO cargar si estamos en modo EDIT real
        if self.mode != "edit" or not self.draft_report_number:
            return

        try:
            from api_client import get_full_draft_survey_api

            response = get_full_draft_survey_api(self.draft_report_number)

            # 🔒 Si no existe en DB
            if not response:
                messagebox.showwarning(
                    "Aviso",
                    "El Draft aún no existe en base de datos."
                )
                return

            if not isinstance(response, dict):
                messagebox.showerror(
                    "Error",
                    "La respuesta del servidor no es válida."
                )
                return

            # =====================================================
            # 🔥 UNWRAP SEGURO (UNIFIED WRAPPER O FLAT)
            # =====================================================
            payload = response

            # Caso típico UNIFIED:
            # { "success": True, "draft_report_number": "...", "data": { ... } }
            if isinstance(response.get("data"), dict):
                payload = response.get("data")

            # Blindaje extra por si cambia estructura futura
            if not isinstance(payload, dict):
                messagebox.showerror(
                    "Error",
                    "El formato del payload no es válido."
                )
                return

            # =====================================================
            # 1️⃣ Cargar datos en el form (usa payload plano)
            # =====================================================
            self.set_payload(payload)

            # =====================================================
            # 2️⃣ Header meta (USAR PAYLOAD REAL)
            # =====================================================
            try:
                self.meta_vars["anio"].set(str(payload.get("year", "") or ""))
                self.meta_vars["mes"].set(str(payload.get("month", "") or ""))
                self.meta_vars["continente"].set(payload.get("continent", "") or "")
                self.meta_vars["pais"].set(payload.get("country", "") or "")
                self.meta_vars["puerto"].set(payload.get("port", "") or "")
                self.meta_vars["cliente"].set(payload.get("client", "") or "")
                self.meta_vars["num_informe"].set(
                    payload.get("draft_report_number", self.draft_report_number)
                )
            except Exception:
                pass

            # =====================================================
            # 3️⃣ Bloquear edición (modo lectura)
            # =====================================================
            self._set_edit_mode(False)

            if self.btn_editar:
                try:
                    self.btn_editar.config(state="normal")
                except Exception:
                    pass

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar Draft Survey:\n{e}"
            )


    # =========================================================
    # SERVICIO SELECTOR
    # =========================================================

    def _open_servicio_selector(self):

        try:
            from Modulos.Informes.Vessel_Draft_Survey.popup_servicio_draft_selector import (
                PopupServicioDraftSelector
            )

            PopupServicioDraftSelector(
                parent=self,
                on_select=self._on_servicio_selected
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el selector:\n{e}"
            )



    def _on_servicio_selected(self, values):
        """
        values:
        (
            num_informe,
            buque_contenedor,
            cliente,
            continente,
            pais,
            puerto,
            operacion,
            fecha_inicio
        )
        """

        # 🔥 CLAVE: al seleccionar servicio SIEMPRE es CREATE (NO GET)
        self._force_create_mode()

        try:

            num_informe = values[0]
            vessel = values[1]
            cliente = values[2]
            continente = values[3]
            pais = values[4]
            puerto = values[5]
            fecha_inicio = values[7]

            # =====================================================
            # CALCULAR AÑO / MES
            # =====================================================
            from datetime import datetime

            try:
                if fecha_inicio and isinstance(fecha_inicio, str):
                    raw = fecha_inicio.split(" ")[0]

                    if len(raw.split("-")[0]) == 4:
                        dt = datetime.strptime(raw, "%Y-%m-%d")
                    else:
                        dt = datetime.strptime(raw, "%d-%m-%Y")

                    anio = str(dt.year)
                    mes = str(dt.month)
                else:
                    now = datetime.now()
                    anio = str(now.year)
                    mes = str(now.month)

            except Exception:
                now = datetime.now()
                anio = str(now.year)
                mes = str(now.month)

            # =====================================================
            # HEADER META (READONLY)
            # =====================================================
            self.meta_vars["anio"].set(anio)
            self.meta_vars["mes"].set(mes)
            self.meta_vars["pais"].set(pais or "")
            self.meta_vars["continente"].set(continente or "")
            self.meta_vars["puerto"].set(puerto or "")
            self.meta_vars["cliente"].set(cliente or "")
            self.meta_vars["num_informe"].set(num_informe or "")

            # =====================================================
            # GENERAL TAB FIELDS
            # =====================================================
            if "vessel_mv" in self.fields:
                self.fields["vessel_mv"].config(state="normal")
                self.fields["vessel_mv"].delete(0, "end")
                self.fields["vessel_mv"].insert(0, vessel)

            if "survey_no" in self.fields:
                self.fields["survey_no"].config(state="normal")
                self.fields["survey_no"].delete(0, "end")
                self.fields["survey_no"].insert(0, num_informe)

            if "survey_requested_by" in self.fields:
                self.fields["survey_requested_by"].config(state="normal")
                self.fields["survey_requested_by"].delete(0, "end")
                self.fields["survey_requested_by"].insert(0, cliente)

            # =====================================================
            # WORD TAB SYNC
            # =====================================================
            if "word_vessel" in self.fields:
                self.fields["word_vessel"].config(state="normal")
                self.fields["word_vessel"].delete(0, "end")
                self.fields["word_vessel"].insert(0, vessel)

            if "word_name" in self.fields:
                self.fields["word_name"].config(state="normal")
                self.fields["word_name"].delete(0, "end")
                self.fields["word_name"].insert(0, vessel)

            if "word_port" in self.fields:
                self.fields["word_port"].config(state="normal")
                self.fields["word_port"].delete(0, "end")
                self.fields["word_port"].insert(0, puerto)

            if "word_country" in self.fields:
                self.fields["word_country"].config(state="normal")
                self.fields["word_country"].delete(0, "end")
                self.fields["word_country"].insert(0, pais)

            if "word_survey_requested_by" in self.fields:
                self.fields["word_survey_requested_by"].config(state="normal")
                self.fields["word_survey_requested_by"].delete(0, "end")
                self.fields["word_survey_requested_by"].insert(0, cliente)

            # =====================================================
            # 🔒 BLOQUEAR CAMPOS CONTROLADOS POR SERVICIO
            # =====================================================
            self._lock_fields([
                # GENERAL
                "vessel_mv",
                "survey_no",
                "survey_requested_by",

                # WORD
                "word_vessel",
                "word_name",
                "word_port",
                "word_country",
                "word_survey_requested_by",
            ])

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el servicio:\n{e}"
            )

    # =========================================================
    # ENVIAR A REVISION (GENERAL + BALLAST + WORD) — FIX 400
    # =========================================================
    def _enviar_revision(self):

        self.update_idletasks()
        self.update()

        full_payload = self.get_payload()

        # ================= VALIDACIÓN =================
        if not full_payload.get("vessel_mv"):
            messagebox.showwarning(
                "Validación",
                "Debe seleccionar un servicio antes de enviar."
            )
            return

        metadata_keys = [
            "year", "month", "continent",
            "country", "port", "client",
            "draft_report_number"
        ]

        for key in metadata_keys:
            if not full_payload.get(key):
                messagebox.showwarning(
                    "Validación",
                    f"Falta metadata obligatoria: {key}"
                )
                return

        try:
            from api_client import (
                create_draft_survey_api,
                create_draft_survey_ballast_api,
                create_draft_survey_word_api
            )

            # =====================================================
            # 1️⃣ GENERAL
            # =====================================================
            response = create_draft_survey_api(full_payload)

            if not response.get("success"):
                messagebox.showerror(
                    "Error",
                    response.get("error", "No se pudo crear el Draft Survey.")
                )
                return

            draft_survey_id = response.get("general_id")

            if not draft_survey_id:
                messagebox.showerror(
                    "Error",
                    "El backend no devolvió general_id."
                )
                return

            # =====================================================
            # 2️⃣ PREPARAR BALLAST CORRECTAMENTE
            # =====================================================
            ballast_payload = {}

            # 🔹 Copiar metadata
            for key in metadata_keys:
                ballast_payload[key] = full_payload.get(key)

            # 🔹 Convertir estructura dinámica a columnas SQL
            ballast_data = full_payload.get("ballast", {})

            for phase in ["init", "final"]:

                tank_list = ballast_data.get(phase, [])

                for tank in tank_list:

                    tank_name = tank.get("tank_name", "").lower().replace(" ", "_")

                    if not tank_name:
                        continue

                    base = f"{phase}_{tank_name}"

                    ballast_payload[f"{base}_sounding"] = tank.get("sounding")
                    ballast_payload[f"{base}_volume"] = tank.get("volume")
                    ballast_payload[f"{base}_density"] = tank.get("density")

            ballast_response = create_draft_survey_ballast_api(
                draft_survey_id,
                ballast_payload
            )

            if not ballast_response.get("success"):
                messagebox.showerror(
                    "Error",
                    ballast_response.get("error", "Error creando Ballast.")
                )
                return

            # =====================================================
            # 3️⃣ WORD
            # =====================================================
            word_payload = {
                k: v for k, v in full_payload.items()
                if k.startswith("word_")
            }

            # 🔹 añadir metadata
            for key in metadata_keys:
                word_payload[key] = full_payload.get(key)

            if word_payload:

                word_response = create_draft_survey_word_api(
                    draft_survey_id,
                    word_payload
                )

                if not word_response.get("success"):
                    messagebox.showerror(
                        "Error",
                        word_response.get("error", "Error creando Word Report.")
                    )
                    return

            # =====================================================
            # TODO OK
            # =====================================================
            messagebox.showinfo(
                "Éxito",
                "Draft Survey enviado correctamente a revisión."
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error enviando Draft Survey:\n{e}"
            )

    # =========================================================
    # BUILD: BALLAST TAB
    # =========================================================
    def _build_ballast_tab(self, parent):

        # ================= SAP HEADER =================
        self._build_sap_metadata_header(parent)

        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True, pady=8)
        container.grid_columnconfigure(0, weight=1)
        container.grid_columnconfigure(1, weight=1)

        lf_initial = ttk.LabelFrame(container, text="INITIAL")
        lf_final = ttk.LabelFrame(container, text="FINAL")

        lf_initial.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        lf_final.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._ballast_table_block(lf_initial, prefix="init")
        self._ballast_table_block(lf_final, prefix="final")

    # =========================================================
    # BALLAST + FRESH WATER (ALINEADO 1:1 CON DB)
    # =========================================================
    def _ballast_table_block(self, parent, prefix: str):

        # =========================================================
        # INIT STRUCTURE (SAFE)
        # =========================================================
        if not hasattr(self, "dynamic_ballast"):
            self.dynamic_ballast = {"init": [], "final": []}

        if prefix not in self.dynamic_ballast:
            self.dynamic_ballast[prefix] = []

        # =========================================================
        # TITLE
        # =========================================================
        ttk.Label(
            parent,
            text="BALLAST",
            font=("Segoe UI", 11, "bold")
        ).grid(row=0, column=0, sticky="w", padx=6, pady=(6, 4))

        headers = ["Tank", "Sounding", "Volume", "Density", "Total", ""]

        for col, header in enumerate(headers):
            ttk.Label(
                parent,
                text=header,
                font=("Segoe UI", 9, "bold")
            ).grid(row=1, column=col, padx=6, pady=4)

        # =========================================================
        # AVAILABLE TANKS (EDITABLE LIST)
        # =========================================================
        available_tanks = [
            "FPT", "APT", "SLOP TANK",
            "WBT 1P", "WBT 1S",
            "WBT 2P", "WBT 2S",
            "WBT 3P", "WBT 3S",
            "WBT 4P", "WBT 4S",
            "WBT 5P", "WBT 5S",
            "WBT 6P", "WBT 6S",
            "WBT 7P", "WBT 7S",
            "WBT 8P", "WBT 8S",
            "WBT 9P", "WBT 9S",
            "WBT 10P", "WBT 10S"
        ]

        start_row = 2

        self.vars[f"{prefix}_ballast_total"] = tk.StringVar(value="0.00")

        # =========================================================
        # RECALC FUNCTION
        # =========================================================
        def recalc_ballast():

            grand_total = 0.0

            for tank in self.dynamic_ballast[prefix]:
                try:
                    volume = float(tank["volume"].get() or 0)
                    density = float(tank["density"].get() or 0)
                    total = volume * density
                except Exception:
                    total = 0.0

                tank["total_var"].set(f"{total:.2f}")
                grand_total += total

            self.vars[f"{prefix}_ballast_total"].set(f"{grand_total:.2f}")

        # =========================================================
        # REMOVE ROW
        # =========================================================
        def remove_row(tank_dict):

            try:
                for widget in tank_dict["widgets"]:
                    widget.destroy()
            except Exception:
                pass

            if tank_dict in self.dynamic_ballast[prefix]:
                self.dynamic_ballast[prefix].remove(tank_dict)

            recalc_ballast()
            redraw_rows()

        # =========================================================
        # REDRAW ROWS (keeps layout clean)
        # =========================================================
        def redraw_rows():

            for idx, tank in enumerate(self.dynamic_ballast[prefix]):
                row = start_row + idx

                for col, widget in enumerate(tank["widgets"]):
                    widget.grid_configure(row=row, column=col)

        # =========================================================
        # ADD ROW
        # =========================================================
        def add_tank_row():

            # Prevent duplicate tank selection
            existing = [
                t["tank_name"].get()
                for t in self.dynamic_ballast[prefix]
            ]

            row = start_row + len(self.dynamic_ballast[prefix])

            tank_cb = ttk.Combobox(
                parent,
                values=available_tanks,
                width=18,
                state="readonly"
            )
            tank_cb.grid(row=row, column=0, padx=6, pady=2)

            sounding = ttk.Entry(parent, width=10)
            sounding.grid(row=row, column=1, padx=6)

            volume = ttk.Entry(parent, width=10)
            volume.grid(row=row, column=2, padx=6)

            density = ttk.Entry(parent, width=10)
            density.grid(row=row, column=3, padx=6)

            total_var = tk.StringVar(value="0.00")

            total_entry = ttk.Entry(
                parent,
                textvariable=total_var,
                state="readonly",
                width=12
            )
            total_entry.grid(row=row, column=4, padx=6)

            remove_btn = ttk.Button(
                parent,
                text="✕",
                width=3
            )
            remove_btn.grid(row=row, column=5, padx=4)

            tank_dict = {
                "tank_name": tank_cb,
                "sounding": sounding,
                "volume": volume,
                "density": density,
                "total_var": total_var,
                "widgets": [
                    tank_cb,
                    sounding,
                    volume,
                    density,
                    total_entry,
                    remove_btn
                ]
            }

            remove_btn.config(command=lambda: remove_row(tank_dict))

            volume.bind("<KeyRelease>", lambda e: recalc_ballast())
            density.bind("<KeyRelease>", lambda e: recalc_ballast())

            self.dynamic_ballast[prefix].append(tank_dict)

        # =========================================================
        # ADD BUTTON
        # =========================================================
        ttk.Button(
            parent,
            text="+ Add Tank",
            command=add_tank_row
        ).grid(row=start_row, column=6, padx=(15, 0))

        # =========================================================
        # TOTAL ROW
        # =========================================================
        total_row = start_row + 100  # safe separation

        ttk.Label(
            parent,
            text="TOTAL BALLAST",
            font=("Segoe UI", 10, "bold")
        ).grid(row=total_row, column=3, sticky="e", padx=6, pady=(20, 6))

        ttk.Entry(
            parent,
            textvariable=self.vars[f"{prefix}_ballast_total"],
            state="readonly",
            width=15
        ).grid(row=total_row, column=4, padx=6, pady=(20, 6))

        for c in range(7):
            parent.grid_columnconfigure(c, weight=1)



    # =========================================================
    # BUILD: WORD REPORT TAB (CORREGIDO + BLINDADO HORAS)
    # =========================================================
    def _build_word_tab(self, parent):

        # ================= SAP HEADER =================
        self._build_sap_metadata_header(parent)

        # =====================================================
        # HELPERS INTERNOS
        # =====================================================
        def _year_selector(parent, row, key, label):
            frm = ttk.Frame(parent)
            frm.grid(row=row, column=0, sticky="ew", padx=8, pady=6)
            frm.grid_columnconfigure(1, weight=1)

            ttk.Label(frm, text=label).grid(row=0, column=0, sticky="w")

            current_year = datetime.now().year
            years = [str(y) for y in range(current_year, 1950, -1)]

            cb = ttk.Combobox(
                frm,
                values=years,
                width=8,
                state="readonly"
            )
            cb.grid(row=0, column=1, sticky="w", padx=(10, 0))

            self.fields[key] = cb
            return cb

        def _datetime_row(parent, row, key, label):

            frm = ttk.Frame(parent)
            frm.grid(row=row, column=0, sticky="ew", padx=8, pady=6)

            ttk.Label(frm, text=label).grid(row=0, column=0, sticky="w")

            # ================= DATE =================
            if DateEntry:
                date_widget = DateEntry(
                    frm,
                    width=12,
                    date_pattern="mm-dd-yyyy"
                )
            else:
                date_widget = ttk.Entry(frm, width=12)

            date_widget.grid(row=0, column=1, padx=(10, 5))

            # Guardamos referencia real
            self.vars[f"{key}_date_widget"] = date_widget

            # ================= TIME =================
            hour = tk.StringVar(value="00")
            minute = tk.StringVar(value="00")

            self.vars[f"{key}_hour"] = hour
            self.vars[f"{key}_minute"] = minute

            spin_h = tk.Spinbox(
                frm,
                from_=0,
                to=23,
                width=3,
                format="%02.0f",
                textvariable=hour
            )
            spin_h.grid(row=0, column=2)

            ttk.Label(frm, text=":").grid(row=0, column=3)

            spin_m = tk.Spinbox(
                frm,
                from_=0,
                to=59,
                width=3,
                format="%02.0f",
                textvariable=minute
            )
            spin_m.grid(row=0, column=4)

            # Variable final enviada al payload
            final_var = tk.StringVar()
            self.fields[key] = final_var

            def update_datetime(*args):
                try:
                    if DateEntry and isinstance(date_widget, DateEntry):
                        raw = date_widget.get_date()
                        formatted = raw.strftime("%m-%d-%Y")
                    else:
                        formatted = date_widget.get()

                    final_var.set(f"{formatted} {hour.get()}:{minute.get()}")
                except Exception:
                    final_var.set("")

            hour.trace("w", update_datetime)
            minute.trace("w", update_datetime)

            if DateEntry:
                date_widget.bind("<<DateEntrySelected>>", lambda e: update_datetime())
            else:
                date_widget.bind("<KeyRelease>", lambda e: update_datetime())

            update_datetime()

        # =====================================================
        # 1. INTRODUCTION
        # =====================================================
        lf_intro = ttk.LabelFrame(parent, text="1. INTRODUCTION")
        lf_intro.pack(fill="x", pady=8)

        self._row_1col(lf_intro, 0, "word_mt", "Metric Tons (MT)", 20)
        self._row_1col(lf_intro, 1, "word_product", "Product", 40)
        self._row_1col(lf_intro, 2, "word_vessel", "Vessel", 30)
        self._row_1col(lf_intro, 3, "word_port", "Port", 30)
        self._row_1col(lf_intro, 4, "word_country", "Country", 30)
        self._row_1col(lf_intro, 5, "word_survey_requested_by", "Survey requested by", 40)
        self._row_1col(lf_intro, 6, "word_on_behalf_of", "On behalf of", 40)
        self._row_1col(lf_intro, 7, "word_master", "Master of the ship", 40)
        self._row_1col(lf_intro, 8, "word_chief_officer", "Chief Officer", 40)

        # =====================================================
        # 2. VESSEL PARTICULARS
        # =====================================================
        lf_vessel = ttk.LabelFrame(parent, text="2. VESSEL PARTICULARS")
        lf_vessel.pack(fill="x", pady=8)

        self._row_1col(lf_vessel, 0, "word_name", "Name", 30)
        self._row_1col(lf_vessel, 1, "word_port_registry", "Port of Registry / Flag", 30)
        self._row_1col(lf_vessel, 2, "word_grt", "GRT", 20)
        self._row_1col(lf_vessel, 3, "word_nrt", "NRT", 20)

        _year_selector(lf_vessel, 4, "word_year", "Year Built")

        self._row_1col(lf_vessel, 5, "word_imo", "IMO Number", 20)

        # =====================================================
        # 3. EXTRACT TIME SHEET
        # =====================================================
        lf_time = ttk.LabelFrame(parent, text="3. EXTRACT TIME SHEET")
        lf_time.pack(fill="x", pady=8)

        _datetime_row(lf_time, 0, "word_arrived_buoy", "Vessel Arrived at Sea Buoy")
        _datetime_row(lf_time, 1, "word_nor_tendered", "N.O.R Tendered")
        _datetime_row(lf_time, 2, "word_all_fast", "All Fast")
        _datetime_row(lf_time, 3, "word_initial_draft", "Initial Draft Survey")
        _datetime_row(lf_time, 4, "word_commenced", "Commenced Discharge")
        _datetime_row(lf_time, 5, "word_completed", "Completed Discharge")
        _datetime_row(lf_time, 6, "word_final_draft", "Final Draft Survey")

        # =====================================================
        # 4. THE GOODS
        # =====================================================
        lf_goods = ttk.LabelFrame(parent, text="4. THE GOODS")
        lf_goods.pack(fill="x", pady=8)

        self._row_1col(lf_goods, 0, "word_metric_tons", "Metric Tons", 20)
        self._row_1col(lf_goods, 1, "word_goods_product", "Product", 40)
        self._row_1col(lf_goods, 2, "word_holds", "Holds", 20)

        # =====================================================
        # 5. CARGO QUANTITY BY DRAFT SURVEY
        # =====================================================
        lf_cargo = ttk.LabelFrame(parent, text="5. CARGO QUANTITY DISCHARGED BY DRAFT SURVEY")
        lf_cargo.pack(fill="x", pady=8)

        self._row_1col(lf_cargo, 0, "word_draft_figures", "Draft Survey Figures", 20)
        self._row_1col(lf_cargo, 1, "word_bl_figures", "B/L Figures", 20)
        self._row_1col(lf_cargo, 2, "word_difference", "Difference", 20)
        self._row_1col(lf_cargo, 3, "word_percentage", "Percentage (%)", 20)

        # =====================================================
        # SHORE SCALE SECTION
        # =====================================================
        lf_shore = ttk.LabelFrame(parent, text="TOTAL DISCHARGED BY SHORE SCALE")
        lf_shore.pack(fill="x", pady=8)

        self._row_1col(lf_shore, 0, "word_shore_scale", "Shore Scale Figures", 20)
        self._row_1col(lf_shore, 1, "word_shore_bl", "B/L Figures", 20)
        self._row_1col(lf_shore, 2, "word_shore_difference", "Difference", 20)
        self._row_1col(lf_shore, 3, "word_shore_percentage", "Percentage (%)", 20)

        ttk.Label(parent, text="").pack(pady=10)

    # =========================================================
    # SANITIZADOR SEGURO PARA EXCEL (ANTI-FÓRMULA PROFESIONAL)
    # =========================================================
    def _sanitize_for_excel(self, value):

        if value is None:
            return value

        # Si ya es numérico real, no tocar
        if isinstance(value, (int, float)):
            return value

        if isinstance(value, str):

            value = value.strip()

            # Intentar convertir a número válido (incluye negativos)
            try:
                num = float(value)
                return num
            except Exception:
                pass

            # Si comienza con símbolos peligrosos y NO es número válido
            if value.startswith(("=", "+", "@", "/")):
                return "'" + value

            # Caso especial: empieza con "-" pero no es número
            if value.startswith("-"):
                try:
                    float(value)
                    return float(value)
                except Exception:
                    return "'" + value

        return value


    # =========================================================
    # UI — SELECTOR FINAL vs INTERMEDIATE
    # =========================================================
    def _ask_draft_variant(self):
        """
        Retorna:
            "final" | "intermediate" | None (si cancela)
        """
        win = tk.Toplevel(self)
        win.title("Visualizar Draft Survey")
        win.geometry("420x200")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        choice = tk.StringVar(value="final")

        ttk.Label(
            win,
            text="¿Qué versión deseas visualizar?",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=15, pady=(15, 8))

        frm = ttk.Frame(win)
        frm.pack(fill="x", padx=15)

        ttk.Radiobutton(
            frm,
            text="Final Draft Survey (Default)",
            variable=choice,
            value="final"
        ).pack(anchor="w", pady=4)

        ttk.Radiobutton(
            frm,
            text="Intermediate Draft Survey",
            variable=choice,
            value="intermediate"
        ).pack(anchor="w", pady=4)

        result = {"value": None}

        btns = ttk.Frame(win)
        btns.pack(fill="x", padx=15, pady=15)

        def _ok():
            result["value"] = choice.get()
            win.destroy()

        def _cancel():
            result["value"] = None
            win.destroy()

        ttk.Button(btns, text="Cancelar", command=_cancel).pack(side="right")
        ttk.Button(btns, text="Abrir", command=_ok).pack(side="right", padx=(0, 8))

        win.wait_window()
        return result["value"]

    # =========================================================
    # VISUALIZAR DRAFT (BLINDADO + RECÁLCULO REAL + BLOQUEO)
    # =========================================================
    def _visualizar_draft(self):

        # 🔒 Forzar actualización de widgets
        self.update_idletasks()
        self.update()

        # ==============================
        # 1) Preguntar variante
        # ==============================
        variant = self._ask_draft_variant()
        if not variant:
            return  # cancelado

        payload = self.get_payload()

        # =====================================================
        # SANITIZAR PAYLOAD COMPLETO
        # =====================================================
        sanitized_payload = {
            k: self._sanitize_for_excel(v)
            for k, v in payload.items()
        }

        # =====================================================
        # VALIDACIÓN MÍNIMA
        # =====================================================
        if not sanitized_payload.get("vessel_mv"):
            messagebox.showwarning(
                "Validación",
                "Debe seleccionar un servicio antes de visualizar."
            )
            return

        # =====================================================
        # 2) GENERAR EXCEL
        # =====================================================
        try:
            from backend_api.services.draft_survey_excel_service import (
                generate_draft_survey_excel
            )

            tmp_path = generate_draft_survey_excel(
                sanitized_payload,
                variant=variant
            )

            if not tmp_path:
                raise Exception("No se generó archivo temporal.")

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo generar el preview:\n{e}"
            )
            return

        # =====================================================
        # 3) ABRIR EXCEL + FORZAR RECÁLCULO + BLOQUEAR
        # =====================================================
        try:
            import win32com.client
            import pythoncom

            pythoncom.CoInitialize()

            excel = win32com.client.Dispatch("Excel.Application")

            # Configuración segura
            excel.Visible = True
            excel.DisplayAlerts = False
            excel.ScreenUpdating = True

            # 🔥 IMPORTANTE: NO abrir en ReadOnly
            workbook = excel.Workbooks.Open(tmp_path)

            # =====================================================
            # 🔥 FORZAR RECÁLCULO COMPLETO REAL
            # =====================================================
            try:
                # Modo automático
                excel.Calculation = -4105  # xlCalculationAutomatic

                # Rebuild completo del árbol de dependencias
                excel.CalculateFullRebuild()

                # Refrescar conexiones si existen
                workbook.RefreshAll()

                # Esperar a que termine cálculo
                while excel.CalculationState != 0:
                    pass

            except Exception:
                pass

            workbook.Saved = True

            # =====================================================
            # PROTEGER ESTRUCTURA
            # =====================================================
            try:
                workbook.Protect(
                    Password="msl_view_only",
                    Structure=True,
                    Windows=False
                )
            except Exception:
                pass

            # =====================================================
            # PROTEGER HOJAS
            # =====================================================
            for sheet in workbook.Worksheets:
                try:
                    sheet.Protect(
                        Password="msl_view_only",
                        DrawingObjects=True,
                        Contents=True,
                        Scenarios=True
                    )
                except Exception:
                    try:
                        sheet.Protect(Password="msl_view_only")
                    except Exception:
                        pass

                try:
                    sheet.EnableSelection = 0  # xlNoSelection
                except Exception:
                    pass

            # =====================================================
            # BLOQUEO VISUAL UI
            # =====================================================
            try:
                excel.DisplayFormulaBar = False
            except Exception:
                pass

            try:
                excel.ExecuteExcel4Macro('SHOW.TOOLBAR("Ribbon",False)')
            except Exception:
                pass

        except Exception as e:
            messagebox.showwarning(
                "Aviso",
                f"El Excel se abrió, pero no se pudo aplicar el modo bloqueado completo:\n{e}"
            )


    # =========================================================
    # HARD CREATE MODE (ANTI-GET / ANTI-REBUILD)
    # =========================================================
    def _force_create_mode(self):
        """
        Fuerza el formulario a modo CREATE real.
        - Nunca hace GET
        - No reconstruye UI
        - Editar deshabilitado
        - Campos editables
        """

        self.mode = "create"
        self.draft_report_number = None
        self._db_autoload_enabled = False

        # Editar siempre deshabilitado en create
        if self.btn_editar:
            try:
                self.btn_editar.config(state="disabled")
            except Exception:
                pass

        # 🔥 En CREATE los campos deben estar editables
        self._edit_mode = True

        for key, widget in self.fields.items():

            # No tocar variables internas
            if isinstance(widget, (tk.BooleanVar, tk.StringVar)):
                continue

            try:
                if isinstance(widget, ttk.Entry):
                    widget.config(state="normal")
                elif isinstance(widget, ttk.Combobox):
                    # Combobox permanece readonly para evitar texto libre
                    widget.config(state="readonly")
            except Exception:
                pass