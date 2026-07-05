import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Informes.vessel.vessel_grain_sampling_form import (
    GrainSamplingVesselForm
)

from Modulos.Informes.vessel_truck_supervision.vessel_truck_supervision_form import (
    VesselTruckSupervisionForm
)

from Modulos.Informes.Vessel_Draft_Survey.draft_survey_form import (
    DraftSurveyForm
)

from Modulos.Informes.Vessel_Draft_Survey.popup_draft_survey_selector import (
    PopupDraftSurveySelector
)

from Modulos.Informes.vessel_bunker.vessel_bunker_form import (
    VesselBunkerReportForm
)

# ✅ NUEVO — CARGO CONDITION SURVEY
from Modulos.Informes.vessel_cargo_condition_survey.vessel_cargo_condition_survey_form import (
    VesselCargoConditionSurveyForm
)


# ✅ NUEVO — CRANE INSPECTION SURVEY
from Modulos.Informes.crane_inspection.crane_inspection_form import (
    CraneInspectionForm
)

# ✅ NUEVO — VESSEL CONDITION SURVEY
from Modulos.Informes.vessel_condition_survey.vessel_condition_survey_form import (
    VesselConditionSurveyForm
)

# ✅ NUEVO — PORT CAPTANCY REPORT
from Modulos.Informes.port_captancy.port_captancy_form import (
    PortCaptancyForm
)


class PopupVesselReportSelector(tk.Toplevel):
    """
    POPUP — Vessel Report Type Selector
    """

    def __init__(self, parent, usuario=None, rol=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol

        self.title("Select Vessel Report Type")
        self.geometry("520x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        container = ttk.Frame(self, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Vessel Report Type",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0, 15))

        ttk.Label(
            container,
            text="Select the type of vessel report you want to create:",
            wraplength=460
        ).pack(anchor="w", pady=(0, 20))

        # ================= OPTIONS =================

        self._build_button(
            container,
            text="✅ Muestreo de Granos",
            enabled=True,
            command=self._open_grain_sampling
        )

        self._build_button(
            container,
            text="🚛 Logistics Supervision",
            enabled=True,
            command=self._open_truck_supervision
        )

        self._build_button(
            container,
            text="📐 Draft Survey",
            enabled=True,
            command=self._open_draft_survey
        )

        # =========================================================
        # VESSEL HIRE & BUNKER (SIN CONDICIONAL)
        # =========================================================
        self._build_button(
            container,
            text="⛽ Vessel Hire & Bunker Survey (On / Off / Spot)",
            enabled=True,
            command=self._open_vessel_bunker_report
        )

        # =========================================================
        # CARGO CONDITION SURVEY — HABILITADO
        # =========================================================
        self._build_button(
            container,
            text="🏗️ Crane Inspection",
            enabled=True,
            command=self._open_crane_inspection
        )


        # =========================================================
        # CRANE INSPECTION — HABILITADO
        # =========================================================
        self._build_button(
            container,
            text="📦 Cargo Condition Survey",
            enabled=True,
            command=self._open_cargo_condition
        )

        # =========================================================
        # VESSEL CONDITION SURVEY — NUEVO
        # =========================================================
        self._build_button(
            container,
            text="🚢 Vessel Condition Survey",
            enabled=True,
            command=self._open_vessel_condition
        )

        # =========================================================
        # PORT CAPTANCY — NUEVO
        # =========================================================
        self._build_button(
            container,
            text="🧭 Port Captancy",
            enabled=True,
            command=self._open_port_captancy
        )

    # =========================================================
    # HELPERS
    # =========================================================
    def _build_button(self, parent, text, enabled, command=None):

        btn = ttk.Button(
            parent,
            text=text,
            command=command if enabled else None
        )
        btn.pack(fill="x", pady=5)

        if not enabled:
            btn.state(["disabled"])

    # =========================================================
    # ACTIONS
    # =========================================================

    def _open_grain_sampling(self):

        self.destroy()
        self._clear_parent()

        GrainSamplingVesselForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )

    def _open_truck_supervision(self):

        self.destroy()
        self._clear_parent()

        VesselTruckSupervisionForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent,
            mode="create"
        )

    # =========================================================
    # DRAFT SURVEY (SE MANTIENE CON CONDICIONAL)
    # =========================================================
    def _open_draft_survey(self):

        choice = messagebox.askyesnocancel(
            "Draft Survey",
            "¿Desea realizar un Reporte desde 0?\n\n"
            "Sí  → Crear nuevo\n"
            "No → Cargar existente"
        )

        if choice is None:
            return

        # ================= NUEVO =================
        if choice is True:

            self.destroy()
            self._clear_parent()

            DraftSurveyForm(
                self.parent,
                usuario=self.usuario,
                rol=self.rol,
                on_back=self._back_to_parent
            )

        # ================= CARGAR EXISTENTE =================
        else:

            self.destroy()

            PopupDraftSurveySelector(
                self.parent,
                on_select=self._open_existing_draft
            )

    # =========================================================
    # ABRIR DRAFT EXISTENTE
    # =========================================================
    def _open_existing_draft(self, num_informe):

        self._clear_parent()

        DraftSurveyForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent,
            mode="edit",
            draft_report_number=num_informe
        )

    # =========================================================
    # VESSEL BUNKER (SIN CONDICIONAL — SIEMPRE NUEVO)
    # =========================================================
    def _open_vessel_bunker_report(self):

        self.destroy()
        self._clear_parent()

        VesselBunkerReportForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )

    # =========================================================
    # CARGO CONDITION SURVEY
    # =========================================================
    def _open_cargo_condition(self):

        self.destroy()
        self._clear_parent()

        VesselCargoConditionSurveyForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )


    # =========================================================
    # CRANE INSPECTION SURVEY
    # =========================================================
    def _open_crane_inspection(self):

        self.destroy()
        self._clear_parent()

        CraneInspectionForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )


    # =========================================================
    # VESSEL CONDITION SURVEY
    # =========================================================
    def _open_vessel_condition(self):

        self.destroy()
        self._clear_parent()

        VesselConditionSurveyForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )

    # =========================================================
    # PORT CAPTANCY REPORT
    # =========================================================
    def _open_port_captancy(self):

        self.destroy()
        self._clear_parent()

        PortCaptancyForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )

    # =========================================================
    # UTILIDADES
    # =========================================================
    def _clear_parent(self):

        for widget in self.parent.winfo_children():
            widget.destroy()

    def _back_to_parent(self):

        for widget in self.parent.winfo_children():
            widget.destroy()
