import tkinter as tk
from tkinter import ttk

from Modulos.HHRR.date_utils import is_date_column, to_long_english_date


class TablaLazy(ttk.Frame):
    """
    Tabla reutilizable LAZY.
    NO carga datos automáticamente.
    SOLO carga cuando se llama explícitamente a cargar_datos().
    """

    def __init__(
        self,
        parent,
        columnas,
        ancho_columnas=None,
        alto=15
    ):
        super().__init__(parent)

        self.columnas = columnas
        self.ancho_columnas = ancho_columnas or {}
        self.alto = alto

        self._datos_actuales = []

        self._construir_ui()

    # =========================================================
    # UI
    # =========================================================
    def _construir_ui(self):

        self.tree = ttk.Treeview(
            self,
            columns=self.columnas,
            show="headings",
            height=self.alto
        )

        for col in self.columnas:
            self.tree.heading(col, text=col)
            self.tree.column(
                col,
                width=self.ancho_columnas.get(col, 120),
                anchor="center"
            )

        scrollbar_y = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    # =========================================================
    # MÉTODOS LAZY (CLAVE)
    # =========================================================
    def cargar_datos(self, filas):
        """
        Carga datos SOLO cuando se llama explícitamente.
        """
        self.limpiar()

        self._datos_actuales = filas or []

        for fila in self._datos_actuales:
            valores = []
            for col in self.columnas:
                value = fila.get(col, "")
                if is_date_column(col):
                    value = to_long_english_date(value)
                valores.append(value)
            self.tree.insert("", "end", values=valores)

    def limpiar(self):
        """
        Limpia la tabla.
        """
        self.tree.delete(*self.tree.get_children())

    def obtener_seleccionado(self):
        """
        Devuelve el registro seleccionado (dict) o None.
        """
        seleccionado = self.tree.selection()
        if not seleccionado:
            return None

        index = self.tree.index(seleccionado[0])
        return self._datos_actuales[index]

    def get_all_rows(self):
        """
        Devuelve una copia de las filas cargadas actualmente.
        """
        return list(self._datos_actuales or [])

    # =========================================================
    # UTILIDADES
    # =========================================================
    def esta_vacia(self):
        return len(self._datos_actuales) == 0
