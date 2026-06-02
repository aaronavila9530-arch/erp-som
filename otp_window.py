import os
import sys
import io
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox

# ====================================================
# PIL OPCIONAL
# ====================================================
try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except Exception:
    Image = None
    ImageTk = None
    _PIL_OK = False


# ====================================================
# LOGIN LOCAL (SIN API HTTP)
# ====================================================
from auth_api import (
    confirmar_registro_totp,
    validar_totp_login
)

from session_context import set_user_context
from secure_credentials import save_credentials

# ====================================================
# VERSION + UPDATE (ANTI-LOOP)
# ====================================================
from version import APP_VERSION
from api_client import get_version_info
from update_window import UpdateWindow


# ====================================================
# MAINAPP LOADER (BLINDADO ANTI-COLISIÓN)
# ✅ En lugar de importlib.import_module("main") (ambiguo),
#    importamos MainApp desde __main__ (bootloader del EXE)
# 🔒 Blindaje extra:
#    - Si no está en __main__, intenta fallback a import "main"
#    - Maneja errores con detalle técnico
# ====================================================
def _get_mainapp():
    """
    Retorna (MainApp, None) si existe, o (None, error) si falla.
    """
    # 1) Preferido: __main__ (cuando PyInstaller ejecuta tu entrypoint)
    try:
        mod = sys.modules.get("__main__")
        if mod and hasattr(mod, "MainApp"):
            return getattr(mod, "MainApp"), None
    except Exception as e:
        last_err = e
    else:
        last_err = None

    # 2) Fallback: intentar importar módulo "main"
    try:
        import importlib
        m = importlib.import_module("main")
        if hasattr(m, "MainApp"):
            return getattr(m, "MainApp"), None
        raise ImportError("MainApp no encontrado en módulo 'main'")
    except Exception as e:
        if last_err:
            return None, Exception(f"{last_err} | {e}")
        return None, e


