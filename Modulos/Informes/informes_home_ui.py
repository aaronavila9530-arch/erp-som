import tkinter as tk
from tkinter import ttk

from Modulos.Informes.status_informes_table import StatusInformesTable
from Modulos.Informes.informes_table import InformesTable
from Modulos.Informes.informes_vessel_grain_table import VesselGrainSamplingTable
from Modulos.Informes.vessel_truck_supervision.vessel_truck_supervision_table import (
    VesselTruckSupervisionTable
)
from Modulos.Informes.Vessel_Draft_Survey.draft_survey_table import DraftSurveyTable

from Modulos.Informes.vessel_bunker.vessel_bunker_table import VesselBunkerTable

from Modulos.Informes.vessel_cargo_condition_survey.vessel_cargo_condition_table import (
    VesselCargoConditionTable
)


from Modulos.Informes.crane_inspection.crane_inspection_table import (
    CraneInspectionTable
)


from Modulos.Informes.proyectos_calculo_ui import ProyectosCalculoUI


class InformesHomeUI(ttk.Frame):
    """
    HOME — MÓDULO INFORMES MARÍTIMOS

    • StatusInformesTable como MAIN SCREEN fijo
    • Combobox "Revisar informes" SOLO para cambiar tipo
    • Cambio dinámico de tabla
    • Sin auto-load
    """

    def __init__(self, parent, usuario, rol, callbacks=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.callbacks = callbacks or {}

        # 🔒 BLINDAJE LAYOUT
        try:
            parent.grid_rowconfigure(0, weight=1)
            parent.grid_columnconfigure(0, weight=1)
            parent.pack_propagate(False)
            parent.grid_propagate(False)
        except Exception:
            pass

        self.grid(row=0, column=0, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.current_table = None

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        # ================= HEADER =================
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=(15, 10))

        ttk.Label(
            header,
            text="Informes Marítimos",
            font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        actions = ttk.Frame(header)
        actions.pack(side="right")

        # =========================================================
        # 🔽 REVISAR INFORMES (SOLO TIPOS)
        # =========================================================
        ttk.Label(actions, text="Revisar informes:").pack(
            side="left", padx=(0, 5)
        )

        self.review_option = tk.StringVar()

        self.review_cb = ttk.Combobox(
            actions,
            textvariable=self.review_option,
            state="readonly",
            width=30,
            values=[
                "Informes de contenedores",
                "Informe de muestreos de granos",
                "Informe Truck Supervision",
                "Informe Draft Survey",
                "Informe Vessel Bunker",
                "Informe Cargo Condition Survey",
                "Informe Crane Inspection"
            ]
        )
        self.review_cb.pack(side="left", padx=(0, 15))
        self.review_cb.bind("<<ComboboxSelected>>", self._change_table)

        # -----------------------------------------------------
        # GENERAR
        # -----------------------------------------------------
        ttk.Button(
            actions,
            text="➕ Generar Informe",
            command=self._on_generate_report
        ).pack(side="left", padx=(0, 10))

        # -----------------------------------------------------
        # CALCULADORA
        # -----------------------------------------------------
        ttk.Button(
            actions,
            text="🧮 Calculadora de proyectos",
            command=self._on_project_calculator
        ).pack(side="left")

        # ================= CONTENT AREA =================
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 20)
        )

        # -----------------------------------------------------
        # MAIN SCREEN FIJO (NO DEPENDE DEL COMBO)
        # -----------------------------------------------------
        self._load_status_informes()

    # =========================================================
    # TABLE SWITCHER
    # =========================================================
    def _clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def _change_table(self, event=None):

        selection = self.review_option.get()

        self._clear_content()

        if selection == "Informes de contenedores":
            self._load_container_reports()

        elif selection == "Informe de muestreos de granos":
            self._load_grain_sampling()

        elif selection == "Informe Truck Supervision":
            self._load_truck_supervision()

        elif selection == "Informe Draft Survey":
            self._load_draft_survey()

        elif selection == "Informe Vessel Bunker":
            self._load_vessel_bunker()

        elif selection == "Informe Cargo Condition Survey":
            self._load_cargo_condition()

        elif selection == "Informe Crane Inspection":
            self._load_crane_inspection()

    # ---------------------------------------------------------
    # LOADERS
    # ---------------------------------------------------------
    def _load_status_informes(self):
        self.current_table = StatusInformesTable(self.content_frame)
        self.current_table.pack(fill="both", expand=True)

    def _load_container_reports(self):
        self.current_table = InformesTable(self.content_frame)
        self.current_table.pack(fill="both", expand=True)

    def _load_grain_sampling(self):
        self.current_table = VesselGrainSamplingTable(self.content_frame)
        self.current_table.pack(fill="both", expand=True)

    # ---------------------------------------------------------
    # LOAD TRUCK SUPERVISION
    # ---------------------------------------------------------
    def _load_truck_supervision(self):

        self.current_table = VesselTruckSupervisionTable(
            self.content_frame
        )

        self.current_table.pack(
            fill="both",
            expand=True
        )


    # ---------------------------------------------------------
    # LOAD DRAFT SURVEY
    # ---------------------------------------------------------
    def _load_draft_survey(self):

        self.current_table = DraftSurveyTable(
            self.content_frame
        )

        self.current_table.pack(
            fill="both",
            expand=True
        )


    # ---------------------------------------------------------
    # LOAD VESSEL BUNKER
    # ---------------------------------------------------------
    def _load_vessel_bunker(self):

        self.current_table = VesselBunkerTable(
            self.content_frame
        )

        self.current_table.pack(
            fill="both",
            expand=True
        )


    # ---------------------------------------------------------
    # LOAD CARGO CONDITION SURVEY
    # ---------------------------------------------------------
    def _load_cargo_condition(self):

        self.current_table = VesselCargoConditionTable(
            self.content_frame
        )

        self.current_table.pack(
            fill="both",
            expand=True
        )


    # ---------------------------------------------------------
    # LOAD CRANE INSPECTION
    # ---------------------------------------------------------
    def _load_crane_inspection(self):

        self.current_table = CraneInspectionTable(
            self.content_frame,
            usuario=self.usuario,
            rol=self.rol
        )

        self.current_table.pack(
            fill="both",
            expand=True
        )


    # =========================================================
    # ACTIONS
    # =========================================================
    def _on_generate_report(self):
        cb = self.callbacks.get("open_report_selector")
        if cb:
            cb()

    def _on_project_calculator(self):
        self._open_proyectos_calculo()

    # =========================================================
    # NAVIGATION
    # =========================================================
    def _open_proyectos_calculo(self):

        for widget in self.parent.winfo_children():
            widget.destroy()

        ProyectosCalculoUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._volver_home
        )

    def _volver_home(self):

        for widget in self.parent.winfo_children():
            widget.destroy()

        InformesHomeUI(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            callbacks=self.callbacks
        )
