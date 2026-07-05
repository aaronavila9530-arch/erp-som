import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

try:
    from tkcalendar import DateEntry
except Exception:
    DateEntry = None

from Modulos.Informes.date_utils import to_db_date, to_long_english_date


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

        # ---------------- BACK (FIX: ir a HOME) ----------------
        def go_home():
            try:
                from Modulos.Informes.informes_home_ui import InformesHomeUI

                for widget in self.parent.winfo_children():
                    widget.destroy()

                InformesHomeUI(
                    self.parent,
                    usuario=self.usuario,
                    rol=self.rol
                ).grid(row=0, column=0, sticky="nsew")

            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"No se pudo volver al Home:\n{e}"
                )

        ttk.Button(
            header,
            text="← Back",
            command=go_home
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
            try:
                canvas.configure(scrollregion=canvas.bbox("all"))
            except Exception:
                pass

        def _on_canvas_configure(event):
            try:
                canvas.itemconfigure(inner_id, width=event.width)
            except Exception:
                pass

        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # =====================================================
        # 🔥 SCROLL ROBUSTO PARA TODAS LAS TABS
        # =====================================================
        if not hasattr(self, "_mousewheel_canvas"):
            self._mousewheel_canvas = None
            self._mousewheel_bound = False

        def _set_active_canvas(event=None):
            self._mousewheel_canvas = canvas

        def _clear_active_canvas(event=None):
            if self._mousewheel_canvas == canvas:
                self._mousewheel_canvas = None

        def _on_mousewheel_windows(event):
            target = getattr(self, "_mousewheel_canvas", None)
            if target is None:
                return
            try:
                delta = event.delta
                if delta == 0:
                    return
                target.yview_scroll(int(-1 * (delta / 120)), "units")
            except Exception:
                pass

        def _on_mousewheel_linux_up(event):
            target = getattr(self, "_mousewheel_canvas", None)
            if target is None:
                return
            try:
                target.yview_scroll(-1, "units")
            except Exception:
                pass

        def _on_mousewheel_linux_down(event):
            target = getattr(self, "_mousewheel_canvas", None)
            if target is None:
                return
            try:
                target.yview_scroll(1, "units")
            except Exception:
                pass

        # Bind global UNA sola vez, pero scroll al canvas activo
        if not self._mousewheel_bound:
            self.bind_all("<MouseWheel>", _on_mousewheel_windows, add="+")
            self.bind_all("<Button-4>", _on_mousewheel_linux_up, add="+")
            self.bind_all("<Button-5>", _on_mousewheel_linux_down, add="+")
            self._mousewheel_bound = True

        # Cuando el mouse entra a esta zona, esta tab se vuelve la activa
        outer.bind("<Enter>", _set_active_canvas, add="+")
        outer.bind("<Leave>", _clear_active_canvas, add="+")
        canvas.bind("<Enter>", _set_active_canvas, add="+")
        canvas.bind("<Leave>", _clear_active_canvas, add="+")
        inner.bind("<Enter>", _set_active_canvas, add="+")
        inner.bind("<Leave>", _clear_active_canvas, add="+")

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
            date = DateEntry(frm, width=12, date_pattern="yyyy-mm-dd")
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
            w = DateEntry(frm, width=15, date_pattern="yyyy-mm-dd")
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
        """

        self._edit_mode = bool(enabled)

        always_editable = {
            "on_account_of",
            "word_on_behalf_of",
            "survey_requested_by",
            "word_survey_requested_by"
        }

        def _apply_state(widget, state_entry, state_combo):

            if isinstance(widget, ttk.Entry):
                widget.config(state=state_entry)

            elif isinstance(widget, ttk.Combobox):
                widget.config(state=state_combo)

        for key, widget in self.fields.items():

            # 🔥 SOPORTA MULTI-WIDGET
            widgets = widget if isinstance(widget, list) else [widget]

            for w in widgets:

                # No tocar vars internas
                if isinstance(w, (tk.BooleanVar, tk.StringVar)):
                    continue

                # 🔥 SIEMPRE EDITABLE
                if key in always_editable:
                    try:
                        _apply_state(w, "normal", "readonly")
                    except Exception:
                        pass
                    continue

                # 🔒 CONTROLADOS POR SERVICIO
                if key in getattr(self, "_non_editable_keys", []):
                    try:
                        _apply_state(w, "readonly", "readonly")
                    except Exception:
                        pass
                    continue

                # NORMAL FLOW
                try:
                    if enabled:
                        _apply_state(w, "normal", "readonly")
                    else:
                        _apply_state(w, "readonly", "readonly")
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
        ✅ Guardar:
        - SOLO UPDATE (PUT)
        - ENVÍA TODO EL PAYLOAD REAL (NO FRAGMENTADO)
        """

        self.update_idletasks()
        self.update()

        full_payload = self.get_payload()

        # 🔥 DEBUG REAL
        print("===================================")
        print("PAYLOAD ENVIADO AL PUT:")
        print(full_payload)
        print("===================================")

        # =====================================================
        # 🔒 BLOQUEO TOTAL DE CREATE
        # =====================================================
        if not self.draft_report_number:
            messagebox.showwarning(
                "Aviso",
                "Debe enviar a revisión primero antes de poder guardar."
            )
            return

        try:
            from api_client import (
                update_draft_survey_api,
                update_draft_survey_ballast_api,
                update_draft_survey_word_api
            )

            draft_id = self.draft_report_number

            # =====================================================
            # 🔥 1️⃣ UPDATE MAIN (ENVÍO COMPLETO)
            # =====================================================
            response_main = update_draft_survey_api(
                draft_id,
                full_payload   # ✅ AQUÍ ESTABA EL ERROR
            )

            if not response_main.get("success"):
                messagebox.showerror(
                    "Error",
                    response_main.get("error", "Error actualizando Draft.")
                )
                return

            # =====================================================
            # 🔥 2️⃣ BALLAST + FRESH WATER
            # =====================================================
            ballast_payload = {
                "ballast": full_payload.get("ballast") or {},
                "fresh_water": full_payload.get("fresh_water") or {}
            }

            if ballast_payload["ballast"] or ballast_payload["fresh_water"]:
                response_ballast = update_draft_survey_ballast_api(
                    draft_id,
                    ballast_payload
                )

                print("===================================")
                print("RESPUESTA BALLAST PUT:")
                print(response_ballast)
                print("===================================")

                if not response_ballast.get("success"):
                    messagebox.showerror(
                        "Error",
                        response_ballast.get("error", "Error actualizando Ballast.")
                    )
                    return

            # =====================================================
            # 🔥 3️⃣ WORD
            # =====================================================
            word_payload = full_payload.get("word")

            if isinstance(word_payload, dict):
                response_word = update_draft_survey_word_api(
                    draft_id,
                    word_payload
                )

                if not response_word.get("success"):
                    messagebox.showerror(
                        "Error",
                        response_word.get("error", "Error actualizando Word Report.")
                    )
                    return

            # =====================================================
            # ✅ OK
            # =====================================================
            messagebox.showinfo(
                "Éxito",
                "Draft actualizado correctamente."
            )

            self._set_edit_mode(False)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error guardando Draft:\n{e}"
            )


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
                return to_db_date(widget.get())

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
        # 1️⃣ CAMPOS NORMALES DEL FORM (FIX MULTI-WIDGET)
        # ============================================
        for key, w in self.fields.items():

            try:

                # 🔥 SI ES LISTA → TOMAR EL PRIMER WIDGET VÁLIDO
                if isinstance(w, list):

                    value = None

                    for widget in w:
                        v = _get_value(widget)

                        # PRIORIDAD: primer valor no vacío
                        if v not in ["", None]:
                            value = v
                            break

                    data[key] = value

                else:
                    data[key] = _get_value(w)

            except Exception:
                data[key] = None

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

        # ============================================
        # 5️⃣ 🔥 DYNAMIC FRESH WATER
        # ============================================
        if hasattr(self, "dynamic_freshwater") and isinstance(self.dynamic_freshwater, dict):

            data["fresh_water"] = {
                "init": [],
                "final": []
            }

            for prefix in ["init", "final"]:

                tank_list = self.dynamic_freshwater.get(prefix, [])

                if not isinstance(tank_list, list):
                    continue

                for tank in tank_list:

                    try:
                        tank_name = tank["tank_name"].get().strip()
                    except Exception:
                        tank_name = ""

                    if not tank_name:
                        continue

                    try:
                        height = tank["height"].get().strip()
                    except Exception:
                        height = ""

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

                    data["fresh_water"][prefix].append({
                        "tank_name": tank_name,
                        "height": height,
                        "sounding": sounding,
                        "volume": volume,
                        "density": density
                    })

        return data

    def set_payload(self, data: dict):
        """
        Carga datos al form.

        BLINDADO:
        - Soporta wrapper UNIFIED
        - Soporta dict plano
        - Fusiona fresh_water que venga fuera de data
        - Reconstruye UI dinámica de Fresh Water
        """

        if not isinstance(data, dict):
            return

        # =====================================================
        # 0) UNWRAP + MERGE SEGURO
        # =====================================================
        payload = {}

        if isinstance(data.get("data"), dict):
            payload.update(data.get("data") or {})
        elif isinstance(data.get("payload"), dict):
            payload.update(data.get("payload") or {})
        else:
            payload.update(data or {})

        # 🔥 NO PISAR metadata; solo guardar FW como bloque aparte
        fresh_water_block = data.get("fresh_water")
        if isinstance(fresh_water_block, dict):
            payload["fresh_water"] = dict(fresh_water_block)

        if not isinstance(payload, dict):
            return

        # =====================================================
        # 1) HEADER META
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
        # 2) HELPERS
        # =====================================================
        def _set_entry(entry, value):
            try:
                state = entry.cget("state")
                entry.config(state="normal")
                entry.delete(0, "end")
                entry.insert(0, "" if value is None else str(value))
                entry.config(state=state)
            except Exception:
                pass

        def _apply(widget, value):

            if isinstance(widget, list):
                for w in widget:
                    _apply(w, value)
                return

            if isinstance(widget, tk.BooleanVar):
                try:
                    widget.set(str(value).lower() in ["true", "1", "yes", "y", "si", "sí"])
                except Exception:
                    pass
                return

            if isinstance(widget, tk.StringVar):
                try:
                    widget.set("" if value is None else str(value))
                except Exception:
                    pass
                return

            if DateEntry and isinstance(widget, DateEntry):
                try:
                    if value:
                        raw = str(value).split(" ")[0]
                        parsed = to_db_date(raw)
                        if not parsed:
                            return
                        dt = datetime.strptime(parsed, "%Y-%m-%d")
                        widget.set_date(dt)
                        widget.delete(0, "end")
                        widget.insert(0, to_long_english_date(dt))
                except Exception:
                    pass
                return

            if isinstance(widget, ttk.Combobox):
                try:
                    widget.set("" if value is None else str(value))
                except Exception:
                    pass
                return

            if isinstance(widget, ttk.Entry):
                _set_entry(widget, value)
                return

        # =====================================================
        # 3) SET CAMPOS NORMALES
        # =====================================================
        for key, value in payload.items():

            widget = self.fields.get(key)
            if not widget:
                continue

            if key.endswith("_time_from") or key.endswith("_time_to"):
                if isinstance(value, str) and ":" in value:
                    try:
                        hh, mm = value.split(":")
                        self.vars[f"{key}_hour"].set(hh.zfill(2))
                        self.vars[f"{key}_minute"].set(mm.zfill(2))
                        self.vars[key].set(f"{hh}:{mm}")
                    except Exception:
                        pass
                continue

            _apply(widget, value)

        # =====================================================
        # 🔥 RECONSTRUIR WORD DATETIME (DATE + TIME → UI)
        # =====================================================
        datetime_fields = [
            "word_arrived_buoy",
            "word_nor_tendered",
            "word_all_fast",
            "word_initial_draft",
            "word_commenced",
            "word_completed",
            "word_final_draft"
        ]

        for key in datetime_fields:

            date_val = payload.get(f"{key}_date")
            time_val = payload.get(f"{key}_time")

            try:
                # ================= DATE =================
                if date_val:
                    date_widget = self.vars.get(f"{key}_date_widget")

                    if date_widget:
                        dt = datetime.strptime(str(date_val), "%Y-%m-%d")

                        if DateEntry and hasattr(date_widget, "set_date"):
                            date_widget.set_date(dt)
                            date_widget.delete(0, "end")
                            date_widget.insert(0, to_long_english_date(dt))
                        else:
                            date_widget.delete(0, "end")
                            date_widget.insert(0, to_long_english_date(dt))

                # ================= TIME =================
                if time_val:

                    parts = str(time_val).split(":")

                    if len(parts) >= 2:
                        hh = parts[0]
                        mm = parts[1]
                    else:
                        hh = "00"
                        mm = "00"

                    if f"{key}_hour" in self.vars:
                        self.vars[f"{key}_hour"].set(hh.zfill(2))

                    if f"{key}_minute" in self.vars:
                        self.vars[f"{key}_minute"].set(mm.zfill(2))

                    if key in self.vars:
                        self.vars[key].set(f"{hh}:{mm}")

            except Exception:
                pass

        # =====================================================
        # 4) TRIM TABLES
        # =====================================================
        if "trim_tables_available" in payload:
            try:
                yes = bool(payload.get("trim_tables_available"))
                self.fields["trim_tables_yes"].set(yes)
                self.fields["trim_tables_no"].set(not yes)
            except Exception:
                pass

        # =====================================================
        # 5) RECONSTRUIR FRESH WATER (PLANO + JSON)
        # =====================================================
        reconstructed_fw = {
            "init": [],
            "final": []
        }

        # ================================
        # 5A) DESDE JSON (PRIORIDAD 1)
        # ================================
        fw_json = data.get("fresh_water") or payload.get("fresh_water")

        if isinstance(fw_json, dict):
            for prefix in ["init", "final"]:
                tanks = fw_json.get(prefix, [])
                if isinstance(tanks, list):
                    for tank in tanks:
                        reconstructed_fw[prefix].append({
                            "tank_name": tank.get("tank_name"),
                            "height": tank.get("height"),
                            "sounding": tank.get("sounding"),
                            "volume": tank.get("volume"),
                            "density": tank.get("density")
                        })

        # ================================
        # 5B) FALLBACK: FORMATO PLANO
        # ================================
        if not reconstructed_fw["init"] and not reconstructed_fw["final"]:

            for prefix in ["init", "final"]:
                for i in range(1, 21):

                    name = payload.get(f"{prefix}_fw_{i}_name")
                    height = payload.get(f"{prefix}_fw_{i}_height")
                    sounding = payload.get(f"{prefix}_fw_{i}_sounding")
                    volume = payload.get(f"{prefix}_fw_{i}_volume")
                    density = payload.get(f"{prefix}_fw_{i}_density")

                    if any(v not in [None, ""] for v in [name, height, sounding, volume, density]):
                        reconstructed_fw[prefix].append({
                            "tank_name": name,
                            "height": height,
                            "sounding": sounding,
                            "volume": volume,
                            "density": density
                        })

        # =====================================================
        # 6) 🔥 RECONSTRUIR BALLAST (CRÍTICO)
        # =====================================================
        reconstructed_ballast = {
            "init": [],
            "final": []
        }

        for prefix in ["init", "final"]:

            for i in range(1, 21):

                for side in ["p", "s"]:

                    # Ej: init_wbt_1p
                    base = f"{prefix}_wbt_{i}{side}"

                    name = payload.get(f"{base}_name")
                    sounding = payload.get(f"{base}_sounding")
                    volume = payload.get(f"{base}_volume")
                    density = payload.get(f"{base}_density")

                    if any(v not in [None, ""] for v in [name, sounding, volume, density]):

                        reconstructed_ballast[prefix].append({
                            "tank_name": name or f"WBT {i}{side.upper()}",
                            "sounding": sounding,
                            "volume": volume,
                            "density": density
                        })

            # 🔹 FPT / APT / SLOP
            for tank in ["fpt", "apt", "slop_tank"]:

                name = payload.get(f"{prefix}_{tank}_name")
                sounding = payload.get(f"{prefix}_{tank}_sounding")
                volume = payload.get(f"{prefix}_{tank}_volume")
                density = payload.get(f"{prefix}_{tank}_density")

                if any(v not in [None, ""] for v in [name, sounding, volume, density]):

                    reconstructed_ballast[prefix].append({
                        "tank_name": name or tank.upper().replace("_", " "),
                        "sounding": sounding,
                        "volume": volume,
                        "density": density
                    })

        # =====================================================
        # 8) LIMPIAR + RECREAR UI DINÁMICA BALLAST (BLINDADO)
        # =====================================================
        if hasattr(self, "dynamic_ballast") and isinstance(self.dynamic_ballast, dict):

            for prefix in ["init", "final"]:

                for tank in self.dynamic_ballast.get(prefix, []):

                    widgets = tank.get("widgets", [])

                    if isinstance(widgets, list):
                        for w in widgets:
                            try:
                                w.destroy()
                            except Exception:
                                pass

                self.dynamic_ballast[prefix] = []

        else:
            self.dynamic_ballast = {"init": [], "final": []}

        # =====================================================
        # 🔥 9) LIMPIAR + RECREAR UI FRESH WATER (CRÍTICO)
        # =====================================================
        if hasattr(self, "dynamic_freshwater") and isinstance(self.dynamic_freshwater, dict):

            for prefix in ["init", "final"]:

                for tank in self.dynamic_freshwater.get(prefix, []):

                    widgets = tank.get("widgets", [])

                    if isinstance(widgets, list):
                        for w in widgets:
                            try:
                                w.destroy()
                            except Exception:
                                pass

                self.dynamic_freshwater[prefix] = []

        else:
            self.dynamic_freshwater = {"init": [], "final": []}

        # =====================================================
        # RECREAR DESDE DATA FW
        # =====================================================
        for prefix in ["init", "final"]:

            tank_list = reconstructed_fw.get(prefix, [])

            if not isinstance(tank_list, list):
                continue

            for tank in tank_list:

                try:
                    tank_dict = self._fw_adders[prefix]()

                    if not tank_dict:
                        continue

                    try:
                        tank_dict["tank_name"].insert(0, str(tank.get("tank_name") or ""))
                    except Exception:
                        pass

                    try:
                        tank_dict["height"].insert(0, str(tank.get("height") or ""))
                    except Exception:
                        pass

                    try:
                        tank_dict["sounding"].insert(0, str(tank.get("sounding") or ""))
                    except Exception:
                        pass

                    try:
                        tank_dict["volume"].insert(0, str(tank.get("volume") or ""))
                    except Exception:
                        pass

                    try:
                        tank_dict["density"].insert(0, str(tank.get("density") or ""))
                    except Exception:
                        pass

                except Exception as e:
                    print("❌ ERROR RECONSTRUYENDO FW:", e)

        # =====================================================
        # RECREAR DESDE DATA
        # =====================================================
        for prefix in ["init", "final"]:

            tank_list = reconstructed_ballast.get(prefix, [])

            if not isinstance(tank_list, list):
                continue

            for tank in tank_list:

                try:
                    # 🔥 crear fila usando builder real
                    tank_dict = self._add_ballast_row(prefix)

                    if not tank_dict:
                        continue

                    # ===============================
                    # TANK NAME (Combobox)
                    # ===============================
                    try:
                        name = tank.get("tank_name") or ""
                        tank_dict["tank_name"].set(name)
                    except Exception:
                        pass

                    # ===============================
                    # SOUNDING
                    # ===============================
                    try:
                        val = str(tank.get("sounding") or "")
                        tank_dict["sounding"].delete(0, "end")
                        tank_dict["sounding"].insert(0, val)
                    except Exception:
                        pass

                    # ===============================
                    # VOLUME
                    # ===============================
                    try:
                        val = str(tank.get("volume") or "")
                        tank_dict["volume"].delete(0, "end")
                        tank_dict["volume"].insert(0, val)
                    except Exception:
                        pass

                    # ===============================
                    # DENSITY
                    # ===============================
                    try:
                        val = str(tank.get("density") or "")
                        tank_dict["density"].delete(0, "end")
                        tank_dict["density"].insert(0, val)
                    except Exception:
                        pass

                except Exception as e:
                    print("❌ ERROR RECONSTRUYENDO BALLAST:", e)


        # =====================================================
        # 7) RECALCULAR TOTALES FW VISUALES
        # =====================================================
        for prefix in ["init", "final"]:
            total_fw = 0.0
            for tank in self.dynamic_freshwater.get(prefix, []):
                try:
                    total_fw += float(tank["volume"].get() or 0)
                except Exception:
                    pass

            if f"{prefix}_fresh_water_total" in self.vars:
                self.vars[f"{prefix}_fresh_water_total"].set(f"{total_fw:.2f}")

        # =====================================================
        # 8) RECALCULAR TOTALES BALLAST VISUALES
        # =====================================================
        for prefix in ["init", "final"]:
            total_ballast = 0.0

            for tank in self.dynamic_ballast.get(prefix, []):
                try:
                    volume = float(tank["volume"].get() or 0)
                    density = float(tank["density"].get() or 0)
                    total = volume * density
                except Exception:
                    total = 0.0

                try:
                    tank["total_var"].set(f"{total:.2f}")
                except Exception:
                    pass

                total_ballast += total

            if f"{prefix}_ballast_total" in self.vars:
                self.vars[f"{prefix}_ballast_total"].set(f"{total_ballast:.2f}")



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
            # 🔥 UNWRAP REAL DEL PAYLOAD
            # =====================================================
            if isinstance(response.get("data"), dict):
                payload = dict(response.get("data") or {})
            elif isinstance(response.get("payload"), dict):
                payload = dict(response.get("payload") or {})
            else:
                payload = dict(response or {})

            # Mantener fresh_water separado sin romper metadata
            fresh_water_block = response.get("fresh_water")
            if isinstance(fresh_water_block, dict):
                payload["fresh_water"] = fresh_water_block

            # =====================================================
            # 1️⃣ Cargar TODO el form
            # =====================================================
            self.set_payload({
                "data": payload,
                "fresh_water": fresh_water_block or {}
            })

            # =====================================================
            # 2️⃣ HEADER META — USAR PAYLOAD UNWRAPPED, NO response crudo
            # =====================================================
            try:
                self.meta_vars["anio"].set(str(payload.get("year", "") or ""))
                self.meta_vars["mes"].set(str(payload.get("month", "") or ""))
                self.meta_vars["continente"].set(str(payload.get("continent", "") or ""))
                self.meta_vars["pais"].set(str(payload.get("country", "") or ""))
                self.meta_vars["puerto"].set(str(payload.get("port", "") or ""))
                self.meta_vars["cliente"].set(str(payload.get("client", "") or ""))
                self.meta_vars["num_informe"].set(
                    str(payload.get("draft_report_number", self.draft_report_number) or "")
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
            try:
                if fecha_inicio and isinstance(fecha_inicio, str):
                    raw = to_db_date(fecha_inicio)
                    dt = datetime.strptime(raw, "%Y-%m-%d") if raw else datetime.now()

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
            # HEADER META (READONLY) — TAL CUAL
            # =====================================================
            self.meta_vars["anio"].set("" if anio is None else str(anio))
            self.meta_vars["mes"].set("" if mes is None else str(mes))
            self.meta_vars["pais"].set("" if pais is None else str(pais))
            self.meta_vars["continente"].set("" if continente is None else str(continente))
            self.meta_vars["puerto"].set("" if puerto is None else str(puerto))
            self.meta_vars["cliente"].set("" if cliente is None else str(cliente))
            self.meta_vars["num_informe"].set("" if num_informe is None else str(num_informe))

            # =====================================================
            # GENERAL TAB FIELDS — TAL CUAL
            # =====================================================
            if "vessel_mv" in self.fields:
                self.fields["vessel_mv"].config(state="normal")
                self.fields["vessel_mv"].delete(0, "end")
                self.fields["vessel_mv"].insert(0, "" if vessel is None else str(vessel))

            if "survey_no" in self.fields:
                self.fields["survey_no"].config(state="normal")
                self.fields["survey_no"].delete(0, "end")
                self.fields["survey_no"].insert(0, "" if num_informe is None else str(num_informe))

            # =====================================================
            # WORD TAB SYNC — TAL CUAL
            # =====================================================
            if "word_vessel" in self.fields:
                self.fields["word_vessel"].config(state="normal")
                self.fields["word_vessel"].delete(0, "end")
                self.fields["word_vessel"].insert(0, "" if vessel is None else str(vessel))

            if "word_name" in self.fields:
                self.fields["word_name"].config(state="normal")
                self.fields["word_name"].delete(0, "end")
                self.fields["word_name"].insert(0, "" if vessel is None else str(vessel))

            if "word_port" in self.fields:
                self.fields["word_port"].config(state="normal")
                self.fields["word_port"].delete(0, "end")
                self.fields["word_port"].insert(0, "" if puerto is None else str(puerto))

            if "word_country" in self.fields:
                self.fields["word_country"].config(state="normal")
                self.fields["word_country"].delete(0, "end")
                self.fields["word_country"].insert(0, "" if pais is None else str(pais))


            # =====================================================
            # 🔒 BLOQUEAR CAMPOS CONTROLADOS POR SERVICIO
            # =====================================================
            # 🔒 SOLO CAMPOS REALMENTE CONTROLADOS POR SERVICIO
            self._non_editable_keys = [
                "vessel_mv",
                "survey_no",
                "word_vessel",
                "word_name",
                "word_port",
                "word_country",
            ]

            self._lock_fields(self._non_editable_keys)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo cargar el servicio:\n{e}"
            )


    # =========================================================
    # ENVIAR A REVISION (GENERAL + BALLAST + WORD) — ULTRA FIX FINAL
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
            # 1️⃣ GENERAL — TAL CUAL SALE DEL FORM
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
            # HELPERS SANITIZACIÓN SOLO PARA NUMÉRICOS/VACÍOS
            # (NO MODIFICA TEXTO)
            # =====================================================
            def clean_value(v):

                if v is None:
                    return None

                if isinstance(v, str):
                    if v == "":
                        return None

                    try:
                        return float(v.replace(",", "."))
                    except Exception:
                        return v

                return v

            # =====================================================
            # 2️⃣ BALLAST + FRESH WATER
            #    NUEVO FORMATO PARA API NUEVA
            # =====================================================
            ballast_payload = {
                "ballast": full_payload.get("ballast") or {},
                "fresh_water": full_payload.get("fresh_water") or {}
            }

            print("========== DEBUG BALLAST CREATE ==========")
            print("BALLAST PAYLOAD:")
            print(ballast_payload)
            print("==========================================")

            if ballast_payload["ballast"] or ballast_payload["fresh_water"]:

                from api_client import create_draft_survey_ballast_api

                ballast_response = create_draft_survey_ballast_api(
                    draft_survey_id,
                    ballast_payload
                )

                print("===================================")
                print("RESPUESTA BALLAST POST:")
                print(ballast_response)
                print("===================================")

                if not ballast_response.get("success"):
                    raise Exception(
                        ballast_response.get("error", "Error enviando ballast")
                    )

            # =====================================================
            # 4️⃣ WORD
            # =====================================================
            word_payload = {}

            datetime_fields = [
                "word_arrived_buoy",
                "word_nor_tendered",
                "word_all_fast",
                "word_initial_draft",
                "word_commenced",
                "word_completed",
                "word_final_draft"
            ]

            for key, value in full_payload.items():

                if not key.startswith("word_"):
                    continue

                if key in datetime_fields:

                    date_widget = self.vars.get(f"{key}_date_widget")
                    hour_var = self.vars.get(f"{key}_hour")
                    minute_var = self.vars.get(f"{key}_minute")

                    dt_value = None

                    try:
                        if date_widget:
                            if DateEntry and hasattr(date_widget, "get_date"):
                                dt_value = date_widget.get_date()
                            else:
                                raw = str(date_widget.get()).strip()
                                if raw:
                                    parsed = to_db_date(raw)
                                    if parsed:
                                        dt_value = datetime.strptime(parsed, "%Y-%m-%d")
                    except Exception:
                        dt_value = None

                    word_payload[f"{key}_date"] = (
                        dt_value.strftime("%Y-%m-%d") if dt_value else None
                    )

                    hh = "00"
                    mm = "00"

                    try:
                        if hour_var:
                            hh = str(hour_var.get()).zfill(2)
                        if minute_var:
                            mm = str(minute_var.get()).zfill(2)
                    except Exception:
                        pass

                    word_payload[f"{key}_time"] = f"{hh}:{mm}"
                    continue

                word_payload[key] = value

            for key in metadata_keys:
                word_payload[key] = full_payload.get(key)

            if word_payload:
                word_response = create_draft_survey_word_api(
                    draft_survey_id,
                    word_payload
                )

                if not word_response.get("success"):
                    raise Exception(word_response)

            messagebox.showinfo(
                "Éxito",
                "Draft Survey enviado correctamente a revisión."
            )

            # =====================================================
            # 🔥 CAMBIAR A MODO EDIT DESPUÉS DEL POST
            # =====================================================
            self.draft_report_number = draft_survey_id
            self.mode = "edit"
            self._db_autoload_enabled = True

            if self.btn_editar:
                try:
                    self.btn_editar.config(state="normal")
                except Exception:
                    pass

            # 🔒 bloquear edición hasta que usuario presione Editar
            self._set_edit_mode(False)


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
    # BALLAST + FRESH WATER (LAYOUT CORREGIDO PARA LAPTOP)
    # =========================================================
    def _ballast_table_block(self, parent, prefix: str):

        # =========================================================
        # INIT STRUCTURE (SAFE)
        # =========================================================
        if not hasattr(self, "dynamic_ballast"):
            self.dynamic_ballast = {"init": [], "final": []}

        if prefix not in self.dynamic_ballast:
            self.dynamic_ballast[prefix] = []

        if not hasattr(self, "dynamic_freshwater"):
            self.dynamic_freshwater = {"init": [], "final": []}

        if prefix not in self.dynamic_freshwater:
            self.dynamic_freshwater[prefix] = []

        self.vars[f"{prefix}_ballast_total"] = tk.StringVar(value="0.00")
        self.vars[f"{prefix}_fresh_water_total"] = tk.StringVar(value="0.00")

        # =========================================================
        # WRAPPER PRINCIPAL
        # =========================================================
        wrapper = ttk.Frame(parent)
        wrapper.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        # =========================================================
        # BLOQUE 1: BALLAST
        # =========================================================
        ballast_box = ttk.LabelFrame(wrapper, text="BALLAST")
        ballast_box.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        ballast_box.grid_columnconfigure(0, weight=1)
        ballast_box.grid_rowconfigure(0, weight=1)

        ballast_canvas = tk.Canvas(ballast_box, highlightthickness=0, height=260)
        ballast_canvas.grid(row=0, column=0, sticky="nsew")

        ballast_scroll = ttk.Scrollbar(
            ballast_box,
            orient="vertical",
            command=ballast_canvas.yview
        )
        ballast_scroll.grid(row=0, column=1, sticky="ns")

        ballast_canvas.configure(yscrollcommand=ballast_scroll.set)

        ballast_inner = ttk.Frame(ballast_canvas)
        ballast_window = ballast_canvas.create_window(
            (0, 0),
            window=ballast_inner,
            anchor="nw"
        )

        def _on_ballast_inner_configure(event):
            try:
                ballast_canvas.configure(scrollregion=ballast_canvas.bbox("all"))
            except Exception:
                pass

        def _on_ballast_canvas_configure(event):
            try:
                ballast_canvas.itemconfigure(ballast_window, width=event.width)
            except Exception:
                pass

        ballast_inner.bind("<Configure>", _on_ballast_inner_configure)
        ballast_canvas.bind("<Configure>", _on_ballast_canvas_configure)

        # =========================================================
        # BLOQUE 2: FRESH WATER
        # =========================================================
        fw_box = ttk.LabelFrame(wrapper, text="FRESH WATER")
        fw_box.grid(row=1, column=0, sticky="nsew")

        fw_box.grid_columnconfigure(0, weight=1)
        fw_box.grid_rowconfigure(0, weight=1)

        fw_canvas = tk.Canvas(fw_box, highlightthickness=0, height=260)
        fw_canvas.grid(row=0, column=0, sticky="nsew")

        # =========================
        # SCROLL VERTICAL
        # =========================
        fw_scroll_y = ttk.Scrollbar(
            fw_box,
            orient="vertical",
            command=fw_canvas.yview
        )
        fw_scroll_y.grid(row=0, column=1, sticky="ns")

        # =========================
        # 🔥 SCROLL HORIZONTAL
        # =========================
        fw_scroll_x = ttk.Scrollbar(
            fw_box,
            orient="horizontal",
            command=fw_canvas.xview
        )
        fw_scroll_x.grid(row=1, column=0, sticky="ew")

        # =========================
        # CONFIGURACIÓN
        # =========================
        fw_canvas.configure(
            yscrollcommand=fw_scroll_y.set,
            xscrollcommand=fw_scroll_x.set
        )

        fw_inner = ttk.Frame(fw_canvas)
        fw_window = fw_canvas.create_window(
            (0, 0),
            window=fw_inner,
            anchor="nw"
        )

        def _on_fw_inner_configure(event):
            try:
                fw_canvas.configure(scrollregion=fw_canvas.bbox("all"))
            except Exception:
                pass

        def _on_fw_canvas_configure(event):
            try:
                # 🔥 NO forzar width → permite scroll horizontal
                fw_canvas.itemconfigure(fw_window)
            except Exception:
                pass

        fw_inner.bind("<Configure>", _on_fw_inner_configure)
        fw_canvas.bind("<Configure>", _on_fw_canvas_configure)

        # =========================================================
        # SCROLL CON RUEDA EN SUBCANVAS
        # =========================================================
        def _bind_local_mousewheel(canvas_widget):
            def _on_mousewheel(event):
                try:
                    if event.delta != 0:
                        canvas_widget.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except Exception:
                    pass

            def _on_linux_up(event):
                try:
                    canvas_widget.yview_scroll(-1, "units")
                except Exception:
                    pass

            def _on_linux_down(event):
                try:
                    canvas_widget.yview_scroll(1, "units")
                except Exception:
                    pass

            canvas_widget.bind("<Enter>", lambda e: canvas_widget.focus_set(), add="+")
            canvas_widget.bind("<MouseWheel>", _on_mousewheel, add="+")
            canvas_widget.bind("<Button-4>", _on_linux_up, add="+")
            canvas_widget.bind("<Button-5>", _on_linux_down, add="+")

        _bind_local_mousewheel(ballast_canvas)
        _bind_local_mousewheel(fw_canvas)

        # =========================================================
        # AVAILABLE TANKS
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

        # =========================================================
        # BALLAST HEADERS
        # =========================================================
        ballast_headers = ["Tank", "Sounding", "Volume", "Density", "Total", ""]
        for col, header in enumerate(ballast_headers):
            ttk.Label(
                ballast_inner,
                text=header,
                font=("Segoe UI", 9, "bold")
            ).grid(row=0, column=col, padx=6, pady=4, sticky="w")

        start_row_ballast = 1

        # =========================================================
        # HELPERS BALLAST
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

                try:
                    tank["total_var"].set(f"{total:.2f}")
                except Exception:
                    pass

                grand_total += total

            self.vars[f"{prefix}_ballast_total"].set(f"{grand_total:.2f}")

        def redraw_ballast_rows():

            for idx, tank in enumerate(self.dynamic_ballast[prefix]):
                row = start_row_ballast + idx

                for col, widget in enumerate(tank["widgets"]):
                    try:
                        widget.grid_configure(row=row, column=col)
                    except Exception:
                        pass

            try:
                ballast_total_label.grid_configure(
                    row=start_row_ballast + len(self.dynamic_ballast[prefix]) + 1
                )
                ballast_total_entry.grid_configure(
                    row=start_row_ballast + len(self.dynamic_ballast[prefix]) + 1
                )
            except Exception:
                pass

        def remove_ballast_row(tank_dict):

            try:
                for widget in tank_dict["widgets"]:
                    widget.destroy()
            except Exception:
                pass

            if tank_dict in self.dynamic_ballast[prefix]:
                self.dynamic_ballast[prefix].remove(tank_dict)

            redraw_ballast_rows()
            recalc_ballast()

        def add_tank_row():

            row = start_row_ballast + len(self.dynamic_ballast[prefix])

            tank_cb = ttk.Combobox(
                ballast_inner,
                values=available_tanks,
                width=18,
                state="readonly"
            )
            tank_cb.grid(row=row, column=0, padx=6, pady=2, sticky="w")

            sounding = ttk.Entry(ballast_inner, width=10)
            sounding.grid(row=row, column=1, padx=6, pady=2, sticky="w")

            volume = ttk.Entry(ballast_inner, width=10)
            volume.grid(row=row, column=2, padx=6, pady=2, sticky="w")

            density = ttk.Entry(ballast_inner, width=10)
            density.grid(row=row, column=3, padx=6, pady=2, sticky="w")

            total_var = tk.StringVar(value="0.00")

            total_entry = ttk.Entry(
                ballast_inner,
                textvariable=total_var,
                state="readonly",
                width=12
            )
            total_entry.grid(row=row, column=4, padx=6, pady=2, sticky="w")

            remove_btn = ttk.Button(
                ballast_inner,
                text="✕",
                width=3
            )
            remove_btn.grid(row=row, column=5, padx=4, pady=2, sticky="w")

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

            remove_btn.config(command=lambda: remove_ballast_row(tank_dict))
            volume.bind("<KeyRelease>", lambda e: recalc_ballast())
            density.bind("<KeyRelease>", lambda e: recalc_ballast())

            self.dynamic_ballast[prefix].append(tank_dict)

            redraw_ballast_rows()
            recalc_ballast()

            return tank_dict

        # =========================================================
        # BOTÓN ADD BALLAST
        # =========================================================
        ttk.Button(
            ballast_inner,
            text="+ Add Tank",
            command=add_tank_row
        ).grid(row=0, column=6, padx=(10, 0), pady=2, sticky="w")

        # =========================================================
        # TOTAL BALLAST
        # =========================================================
        ballast_total_label = ttk.Label(
            ballast_inner,
            text="TOTAL BALLAST",
            font=("Segoe UI", 10, "bold")
        )
        ballast_total_label.grid(
            row=start_row_ballast + len(self.dynamic_ballast[prefix]) + 1,
            column=3,
            sticky="e",
            padx=6,
            pady=(16, 6)
        )

        ballast_total_entry = ttk.Entry(
            ballast_inner,
            textvariable=self.vars[f"{prefix}_ballast_total"],
            state="readonly",
            width=15
        )
        ballast_total_entry.grid(
            row=start_row_ballast + len(self.dynamic_ballast[prefix]) + 1,
            column=4,
            sticky="w",
            padx=6,
            pady=(16, 6)
        )

        for c in range(7):
            ballast_inner.grid_columnconfigure(c, weight=0)
        ballast_inner.grid_columnconfigure(6, weight=1)

        # =========================================================
        # REGISTRAR BUILDER BALLAST
        # =========================================================
        if not hasattr(self, "_ballast_adders"):
            self._ballast_adders = {}

        self._ballast_adders[prefix] = add_tank_row

        # =========================================================
        # FRESH WATER HEADERS
        # =========================================================
        fw_headers = ["Tank", "Height", "Sounding", "Volume", "Density", "Total", ""]
        for col, header in enumerate(fw_headers):
            ttk.Label(
                fw_inner,
                text=header,
                font=("Segoe UI", 9, "bold")
            ).grid(row=0, column=col, padx=6, pady=4, sticky="w")

        start_row_fw = 1

        # =========================================================
        # HELPERS FRESH WATER
        # =========================================================
        def recalc_fw():

            total_fw = 0.0

            for tank in self.dynamic_freshwater[prefix]:
                try:
                    volume = float(tank["volume"].get() or 0)
                except Exception:
                    volume = 0.0

                result = volume

                try:
                    tank["total_var"].set(f"{result:.2f}")
                except Exception:
                    pass

                total_fw += result

            self.vars[f"{prefix}_fresh_water_total"].set(f"{total_fw:.2f}")

        def redraw_fw_rows():

            for idx, tank in enumerate(self.dynamic_freshwater[prefix]):
                row = start_row_fw + idx

                for col, widget in enumerate(tank["widgets"]):
                    try:
                        widget.grid_configure(row=row, column=col)
                    except Exception:
                        pass

            try:
                fw_total_label.grid_configure(
                    row=start_row_fw + len(self.dynamic_freshwater[prefix]) + 1
                )
                fw_total_entry.grid_configure(
                    row=start_row_fw + len(self.dynamic_freshwater[prefix]) + 1
                )
            except Exception:
                pass

        def remove_fw_row(tank_dict):

            try:
                for widget in tank_dict["widgets"]:
                    widget.destroy()
            except Exception:
                pass

            if tank_dict in self.dynamic_freshwater[prefix]:
                self.dynamic_freshwater[prefix].remove(tank_dict)

            redraw_fw_rows()
            recalc_fw()

        def add_fw_row():

            row = start_row_fw + len(self.dynamic_freshwater[prefix])

            tank_name = ttk.Entry(fw_inner, width=20)
            tank_name.grid(row=row, column=0, padx=6, pady=2, sticky="w")

            height = ttk.Entry(fw_inner, width=10)
            height.grid(row=row, column=1, padx=6, pady=2, sticky="w")

            sounding = ttk.Entry(fw_inner, width=10)
            sounding.grid(row=row, column=2, padx=6, pady=2, sticky="w")

            volume = ttk.Entry(fw_inner, width=10)
            volume.grid(row=row, column=3, padx=6, pady=2, sticky="w")

            density = ttk.Entry(fw_inner, width=10)
            density.grid(row=row, column=4, padx=6, pady=2, sticky="w")

            total_var = tk.StringVar(value="0.00")

            total_entry = ttk.Entry(
                fw_inner,
                textvariable=total_var,
                state="readonly",
                width=12
            )
            total_entry.grid(row=row, column=5, padx=6, pady=2, sticky="w")

            remove_btn = ttk.Button(
                fw_inner,
                text="✕",
                width=3
            )
            remove_btn.grid(row=row, column=6, padx=4, pady=2, sticky="w")

            tank_dict = {
                "tank_name": tank_name,
                "height": height,
                "sounding": sounding,
                "volume": volume,
                "density": density,
                "total_var": total_var,
                "widgets": [
                    tank_name,
                    height,
                    sounding,
                    volume,
                    density,
                    total_entry,
                    remove_btn
                ]
            }

            remove_btn.config(command=lambda: remove_fw_row(tank_dict))
            volume.bind("<KeyRelease>", lambda e: recalc_fw())

            self.dynamic_freshwater[prefix].append(tank_dict)

            redraw_fw_rows()
            recalc_fw()

            return tank_dict

        # =========================================================
        # BOTÓN ADD FRESH WATER
        # =========================================================
        ttk.Button(
            fw_inner,
            text="+ Add FW Tank",
            command=add_fw_row
        ).grid(row=0, column=7, padx=(10, 0), pady=2, sticky="w")

        # =========================================================
        # TOTAL FRESH WATER
        # =========================================================
        fw_total_label = ttk.Label(
            fw_inner,
            text="TOTAL FRESH WATER",
            font=("Segoe UI", 10, "bold")
        )
        fw_total_label.grid(
            row=start_row_fw + len(self.dynamic_freshwater[prefix]) + 1,
            column=3,
            sticky="e",
            padx=6,
            pady=(16, 6)
        )

        fw_total_entry = ttk.Entry(
            fw_inner,
            textvariable=self.vars[f"{prefix}_fresh_water_total"],
            state="readonly",
            width=15
        )
        fw_total_entry.grid(
            row=start_row_fw + len(self.dynamic_freshwater[prefix]) + 1,
            column=4,
            sticky="w",
            padx=6,
            pady=(16, 6)
        )

        for c in range(8):
            fw_inner.grid_columnconfigure(c, weight=0)
        fw_inner.grid_columnconfigure(7, weight=1)

        # =========================================================
        # REGISTRAR BUILDER FRESH WATER
        # =========================================================
        if not hasattr(self, "_fw_adders"):
            self._fw_adders = {}

        self._fw_adders[prefix] = add_fw_row


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
                    date_pattern="yyyy-mm-dd"
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
                        try:
                            raw = date_widget.get_date()
                        except Exception:
                            raw = date_widget.get()
                        formatted = to_long_english_date(raw)
                        if formatted and DateEntry and isinstance(date_widget, DateEntry):
                            date_widget.delete(0, "end")
                            date_widget.insert(0, formatted)
                    else:
                        formatted = date_widget.get()

                    final_var.set(f"{to_db_date(formatted)} {hour.get().zfill(2)}:{minute.get().zfill(2)}")
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

        except Exception as e:
            try:
                messagebox.showerror(
                    "Error Excel",
                    f"No se pudo abrir el archivo:\n{e}"
                )
            except Exception:
                pass
            return

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
            # 🔥 MODO EDITABLE REAL (SIN BLOQUEO)
            # =====================================================

            try:
                workbook.Unprotect()
            except Exception:
                pass

            for sheet in workbook.Worksheets:
                try:
                    sheet.Unprotect()
                except Exception:
                    pass

                try:
                    sheet.EnableSelection = 1  # xlUnlockedCells
                except Exception:
                    pass

            try:
                excel.DisplayFormulaBar = True
            except Exception:
                pass

            try:
                excel.ExecuteExcel4Macro('SHOW.TOOLBAR("Ribbon",True)')
            except Exception:
                pass

            try:
                workbook.Saved = False
            except Exception:
                pass

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


    # =========================================================
    # 🔥 BUILDER BALLAST (CRÍTICO PARA set_payload)
    # =========================================================
    def _add_ballast_row(self, prefix):
        try:
            return self._ballast_adders[prefix]()
        except Exception as e:
            print("❌ ERROR _add_ballast_row:", e)
            return None



