import tkinter as tk
from tkinter import ttk

class PopupCliente(tk.Toplevel):

    def __init__(self, parent, codigo, on_save=None):
        super().__init__(parent)
        self.title("Agregar Cliente")
        self.geometry("650x520")
        self.config(bg="white")
        self.resizable(False, False)

        self.on_save = on_save
        self.codigo_generado = codigo  # asignado desde UI

        # ===========================
        # Variables
        # ===========================
        self.NombreJuridico      = tk.StringVar()
        self.NombreComercial     = tk.StringVar()
        self.Pais                = tk.StringVar()
        self.CedulaJuridicaVAT   = tk.StringVar()

        self.Provincia           = tk.StringVar()
        self.Canton              = tk.StringVar()
        self.Distrito            = tk.StringVar()
        self.DireccionExacta     = tk.StringVar()

        self.FechaDePago         = tk.StringVar()
        self.Correo              = tk.StringVar()

        self.Prefijo             = tk.StringVar()
        self.Telefono            = tk.StringVar()
        self.ContactoPrincipal   = tk.StringVar()
        self.ContactoSecundario  = tk.StringVar()

        self.Comentarios         = tk.StringVar()

        self._build()

    # ===========================
    # UI con Notebook
    # ===========================
    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab1 = tk.Frame(notebook, bg="white")
        tab2 = tk.Frame(notebook, bg="white")
        tab3 = tk.Frame(notebook, bg="white")

        notebook.add(tab1, text="🏢 Empresa")
        notebook.add(tab2, text="📍 Dirección")
        notebook.add(tab3, text="📞 Contacto")

        # ============ TAB 1 ============
        ttk.Label(tab1, text=f"Código: {self.codigo_generado}", foreground="blue", background="white")\
            .grid(row=0, column=0, padx=10, pady=10, sticky="w", columnspan=2)

        ttk.Label(tab1, text="Nombre Jurídico:", background="white")\
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_nombrejuri = ttk.Entry(tab1, textvariable=self.NombreJuridico)
        self.entry_nombrejuri.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="Nombre Comercial:", background="white")\
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_nombrecom = ttk.Entry(tab1, textvariable=self.NombreComercial)
        self.entry_nombrecom.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="País:", background="white")\
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_pais = ttk.Entry(tab1, textvariable=self.Pais)
        self.entry_pais.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab1, text="Cédula Jurídica / VAT:", background="white")\
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_cedula = ttk.Entry(tab1, textvariable=self.CedulaJuridicaVAT)
        self.entry_cedula.grid(row=4, column=1, padx=10, pady=5)

        # ============ TAB 2 ============
        ttk.Label(tab2, text="Provincia:", background="white")\
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_provincia = ttk.Entry(tab2, textvariable=self.Provincia)
        self.entry_provincia.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Cantón:", background="white")\
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_canton = ttk.Entry(tab2, textvariable=self.Canton)
        self.entry_canton.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Distrito:", background="white")\
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_distrito = ttk.Entry(tab2, textvariable=self.Distrito)
        self.entry_distrito.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Dirección exacta:", background="white")\
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_direccion = ttk.Entry(tab2, textvariable=self.DireccionExacta, width=40)
        self.entry_direccion.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Fecha de pago:", background="white")\
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_fechapago = ttk.Entry(tab2, textvariable=self.FechaDePago)
        self.entry_fechapago.grid(row=4, column=1, padx=10, pady=5)

        ttk.Label(tab2, text="Correo:", background="white")\
            .grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.entry_correo = ttk.Entry(tab2, textvariable=self.Correo)
        self.entry_correo.grid(row=5, column=1, padx=10, pady=5)

        # ============ TAB 3 ============
        ttk.Label(tab3, text="Prefijo:", background="white")\
            .grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.combo_prefijo = ttk.Combobox(tab3, textvariable=self.Prefijo, values=["+506", "+57", "+1"], state="readonly")
        self.combo_prefijo.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Teléfono:", background="white")\
            .grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_telefono = ttk.Entry(tab3, textvariable=self.Telefono)
        self.entry_telefono.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Contacto principal:", background="white")\
            .grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_contacto_1 = ttk.Entry(tab3, textvariable=self.ContactoPrincipal)
        self.entry_contacto_1.grid(row=2, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Contacto secundario:", background="white")\
            .grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.entry_contacto_2 = ttk.Entry(tab3, textvariable=self.ContactoSecundario)
        self.entry_contacto_2.grid(row=3, column=1, padx=10, pady=5)

        ttk.Label(tab3, text="Comentarios:", background="white")\
            .grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.entry_comentarios = ttk.Entry(tab3, textvariable=self.Comentarios, width=40)
        self.entry_comentarios.grid(row=4, column=1, padx=10, pady=5)

        # === Botón Guardar ===
        tk.Button(self, text="Guardar", bg="#008C35", fg="white",
                  width=15, command=self._guardar).pack(pady=10)

    # ===========================
    # Guardar
    # ===========================
    def _guardar(self):
        data = {
            "Codigo": self.codigo_generado,
            "NombreJuridico": self.entry_nombrejuri.get().strip(),
            "NombreComercial": self.entry_nombrecom.get().strip(),
            "Pais": self.entry_pais.get().strip(),
            "CedulaJuridicaVAT": self.entry_cedula.get().strip(),
            "Provincia": self.entry_provincia.get().strip(),
            "Canton": self.entry_canton.get().strip(),
            "Distrito": self.entry_distrito.get().strip(),
            "DireccionExacta": self.entry_direccion.get().strip(),
            "FechaDePago": self.entry_fechapago.get().strip(),
            "Correo": self.entry_correo.get().strip(),
            "Prefijo": self.combo_prefijo.get().strip(),
            "Telefono": self.entry_telefono.get().strip(),
            "ContactoPrincipal": self.entry_contacto_1.get().strip(),
            "ContactoSecundario": self.entry_contacto_2.get().strip(),
            "Comentarios": self.entry_comentarios.get().strip(),
        }

        print("💾 Guardar Cliente →", data)

        if self.on_save:
            self.on_save(data)

        self.destroy()
