import tkinter as tk
from tkinter import ttk, messagebox
from resource_utils import resource_path

from api_client import (
    hr_obtener_ultima_noticia,
    hr_publicar_noticias
)
from Modulos.HHRR.popups.popup_noticias import PopupNoticias


class HHRRHomeUI(ttk.Frame):
    """
    HOME del módulo HHRR.

    • Barra superior de accesos
    • Imagen institucional (izquierda)
    • Noticias (derecha)
    """

    def __init__(self, parent, usuario, rol, callbacks):
        super().__init__(parent)

        self.usuario = usuario
        self.rol = (rol or "").lower()
        self.callbacks = callbacks

        if hasattr(parent, "btn_volver"):
            try:
                parent.btn_volver.grid_remove()
            except Exception:
                pass

        self._build_ui()
        self._cargar_noticias()

    # =========================================================
    # UI
    # =========================================================
    def _build_ui(self):

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ---------------- TOP BAR ----------------
        top_bar = ttk.Frame(self)
        top_bar.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 12))

        # ---------------------------------------------------------
        # RBAC LOCAL PARA BOTONES HHRR
        # ---------------------------------------------------------

        usuario = (self.usuario or "").lower()

        # Surveyors → acceso limitado
        if usuario in ("surveyor01", "surveyor02"):

            acciones = [
                ("Colillas", "paylips"),
                ("Solicitudes", "solicitudes"),
                ("Horas", "horas"),
                ("Políticas", "politicas"),
            ]

        else:

            acciones = [
                ("Payroll", "payroll"),
                ("Colillas", "paylips"),
                ("Solicitudes", "solicitudes"),
                ("Horas", "horas"),
                ("Empleados", "empleados"),
                ("Calculadora salarial", "calculadora_salarial"),
                ("Políticas", "politicas"),
            ]

        for texto, key in acciones:
            ttk.Button(
                top_bar,
                text=texto,
                command=self.callbacks.get(key)
            ).pack(side="left", padx=4)

        # ---------------- BODY ----------------
        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        # ---------------- IMAGE ----------------
        cont_img = ttk.Frame(body)
        cont_img.grid(row=0, column=0, sticky="nsew", padx=(0, 15))

        try:
            self.img_hhrr = tk.PhotoImage(
                file=resource_path("assets/HHRR.png")
            )
            ttk.Label(cont_img, image=self.img_hhrr).place(
                relx=0.5, rely=0.5, anchor="center"
            )
        except Exception:
            ttk.Label(
                cont_img,
                text="HHRR",
                font=("Segoe UI", 30, "bold")
            ).place(relx=0.5, rely=0.5, anchor="center")

        # ---------------- NEWS ----------------
        cont_news = ttk.LabelFrame(body, text="Noticias")
        cont_news.grid(row=0, column=1, sticky="nsew")

        cont_news.columnconfigure(0, weight=1)
        cont_news.rowconfigure(0, weight=1)   # 🔧 CLAVE
        cont_news.rowconfigure(1, weight=0)

        news_frame = ttk.Frame(cont_news)
        news_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        news_frame.columnconfigure(0, weight=1)
        news_frame.rowconfigure(1, weight=1)  # 🔧 CLAVE

        self.lbl_bienvenida = ttk.Label(
            news_frame,
            text="Bienvenido al módulo HHRR",
            font=("Segoe UI", 12, "bold")
        )
        self.lbl_bienvenida.grid(row=0, column=0, sticky="w", pady=(0, 6))

        scrollbar = ttk.Scrollbar(news_frame, orient="vertical")
        self.lst_noticias = tk.Listbox(
            news_frame,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.lst_noticias.yview)

        self.lst_noticias.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        # ---------------------------------------------------------
        # 🔒 PUBLICAR NOTICIA (OCULTO PARA SURVEYORS)
        # ---------------------------------------------------------
        usuario = (self.usuario or "").lower()

        if self.rol in ("admin", "master") and usuario not in ("surveyor01", "surveyor02"):
            ttk.Button(
                cont_news,
                text="Publicar noticia",
                command=self._publicar_noticia
            ).grid(row=1, column=0, pady=(6, 8))

    # =========================================================
    # DATA
    # =========================================================
    def _cargar_noticias(self):
        self.lst_noticias.delete(0, "end")

        try:
            data = hr_obtener_ultima_noticia()
        except Exception:
            return

        for i in range(1, 6):
            txt = data.get(f"noticia_{i}")
            if txt:
                self.lst_noticias.insert("end", f"• {txt}")

    # =========================================================
    # ACTIONS
    # =========================================================
    def _publicar_noticia(self):
        PopupNoticias(
            parent=self,
            on_save=self._on_noticia_publicada
        )

    def _on_noticia_publicada(self, payload):
        """
        Publica noticias y refresca HOME inmediatamente
        """
        hr_publicar_noticias(
            noticia_1=payload.get("noticia_1"),
            noticia_2=payload.get("noticia_2"),
            noticia_3=payload.get("noticia_3"),
            noticia_4=payload.get("noticia_4"),
            noticia_5=payload.get("noticia_5"),
        )

        self._cargar_noticias()
