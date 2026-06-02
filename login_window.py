import os
import sys
import json
import time
import tkinter as tk
from tkinter import ttk, messagebox

from auth_api import login_usuario
from api_client import set_user_role, get_version_info
from resource_utils import resource_path
from update_window import UpdateWindow
from version import APP_VERSION
from secure_credentials import (
    delete_credentials,
    has_saved_credentials,
    is_windows_protection_available,
    load_credentials,
)


class LoginWindow(tk.Toplevel):

    # ====================================================
    # ANTI-LOOP UPDATE (BLINDADO)
    # - Si ya se intentó instalar la MISMA versión hace poco,
    #   NO volver a bloquear el login con update infinito.
    # ====================================================
    UPDATE_COOLDOWN_SECONDS = 15 * 60  # 15 minutos

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.remember_credentials = tk.BooleanVar(value=has_saved_credentials())
        self._switch_canvas = None
        self._switch_label = None

        # ----------------------------------------------------
        # ICONO VENTANA
        # ----------------------------------------------------
        try:
            self.iconbitmap(resource_path("assets/logo_menu_tareas.ico"))
        except Exception:
            pass

        self.title("ERP-SOM | Login")
        self.geometry("1000x600")
        self.minsize(900, 550)

        try:
            self.state("zoomed")
        except Exception:
            pass

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

        tk.Label(
            self.left,
            text="Usuario",
            bg="white"
        ).grid(row=1, column=0, sticky="w", pady=(10, 5))

        self.usuario = ttk.Entry(self.left, width=30)
        self.usuario.grid(row=2, column=0, sticky="w")
        self.usuario.focus_set()

        tk.Label(
            self.left,
            text="Contraseña",
            bg="white"
        ).grid(row=3, column=0, sticky="w", pady=(20, 5))

        self.password = ttk.Entry(self.left, width=30, show="*")
        self.password.grid(row=4, column=0, sticky="w")

        self._build_credentials_switch(row=5)

        ttk.Button(
            self.left,
            text="Ingresar",
            command=self._login
        ).grid(row=6, column=0, sticky="w", pady=(22, 10))

        self.btn_windows_unlock = ttk.Button(
            self.left,
            text="Usar credenciales guardadas",
            command=self._unlock_with_windows
        )
        self.btn_windows_unlock.grid(row=7, column=0, sticky="w", pady=(0, 10))

        if not has_saved_credentials() or not is_windows_protection_available():
            self.btn_windows_unlock.state(["disabled"])

        ttk.Button(
            self.left,
            text="Olvidé mi contraseña",
            command=self._forgot
        ).grid(row=8, column=0, sticky="w")

        # ENTER = LOGIN
        self.bind("<Return>", lambda e: self._login())

        # ====================================================
        # DERECHA — IMAGEN (BLINDADO)
        # ====================================================
        self.right = tk.Frame(self, bg="white")
        self.right.grid(row=0, column=1, sticky="nsew")

        bg_image = getattr(self.parent, "_login_bg_image", None)

        if bg_image:
            self.lbl_img = tk.Label(
                self.right,
                bg="white",
                image=bg_image
            )
            self.lbl_img.image = bg_image
            self.lbl_img.pack(fill="both", expand=True)
        else:
            tk.Label(
                self.right,
                bg="white",
                text="",
            ).pack(fill="both", expand=True)

    def _build_credentials_switch(self, row: int):
        frame = tk.Frame(self.left, bg="white")
        frame.grid(row=row, column=0, sticky="w", pady=(12, 0))

        self._switch_canvas = tk.Canvas(
            frame,
            width=48,
            height=26,
            bg="white",
            highlightthickness=0,
            cursor="hand2",
        )
        self._switch_canvas.grid(row=0, column=0, sticky="w")
        self._switch_canvas.bind(
            "<Button-1>",
            lambda _e: self._toggle_credentials_switch(),
        )

        self._switch_label = tk.Label(
            frame,
            text="Guardar credenciales en Windows",
            bg="white",
            fg="#1F2937",
            cursor="hand2",
        )
        self._switch_label.grid(row=0, column=1, sticky="w", padx=(10, 0))
        self._switch_label.bind(
            "<Button-1>",
            lambda _e: self._toggle_credentials_switch(),
        )
        self._draw_credentials_switch()

    def _draw_credentials_switch(self):
        if not self._switch_canvas:
            return

        enabled = bool(self.remember_credentials.get())
        bg = "#0B64C0" if enabled else "#B8BEC8"
        knob_x = 35 if enabled else 13

        self._switch_canvas.delete("all")
        self._switch_canvas.create_oval(1, 1, 25, 25, fill=bg, outline=bg)
        self._switch_canvas.create_oval(23, 1, 47, 25, fill=bg, outline=bg)
        self._switch_canvas.create_rectangle(13, 1, 35, 25, fill=bg, outline=bg)
        self._switch_canvas.create_oval(
            knob_x - 10,
            3,
            knob_x + 10,
            23,
            fill="white",
            outline="#E5E7EB",
        )

    def _toggle_credentials_switch(self):
        next_value = not bool(self.remember_credentials.get())
        self.remember_credentials.set(next_value)
        self._draw_credentials_switch()

        if not next_value and has_saved_credentials():
            try:
                delete_credentials()
            except Exception as e:
                messagebox.showerror(
                    "Credenciales guardadas",
                    "No se pudieron quitar las credenciales guardadas.\n\n"
                    f"{e}",
                    parent=self,
                )

        self._refresh_saved_credentials_button()

    def _refresh_saved_credentials_button(self):
        try:
            if has_saved_credentials() and is_windows_protection_available():
                self.btn_windows_unlock.state(["!disabled"])
            else:
                self.btn_windows_unlock.state(["disabled"])
        except Exception:
            pass

    # ====================================================
    # UPDATE STATE (ANTI-LOOP)
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
        """
        Si ya intentamos instalar ESTA misma versión hace poco, no bloquear login.
        """
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

    # ====================================================
    # CHECK VERSION + UPDATE (BLINDADO REAL + ANTI-LOOP)
    # ====================================================
    def _check_version_and_update(self) -> bool:

        # En desarrollo nunca bloquear
        if not getattr(sys, "frozen", False):
            return True

        try:
            ok, data = get_version_info()
            if not ok:
                return True

            latest_version = (data.get("latest_version") or "")
            current_version = (APP_VERSION or "")
            download_url = data.get("download_url")

            if not str(latest_version).strip():
                return True

            # ===============================
            # NORMALIZAR VERSIONES (FUERTE)
            # ===============================
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

            # ===============================
            # YA ESTAMOS ACTUALIZADOS
            # ===============================
            if latest_t <= current_t:
                return True

            # ===============================
            # ANTI-LOOP: si ya intentaste esta versión hace poco,
            # NO vuelvas a bloquear el login.
            # ===============================
            if self._should_skip_update_due_to_loop(latest_clean):
                return True

            # ===============================
            # SOLO SI REALMENTE ES MAYOR
            # ===============================
            if download_url:
                # Registrar intento (antes de abrir installer)
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
    # LOGIN
    # ====================================================
    def _login(self):
        usuario = self.usuario.get().strip()
        password = self.password.get()

        if not usuario or not password:
            messagebox.showwarning(
                "Atención",
                "Ingrese usuario y contraseña",
                parent=self
            )
            return

        try:
            ok, data = login_usuario(usuario, password)
        except Exception as e:
            messagebox.showerror(
                "Error de autenticación",
                "No se pudo conectar o validar el usuario.\n\n"
                f"{e}",
                parent=self
            )
            return

        if not ok:
            messagebox.showerror(
                "Error",
                data.get("error", "Credenciales inválidas"),
                parent=self
            )
            return

        # RBAC visual
        rol = data.get("rol")
        if rol:
            set_user_role(rol)

        try:
            from otp_window import OTPWindow
        except Exception as e:
            messagebox.showerror(
                "Error crítico",
                f"No se pudo cargar el módulo de autenticación.\n\n{e}",
                parent=self
            )
            return

        action = (data.get("action") or "").strip()

        if action == "ENROLL_TOTP":
            OTPWindow(
                self,
                usuario=data.get("usuario", usuario),
                rol=rol,
                mode="ENROLL_TOTP",
                qr_bytes=data.get("qr"),
                password=password,
                remember_credentials=self.remember_credentials.get()
            )

        elif action == "VERIFY_TOTP":
            OTPWindow(
                self,
                usuario=data.get("usuario", usuario),
                rol=rol,
                mode="VERIFY_TOTP",
                password=password,
                remember_credentials=self.remember_credentials.get()
            )
        else:
            messagebox.showerror(
                "Error",
                "Respuesta inválida del servidor de autenticación.",
                parent=self
            )

    def _unlock_with_windows(self):
        try:
            saved = load_credentials()
        except Exception as e:
            messagebox.showerror(
                "Credenciales guardadas",
                "No se pudieron usar las credenciales guardadas en Windows.\n\n"
                f"{e}",
                parent=self
            )
            return

        if not saved:
            messagebox.showinfo(
                "Credenciales guardadas",
                "No hay credenciales guardadas para este usuario de Windows.",
                parent=self
            )
            return

        self.usuario.delete(0, tk.END)
        self.usuario.insert(0, saved.get("usuario", ""))
        self.password.delete(0, tk.END)
        self.password.insert(0, saved.get("password", ""))
        self.remember_credentials.set(True)
        self._draw_credentials_switch()
        self._login()

    # ====================================================
    # RESET PASSWORD
    # ====================================================
    def _forgot(self):
        try:
            from password_reset_window import PasswordResetWindow
            PasswordResetWindow(self)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el reset de contraseña.\n\n{e}",
                parent=self
            )

    # ====================================================
    # CERRAR TODO
    # ====================================================
    def _cerrar_todo(self):
        try:
            self.parent.destroy()
        except Exception:
            pass
        try:
            sys.exit(0)
        except Exception:
            pass
