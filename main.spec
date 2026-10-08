# -*- mode: python ; coding: utf-8 -*-

# ============================================================
# ERP-SOM - SPEC CLIENTE DESKTOP
# Incluye Tk/Tcl para que el ejecutable pueda abrir Tkinter.
# Incluye backend_api.database porque auth_api lo importa en desktop.
# ============================================================

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# Ruta fija del proyecto.
project_root = os.path.abspath(SPECPATH)
python_root = os.path.dirname(os.__file__)
python_base = os.path.dirname(python_root)
tcl_root = os.path.join(python_base, "tcl")

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
    "password_reset_window",
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
hidden_imports += collect_submodules(
    "backend_api",
    filter=lambda name: not (
        name == "backend_api.reports.container_reports_router"
        or name == "backend_api.routers.vessel_grain_sampling"
    ),
)

# --------------------------
# PILLOW (QR)
# --------------------------
hidden_imports += collect_submodules("PIL")
hidden_imports += collect_submodules("tkinter")

# --------------------------
# REQUESTS (API HTTP)
# --------------------------
hidden_imports += collect_submodules("requests")
hidden_imports += ["pythoncom", "pywintypes", "win32com", "win32com.client"]

# ============================================================
# DATAS
# ============================================================

tcl_datas = []
for src, dest in (
    (os.path.join(tcl_root, "tcl8.6"), "_tcl_data"),
    (os.path.join(tcl_root, "tk8.6"), "_tk_data"),
    (os.path.join(tcl_root, "tcl8.6"), "_tcl"),
    (os.path.join(tcl_root, "tk8.6"), "_tk"),
    (os.path.join(tcl_root, "tcl8.6"), os.path.join("tcl", "tcl8.6")),
    (os.path.join(tcl_root, "tk8.6"), os.path.join("tcl", "tk8.6")),
):
    if os.path.isdir(src):
        tcl_datas.append((src, dest))

datas = [
    ("assets", "assets"),
    ("Modulos", "Modulos"),
    ("backend_api", "backend_api"),
    ("desktop_services", "desktop_services"),
    ("resource_utils.py", "."),
    ("version.py", "."),
    *tcl_datas,
]

# Do not distribute local records, caches, or credentials with the desktop app.
safe_datas = []
for source, destination in datas:
    root = Path(source)
    if source in {"assets", "Modulos", "backend_api", "desktop_services"}:
        for file in root.rglob("*"):
            if not file.is_file():
                continue
            relative = file.relative_to(root)
            if any(part in {"__pycache__", ".git", "storage", "tmp", "tests"} for part in relative.parts):
                continue
            if file.name.startswith((".env", "~$")) or file.name == "Varios Aaron.xlsx" or file.suffix.lower() in {".pyc", ".pyo", ".pem", ".key", ".log", ".db", ".sqlite"}:
                continue
            if source == "backend_api" and file.name in {"surveyors.xlsx", "git"}:
                continue
            safe_datas.append((str(file), str(Path(destination) / relative.parent)))
    else:
        safe_datas.append((source, destination))
datas = safe_datas

binaries = []
for dll in ("tcl86t.dll", "tk86t.dll"):
    src = os.path.join(python_base, "DLLs", dll)
    if os.path.isfile(src):
        binaries.append((src, "."))

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
        "uvicorn",
        "sqlalchemy",
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
