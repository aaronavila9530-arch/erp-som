import tkinter as tk
from tkinter import ttk, messagebox
from api_client import get_servicio_api, confirmar_informe_api


class PopupVistaInforme(tk.Toplevel):

    def __init__(self, parent, consec):
        super().__init__(parent)
        self.parent = parent
        self.consec = consec

        self.title("Vista previa del informe")
        self.geometry("750x550")
        self.config(bg="white")

        self.data = get_servicio_api(consec)

        # ==============================
        # CONTENEDOR CON SCROLL
        # ==============================
        container = tk.Frame(self, bg="white")
        container.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        scroll_frame = tk.Frame(canvas, bg="white")
        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ==============================
        # TABLA KEY - VALUE (ELEGANTE)
        # ==============================
        tree = ttk.Treeview(
            scroll_frame,
            columns=("campo", "valor"),
            show="headings",
            height=20
        )
        tree.heading("campo", text="Campo")
        tree.heading("valor", text="Valor")

        tree.column("campo", width=220, anchor="w")
        tree.column("valor", width=450, anchor="w")

        tree.pack(fill="both", expand=True)

        campos_mostrar = [
            "tipo", "estado", "num_informe",
            "buque_contenedor", "cliente", "contacto", "detalle",
            "continente", "pais", "puerto",
            "operacion", "surveyor",
            "honorarios", "costo_operativo",
            "fecha_inicio", "hora_inicio",
            "fecha_fin", "hora_fin",
            "demoras"
        ]

        for c in campos_mostrar:
            tree.insert(
                "",
                "end",
                values=(
                    c.replace("_", " ").title(),
                    self.data.get(c, "")
                )
            )

        # ==============================
        # BOTONES
        # ==============================
        btns = tk.Frame(self, bg="white")
        btns.pack(pady=12)

        tk.Button(
            btns,
            text="Editar",
            bg="#F7D08A",
            width=16,
            command=self.editar
        ).pack(side="left", padx=10)

        tk.Button(
            btns,
            text="Confirmar",
            bg="#A8D5B5",
            width=16,
            command=self.confirmar
        ).pack(side="left", padx=10)

    # ==============================
    # EDITAR → EDITOR COMPLETO
    # ==============================
    def editar(self):
        self.destroy()

        from Modulos.Servicios.Popup_servicios.popup_editar_servicio import PopupEditarServicio

        PopupEditarServicio(
            self.parent,
            self.consec,
            on_success=self._volver_vista_previa
        )

    def _volver_vista_previa(self):
        PopupVistaInforme(self.parent, self.consec)

    # ==============================
    # CONFIRMAR INFORME (FINAL)
    # ==============================
    def confirmar(self):
        if not messagebox.askyesno(
            "Confirmar informe",
            "¿Está seguro con los datos ingresados?\n"
            "Si confirma, el informe quedará FINALIZADO y no podrá modificarse."
        ):
            return

        resp = confirmar_informe_api(self.consec)

        if resp.get("status") == "ok":
            num = resp.get("num_informe", "")

            messagebox.showinfo(
                "Informe generado",
                f"Informe generado con éxito.\n\nNúmero de informe:\n{num}"
            )

            # ✅ REFRESH del ERP (tabla de servicios)
            # Si el parent (VistaServicios) tiene refresh, úsalo
            try:
                if hasattr(self.parent, "refresh"):
                    self.parent.refresh()
            except Exception:
                pass

            self.destroy()
        else:
            messagebox.showerror("Error", resp.get("error", "No se pudo generar el informe."))
