import threading
import tkinter as tk
from tkinter import messagebox, ttk

from api_client import (
    ask_portia_api,
    get_portia_context_api,
    get_portia_suggestions_api,
)

try:
    from backend_api.ai.som_portia import answer_som_portia
    from backend_api.ai.som_portia_knowledge import PORTIA_SUGGESTED_QUESTIONS
except Exception:
    answer_som_portia = None
    PORTIA_SUGGESTED_QUESTIONS = [
        "Resume el estado financiero actual.",
        "Que servicios estan listos para facturar?",
        "Que puertos concentran mayor actividad?",
    ]


NAVY = "#003A75"
BLUE = "#0B5CAD"
CYAN = "#0AA2C0"
BG = "#F3F6FA"
CARD = "#FFFFFF"
BORDER = "#D8E0EA"
TEXT = "#172033"
MUTED = "#667085"


class PortiaUI(tk.Frame):
    def __init__(self, parent, usuario=None, rol=None, on_back=None):
        super().__init__(parent, bg=BG)
        self.parent = parent
        self.usuario = usuario
        self.rol = rol
        self.on_back = on_back
        self.context = {}
        self.scope_var = tk.StringVar(value="Datos ERP")

        self.pack(fill="both", expand=True)
        self._build_ui()
        self._load_initial_data()

    def _card(self, parent):
        frame = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        return frame

    def _button(self, parent, text, command, bg=BLUE):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg="white",
            activebackground=NAVY,
            activeforeground="white",
            relief="flat",
            padx=14,
            pady=7,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )

    def _build_ui(self):
        header = tk.Frame(self, bg=NAVY, height=74)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_box = tk.Frame(header, bg=NAVY)
        title_box.pack(side="left", padx=22, pady=10)

        tk.Label(
            title_box,
            text="PORTIA SOM",
            bg=NAVY,
            fg="white",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text="Consultas ejecutivas sobre finanzas, comercial, servicios, puertos e informes",
            bg=NAVY,
            fg="#D9ECFF",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        actions = tk.Frame(header, bg=NAVY)
        actions.pack(side="right", padx=16)
        self._button(actions, "Actualizar contexto", self._load_context, CYAN).pack(side="right", padx=4)
        if self.on_back:
            self._button(actions, "Volver", self.on_back, "#40617F").pack(side="right", padx=4)

        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=18, pady=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(1, weight=1)

        self.context_cards = tk.Frame(main, bg=BG)
        self.context_cards.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        left = self._card(main)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        right = self._card(main)
        right.grid(row=1, column=1, sticky="nsew")

        self._build_left(left)
        self._build_right(right)

    def _build_left(self, parent):
        tk.Label(
            parent,
            text="Consultas sugeridas",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        self.suggestions_frame = tk.Frame(parent, bg=CARD)
        self.suggestions_frame.pack(fill="x", padx=12)

        tk.Label(
            parent,
            text="PORTIA no modifica datos. Solo consulta, resume y orienta.",
            bg=CARD,
            fg=MUTED,
            wraplength=380,
            justify="left",
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.status_var = tk.StringVar(value="Listo")
        tk.Label(
            parent,
            textvariable=self.status_var,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=14, pady=(0, 12))

    def _build_right(self, parent):
        top = tk.Frame(parent, bg=CARD)
        top.pack(fill="x", padx=14, pady=(12, 8))

        tk.Label(
            top,
            text="Pregunta",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(side="left")

        self.ask_button = self._button(top, "Preguntar", self._ask_portia)
        self.ask_button.pack(side="right")

        scope_box = tk.Frame(parent, bg=CARD)
        scope_box.pack(fill="x", padx=14, pady=(0, 8))
        tk.Label(
            scope_box,
            text="Alcance",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 8))
        self.scope_combo = ttk.Combobox(
            scope_box,
            textvariable=self.scope_var,
            values=("Datos ERP", "Manual Q&A SOM", "Pregunta general"),
            state="readonly",
            width=22,
            font=("Segoe UI", 9),
        )
        self.scope_combo.pack(side="left")
        tk.Label(
            scope_box,
            text="Datos ERP consulta base de datos; General responde tipo asistente sin modificar datos.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="left", padx=12)

        question_wrap = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        question_wrap.pack(fill="x", padx=14)

        self.question_text = tk.Text(
            question_wrap,
            height=4,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            bg="white",
            fg=TEXT,
            padx=10,
            pady=8,
        )
        self.question_text.pack(fill="x")

        tk.Label(
            parent,
            text="Respuesta de PORTIA",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=14, pady=(14, 8))

        answer_wrap = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        answer_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.answer_text = tk.Text(
            answer_wrap,
            wrap="word",
            font=("Segoe UI", 10),
            relief="flat",
            bg="white",
            fg=TEXT,
            padx=12,
            pady=10,
        )
        self.answer_text.pack(fill="both", expand=True)
        self.answer_text.configure(state="disabled")

    def _load_initial_data(self):
        self._render_suggestions(PORTIA_SUGGESTED_QUESTIONS)
        threading.Thread(target=self._load_initial_worker, daemon=True).start()

    def _load_initial_worker(self):
        try:
            suggestions = get_portia_suggestions_api().get("data", []) or PORTIA_SUGGESTED_QUESTIONS
        except Exception:
            suggestions = PORTIA_SUGGESTED_QUESTIONS

        try:
            context = get_portia_context_api().get("data", {})
        except Exception:
            context = {}

        self.after(0, lambda: self._apply_initial_data(suggestions, context))

    def _apply_initial_data(self, suggestions, context):
        self._render_suggestions(suggestions)
        self.context = context or {}
        self._render_context_cards()
        self.status_var.set("Listo")

    def _render_suggestions(self, suggestions):
        for widget in self.suggestions_frame.winfo_children():
            widget.destroy()

        for question in suggestions[:10]:
            btn = tk.Button(
                self.suggestions_frame,
                text=question,
                command=lambda q=question: self._set_question(q),
                anchor="w",
                justify="left",
                bg="#F7FAFC",
                fg=TEXT,
                activebackground="#E6F2FF",
                relief="flat",
                padx=10,
                pady=8,
                wraplength=390,
                cursor="hand2",
            )
            btn.pack(fill="x", pady=3)

    def _render_context_cards(self):
        for widget in self.context_cards.winfo_children():
            widget.destroy()

        items = [
            ("Servicios finalizados", self.context.get("servicios", {}).get("finalizados")),
            ("Pendientes factura", self.context.get("servicios", {}).get("pendientes_factura")),
            ("Cuentas por cobrar", self.context.get("finanzas", {}).get("cuentas_por_cobrar")),
            ("Cotizaciones aprobadas", self.context.get("comercial", {}).get("cotizaciones_aprobadas")),
            ("Puertos", self.context.get("master_data", {}).get("puertos")),
        ]

        for title, value in items:
            card = tk.Frame(self.context_cards, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(card, text=title, bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(8, 2))
            tk.Label(card, text=self._format_value(value), bg=CARD, fg=NAVY, font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=(0, 8))

    def _format_value(self, value):
        if value is None:
            return "N/D"
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, int):
            return f"{value:,}"
        return str(value)

    def _load_context(self):
        self.status_var.set("Actualizando contexto...")
        threading.Thread(target=self._load_context_worker, daemon=True).start()

    def _load_context_worker(self):
        try:
            context = get_portia_context_api().get("data", {})
            self.after(0, lambda: self._apply_context(context))
        except Exception as exc:
            self.after(0, lambda: self._show_error("PORTIA", exc, popup=False))

    def _apply_context(self, context):
        self.context = context or {}
        self._render_context_cards()
        self.status_var.set("Contexto actualizado")

    def _set_question(self, value):
        self.question_text.delete("1.0", "end")
        self.question_text.insert("1.0", value)

    def _ask_portia(self):
        question = self.question_text.get("1.0", "end").strip()
        if not question:
            messagebox.showwarning("PORTIA", "Escribe una pregunta para PORTIA.")
            return

        self.ask_button.configure(state="disabled")
        self.status_var.set("Consultando PORTIA...")
        self._set_answer("PORTIA esta analizando la consulta...")
        scope = self._scope_code()
        threading.Thread(target=self._ask_worker, args=(question, scope), daemon=True).start()

    def _scope_code(self):
        selected = self.scope_var.get()
        if selected == "Pregunta general":
            return "general_chat"
        if selected == "Manual Q&A SOM":
            return "qa"
        return "erp"

    def _ask_worker(self, question, scope):
        try:
            response = ask_portia_api(question, scope=scope)
            if not isinstance(response, dict) or not str(response.get("answer") or "").strip():
                raise ValueError("Respuesta remota PORTIA sin answer.")
            self.after(0, lambda: self._apply_answer(response))
        except Exception:
            if answer_som_portia:
                response = answer_som_portia(question, self.context or {}, [], scope=scope)
                self.after(0, lambda: self._apply_answer(response))
            else:
                self.after(0, lambda: self._set_answer("PORTIA no pudo conectarse al backend."))
        finally:
            self.after(0, lambda: self.ask_button.configure(state="normal"))

    def _apply_answer(self, response):
        answer = str(response.get("answer") or "").strip()
        if not answer and answer_som_portia:
            question = self.question_text.get("1.0", "end").strip()
            fallback = answer_som_portia(question, self.context or {}, [], scope=self._scope_code())
            answer = fallback.get("answer") or "PORTIA no devolvio respuesta."
            response = fallback
        elif not answer:
            answer = "PORTIA no devolvio respuesta."
        mode = response.get("mode") or "local"
        self._set_answer(answer)
        self.status_var.set(f"Respuesta generada ({mode})")
        if response.get("context"):
            self.context = response.get("context") or {}
            self._render_context_cards()

    def _set_answer(self, value):
        self.answer_text.configure(state="normal")
        self.answer_text.delete("1.0", "end")
        self.answer_text.insert("1.0", value)
        self.answer_text.configure(state="disabled")

    def _show_error(self, title, exc, popup=True):
        self.status_var.set("No se pudo conectar al backend; usando datos locales.")
        if popup:
            messagebox.showerror(title, str(exc))
