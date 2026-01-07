import tkinter as tk
from tkinter import ttk, messagebox

from auth_api import login_usuario
from api_client import set_user_role   # ✅ IMPORT CLAVE PARA RBAC


class LoginWindow(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("ERP-SOM | Login")
        self.geometry("1000x600")
        self.minsize(900, 550)
        self.state("zoomed")
        self.configure(bg="white")
        self.protocol("WM_DELETE_WINDOW", self._cerrar_todo)

        # Grid base
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ====================================================
        # IZQUIERDA — LOGIN
        # ====================================================
        self.left = tk.Frame(self, bg="white", padx=60, pady=40)
        self.left.grid(row=0, column=0, sticky="nw")

        tk.Label(
            self.left,
            text="Bienvenido a ERP-SOM",
            font=("Segoe UI", 20, "bold"),
            bg="white",
            fg="#003A75"
        ).grid(row=0, column=0, sticky="w", pady=(0, 25))

        tk.Label(self.left, text="Usuario", bg="white").grid(
            row=1, column=0, sticky="w", pady=(10, 5)
        )
        self.usuario = ttk.Entry(self.left, width=30)
        self.usuario.grid(row=2, column=0, sticky="w")

        tk.Label(self.left, text="Contraseña", bg="white").grid(
            row=3, column=0, sticky="w", pady=(20, 5)
        )
        self.password = ttk.Entry(self.left, width=30, show="*")
        self.password.grid(row=4, column=0, sticky="w")

        ttk.Button(
            self.left,
            text="Ingresar",
            command=self._login
        ).grid(row=5, column=0, sticky="w", pady=(30, 10))

        ttk.Button(
            self.left,
            text="Olvidé mi contraseña",
            command=self._forgot
        ).grid(row=6, column=0, sticky="w")

        # ====================================================
        # DERECHA — IMAGEN
        # ====================================================
        self.right = tk.Frame(self, bg="white")
        self.right.grid(row=0, column=1, sticky="nsew")

        self.lbl_img = tk.Label(
            self.right,
            bg="white",
            image=self.parent._login_bg_image
        )
        self.lbl_img.image = self.parent._login_bg_image
        self.lbl_img.pack(fill="both", expand=True)

    # ====================================================
    # LOGIN
    # ====================================================
    def _login(self):
        usuario = self.usuario.get().strip()
        password = self.password.get().strip()

        if not usuario or not password:
            messagebox.showwarning(
                "Atención",
                "Ingrese usuario y contraseña",
                parent=self
            )
            return

        ok, data = login_usuario(usuario, password)

        if not ok:
            messagebox.showerror(
                "Error",
                data.get("error", "Credenciales inválidas"),
                parent=self
            )
            return

        # ✅ SETEO GLOBAL DEL ROL (RBAC)
        set_user_role(data["rol"])

        from otp_window import OTPWindow

        if data["action"] == "ENROLL_TOTP":
            OTPWindow(
                self,
                usuario=data["usuario"],
                rol=data["rol"],
                mode="ENROLL_TOTP",
                qr_bytes=data["qr"]
            )

        elif data["action"] == "VERIFY_TOTP":
            OTPWindow(
                self,
                usuario=data["usuario"],
                rol=data["rol"],
                mode="VERIFY_TOTP"
            )

    # ====================================================
    # RESET PASSWORD
    # ====================================================
    def _forgot(self):
        from password_reset_window import PasswordResetWindow
        PasswordResetWindow(self)

    # ====================================================
    # CERRAR TODO
    # ====================================================
    def _cerrar_todo(self):
        self.parent.destroy()
