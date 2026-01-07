import tkinter as tk
from tkinter import ttk, messagebox

from password_reset import (
    verify_identity,
    verify_reset_totp,
    reset_password_final
)


class PasswordResetWindow(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.usuario = None

        self.title("Recuperar contraseña")
        self.geometry("360x320")
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

        ttk.Button(
            self.container,
            text="Continuar",
            command=self._verify_identity
        ).pack(pady=20)

    def _verify_identity(self):
        usuario = self.fields["Usuario"].get().strip()
        nombre = self.fields["Nombre"].get().strip()
        apellido = self.fields["Apellido"].get().strip()

        ok, data = verify_identity(usuario, nombre, apellido)

        if not ok:
            messagebox.showerror("Error", data["error"], parent=self)
            return

        self.usuario = usuario
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
        codigo = self.fields["Código"].get().strip()

        ok, data = verify_reset_totp(self.usuario, codigo)

        if not ok:
            messagebox.showerror("Error", data["error"], parent=self)
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

        ok, data = reset_password_final(self.usuario, p1)

        if not ok:
            messagebox.showerror("Error", data["error"], parent=self)
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
