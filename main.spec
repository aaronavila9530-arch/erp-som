# -*- mode: python ; coding: utf-8 -*-

# ============================================================
# ERP-SOM - SPEC CLIENTE DESKTOP
# Incluye Tk/Tcl para que el ejecutable pueda abrir Tkinter.
# Incluye backend_api.database porque auth_api lo importa en desktop.
# ============================================================

import os
from PyInstaller.utils.hooks import collect_submodules

# Ruta fija del proyecto.
project_root = os.path.abspath(SPECPATH)
python_root = os.path.dirname(os.__file__)
python_base = os.path.dirname(python_root)

# ============================================================
# HIDDEN IMPORTS
# ============================================================

hidden_imports = []

# --------------------------
# FRONTEND CORE
# --------------------------
hidden_imports += [
    "_tkinter",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "login_window",
    "otp_window",
    "otp_service",
    "auth_api",
    "session_context",
    "secure_credentials",
    "api_client",
    "backend_api.database",
    "resource_utils",
    "splash_screen",
    "update_window",
    "version",
]

# --------------------------
# MODULOS ERP DINAMICOS
# --------------------------
hidden_imports += collect_submodules("Modulos")

# --------------------------
# PILLOW (QR)
# --------------------------
hidden_imports += collect_submodules("PIL")
hidden_imports += collect_submodules("tkinter")

# --------------------------
# REQUESTS (API HTTP)
# --------------------------
hidden_imports += collect_submodules("requests")

# ============================================================
# DATAS
# ============================================================

datas = [
    ("assets", "assets"),
    ("backend_api", "backend_api"),
    (os.path.join(python_base, "tcl"), "tcl"),
]

binaries = [
    (os.path.join(python_base, "DLLs", "tcl86t.dll"), "."),
    (os.path.join(python_base, "DLLs", "tk86t.dll"), "."),
]

# ============================================================
# ANALYSIS
# ============================================================

a = Analysis(
    ["main.py"],  # ENTRYPOINT PRINCIPAL (Tkinter)
    pathex=[project_root],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=["pyi_rth_tkinter_fix.py"],
    excludes=[
        "fastapi",
        "uvicorn"
    ],
    noarchive=False,
    optimize=0,
)

# ============================================================
# PYZ
# ============================================================

pyz = PYZ(a.pure)

# ============================================================
# EXE
# ============================================================

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ERP-SOM",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(project_root, "assets", "logo_menu_tareas.ico"),
)

# ============================================================
# COLLECT (ONEDIR)
# ============================================================

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ERP-SOM",
)
