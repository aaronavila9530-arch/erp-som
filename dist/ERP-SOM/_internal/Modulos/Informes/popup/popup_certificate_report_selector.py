import tkinter as tk
from tkinter import ttk, messagebox

from Modulos.Informes.weight_certificate.weight_certificate_form import (
    WeightCertificateForm
)


from Modulos.Informes.vessel_holds_inspection_certificate.vessel_holds_inspection_certificate_form import (
    VesselHoldsInspectionCertificateForm
)

from Modulos.Informes.sampling_certificate.sampling_certificate_form import (
    SamplingCertificateForm
)

from Modulos.Informes.sealing_certificate.sealing_certificate_form import (
    SealingCertificateForm
)

from Modulos.Informes.lashing_certificate.lashing_certificate_form import (
    LashingCertificateForm
)

class PopupCertificateReportSelector(tk.Toplevel):
    """
    POPUP — Certificate Report Selector
    """

    def __init__(self, parent, usuario=None, rol=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol

        self.title("Select Certificate Type")
        self.geometry("520x460")
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
            text="Certificate Type",
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", pady=(0, 15))

        ttk.Label(
            container,
            text="Select the certificate you want to generate:",
            wraplength=460
        ).pack(anchor="w", pady=(0, 20))

        # ================= OPTIONS =================

        self._build_button(
            container,
            text="⚖️ Weight Certificate",
            enabled=True,
            command=self._open_weight_certificate
        )

        self._build_button(
            container,
            text="🏗️ Holds Inspection Certificate",
            enabled=True,
            command=self._open_holds_inspection_certificate
        )

        self._build_button(
            container,
            text="🌽 Sampling Certificate",
            enabled=True,
            command=self._open_sampling_certificate
        )

        self._build_button(
            container,
            text="🔒 Sealing Certificate",
            enabled=True,
            command=self._open_sealing_certificate
        )

        self._build_button(
            container,
            text="⛓️ Lashing Certificate",
            enabled=True,
            command=self._open_lashing_certificate
        )


    # =========================================================
    # BUTTON BUILDER
    # =========================================================
    def _build_button(self, parent, text, enabled=True, command=None):

        btn = ttk.Button(
            parent,
            text=text,
            command=command if enabled else None
        )

        btn.pack(fill="x", pady=6)

        if not enabled:
            btn.state(["disabled"])

    # =========================================================
    # ACTIONS
    # =========================================================
    def _open_weight_certificate(self):

        self.destroy()
        self._clear_parent()

        WeightCertificateForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )


    def _open_holds_inspection_certificate(self):

        self.destroy()
        self._clear_parent()

        VesselHoldsInspectionCertificateForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )


    def _open_sampling_certificate(self):

        self.destroy()
        self._clear_parent()

        SamplingCertificateForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )

    def _open_sealing_certificate(self):

        self.destroy()
        self._clear_parent()

        SealingCertificateForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )

    def _open_lashing_certificate(self):

        self.destroy()
        self._clear_parent()

        LashingCertificateForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self._back_to_parent
        )

    # =========================================================
    # UTILITIES
    # =========================================================
    def _clear_parent(self):

        for widget in self.parent.winfo_children():
            widget.destroy()

    def _back_to_parent(self):

        for widget in self.parent.winfo_children():
            widget.destroy()