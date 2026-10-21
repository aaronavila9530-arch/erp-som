import tkinter as tk
from tkinter import ttk, messagebox

class PopupServicio(tk.Toplevel):
    def __init__(self, parent, codigo, on_save):
        super().__init__(parent)
        self.title("Nuevo Servicio")
        self.geometry("420x260")
        self.configure(bg="white")
        self.grab_set()

        self.on_save = on_save

        # Variables
        self.codigo = tk.StringVar(value=codigo)

        # ======================
        # UI
        # ======================
        # Código
        ttk.Label(self, text="Código:", background="white").grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        ttk.Entry(self, textvariable=self.codigo, state="readonly").grid(
            row=0, column=1, padx=10, pady=10
        )

        # Código producto
        ttk.Label(self, text="Código Producto:", background="white").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.entry_codigo_prod = ttk.Entry(self)
        self.entry_codigo_prod.grid(row=1, column=1, padx=10, pady=5)

        # Nombre servicio
        ttk.Label(self, text="Nombre del servicio:", background="white").grid(
            row=2, column=0, padx=10, pady=5, sticky="w"
        )
        self.entry_nombre = ttk.Entry(self)
        self.entry_nombre.grid(row=2, column=1, padx=10, pady=5)

        # Costo
        ttk.Label(self, text="Costo:", background="white").grid(
            row=3, column=0, padx=10, pady=5, sticky="w"
        )
        self.entry_costo = ttk.Entry(self)
        self.entry_costo.grid(row=3, column=1, padx=10, pady=5)

        # BOTÓN GUARDAR
        btn = tk.Button(
            self,
            text="Guardar",
            bg="#008C35",
            fg="white",
            width=12,
            command=self._guardar,
        )
        btn.grid(row=4, column=0, columnspan=2, pady=15)

    # ======================
    # SAVE
    # ======================
    def _guardar(self):
        nombre = self.entry_nombre.get().strip()
        codigo_prod = self.entry_codigo_prod.get().strip()
        costo = self.entry_costo.get().strip()

        # Debug por si vuelve a fallar
        print(f"[DEBUG] Nombre capturado: {repr(nombre)}")

        if not nombre:
            messagebox.showerror("Error", "El nombre del servicio es obligatorio")
            return

        data = {
            "codigo": self.codigo.get(),
            "codigo_prod": codigo_prod,
            "nombre": nombre,
            "costo": costo,
        }

        print("💾 Guardar Servicio →", data)
        self.on_save(data)
        self.destroy()
