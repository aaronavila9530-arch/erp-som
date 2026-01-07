import tkinter as tk
from tkinter import ttk
from threading import Thread
import time
from PIL import Image, ImageTk
import tkinter as tk
from resource_utils import resource_path


class SplashScreen(tk.Toplevel):

    def __init__(self, parent, callback):
        super().__init__(parent)

        # ICONO SPLASH (barra de tareas)
        try:
            self.iconbitmap(resource_path("assets/logo_menu_tareas.ico"))
        except Exception:
            pass

        self.callback = callback

        self.overrideredirect(True)
        self.configure(bg="white")

        # Tamaño Splash
        w, h = 420, 300
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # 👉 Cargar logo y redimensionar (ajusta tu ruta real)
        img = Image.open(r"C:\Users\Aaron Avila\Documents\ERP-SOM\assets\msl_logo.png")
        img = img.resize((260, 160), Image.LANCZOS)
        self.logo = ImageTk.PhotoImage(img)

        tk.Label(self, image=self.logo, bg="white").pack(pady=10)

        # Estilo Azul Corporativo para ProgressBar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Blue.Horizontal.TProgressbar",
            troughcolor="white",
            background="#003A75",
            thickness=10
        )

        # ProgressBar con estilo corporativo
        self.progress = ttk.Progressbar(
            self,
            mode="determinate",
            length=300,
            style="Blue.Horizontal.TProgressbar"
        )
        self.progress.pack(pady=10)

        # Hilo de carga
        Thread(target=self._cargar_sistema, daemon=True).start()


    def _cargar_sistema(self):
        for i in range(101):
            time.sleep(0.035)
            self.progress["value"] = i
            self.update_idletasks()

        self._fin()

    def _fin(self):
        self._prepare_login_assets()
        self.destroy()
        self.callback()

    def _prepare_login_assets(self):
        """
        Pre-renderiza la imagen del login para evitar flicker.
        """
        # Tamaño objetivo del login (mitad derecha)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        login_w = int(screen_w / 2)
        login_h = screen_h

        img = Image.open(
            r"C:\Users\Aaron Avila\Documents\ERP-SOM\assets\barco.jpg"
        )
        img.thumbnail((login_w, login_h), Image.LANCZOS)

        # Guardar en el root para compartirlo
        self.master._login_bg_image = ImageTk.PhotoImage(img)

