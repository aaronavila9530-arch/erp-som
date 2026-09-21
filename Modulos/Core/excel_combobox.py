import tkinter as tk
from tkinter import ttk
import unicodedata


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


def _normalized(value):
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.casefold().strip()


class ExcelFilterCombobox(ttk.Combobox):
    """ttk.Combobox with Excel-like type-to-filter behavior."""

    _navigation_keys = {
        "Up", "Down", "Left", "Right", "Home", "End", "Prior", "Next",
        "Escape", "Tab", "Shift_L", "Shift_R", "Control_L",
        "Control_R", "Alt_L", "Alt_R", "Caps_Lock",
    }

    def __init__(self, master=None, **kwargs):
        self._excel_filter_enabled = kwargs.pop("excel_filter", True)
        self._excel_internal_config = False
        self._excel_popup_after = None
        self._excel_popup = None
        self._excel_popup_listbox = None
        self._excel_last_filtered = []
        super().__init__(master, **kwargs)
        self._excel_all_values = _as_list(super().cget("values"))
        self._excel_original_state = str(super().cget("state") or "")
        self._install_excel_filter()
        self._fit_width_to_values()

    def configure(self, cnf=None, **kwargs):
        result = super().configure(cnf, **kwargs)
        if not self._excel_internal_config:
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
        if self._excel_internal_config:
            return result
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
        self.bind("<Button-1>", self._on_click, add="+")
        self.bind("<Alt-Down>", self._open_and_filter, add="+")
        self.bind("<Down>", self._focus_popup_selection, add="+")
        self.bind("<<ComboboxSelected>>", self._on_selected, add="+")
        self.bind("<Escape>", self._on_escape, add="+")
        self.bind("<Return>", self._on_return, add="+")
        self.bind("<KP_Enter>", self._on_return, add="+")
        self.bind("<Control-a>", self._select_all, add="+")

    def _on_focus_in(self, _event=None):
        try:
            state = str(super().cget("state") or "")
            if state == "readonly":
                super().configure(state="normal")
            self.icursor(tk.END)
        except Exception:
            pass

    def _on_focus_out(self, _event=None):
        self._cancel_popup()
        self._reset_values()
        self.after(120, self._finish_focus_out)

    def _on_selected(self, _event=None):
        self._hide_popup()
        self._reset_values()
        self._fit_width_to_values()

    def _on_key_release(self, event=None):
        if not self._excel_filter_enabled:
            return
        if event and event.keysym in self._navigation_keys:
            return
        if self._is_disabled():
            return
        if event and event.keysym in {"Return", "KP_Enter"}:
            return
        typed = str(self.get() or "")
        all_values = self._excel_all_values or _as_list(super().cget("values"))
        filtered = self._filter_values(typed, all_values)
        self._excel_last_filtered = filtered
        try:
            self._set_values_internal(filtered)
            self._fit_width_to_values(all_values)
            self._schedule_dropdown()
        except Exception:
            pass

    def _on_click(self, _event=None):
        if self._excel_filter_enabled and not self._is_disabled():
            self.focus_set()
            self.icursor(tk.END)
            self.after_idle(self._open_and_filter)
            return "break"
        return None

    def _open_and_filter(self, _event=None):
        if not self._excel_filter_enabled or self._is_disabled():
            return None
        typed = str(self.get() or "")
        all_values = self._excel_all_values or _as_list(super().cget("values"))
        filtered = self._filter_values(typed, all_values)
        self._excel_last_filtered = filtered
        self._set_values_internal(filtered)
        self._show_popup()
        return "break"

    def _on_return(self, _event=None):
        if not self._excel_filter_enabled or self._is_disabled():
            return
        current = str(self.get() or "")
        all_values = self._excel_all_values or _as_list(super().cget("values"))
        filtered = self._excel_last_filtered or self._filter_values(current, all_values)
        target = self._exact_match(current, all_values) or (filtered[0] if filtered else None)
        if target is not None:
            self.set(target)
            self.icursor(tk.END)
            self._hide_popup()
            self._reset_values()
            self.event_generate("<<ComboboxSelected>>")
            return "break"
        return None

    def _on_escape(self, _event=None):
        self._cancel_popup()
        self._hide_popup()
        self._reset_values()
        self.icursor(tk.END)
        return "break"

    def _select_all(self, _event=None):
        try:
            self.selection_range(0, tk.END)
            self.icursor(tk.END)
            return "break"
        except Exception:
            return None

    def _reset_values(self, _event=None):
        try:
            self._set_values_internal(self._excel_all_values)
            self._fit_width_to_values()
        except Exception:
            pass

    def _set_values_internal(self, values):
        self._excel_internal_config = True
        try:
            super().configure(values=values)
        finally:
            self._excel_internal_config = False

    def _filter_values(self, typed, all_values):
        needle = _normalized(typed)
        if not needle:
            return all_values
        starts = []
        contains = []
        tokens = [token for token in needle.split() if token]
        for value in all_values:
            haystack = _normalized(value)
            if haystack.startswith(needle):
                starts.append(value)
            elif needle in haystack or all(token in haystack for token in tokens):
                contains.append(value)
        return starts + contains

    def _exact_match(self, typed, all_values):
        needle = _normalized(typed)
        for value in all_values:
            if _normalized(value) == needle:
                return value
        return None

    def _is_disabled(self):
        try:
            return str(super().cget("state") or "") == "disabled"
        except Exception:
            return False

    def _schedule_dropdown(self):
        self._cancel_popup()
        try:
            self._excel_popup_after = self.after(80, self._post_dropdown)
        except Exception:
            self._excel_popup_after = None

    def _cancel_popup(self):
        if not self._excel_popup_after:
            return
        try:
            self.after_cancel(self._excel_popup_after)
        except Exception:
            pass
        self._excel_popup_after = None

    def _post_dropdown(self):
        self._excel_popup_after = None
        try:
            if self.focus_get() != self or not self._excel_last_filtered:
                self._hide_popup()
                return
            self._show_popup()
            self.icursor(tk.END)
            self.focus_set()
        except Exception:
            pass

    def _show_popup(self):
        values = self._excel_last_filtered or []
        if not values:
            self._hide_popup()
            return
        try:
            if self._excel_popup is None or not self._excel_popup.winfo_exists():
                popup = tk.Toplevel(self)
                popup.overrideredirect(True)
                popup.transient(self.winfo_toplevel())
                popup.attributes("-topmost", True)
                frame = ttk.Frame(popup, borderwidth=1, relief="solid")
                frame.pack(fill="both", expand=True)
                listbox = tk.Listbox(frame, activestyle="dotbox", exportselection=False)
                listbox.pack(side="left", fill="both", expand=True)
                scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
                scrollbar.pack(side="right", fill="y")
                listbox.configure(yscrollcommand=scrollbar.set)
                listbox.bind("<ButtonRelease-1>", self._select_popup_value, add="+")
                listbox.bind("<Return>", self._select_popup_value, add="+")
                listbox.bind("<KP_Enter>", self._select_popup_value, add="+")
                listbox.bind("<Escape>", self._on_escape, add="+")
                listbox.bind("<KeyPress>", self._on_popup_keypress, add="+")
                self._excel_popup = popup
                self._excel_popup_listbox = listbox

            listbox = self._excel_popup_listbox
            listbox.delete(0, tk.END)
            for value in values:
                listbox.insert(tk.END, value)
            if values:
                listbox.selection_set(0)
                listbox.activate(0)

            self.update_idletasks()
            x = self.winfo_rootx()
            y = self.winfo_rooty() + self.winfo_height()
            width = max(self.winfo_width(), 180)
            visible_rows = min(max(len(values), 1), 10)
            row_height = 22
            height = (visible_rows * row_height) + 4
            self._excel_popup.geometry(f"{width}x{height}+{x}+{y}")
            self._excel_popup.deiconify()
            self._excel_popup.lift()
        except Exception:
            pass

    def _hide_popup(self):
        try:
            if self._excel_popup is not None and self._excel_popup.winfo_exists():
                self._excel_popup.withdraw()
        except Exception:
            pass

    def _finish_focus_out(self):
        try:
            focus = self.focus_get()
            if focus in {self, self._excel_popup_listbox}:
                return
            if self._excel_original_state == "readonly":
                super().configure(state="readonly")
            self._hide_popup()
        except Exception:
            self._hide_popup()
            try:
                if self._excel_original_state == "readonly":
                    super().configure(state="readonly")
            except Exception:
                pass

    def _focus_popup_selection(self, _event=None):
        try:
            if self._excel_popup is not None and self._excel_popup.winfo_viewable():
                self._excel_popup_listbox.focus_set()
                return "break"
        except Exception:
            pass
        return None

    def _select_popup_value(self, _event=None):
        try:
            selection = self._excel_popup_listbox.curselection()
            if not selection:
                return "break"
            value = self._excel_popup_listbox.get(selection[0])
            self.set(value)
            self.icursor(tk.END)
            self._hide_popup()
            self._reset_values()
            self.focus_set()
            self.event_generate("<<ComboboxSelected>>")
            return "break"
        except Exception:
            return "break"

    def _on_popup_keypress(self, event):
        keysym = getattr(event, "keysym", "")
        char = getattr(event, "char", "")
        if not self._excel_filter_enabled or self._is_disabled():
            return None
        if keysym in {"Up", "Down", "Prior", "Next", "Home", "End"}:
            return None
        if keysym in {"Tab", "Return", "KP_Enter", "Escape"}:
            return None
        try:
            if keysym == "BackSpace":
                current = str(self.get() or "")
                self.delete(max(len(current) - 1, 0), tk.END)
            elif keysym == "Delete":
                self.delete(0, tk.END)
            elif char and char.isprintable():
                self.insert(tk.END, char)
            else:
                return None
            self.icursor(tk.END)
            typed = str(self.get() or "")
            all_values = self._excel_all_values or _as_list(super().cget("values"))
            filtered = self._filter_values(typed, all_values)
            self._excel_last_filtered = filtered
            self._set_values_internal(filtered)
            self._show_popup()
            self.focus_set()
            return "break"
        except Exception:
            return None

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
