from tkinter import ttk


try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    Figure = None
    FigureCanvasTkAgg = None
    MATPLOTLIB_AVAILABLE = False


def _safe_number(value):
    try:
        if value is None:
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _safe_text(value):
    text = str(value or "").strip()
    return text or "N/A"


def _fallback_table(parent, title, labels, values):
    title_frame = ttk.Frame(parent)
    title_frame.pack(fill="x", pady=(0, 4))

    ttk.Label(
        title_frame,
        text=f"{title} (tabla)",
        font=("Segoe UI", 11, "bold"),
    ).pack(anchor="w")

    tree = ttk.Treeview(parent, columns=("concepto", "valor"), show="headings", height=min(max(len(labels), 3), 10))
    tree.heading("concepto", text="Concepto")
    tree.heading("valor", text="Valor")
    tree.column("concepto", width=320, anchor="w")
    tree.column("valor", width=140, anchor="e")

    for label, value in zip(labels, values):
        tree.insert("", "end", values=(label, f"{_safe_number(value):,.2f}"))

    tree.pack(fill="x", expand=False)


def render_bar_chart(parent, title, dataset, label_key, value_key, rotate_labels=False):
    dataset = dataset if isinstance(dataset, list) else []
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=10)

    labels = []
    values = []
    for row in dataset:
        if not isinstance(row, dict):
            continue
        labels.append(_safe_text(row.get(label_key)))
        values.append(_safe_number(row.get(value_key)))

    if not labels:
        ttk.Label(frame, text=f"{title}: sin datos").pack(anchor="w")
        return

    if not MATPLOTLIB_AVAILABLE:
        _fallback_table(frame, title, labels, values)
        return

    fig = Figure(figsize=(10, 4), dpi=100)
    ax = fig.add_subplot(111)
    ax.bar(labels, values)

    if rotate_labels:
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")

    ax.set_title(title)
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)


def render_pie_chart(parent, title, dataset, label_key, value_key):
    dataset = dataset if isinstance(dataset, list) else []
    frame = ttk.Frame(parent)
    frame.pack(fill="x", pady=10)

    labels = []
    values = []
    for row in dataset:
        if not isinstance(row, dict):
            continue
        labels.append(_safe_text(row.get(label_key)))
        values.append(_safe_number(row.get(value_key)))

    if not labels:
        ttk.Label(frame, text=f"{title}: sin datos").pack(anchor="w")
        return

    if not MATPLOTLIB_AVAILABLE:
        _fallback_table(frame, title, labels, values)
        return

    fig = Figure(figsize=(9, 4), dpi=100)
    ax = fig.add_subplot(111)
    ax.pie(values, labels=labels, autopct="%1.1f%%")
    ax.set_title(title)
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)
