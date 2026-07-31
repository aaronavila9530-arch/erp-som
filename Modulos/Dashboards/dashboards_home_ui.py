import tkinter as tk
from tkinter import ttk, messagebox


class DashboardsHomeUI(ttk.Frame):

    def __init__(self, parent):
        super().__init__(parent)

        self.parent = parent

        self.pack(fill="both", expand=True)

        self._build_ui()


    # =========================================================
    # UI
    # =========================================================

    def _build_ui(self):

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # -----------------------------------------------------
        # TITLE
        # -----------------------------------------------------

        ttk.Label(
            container,
            text="Dashboards",
            font=("Segoe UI", 18, "bold")
        ).pack(anchor="w", pady=(0, 10))

        ttk.Separator(container).pack(fill="x", pady=10)

        # -----------------------------------------------------
        # BUTTON GRID
        # -----------------------------------------------------

        grid = ttk.Frame(container)
        grid.pack(pady=20)

        # -----------------------------------------------------
        # SERVICIOS
        # -----------------------------------------------------

        ttk.Button(
            grid,
            text="Servicios",
            width=25,
            command=self._open_servicios
        ).grid(row=0, column=0, padx=10, pady=10)

        # -----------------------------------------------------
        # FINANZAS
        # -----------------------------------------------------

        ttk.Button(
            grid,
            text="Finanzas",
            width=25,
            command=self._open_finanzas
        ).grid(row=0, column=1, padx=10, pady=10)

        # -----------------------------------------------------
        # COMERCIAL
        # -----------------------------------------------------

        ttk.Button(
            grid,
            text="Comercial",
            width=25,
            command=self._open_comercial
        ).grid(row=1, column=0, padx=10, pady=10)

        # -----------------------------------------------------
        # INFORMES
        # -----------------------------------------------------

        ttk.Button(
            grid,
            text="Informes",
            width=25,
            command=self._open_informes
        ).grid(row=1, column=1, padx=10, pady=10)


    # =========================================================
    # CLEAN HOST
    # =========================================================

    def _clear_host(self):

        for child in self.parent.winfo_children():
            child.destroy()


    # =========================================================
    # SERVICIOS DASHBOARD
    # =========================================================

    def _open_servicios(self):

        try:

            self._clear_host()

            from Modulos.Dashboards.dashboards_servicios import DashboardsServiciosUI

            DashboardsServiciosUI(self.parent)

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudo abrir el dashboard de servicios:\n{str(e)}"
            )


    # =========================================================
    # FINANZAS DASHBOARD
    # =========================================================

    def _open_finanzas(self):

        try:

            self._clear_host()

            from Modulos.Dashboards.dashboards_finanzas_ui import DashboardsFinanzasUI

            DashboardsFinanzasUI(self.parent)

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudo abrir el dashboard de finanzas:\n{str(e)}"
            )


    # =========================================================
    # COMERCIAL DASHBOARD
    # =========================================================

    def _open_comercial(self):

        try:

            self._clear_host()

            from Modulos.Dashboards.dashboards_comercial_ui import DashboardsComercialUI

            DashboardsComercialUI(self.parent)

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudo abrir el dashboard comercial:\n{str(e)}"
            )


    # =========================================================
    # INFORMES DASHBOARD
    # =========================================================

    def _open_informes(self):

        try:

            self._clear_host()

            from Modulos.Dashboards.dashboards_informes_ui import DashboardsInformesUI

            DashboardsInformesUI(self.parent)

        except Exception as e:

            messagebox.showerror(
                "Error",
                f"No se pudo abrir el dashboard de informes:\n{str(e)}"
            )