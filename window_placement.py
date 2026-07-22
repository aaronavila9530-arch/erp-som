"""Global window placement policy for ERP-SOM.

Keeps child windows and native Tk dialogs on the same monitor as the SOM
window that opened them.  This module must be installed once during startup.
"""

from __future__ import annotations

import ctypes
import os
import tkinter as tk
from tkinter import commondialog


_INSTALLED = False
_ORIGINAL_TOPLEVEL_INIT = tk.Toplevel.__init__
_ORIGINAL_DIALOG_SHOW = commondialog.Dialog.show


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _Rect),
        ("rcWork", _Rect),
        ("dwFlags", ctypes.c_ulong),
    ]


def _active_toplevel(fallback=None):
    """Return the focused SOM toplevel, or a safe fallback."""
    try:
        root = tk._default_root
        focused = root.focus_get() if root is not None else None
        if focused is not None:
            return focused.winfo_toplevel()
    except (AttributeError, KeyError, tk.TclError):
        pass

    try:
        return fallback.winfo_toplevel() if fallback is not None else tk._default_root
    except (AttributeError, tk.TclError):
        return tk._default_root


def _monitor_work_area(window):
    """Get the Windows work area (excluding the taskbar) for a Tk window."""
    if os.name != "nt" or window is None:
        return None
    try:
        hwnd = window.winfo_id()
        monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, 2)
        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(_MonitorInfo)
        if monitor and ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            work = info.rcWork
            return work.left, work.top, work.right, work.bottom
    except (AttributeError, OSError, tk.TclError):
        pass
    return None


def _fit_position(parent_box, child_size, work_area):
    """Center a child on its parent and clamp it to the monitor work area."""
    px, py, pw, ph = parent_box
    width, height = child_size
    left, top, right, bottom = work_area
    available_width = max(1, right - left)
    available_height = max(1, bottom - top)
    width = min(max(1, width), available_width)
    height = min(max(1, height), available_height)
    x = px + (pw - width) // 2
    y = py + (ph - height) // 2
    x = min(max(x, left), right - width)
    y = min(max(y, top), bottom - height)
    return x, y, width, height


def place_on_parent_monitor(window, parent=None):
    """Place *window* on the monitor occupied by *parent*."""
    try:
        if not window.winfo_exists() or window.state() in {"zoomed", "iconic"}:
            return
        parent = _active_toplevel(parent)
        if parent is None or parent is window or not parent.winfo_exists():
            return
        window.update_idletasks()
        parent.update_idletasks()
        work_area = _monitor_work_area(parent)
        if work_area is None:
            work_area = (
                parent.winfo_vrootx(),
                parent.winfo_vrooty(),
                parent.winfo_vrootx() + parent.winfo_vrootwidth(),
                parent.winfo_vrooty() + parent.winfo_vrootheight(),
            )
        width = max(window.winfo_width(), window.winfo_reqwidth())
        height = max(window.winfo_height(), window.winfo_reqheight())
        parent_box = (
            parent.winfo_rootx(),
            parent.winfo_rooty(),
            parent.winfo_width(),
            parent.winfo_height(),
        )
        x, y, width, height = _fit_position(parent_box, (width, height), work_area)
        window.geometry(f"{width}x{height}+{x}+{y}")
    except (AttributeError, KeyError, RuntimeError, tk.TclError):
        # Window creation must never fail because positioning was unavailable.
        return


def _patched_toplevel_init(self, master=None, cnf=None, **kw):
    if cnf is None:
        cnf = {}
    parent = _active_toplevel(master)
    _ORIGINAL_TOPLEVEL_INIT(self, master, cnf, **kw)
    self._som_placement_parent = parent
    self._som_placement_done = False

    def place_once(_event=None):
        if self._som_placement_done:
            return
        self._som_placement_done = True
        # Constructors commonly set geometry after super().__init__. Waiting a
        # little ensures their final size is known before choosing the monitor.
        self.after_idle(lambda: place_on_parent_monitor(self, parent))
        self.after(80, lambda: place_on_parent_monitor(self, parent))

    self.bind("<Map>", place_once, add="+")


def _patched_dialog_show(self, **options):
    # messagebox, filedialog, colorchooser and simple native dialogs inherit
    # this method. Supplying a parent makes Windows open them on that monitor.
    if options.get("parent") is None and self.options.get("parent") is None:
        parent = _active_toplevel(self.master)
        if parent is not None:
            options["parent"] = parent
    return _ORIGINAL_DIALOG_SHOW(self, **options)


def install_same_monitor_policy():
    """Install ERP-SOM's process-wide same-monitor popup policy once."""
    global _INSTALLED
    if _INSTALLED:
        return
    tk.Toplevel.__init__ = _patched_toplevel_init
    commondialog.Dialog.show = _patched_dialog_show
    _INSTALLED = True

