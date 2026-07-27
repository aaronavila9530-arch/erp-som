import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from api_client import post_accounting_ai_analysis_api


class PopupAccountingAI(tk.Toplevel):
    def __init__(self, parent, filters=None):
        super().__init__(parent)
        self.filters = filters or {}
        self.result = None
        self.title("IA contable")
        self.geometry("1120x720")
        self.transient(parent)
        self.grab_set()
        self._build_ui()

    def _build_ui(self):
        header = ttk.Frame(self, padding=10)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="IA contable para sugerencias y explicacion de diferencias",
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        ttk.Button(header, text="Cerrar", command=self.destroy).pack(side="right")
        ttk.Button(header, text="Copiar resultado", command=self._copy_result).pack(side="right", padx=6)

        scope = ttk.LabelFrame(self, text="Alcance del analisis", padding=10)
        scope.pack(fill="x", padx=10, pady=(0, 8))

        scope_text = self._scope_text()
        ttk.Label(scope, text=scope_text).pack(anchor="w")

        options = ttk.Frame(scope)
        options.pack(fill="x", pady=(8, 0))
        ttk.Label(options, text="Idioma").pack(side="left")
        self.language_var = tk.StringVar(value="ES")
        ttk.Combobox(
            options,
            values=("ES", "EN"),
            textvariable=self.language_var,
            state="readonly",
            width=8,
        ).pack(side="left", padx=(6, 18))

        ttk.Button(options, text="Analizar con IA", command=self._run).pack(side="left")

        question_frame = ttk.LabelFrame(self, text="Pregunta o enfoque", padding=10)
        question_frame.pack(fill="x", padx=10, pady=(0, 8))
        self.question = tk.Text(question_frame, height=4, wrap="word")
        self.question.pack(fill="x")
        self.question.insert(
            "1.0",
            "Explica las diferencias contables, riesgos de cierre y sugiere que revisar antes de aprobar o cerrar el periodo.",
        )

        self.status_var = tk.StringVar(value="Listo para analizar.")
        ttk.Label(self, textvariable=self.status_var).pack(anchor="w", padx=12)

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        result_frame = ttk.LabelFrame(body, text="Analisis")
        body.add(result_frame, weight=3)
        self.output = tk.Text(result_frame, wrap="word")
        out_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=out_scroll.set)
        self.output.pack(side="left", fill="both", expand=True)
        out_scroll.pack(side="right", fill="y")

        context_frame = ttk.LabelFrame(body, text="Contexto usado")
        body.add(context_frame, weight=2)
        self.context_text = tk.Text(context_frame, wrap="none")
        ctx_y = ttk.Scrollbar(context_frame, orient="vertical", command=self.context_text.yview)
        ctx_x = ttk.Scrollbar(context_frame, orient="horizontal", command=self.context_text.xview)
        self.context_text.configure(yscrollcommand=ctx_y.set, xscrollcommand=ctx_x.set)
        self.context_text.grid(row=0, column=0, sticky="nsew")
        ctx_y.grid(row=0, column=1, sticky="ns")
        ctx_x.grid(row=1, column=0, sticky="ew")
        context_frame.rowconfigure(0, weight=1)
        context_frame.columnconfigure(0, weight=1)

    def _scope_text(self):
        if self.filters.get("period"):
            period = self.filters.get("period")
            return f"Periodo: {period} | Origen: {self.filters.get('origin') or 'TODOS'}"
        return (
            f"Rango: {self.filters.get('period_from') or 'inicio'} a "
            f"{self.filters.get('period_to') or 'fin'} | Origen: {self.filters.get('origin') or 'TODOS'}"
        )

    def _run(self):
        self.status_var.set("Analizando datos contables...")
        self.output.delete("1.0", "end")
        self.context_text.delete("1.0", "end")
        payload = dict(self.filters)
        payload["language"] = self.language_var.get()
        payload["question"] = self.question.get("1.0", "end").strip()
        threading.Thread(target=self._worker, args=(payload,), daemon=True).start()

    def _worker(self, payload):
        try:
            data = post_accounting_ai_analysis_api(payload)
            self.after(0, lambda: self._render(data))
        except Exception as exc:
            self.after(0, lambda: self._show_error(exc))

    def _render(self, data):
        self.result = data
        mode = data.get("mode") or "ai"
        self.status_var.set(f"Analisis completado. Modo: {mode}.")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", data.get("analysis") or "Sin analisis disponible.")
        self.context_text.delete("1.0", "end")
        self.context_text.insert(
            "1.0",
            json.dumps(data.get("context") or {}, indent=2, ensure_ascii=False, default=str),
        )

    def _show_error(self, exc):
        self.status_var.set("No se pudo completar el analisis.")
        messagebox.showerror("IA contable", f"No se pudo analizar:\n{exc}", parent=self)

    def _copy_result(self):
        text = self.output.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("IA contable", "No hay resultado para copiar.", parent=self)
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Resultado copiado al portapapeles.")
