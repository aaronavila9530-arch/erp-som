import tkinter as tk
from tkinter import ttk

from Modulos.Informes.popup.popup_vessel_report_selector import (
    PopupVesselReportSelector
)

from Modulos.Informes.popup.popup_certificate_report_selector import (
    PopupCertificateReportSelector
)

from Modulos.Informes.logra_questionnaires_form import (
    LograQuestionnairesForm
)


class ReportTypeSelector(ttk.Frame):
    """
    SELECTOR DE TIPO DE INFORME

    • Vista real (NO popup)
    • Scroll vertical
    • Permite elegir:
        - Informe de Contenedor
        - Informe de Buque (con subtipos)
    • Delegación por callbacks
    """

    def __init__(
        self,
        parent,
        on_container_report=None,
        on_vessel_report=None,
        on_back=None,
        usuario=None,
        rol=None
    ):
        super().__init__(parent)

        self.parent = parent
        self.on_container_report = on_container_report
        self.on_vessel_report = on_vessel_report
        self.on_back = on_back
        self.usuario = usuario
        self.rol = rol

        # =====================================================
        # 🔒 BLINDAJE TOTAL DE LAYOUT + FULL SCREEN
        # =====================================================
        try:
            parent.state("zoomed")
            parent.grid_rowconfigure(0, weight=1)
            parent.grid_columnconfigure(0, weight=1)
            parent.pack_propagate(False)
            parent.grid_propagate(False)
        except Exception:
            pass

        self.grid(row=0, column=0, sticky="nsew")

        self._build_ui()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ================= CANVAS + SCROLL =================
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.scrollable = ttk.Frame(self.canvas)
        self.scrollable.columnconfigure(0, weight=1)

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable, anchor="nw")

        self.scrollable.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))
        self.scrollable.bind("<Enter>", self._bind_mousewheel)
        self.scrollable.bind("<Leave>", self._unbind_mousewheel)

        # ================= HEADER =================
        header = ttk.Frame(self.scrollable)
        header.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Generar Informe Marítimo",
            font=("Segoe UI", 16, "bold")
        ).grid(row=0, column=0, sticky="w")

        if self.on_back:
            ttk.Button(
                header,
                text="⬅ Volver",
                command=self.on_back
            ).grid(row=0, column=1, sticky="e")

        ttk.Separator(self.scrollable).grid(
            row=1, column=0, sticky="ew", padx=25, pady=(5, 20)
        )

        # ================= INTRO =================
        ttk.Label(
            self.scrollable,
            text=(
                "Seleccione el tipo de informe que desea generar.\n"
                "Cada tipo de informe cuenta con formularios y flujos específicos."
            ),
            justify="left",
            wraplength=1200
        ).grid(row=2, column=0, sticky="w", padx=25, pady=(0, 25))

        # ================= OPCIONES =================
        self._build_option_card(
            row=3,
            title="📦 Informe de Contenedor",
            description=(
                "Informe técnico para inspección de contenedores.\n"
                "Incluye condición estructural, daños, mercancía, "
                "observaciones y conclusiones formales."
            ),
            button_text="Generar Informe de Contenedor",
            command=self._on_container
        )

        self._build_option_card(
            row=4,
            title="🚢 Informe de Buque",
            description=(
                "Seleccione el tipo de informe de buque a generar.\n"
                "Cada operación cuenta con su propio formulario especializado."
            ),
            button_text="Seleccionar Tipo de Informe de Buque",
            command=self._open_vessel_selector,
            disabled=False
        )

        self._build_option_card(
            row=5,
            title="📜 Certificates",
            description=(
                "Certificados operativos generados a partir de inspecciones "
                "y registros portuarios.\n"
                "Incluye Weight Certificates, cargo verification "
                "y otros certificados oficiales."
            ),
            button_text="Seleccionar Tipo de Certificado",
            command=self._open_certificate_selector,
            disabled=False
        )

        self._build_option_card(
            row=6,
            title="ONG",
            description=(
                "Cuestionarios de factibilidad nautica y portuaria con agenda, "
                "preguntas del documento, bullets dinamicos, PORTIA y adjuntos."
            ),
            button_text="Abrir Cuestionarios ONG",
            command=self._open_logra_questionnaires,
            disabled=False
        )

    # =========================================================
    # CARDS
    # =========================================================
    def _build_option_card(
        self,
        row,
        title,
        description,
        button_text,
        command,
        disabled=False
    ):
        card = ttk.Frame(self.scrollable, relief="ridge", padding=20)
        card.grid(row=row, column=0, sticky="ew", padx=25, pady=15)
        card.columnconfigure(0, weight=1)

        ttk.Label(
            card,
            text=title,
            font=("Segoe UI", 12, "bold")
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            card,
            text=description,
            wraplength=1200,
            justify="left"
        ).grid(row=1, column=0, sticky="w", pady=(8, 15))

        btn = ttk.Button(
            card,
            text=button_text,
            command=command
        )
        btn.grid(row=2, column=0, sticky="e")

        if disabled:
            btn.state(["disabled"])

    def _bind_mousewheel(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

    def _unbind_mousewheel(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)) * 3, "units")

    # =========================================================
    # ACTIONS
    # =========================================================
    def _on_container(self):
        if self.on_container_report:
            self.on_container_report()

    # =========================================================
    # VESSEL SELECTOR → POPUP
    # =========================================================
    def _open_vessel_selector(self):
        PopupVesselReportSelector(
            self,
            usuario=self.usuario,
            rol=self.rol
        )


    # =========================================================
    # CERTIFICATE SELECTOR → POPUP
    # =========================================================
    def _open_certificate_selector(self):

        PopupCertificateReportSelector(
            self,
            usuario=self.usuario,
            rol=self.rol
        )

    def _open_logra_questionnaires(self):

        for widget in self.parent.winfo_children():
            widget.destroy()

        LograQuestionnairesForm(
            self.parent,
            usuario=self.usuario,
            rol=self.rol,
            on_back=self.on_back
        )
