import tkinter as tk
from tkinter import ttk


_INSTALLED = False


def _as_list(values):
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    try:
        return list(values)
    except Exception:
        return []


class ExcelFilterCombobox(ttk.Combobox):
    """ttk.Combobox with Excel-like type-to-filter behavior."""

    _navigation_keys = {
        "Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next",
        "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L",
        "Control_R", "Alt_L", "Alt_R", "Caps_Lock",
    }

    def __init__(self, master=None, **kwargs):
        self._excel_filter_enabled = kwargs.pop("excel_filter", True)
        super().__init__(master, **kwargs)
        self._excel_all_values = _as_list(super().cget("values"))
        self._excel_original_state = str(super().cget("state") or "")
        self._install_excel_filter()
        self._fit_width_to_values()

    def configure(self, cnf=None, **kwargs):
        result = super().configure(cnf, **kwargs)
        if cnf is None and "values" in kwargs:
            self._excel_all_values = _as_list(kwargs.get("values"))
            self._fit_width_to_values()
        elif isinstance(cnf, dict) and "values" in cnf:
            self._excel_all_values = _as_list(cnf.get("values"))
            self._fit_width_to_values()
        if cnf is None and "state" in kwargs:
            self._excel_original_state = str(kwargs.get("state") or "")
        elif isinstance(cnf, dict) and "state" in cnf:
            self._excel_original_state = str(cnf.get("state") or "")
        return result

    config = configure

    def __setitem__(self, key, value):
        result = super().__setitem__(key, value)
        if key == "values":
            self._excel_all_values = _as_list(value)
            self._fit_width_to_values()
        elif key == "state":
            self._excel_original_state = str(value or "")
        return result

    def _install_excel_filter(self):
        if not self._excel_filter_enabled:
            return
        self.bind("<FocusIn>", self._on_focus_in, add="+")
        self.bind("<FocusOut>", self._on_focus_out, add="+")
        self.bind("<KeyRelease>", self._on_key_release, add="+")
        self.bind("<<ComboboxSelected>>", self._on_selected, add="+")
        self.bind("<Escape>", self._reset_values, add="+")

    def _on_focus_in(self, _event=None):
        try:
            if str(super().cget("state")) == "readonly":
                super().configure(state="normal")
        except Exception:
            pass

    def _on_focus_out(self, _event=None):
        self._reset_values()
        try:
            if self._excel_original_state == "readonly":
                super().configure(state="readonly")
        except Exception:
            pass

    def _on_selected(self, _event=None):
        self._reset_values()

    def _on_key_release(self, event=None):
        if not self._excel_filter_enabled:
            return
        if event and event.keysym in self._navigation_keys:
            return
        typed = str(self.get() or "").strip().lower()
        all_values = self._excel_all_values or _as_list(super().cget("values"))
        if not typed:
            filtered = all_values
        else:
            starts = [v for v in all_values if str(v).lower().startswith(typed)]
            contains = [v for v in all_values if typed in str(v).lower() and v not in starts]
            filtered = starts + contains
        try:
            super().configure(values=filtered)
            self._fit_width_to_values(filtered or all_values)
            if filtered:
                self.event_generate("<Down>")
        except Exception:
            pass

    def _reset_values(self, _event=None):
        try:
            super().configure(values=self._excel_all_values)
            self._fit_width_to_values()
        except Exception:
            pass

    def _fit_width_to_values(self, values=None):
        try:
            current = int(super().cget("width") or 0)
        except Exception:
            current = 0
        values = _as_list(values if values is not None else self._excel_all_values)
        longest = max([len(str(v)) for v in values] + [current, len(str(self.get() or ""))])
        target = max(6, min(70, longest + 2))
        if target > current:
            try:
                super().configure(width=target)
            except Exception:
                pass


def install_excel_combobox():
    global _INSTALLED
    if _INSTALLED:
        return
    if getattr(ttk.Combobox, "_erp_excel_filter", False):
        _INSTALLED = True
        return
    ExcelFilterCombobox._erp_excel_filter = True
    ttk.Combobox = ExcelFilterCombobox
    _INSTALLED = True
