import tkinter as tk
from tkinter import ttk, messagebox

from api_client import (
    verify_identity_api,
    verify_totp_api,
    set_password_api
)


class PasswordResetWindow(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.usuario = None

        self.title("Recuperar contraseña")
        self.geometry("360x360")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.focus_force()

        self.container = tk.Frame(self, padx=30, pady=25)
        self.container.pack(fill="both", expand=True)

        self._step_identity()

    # =====================================================
    # PASO 1 — IDENTIDAD
    # =====================================================
    def _step_identity(self):
        self._clear()

        tk.Label(
            self.container,
            text="Verificación de identidad",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 15))

        self._field("Usuario")
        self._field("Nombre")
        self._field("Apellido")
        self._field("Email")

        ttk.Button(
            self.container,
            text="Continuar",
            command=self._verify_identity
        ).pack(pady=20)

    def _verify_identity(self):
        payload = {
            "usuario": self.fields["Usuario"].get().strip(),
            "nombre": self.fields["Nombre"].get().strip(),
            "apellido": self.fields["Apellido"].get().strip(),
            "email": self.fields["Email"].get().strip()
        }

        try:
            resp = verify_identity_api(payload)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        if not resp.get("ok"):
            messagebox.showerror("Error", resp.get("error"), parent=self)
            return

        self.usuario = payload["usuario"]
        self._step_totp()

    # =====================================================
    # PASO 2 — TOTP
    # =====================================================
    def _step_totp(self):
        self._clear()

        tk.Label(
            self.container,
            text="Verificación de seguridad",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 15))

        tk.Label(
            self.container,
            text="Ingrese el código de Microsoft Authenticator",
            justify="center"
        ).pack(pady=(0, 10))

        self._field("Código")

        ttk.Button(
            self.container,
            text="Validar",
            command=self._verify_totp
        ).pack(pady=20)

    def _verify_totp(self):
        payload = {
            "usuario": self.usuario,
            "codigo": self.fields["Código"].get().strip()
        }

        try:
            resp = verify_totp_api(payload)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        if not resp.get("ok"):
            messagebox.showerror("Error", resp.get("error"), parent=self)
            return

        self._step_new_password()

    # =====================================================
    # PASO 3 — NUEVA CONTRASEÑA
    # =====================================================
    def _step_new_password(self):
        self._clear()

        tk.Label(
            self.container,
            text="Nueva contraseña",
            font=("Segoe UI", 12, "bold")
        ).pack(pady=(0, 15))

        self._field("Contraseña", show="*")
        self._field("Confirmar", show="*")

        ttk.Button(
            self.container,
            text="Guardar contraseña",
            command=self._save_password
        ).pack(pady=20)

    def _save_password(self):
        p1 = self.fields["Contraseña"].get()
        p2 = self.fields["Confirmar"].get()

        if p1 != p2:
            messagebox.showerror("Error", "Las contraseñas no coinciden", parent=self)
            return

        payload = {
            "usuario": self.usuario,
            "password": p1
        }

        try:
            resp = set_password_api(payload)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return

        if not resp.get("ok"):
            messagebox.showerror("Error", resp.get("error"), parent=self)
            return

        messagebox.showinfo(
            "Listo",
            "La contraseña fue actualizada correctamente",
            parent=self
        )

        self._close()

    # =====================================================
    # UTILIDADES UI
    # =====================================================
    def _field(self, label, show=None):
        if not hasattr(self, "fields"):
            self.fields = {}

        tk.Label(self.container, text=label).pack(anchor="w")
        entry = ttk.Entry(self.container, show=show)
        entry.pack(fill="x", pady=(0, 10))
        self.fields[label] = entry

    def _clear(self):
        for w in self.container.winfo_children():
            w.destroy()
        self.fields = {}

    def _close(self):
        self.grab_release()
        self.destroy()
