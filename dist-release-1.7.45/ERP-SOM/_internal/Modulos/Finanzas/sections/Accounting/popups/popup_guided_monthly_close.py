import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from api_client import (
    get_accounting_guided_close_api,
    post_accounting_guided_close_api,
    update_accounting_close_checklist_api,
)
from session_context import get_user


class PopupGuidedMonthlyClose(tk.Toplevel):
    REVIEW_ALERT_MAP = {
        "TAX_XML_PENDING": "TAX_REVIEW",
        "IVA_NOT_REVIEWED": "TAX_REVIEW",
        "AUXILIARY_DIFFERENCE": "AUX_RECONCILIATION",
        "AUXILIARY_UNMAPPED": "AUX_RECONCILIATION",
    }

    def __init__(self, parent, period):
        super().__init__(parent)
        self.parent = parent
        self.period = tk.StringVar(value=period)
        self.status_var = tk.StringVar(value="Cargando cierre mensual...")
        self.ready_var = tk.StringVar(value="Sin validar")
        self.summary_vars = {}
        self.data = {}
        self.title("Cierre mensual guiado")
        self.geometry("1240x760")
        self.minsize(1080, 660)
        self.transient(parent)
        self.grab_set()
        self._build()
        self.after(120, self.refresh)

    def _build(self):
        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")
        ttk.Label(header, text="Periodo").pack(side="left")
        ttk.Entry(header, textvariable=self.period, width=10).pack(side="left", padx=6)
        ttk.Button(header, text="Actualizar", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(header, text="Ver alertas", command=self._open_alerts).pack(side="left", padx=4)
        ttk.Label(header, textvariable=self.ready_var, font=("Segoe UI", 11, "bold")).pack(side="right")

        guide = ttk.LabelFrame(self, text="Como funciona", padding=8)
        guide.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Label(
            guide,
            text=(
                "Este cierre es una lista de control auditable: valida que el periodo cuadre, "
                "que no existan alertas criticas y que cada paso tenga responsable/evidencia. "
                "Cerrar periodo bloquea nuevos asientos y cambios contables en ese mes."
            ),
            wraplength=1160,
            foreground="#444",
        ).pack(anchor="w")

        cards = ttk.Frame(self, padding=(10, 0, 10, 8))
        cards.pack(fill="x")
        for idx, (key, label) in enumerate((
            ("entries", "Asientos"),
            ("debit", "Debe"),
            ("credit", "Haber"),
            ("difference", "Diferencia"),
            ("critical_alerts", "Criticas"),
            ("warning_alerts", "Advertencias"),
        )):
            box = ttk.LabelFrame(cards, text=label, padding=8)
            box.grid(row=0, column=idx, padx=4, sticky="nsew")
            cards.columnconfigure(idx, weight=1)
            var = tk.StringVar(value="-")
            ttk.Label(box, textvariable=var, font=("Segoe UI", 12, "bold")).pack()
            self.summary_vars[key] = var

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        checklist_frame = ttk.LabelFrame(body, text="Checklist de cierre", padding=6)
        alerts_frame = ttk.LabelFrame(body, text="Validaciones", padding=6)
        body.add(checklist_frame, weight=3)
        body.add(alerts_frame, weight=2)

        cols = ("seq", "category", "title", "auto", "status", "user")
        self.checklist = ttk.Treeview(checklist_frame, columns=cols, show="headings", selectmode="browse")
        for col, label, width in (
            ("seq", "#", 42),
            ("category", "Area", 115),
            ("title", "Paso", 330),
            ("auto", "Control automatico", 310),
            ("status", "Status", 110),
            ("user", "Usuario", 120),
        ):
            self.checklist.heading(col, text=label)
            self.checklist.column(col, width=width, anchor="w")
        self.checklist.tag_configure("ok", background="#dcfce7")
        self.checklist.tag_configure("blocked", background="#fee2e2")
        self.checklist.tag_configure("pending", background="#fef9c3")
        self.checklist.pack(fill="both", expand=True)

        check_buttons = ttk.Frame(checklist_frame)
        check_buttons.pack(fill="x", pady=(6, 0))
        self.status_combo = ttk.Combobox(
            check_buttons,
            values=("IN_PROGRESS", "COMPLETE", "NOT_APPLICABLE", "PENDING"),
            state="readonly",
            width=18,
        )
        self.status_combo.set("COMPLETE")
        self.status_combo.pack(side="left", padx=(0, 4))
        ttk.Button(check_buttons, text="Actualizar paso", command=self._update_step).pack(side="left")

        self.alerts = ttk.Treeview(alerts_frame, columns=("level", "code", "message"), show="headings")
        for col, label, width in (
            ("level", "Nivel", 90),
            ("code", "Codigo", 230),
            ("message", "Detalle", 430),
        ):
            self.alerts.heading(col, text=label)
            self.alerts.column(col, width=width, anchor="w")
        self.alerts.tag_configure("critical", background="#fee2e2")
        self.alerts.tag_configure("warning", background="#fef3c7")
        self.alerts.pack(fill="both", expand=True)

        footer = ttk.Frame(self, padding=10)
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var).pack(side="left")
        ttk.Button(footer, text="Cerrar periodo", command=self._close_period).pack(side="right", padx=4)
        ttk.Button(footer, text="Salir", command=self.destroy).pack(side="right", padx=4)

    def refresh(self):
        period = self.period.get().strip()
        if not period:
            return
        self.status_var.set("Validando cierre mensual...")
        threading.Thread(target=self._load_worker, args=(period,), daemon=True).start()

    def _load_worker(self, period):
        try:
            data = get_accounting_guided_close_api(period)
            self.after(0, self._apply_data, data)
        except Exception as exc:
            self.after(0, self._load_error, str(exc))

    def _load_error(self, message):
        self.status_var.set("No se pudo cargar el cierre.")
        messagebox.showerror("Cierre mensual guiado", message, parent=self)

    def _apply_data(self, data):
        data = self._normalize_close_payload(data)
        self.data = data
        summary = data.get("summary") or {}
        for key, var in self.summary_vars.items():
            value = summary.get(key, 0)
            if key in {"debit", "credit", "difference"}:
                var.set(f"{float(value or 0):,.2f}")
            else:
                var.set(str(value or 0))

        control = data.get("period_control") or {}
        ready = bool(data.get("ready_to_close"))
        control_status = control.get("status") or "OPEN"
        if control_status == "CLOSED":
            self.ready_var.set(f"Periodo cerrado por {control.get('closed_by') or '-'}")
        elif ready:
            self.ready_var.set("Listo para cierre")
        else:
            self.ready_var.set("Pendiente de controles")

        self.checklist.delete(*self.checklist.get_children())
        for row in data.get("checklist") or []:
            check = row.get("automatic_check") or {}
            status = row.get("status") or "PENDING"
            if status in {"COMPLETE", "NOT_APPLICABLE"}:
                tag = "ok"
            elif not check.get("ready"):
                tag = "blocked"
            else:
                tag = "pending"
            self.checklist.insert(
                "",
                "end",
                iid=row.get("item_code"),
                values=(
                    row.get("sequence"),
                    row.get("category"),
                    row.get("title"),
                    check.get("detail") or "",
                    status,
                    row.get("completed_by") or "",
                ),
                tags=(tag,),
            )

        self.alerts.delete(*self.alerts.get_children())
        validation = data.get("validation") or {}
        for row in validation.get("critical") or []:
            self.alerts.insert("", "end", values=("ROJO", row.get("code"), row.get("message")), tags=("critical",))
        for row in validation.get("warnings") or []:
            self.alerts.insert("", "end", values=("AMARILLO", row.get("code"), row.get("message")), tags=("warning",))

        self.status_var.set(
            f"{summary.get('completed', 0)} de {summary.get('total', 0)} pasos completos. "
            f"Criticas: {summary.get('critical_alerts', 0)}. "
            f"Advertencias: {summary.get('warning_alerts', 0)}."
        )

    def _update_step(self):
        selected = self.checklist.selection()
        if not selected:
            messagebox.showwarning("Cierre mensual", "Seleccione un paso del checklist.", parent=self)
            return
        status = self.status_combo.get()
        notes = simpledialog.askstring("Nota de cierre", "Nota o referencia de soporte:", parent=self) or ""
        try:
            update_accounting_close_checklist_api(
                self.period.get().strip(),
                selected[0],
                status,
                get_user() or "unknown",
                notes,
            )
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Cierre mensual", str(exc), parent=self)

    def _close_period(self):
        self.data = self._normalize_close_payload(self.data)
        if not self.data.get("ready_to_close"):
            messagebox.showwarning(
                "Cierre mensual",
                "El periodo aun no esta listo. Complete el checklist obligatorio y corrija alertas criticas.",
                parent=self,
            )
            return
        period = self.period.get().strip()
        if not messagebox.askyesno(
            "Confirmar cierre",
            f"Va a cerrar el periodo {period}. Despues no se podran crear ni editar asientos en ese periodo.\n\nDesea continuar?",
            parent=self,
        ):
            return
        notes = simpledialog.askstring("Nota final", "Nota final del cierre mensual:", parent=self) or ""
        try:
            result = post_accounting_guided_close_api(period, get_user() or "unknown", notes)
            messagebox.showinfo("Cierre mensual", f"Periodo {result.get('period')} cerrado correctamente.", parent=self)
            self.refresh()
            if hasattr(self.parent, "_refresh_validation_alerts_summary"):
                self.parent._refresh_validation_alerts_summary()
        except Exception as exc:
            messagebox.showerror("Cierre mensual", str(exc), parent=self)

    def _normalize_close_payload(self, data):
        data = dict(data or {})
        checklist = list(data.get("checklist") or [])
        validation = dict(data.get("validation") or {})
        completed = {
            row.get("item_code")
            for row in checklist
            if row.get("status") in {"COMPLETE", "NOT_APPLICABLE"}
        }

        remaining_critical = []
        mitigated = []
        for alert in validation.get("critical") or []:
            checklist_code = self.REVIEW_ALERT_MAP.get(alert.get("code"))
            if checklist_code and checklist_code in completed:
                mitigated.append({
                    **alert,
                    "message": f"{alert.get('message') or ''} Revision completada en checklist.",
                })
            else:
                remaining_critical.append(alert)

        warnings = list(validation.get("warnings") or []) + mitigated
        validation["critical"] = remaining_critical
        validation["warnings"] = warnings
        validation["counts"] = {
            **(validation.get("counts") or {}),
            "critical": len(remaining_critical),
            "warning": len(warnings),
        }
        data["validation"] = validation

        summary = dict(data.get("summary") or {})
        blockers = [
            row for row in checklist
            if row.get("mandatory") and row.get("status") not in {"COMPLETE", "NOT_APPLICABLE"}
        ]
        summary["mandatory_blockers"] = len(blockers)
        summary["critical_alerts"] = len(remaining_critical)
        summary["warning_alerts"] = len(warnings)
        summary["completed"] = len(checklist) - len(blockers)
        summary["total"] = len(checklist)
        data["summary"] = summary
        data["blockers"] = blockers
        data["ready_to_close"] = len(blockers) == 0 and len(remaining_critical) == 0
        return data

    def _open_alerts(self):
        try:
            from Modulos.Finanzas.sections.Accounting.popups.popup_validation_alerts import PopupAccountingValidationAlerts

            PopupAccountingValidationAlerts(self, filters={"period": self.period.get().strip()})
        except Exception as exc:
            messagebox.showerror("Alertas", str(exc), parent=self)