# ====================================================
# OTP WINDOW
# ====================================================
class OTPWindow(tk.Toplevel):

    # ====================================================
    # ANTI-LOOP UPDATE (BLINDADO)
    # ====================================================
    UPDATE_COOLDOWN_SECONDS = 15 * 60  # 15 minutos

    def __init__(
        self,
        parent,
        usuario,
        rol,
        mode,
        qr_bytes=None,
        password=None,
        remember_credentials=False
    ):
        super().__init__(parent)

        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.mode = mode
        self.qr_bytes = qr_bytes
        self.password = password
        self.remember_credentials = bool(remember_credentials)
        self._submitting = False

        self.title("Verificación de Seguridad")
        self.geometry("360x420" if mode == "ENROLL_TOTP" else "300x200")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cerrar)

        self.transient(parent)
        self.grab_set()
        self.focus_force()
        self.lift()
        self.attributes("-topmost", True)
        self.after(500, lambda: self.attributes("-topmost", False))

        self._build_ui()
        self._center_on_parent()
        self.bind("<Return>", lambda e: self._validar())

    # ====================================================
    # UPDATE STATE (ANTI-LOOP) — MISMA LÓGICA QUE LOGIN
    # ====================================================
    def _update_state_path(self) -> str:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "ERP-SOM")
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            pass
        return os.path.join(folder, "update_state.json")

    def _read_update_state(self) -> dict:
        path = self._update_state_path()
        try:
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write_update_state(self, latest_version_clean: str):
        path = self._update_state_path()
        payload = {
            "last_attempt_version": latest_version_clean,
            "last_attempt_ts": int(time.time())
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception:
            pass

    def _should_skip_update_due_to_loop(self, latest_version_clean: str) -> bool:
        st = self._read_update_state()
        last_v = str(st.get("last_attempt_version") or "").strip()
        last_ts = st.get("last_attempt_ts")
        try:
            last_ts = int(last_ts)
        except Exception:
            last_ts = 0

        if not last_v or not last_ts:
            return False

        if last_v != latest_version_clean:
            return False

        age = int(time.time()) - last_ts
        return age < self.UPDATE_COOLDOWN_SECONDS

    def _check_version_and_update(self) -> bool:
        """
        Solo EXE (frozen): compara versiones y dispara UpdateWindow.
        Anti-loop: si ya intentaste esa misma versión hace poco, no bloquea.
        Retorna:
          - True  => continuar y abrir MainApp
          - False => se abrió ventana de update (no continuar)
        """
        if not getattr(sys, "frozen", False):
            return True

        try:
            ok, data = get_version_info()
            if not ok:
                return True

            data = data or {}
            latest_version = (data.get("latest_version") or "")
            current_version = (APP_VERSION or "")
            download_url = data.get("download_url")

            if not str(latest_version).strip():
                return True

            def normalize(v: str) -> str:
                v = str(v or "")
                v = v.replace("\r", "").replace("\n", "").replace("\t", "")
                v = (
                    v.lower()
                    .replace("version", "")
                    .replace("erp-som", "")
                    .replace("v", "")
                    .strip()
                )
                return v

            def to_int_tuple(v: str):
                parts = []
                for p in str(v).split("."):
                    p = "".join(ch for ch in p if ch.isdigit())
                    if p == "":
                        continue
                    parts.append(int(p))
                return tuple(parts) if parts else (0,)

            latest_clean = normalize(latest_version)
            current_clean = normalize(current_version)

            latest_t = to_int_tuple(latest_clean)
            current_t = to_int_tuple(current_clean)

            if latest_t <= current_t:
                return True

            # Anti-loop
            if self._should_skip_update_due_to_loop(latest_clean):
                return True

            if download_url:
                self._write_update_state(latest_clean)
                UpdateWindow(
                    parent=self,
                    current_version=str(current_version).strip(),
                    latest_version=str(latest_version).strip(),
                    message=data.get(
                        "message",
                        "Hay una nueva versión disponible del ERP-SOM."
                    ),
                    download_url=download_url
                )
                return False

            return True

        except Exception:
            return True

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

            self._render_qr()

        else:
            tk.Label(
                self,
                text="Código de verificación",
                font=("Segoe UI", 11, "bold")
            ).pack(pady=(25, 10))

        self.codigo = ttk.Entry(
            self,
            width=20,
            justify="center",
            font=("Segoe UI", 12)
        )
        self.codigo.pack(pady=10)
        self.codigo.focus_set()

        self.btn_validar = ttk.Button(
            self,
            text="Validar",
            command=self._validar
        )
        self.btn_validar.pack(pady=20)

    def _center_on_parent(self):
        try:
            self.update_idletasks()
            parent_x = self.parent.winfo_rootx()
            parent_y = self.parent.winfo_rooty()
            parent_w = self.parent.winfo_width()
            parent_h = self.parent.winfo_height()
            win_w = self.winfo_width()
            win_h = self.winfo_height()
            x = parent_x + max((parent_w - win_w) // 2, 0)
            y = parent_y + max((parent_h - win_h) // 2, 0)
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    # ====================================================
    # RENDER QR
    # ====================================================
    def _render_qr(self):
        try:
            if not self.qr_bytes:
                raise ValueError("QR vacío")

            if not _PIL_OK:
                raise RuntimeError(
                    "Pillow no disponible en el EXE (no se puede renderizar QR)."
                )

            image = Image.open(io.BytesIO(self.qr_bytes))
            image = image.resize((220, 220), Image.LANCZOS)
            self.qr_img = ImageTk.PhotoImage(image)

            tk.Label(
                self,
                image=self.qr_img
            ).pack(pady=5)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo mostrar el QR:\n{e}",
                parent=self
            )

    # ====================================================
    # VALIDAR
    # ====================================================
    def _validar(self):

        if self._submitting:
            return

        codigo = (self.codigo.get() or "").strip()

        if not codigo:
            messagebox.showwarning(
                "Atención",
                "Ingrese el código de verificación",
                parent=self
            )
            return

        self._submitting = True
        try:
            self.btn_validar.config(state="disabled")
        except Exception:
            pass

        try:
            self.configure(cursor="watch")
            self.update_idletasks()
        except Exception:
            pass

        try:
            if self.mode == "ENROLL_TOTP":
                ok, data = confirmar_registro_totp(self.usuario, codigo)
            else:
                ok, data = validar_totp_login(self.usuario, codigo)

        except Exception as e:
            self._reset_button()
            messagebox.showerror(
                "Error",
                f"Error validando código:\n{e}",
                parent=self
            )
            return

        if not ok:
            self._reset_button()
            messagebox.showerror(
                "Error",
                (data or {}).get("error", "Código inválido"),
                parent=self
            )
            return

        usuario_ctx = (data or {}).get("usuario") or self.usuario
        rol_ctx = (data or {}).get("rol") or self.rol

        set_user_context(
            usuario_ctx,
            rol_ctx,
            "LOCAL_SESSION"
        )

        if self.remember_credentials and self.password:
            try:
                save_credentials(usuario_ctx, self.password)
            except Exception as e:
                messagebox.showwarning(
                    "Credenciales guardadas",
                    "El login fue correcto, pero no se pudieron guardar "
                    "las credenciales en Windows.\n\n"
                    f"{e}",
                    parent=self
                )

        # ====================================================
        # CHECK UPDATE (ANTI-LOOP) antes de iniciar MainApp
        # ====================================================
        if not self._check_version_and_update():
            self._reset_button()
            return

        # ====================================================
        # INICIAR ERP PRINCIPAL (MainApp)
        # ====================================================
        MainApp, err = _get_mainapp()
        if MainApp is None:
            self._reset_button()
            messagebox.showerror(
                "Error crítico",
                "No se pudo iniciar el sistema principal.\n\n"
                f"Detalle técnico:\n{err}",
                parent=self
            )
            return

        try:
            self.grab_release()
        except tk.TclError:
            pass

        self.destroy()

        # Limpiar ventana raíz (login)
        for w in self.parent.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

        try:
            app = MainApp(self.parent, usuario_ctx, rol_ctx)
            app.pack(fill="both", expand=True)
        except Exception as e:
            messagebox.showerror(
                "Error crítico",
                "El sistema principal falló al iniciar.\n\n"
                f"Detalle técnico:\n{e}"
            )

    # ====================================================
    # RESET BUTTON
    # ====================================================
    def _reset_button(self):
        self._submitting = False
        try:
            self.btn_validar.config(state="normal")
        except Exception:
            pass
        try:
            self.configure(cursor="")
        except Exception:
            pass

    # ====================================================
    # CERRAR
    # ====================================================
    def _cerrar(self):
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
