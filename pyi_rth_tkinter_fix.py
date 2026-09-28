import os
import sys


if getattr(sys, "frozen", False):
    base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))

    tcl_candidates = [
        os.path.join(base, "_tcl_data"),
        os.path.join(base, "_tcl"),
        os.path.join(base, "tcl", "tcl8.6"),
    ]
    tk_candidates = [
        os.path.join(base, "_tk_data"),
        os.path.join(base, "_tk"),
        os.path.join(base, "tcl", "tk8.6"),
    ]

    for tcl_library in tcl_candidates:
        if os.path.isdir(tcl_library):
            os.environ["TCL_LIBRARY"] = tcl_library
            break

    for tk_library in tk_candidates:
        if os.path.isdir(tk_library):
            os.environ["TK_LIBRARY"] = tk_library
            break
