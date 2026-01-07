import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import io

from auth_api import (
    confirmar_registro_totp,
    validar_totp_login
)

from session_context import set_user_context   # ⬅️ CLAVE


class OTPWindow(tk.Toplevel):

    def __init__(self, parent, usuario, rol, mode, qr_bytes=None):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.mode = mode
        self.qr_bytes = qr_bytes

        self.title("Verificación de Seguridad")
        self.geometry("360x420" if mode == "ENROLL_TOTP" else "300x200")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        # ===============================
        # MODAL
        # ===============================
        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self._build_ui()

        # ⌨️ ENTER = VALIDAR
        self.bind("<Return>", lambda e: self._validar())

    # ====================================================
    # UI
    # ====================================================
    def _build_ui(self):

        if self.mode == "ENROLL_TOTP":
            tk.Label(
                self,
                text="Registrar Microsoft Authenticator",
                font=("Segoe UI", 11, "bold")
            ).pack(pady=(15, 10))

            tk.Label(
                self,
                text="Escanee el código QR con su app\nMicrosoft Authenticator",
                justify="center"
            ).pack(pady=(0, 10))

            image = Image.open(io.BytesIO(self.qr_bytes))
            image = image.resize((220, 220), Image.LANCZOS)
            self.qr_img = ImageTk.PhotoImage(image)

            tk.Label(self, image=self.qr_img).pack(pady=5)

        else:
            tk.Label(
                self,
                text="Código de verificación",
                font=("Segoe UI", 11, "bold")
            ).pack(pady=(25, 10))

        # ===============================
        # ENTRY CÓDIGO
        # ===============================
        self.codigo = ttk.Entry(
            self,
            width=20,
            justify="center",
            font=("Segoe UI", 12)
        )
        self.codigo.pack(pady=10)
        self.codigo.focus_set()

        ttk.Button(
            self,
            text="Validar",
            command=self._validar
        ).pack(pady=20)

    # ====================================================
    # VALIDAR
    # ====================================================
    def _validar(self):
        codigo = self.codigo.get().strip()

        if not codigo:
            messagebox.showwarning(
                "Atención",
                "Ingrese el código de verificación",
                parent=self
            )
            return

        # 🧪 DEBUG
        print(f"🔐 TOTP DEBUG | Usuario={self.usuario} | Código={codigo}")

        if self.mode == "ENROLL_TOTP":
            ok, data = confirmar_registro_totp(self.usuario, codigo)
        else:
            ok, data = validar_totp_login(self.usuario, codigo)

        if not ok:
            messagebox.showerror(
                "Error",
                data.get("error", "Código inválido"),
                parent=self
            )
            return

        # ====================================================
        # ✅ CONTEXTO DE SESIÓN (CLAVE PARA RBAC)
        # ====================================================
        set_user_context(self.usuario, self.rol)

        # ====================================================
        # ENTRAR AL ERP
        # ====================================================
        self.grab_release()
        self.destroy()

        for w in self.parent.winfo_children():
            w.destroy()

        from main import MainApp
        MainApp(self.parent, self.usuario, self.rol)

    # ====================================================
    # CERRAR
    # ====================================================
    def _cerrar(self):
        try:
            self.grab_release()
        except tk.TclError:
            pass
        self.destroy()
