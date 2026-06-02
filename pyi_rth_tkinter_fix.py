import os
import sys


if getattr(sys, "frozen", False):
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    tcl_root = os.path.join(base, "tcl")
    tcl_library = os.path.join(tcl_root, "tcl8.6")
    tk_library = os.path.join(tcl_root, "tk8.6")

    if os.path.isdir(tcl_library):
        os.environ.setdefault("TCL_LIBRARY", tcl_library)
    if os.path.isdir(tk_library):
        os.environ.setdefault("TK_LIBRARY", tk_library)
