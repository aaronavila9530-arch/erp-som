import tkinter as tk
from tkinter import ttk

class PopupVerServicio(tk.Toplevel):

    def __init__(self, parent, data):
        super().__init__(parent)
        self.title("Detalles del Servicio")
        self.geometry("600x700")
        self.configure(bg="white")

        self.data = data
        self.cols = [
            "consec", "tipo", "estado", "num_informe",
            "buque_contenedor", "cliente", "contacto", "detalle",
            "continente", "pais", "puerto",
            "operacion", "surveyor", "honorarios", "costo_operativo",
            "fecha_inicio", "hora_inicio",
            "fecha_fin", "hora_fin", "demoras", "duracion",
            "factura", "valor_factura", "fecha_factura",
            "terminos_pago", "fecha_vencimiento", "dias_vencido",
            "razon_cancelacion", "comentario_cancelacion"
        ]

        # ========================================
        # FRAME CON SCROLL
        # ========================================
        container = tk.Frame(self, bg="white")
        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="white")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        container.pack(fill="both", expand=True)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ========================================
        # MOSTRAR CAMPOS (MODO SOLO LECTURA)
        # ========================================
        for i, (campo, valor) in enumerate(zip(self.cols, self.data)):
            ttk.Label(
                scroll_frame,
                text=f"{campo.replace('_',' ').title()}:",
                background="white",
                foreground="black",
                font=("Segoe UI", 10, "bold")
            ).grid(row=i, column=0, sticky="w", padx=10, pady=5)

            entry = ttk.Entry(
                scroll_frame,
                width=40
            )
            entry.grid(row=i, column=1, sticky="w", padx=10, pady=5)
            entry.insert(0, valor)
            entry.config(state="readonly")

        # ========================================
        # BOTÓN CERRAR
        # ========================================
        ttk.Button(self, text="Cerrar", command=self.destroy).pack(pady=10)
