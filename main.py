"""Desktop interface for the bank-credit simulator."""

from __future__ import annotations

from collections.abc import Callable
import csv
import math
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from finance import (
    ExtraPayment,
    LoanConfig,
    SimulationResult,
    recommend_loans,
    simulate,
    validate_compatibility,
)


FONT = "Trebuchet MS"
NAVY = "#12243A"
BLUE = "#2864DC"
TEAL = "#12A88A"
INK = "#172B43"
MUTED = "#6F8094"
PAPER = "#F3F6FA"
WHITE = "#FFFFFF"
LINE = "#E1E8F0"
ORANGE = "#E79A32"


def _rounded_points(width: int, height: int) -> list[float]:
    width = max(width, 18)
    height = max(height, 18)
    radius = min(9, width / 2, height / 2)
    points: list[float] = []
    corners = (
        (width - radius, radius, -90),
        (width - radius, height - radius, 0),
        (radius, height - radius, 90),
        (radius, radius, 180),
    )
    for center_x, center_y, start_angle in corners:
        for step in range(5):
            angle = math.radians(start_angle + step * 22.5)
            points.extend((
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
            ))
    return points


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        master: tk.Misc,
        text: str,
        command: Callable[[], object],
        background: str,
        style: str = "TButton",
    ) -> None:
        fill = BLUE if style == "Primary.TButton" else "#E7EDF5"
        super().__init__(
            master, width=90, height=50, background=background,
            highlightthickness=0,
        )
        self.border = self.create_polygon(
            *_rounded_points(90, 50), fill=fill, outline=fill, width=1,
        )
        self.button = ttk.Button(self, text=text, command=command, style=style)
        self.window = self.create_window(8, 4, anchor="nw", window=self.button)
        self._fit_width()
        self.bind("<Configure>", self._resize)

    def _resize(self, event: tk.Event) -> None:
        self.coords(self.border, *_rounded_points(event.width - 1, event.height - 1))
        self.coords(self.window, 8, 4)
        self.itemconfigure(
            self.window, width=max(1, event.width - 16), height=max(1, event.height - 8),
        )

    def set_text(self, text: str) -> None:
        self.button.configure(text=text)
        self._fit_width()

    def _fit_width(self) -> None:
        self.configure(width=max(90, self.button.winfo_reqwidth() + 16))

    def invoke(self) -> str | None:
        return self.button.invoke()


class ScrollableFrame(ttk.Frame):
    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master)
        self.canvas = tk.Canvas(self, background=PAPER, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = ttk.Frame(self.canvas, style="Page.TFrame")
        self.window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.content.bind("<Configure>", lambda _event: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        ))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(
            self.window, width=event.width
        ))
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(self, event: tk.Event) -> str | None:
        widget = event.widget
        if isinstance(widget, (ttk.Treeview, ttk.Combobox)):
            return None
        if not self.canvas.winfo_ismapped():
            return None
        left = self.canvas.winfo_rootx()
        top = self.canvas.winfo_rooty()
        if not (
            left <= event.x_root < left + self.canvas.winfo_width()
            and top <= event.y_root < top + self.canvas.winfo_height()
        ):
            return None
        number = getattr(event, "num", None)
        if number == 4:
            units = -1
        elif number == 5:
            units = 1
        else:
            delta = getattr(event, "delta", 0)
            units = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
        self.canvas.yview_scroll(units, "units")
        return "break"


class CreditSimulator(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CrediCalc | Simulador de crédito")
        self.geometry("1240x820")
        self.minsize(860, 600)
        self.resizable(True, True)
        self.configure(background=PAPER)
        self.result: SimulationResult | None = None
        self._vars: dict[str, tk.StringVar] = {}
        self._controls: dict[str, ttk.Widget] = {}
        self._field_frames: dict[str, ttk.Frame] = {}
        self._field_hints: dict[str, ttk.Label] = {}
        self._build_style()
        self._build_shell()
        self._build_profile_page()
        self._build_loan_page()
        self._build_results_page()
        self.show_page("Perfil")

    def _show_about(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Acerca de CrediCalc")
        dialog.configure(background=WHITE)
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        card = ttk.Frame(dialog, style="Card.TFrame", padding=26)
        card.pack(fill="both", expand=True)
        ttk.Label(card, text="CREDICALC", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(
            card, text="Universidad Distrital Francisco José de Caldas",
            style="Section.TLabel", wraplength=390,
        ).pack(anchor="w", pady=(12, 3))
        ttk.Label(card, text="Proyecto académico — 2026", style="Muted.TLabel").pack(
            anchor="w", pady=(0, 16)
        )
        ttk.Label(card, text="Integrantes", style="Section.TLabel").pack(anchor="w", pady=(0, 7))
        members = ttk.Frame(card, style="Card.TFrame")
        members.pack(fill="x")
        for name, student_id in (
            ("Harold Mateus", "202626780XX"),
            ("Santiago Castiblanco", "202626780XX"),
            ("Erick Lemus", "20262678012"),
            ("Camilo Ocampo", "20262678061"),
        ):
            row = ttk.Frame(members, style="Page.TFrame", padding=(10, 7))
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=name, style="MemberName.TLabel").pack(side="left")
            ttk.Label(row, text=student_id, style="MemberId.TLabel").pack(side="right")
        self._rounded_button(
            card, text="Cerrar", command=dialog.destroy, style="Primary.TButton",
        ).pack(anchor="e", pady=(20, 0))
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def _build_style(self) -> None:
        style = ttk.Style(self)
        self.style = style
        style.theme_use("clam")
        style.configure(".", font=(FONT, 10), foreground=INK)
        style.configure("Page.TFrame", background=PAPER)
        style.configure("Card.TFrame", background=WHITE)
        style.configure("TLabel", background=PAPER, foreground=INK)
        style.configure("Muted.TLabel", background=WHITE, foreground=MUTED)
        style.configure("Heading.TLabel", font=(FONT, 18, "bold"), background=PAPER, foreground=INK)
        style.configure("Section.TLabel", font=(FONT, 12, "bold"), background=WHITE, foreground=INK)
        style.configure("CardTitle.TLabel", font=(FONT, 9, "bold"), background=WHITE, foreground=MUTED)
        style.configure("CardValue.TLabel", font=(FONT, 19, "bold"), background=WHITE, foreground=INK)
        style.configure("MemberName.TLabel", font=(FONT, 10, "bold"), background="#F3F6FA", foreground=INK)
        style.configure("MemberId.TLabel", font=(FONT, 9), background="#F3F6FA", foreground=MUTED)
        style.configure("TEntry", padding=(7, 2), fieldbackground=WHITE, borderwidth=0, relief="flat")
        style.configure("TCombobox", padding=(6, 2), fieldbackground=WHITE, borderwidth=0, relief="flat")
        style.configure("TButton", padding=(11, 7), background="#E7EDF5", foreground=INK,
                        borderwidth=1, relief="flat")
        style.map("TButton", background=[("active", "#D9E3F0")])
        style.configure("Primary.TButton", padding=(13, 8), background=BLUE, foreground=WHITE,
                        font=(FONT, 10, "bold"), borderwidth=0, relief="flat")
        style.map("Primary.TButton", background=[("active", "#1D50B8")])
        style.configure("Treeview", rowheight=30, background=WHITE, fieldbackground=WHITE, borderwidth=0)
        style.configure("Treeview.Heading", font=(FONT, 9, "bold"), background="#EAF0F7",
                        foreground=INK, padding=8)
        style.configure("TNotebook", background=PAPER, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(17, 9), font=(FONT, 10, "bold"))

    def _build_shell(self) -> None:
        self.sidebar = tk.Frame(self, background=NAVY, width=230)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        brand = tk.Frame(self.sidebar, background=NAVY)
        brand.pack(fill="x", padx=23, pady=(27, 38))
        tk.Label(brand, text="C", font=(FONT, 16, "bold"), fg=WHITE, bg=BLUE,
                 width=2, height=1).pack(side="left", padx=(0, 11))
        tk.Label(brand, text="CREDICALC", font=(FONT, 14, "bold"), fg=WHITE,
                 bg=NAVY).pack(side="left")
        tk.Label(brand, text="SIMULADOR FINANCIERO", font=(FONT, 9),
                 fg="#9FB2C8", bg=NAVY).pack(anchor="w", padx=(48, 0), pady=(2, 0))

        tk.Label(self.sidebar, text="TU SIMULACIÓN", font=(FONT, 9, "bold"),
                 fg="#91A5BC", bg=NAVY).pack(anchor="w", padx=24, pady=(0, 11))
        self.nav_buttons: dict[str, tk.Button] = {}
        for label, icon in (("Perfil", "01"), ("Crédito", "02"), ("Resultados", "03")):
            button = tk.Button(
                self.sidebar, text=f"   {icon}     {label}", anchor="w", relief="flat",
                borderwidth=0, font=(FONT, 10, "bold"), cursor="hand2",
                padx=12, pady=12, fg="#CBD7E4", bg=NAVY, activebackground="#223B58",
                activeforeground=WHITE, command=lambda page=label: self.show_page(page),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[label] = button
        tk.Frame(self.sidebar, bg="#2C4057", height=1).pack(fill="x", padx=22, pady=(25, 16))
        tk.Label(self.sidebar, text="SIMULACIÓN ACADÉMICA\nNo representa una oferta bancaria.",
                 justify="left", wraplength=175, font=(FONT, 9),
                 fg="#91A5BC", bg=NAVY).pack(
                     anchor="w", padx=24
                 )
        tk.Button(
            self.sidebar, text="ⓘ  Acerca del proyecto", anchor="w", relief="flat",
            borderwidth=0, font=(FONT, 9), cursor="hand2", padx=12, pady=9,
            fg="#CBD7E4", bg=NAVY, activebackground="#223B58", activeforeground=WHITE,
            command=self._show_about,
        ).pack(side="bottom", fill="x", padx=12, pady=(0, 18))
        self.body = tk.Frame(self, background=PAPER)
        self.body.pack(side="left", fill="both", expand=True)
        header = tk.Frame(self.body, background=WHITE, height=72)
        header.pack(fill="x")
        header.pack_propagate(False)
        self.page_title = tk.Label(header, text="", font=(FONT, 15, "bold"),
                                   fg=INK, bg=WHITE)
        self.page_title.pack(side="left", padx=29)
        tk.Label(header, text="●  SIN CONEXIÓN  ·  Datos solo en este equipo",
                 font=(FONT, 9), fg=MUTED, bg=WHITE).pack(side="right", padx=28)
        self.pages: dict[str, ttk.Frame] = {}
        self.page_host = ttk.Frame(self.body, style="Page.TFrame")
        self.page_host.pack(fill="both", expand=True)

    def _register_page(self, name: str, frame: ttk.Frame) -> None:
        self.pages[name] = frame

    def show_page(self, name: str) -> None:
        if name == "Resultados" and self.result is None:
            return
        for page in self.pages.values():
            page.pack_forget()
        self.pages[name].pack(fill="both", expand=True)
        self.page_title.configure(text={
            "Perfil": "Cuéntanos un poco de ti",
            "Crédito": "Diseña tu escenario de crédito",
            "Resultados": "Tu simulación, en detalle",
        }[name])
        for label, button in self.nav_buttons.items():
            button.configure(bg="#223B58" if label == name else NAVY,
                             fg=WHITE if label == name else "#CBD7E4")

    def _card(self, parent: tk.Misc, padding: int = 20) -> ttk.Frame:
        frame = ttk.Frame(parent, style="Card.TFrame", padding=padding)
        frame.configure(relief="flat")
        return frame

    def _rounded_button(
        self,
        parent: tk.Misc,
        text: str,
        command: Callable[[], object],
        style: str = "TButton",
    ) -> RoundedButton:
        parent_style = parent.cget("style") if isinstance(parent, ttk.Widget) else "TFrame"
        background = self.style.lookup(parent_style or "TFrame", "background") or WHITE
        return RoundedButton(parent, text, command, background, style)

    def _section(self, parent: tk.Misc, title: str, subtitle: str | None = None) -> ttk.Frame:
        card = self._card(parent)
        card.pack(fill="x", padx=28, pady=(22, 0))
        ttk.Label(card, text=title, style="Section.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(card, text=subtitle, style="Muted.TLabel", wraplength=850).pack(
                anchor="w", pady=(5, 14)
            )
        else:
            ttk.Label(card, text=" ", style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
        return card

    def _field(self, parent: tk.Misc, label: str, key: str, default: str = "",
               width: int = 28, hint: str | None = None) -> ttk.Entry:
        holder = ttk.Frame(parent, style="Card.TFrame")
        holder.pack(fill="x", padx=8, pady=7)
        self._field_frames[key] = holder
        ttk.Label(holder, text=label, style="Muted.TLabel").pack(anchor="w")
        variable = tk.StringVar(value=default)
        self._vars[key] = variable
        _, entry = self._place_rounded_control(
            holder,
            lambda parent: ttk.Entry(parent, textvariable=variable, width=width),
        )
        self._controls[key] = entry
        if hint:
            hint_label = ttk.Label(holder, text=hint, style="Muted.TLabel", font=(FONT, 9))
            hint_label.pack(anchor="w", pady=(3, 0))
            self._field_hints[key] = hint_label
        return entry

    def _choice(self, parent: tk.Misc, label: str, key: str, values: tuple[str, ...],
                default: str) -> ttk.Combobox:
        holder = ttk.Frame(parent, style="Card.TFrame")
        holder.pack(fill="x", padx=8, pady=7)
        ttk.Label(holder, text=label, style="Muted.TLabel").pack(anchor="w")
        variable = tk.StringVar(value=default)
        self._vars[key] = variable
        _, combo = self._place_rounded_control(
            holder,
            lambda parent: ttk.Combobox(
                parent, textvariable=variable, values=values, state="readonly",
            ),
        )
        self._controls[key] = combo
        return combo

    def _place_rounded_control(
        self,
        parent: ttk.Frame,
        create_control: Callable[[tk.Canvas], ttk.Widget],
    ) -> tuple[tk.Canvas, ttk.Widget]:
        surface = tk.Canvas(parent, height=44, background=WHITE, highlightthickness=0)
        surface.pack(fill="x", pady=(5, 0))
        border = surface.create_polygon(0, 0, 0, 0, fill=WHITE, outline="#D5DFEA", width=1)
        control = create_control(surface)
        window = surface.create_window(7, 4, anchor="nw", window=control)

        def resize(event: tk.Event) -> None:
            width = max(event.width, 18)
            height = max(event.height, 18)
            surface.coords(border, *_rounded_points(event.width, event.height))
            surface.coords(window, 7, 4)
            surface.itemconfigure(window, width=max(1, width - 14), height=max(1, height - 8))

        surface.bind("<Configure>", resize)
        return surface, control

    def _two_columns(self, card: ttk.Frame) -> tuple[ttk.Frame, ttk.Frame]:
        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x")
        left = ttk.Frame(row, style="Card.TFrame")
        right = ttk.Frame(row, style="Card.TFrame")

        layout_state: dict[str, bool | None] = {"narrow": None}

        def resize(event: tk.Event) -> None:
            narrow = event.width < 720
            if layout_state["narrow"] == narrow:
                return
            left.pack_forget()
            right.pack_forget()
            if narrow:
                left.pack(fill="x")
                right.pack(fill="x")
            else:
                left.pack(side="left", fill="x", expand=True, padx=(0, 14))
                right.pack(side="left", fill="x", expand=True, padx=(14, 0))
            layout_state["narrow"] = narrow

        row.bind("<Configure>", resize)
        return left, right

    def _build_profile_page(self) -> None:
        page = ScrollableFrame(self.page_host)
        self._register_page("Perfil", page)
        intro = ttk.Frame(page.content, style="Page.TFrame")
        intro.pack(fill="x", padx=30, pady=(25, 0))
        ttk.Label(intro, text="Una simulación que parte de tu realidad.",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(intro, text="Usaremos estos datos solo para contextualizar tu capacidad de pago.",
                  foreground=MUTED).pack(anchor="w", pady=(5, 0))
        institution = self._card(page.content, padding=12)
        institution.pack(fill="x", padx=28, pady=(12, 0))
        institution_header = ttk.Frame(institution, style="Card.TFrame")
        institution_header.pack(fill="x")
        ttk.Label(
            institution_header,
            text="Universidad Distrital Francisco José de Caldas",
            style="Section.TLabel",
        ).pack(side="left")
        ttk.Label(
            institution_header, text="Proyecto académico — 2026", style="Muted.TLabel",
        ).pack(side="right")
        members = ttk.Frame(institution, style="Card.TFrame")
        members.pack(fill="x", pady=(7, 0))
        for column in range(2):
            members.columnconfigure(column, weight=1)
        for index, (name, student_id) in enumerate((
            ("Harold Mateus", "202626780XX"),
            ("Santiago Castiblanco", "202626780XX"),
            ("Erick Lemus", "20262678012"),
            ("Camilo Ocampo", "20262678061"),
        )):
            row = ttk.Frame(members, style="Page.TFrame", padding=(8, 4))
            row.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=2)
            ttk.Label(row, text=name, style="MemberName.TLabel").pack(side="left")
            ttk.Label(row, text=student_id, style="MemberId.TLabel").pack(side="right")

        card = self._section(page.content, "Tu información", "Los campos son orientativos; no se realiza una evaluación crediticia.")
        left, right = self._two_columns(card)
        self._field(left, "Edad", "age", "30")
        self._field(right, "Ocupación o actividad laboral", "occupation", "Empleado")
        self._field(left, "Ingresos mensuales", "income", "4500000", hint="En pesos colombianos (COP).")
        self._field(right, "Gastos mensuales (opcional)", "expenses", "1800000", hint="Para estimar el ingreso disponible.")
        buttons = ttk.Frame(page.content, style="Page.TFrame")
        buttons.pack(fill="x", padx=28, pady=22)
        self._rounded_button(
            buttons, text="Continuar a configurar el crédito  →",
            command=lambda: self.show_page("Crédito"), style="Primary.TButton",
        ).pack(side="right")

    def _build_loan_page(self) -> None:
        page = ScrollableFrame(self.page_host)
        self._register_page("Crédito", page)
        intro = ttk.Frame(page.content, style="Page.TFrame")
        intro.pack(fill="x", padx=30, pady=(25, 0))
        ttk.Label(intro, text="Ajusta cada condición a tu escenario.",
                  style="Heading.TLabel").pack(anchor="w")
        ttk.Label(intro, text="Las tasas se interpretan como efectivas. EA se convierte matemáticamente a cada periodo.",
                  foreground=MUTED).pack(anchor="w", pady=(5, 0))

        basic = self._section(page.content, "01  ·  Parámetros del préstamo")
        left, right = self._two_columns(basic)
        self._field(left, "Monto solicitado (COP)", "principal", "25000000")
        self._field(right, "Plazo total (periodos)", "periods", "24")
        self._field(left, "Tasa de referencia (%)", "rate", "18")
        self._choice(right, "Unidad de la tasa", "rate_unit",
                     ("Efectiva anual (EA)", "Efectiva mensual (EM)", "Efectiva por periodo (EP)"),
                     "Efectiva anual (EA)")

        terms = self._section(page.content, "02  ·  Estructura de pago")
        left, right = self._two_columns(terms)
        self._choice(right, "Periodicidad", "frequency", (
            "Mensual", "Bimestral", "Trimestral", "Cuatrimestral", "Semestral", "Anual",
        ), "Mensual")
        ttk.Label(
            terms, text="Configuración inicial: cuota fija con pago vencido.",
            style="Muted.TLabel",
        ).pack(anchor="w", padx=8, pady=(8, 0))
        self.compatibility_label = ttk.Label(
            terms, text="", style="Muted.TLabel", wraplength=860,
        )
        self.compatibility_label.pack(anchor="w", padx=8, pady=(8, 0))

        self.advanced_toggle = self._rounded_button(
            page.content, text="＋  Ajustes avanzados", command=self._toggle_advanced,
        )
        self.advanced_toggle.pack(fill="x", padx=28, pady=(18, 0))
        self.advanced_frame = ttk.Frame(page.content, style="Page.TFrame")
        self.advanced_visible = False

        mode_section = self._section(
            self.advanced_frame, "03  ·  Modalidad y momento del pago",
            "Las configuraciones especiales se restablecen al cerrar Ajustes avanzados.",
        )
        left, right = self._two_columns(mode_section)
        self._choice(left, "Modalidad de amortización", "amortization", (
            "Cuota fija", "Abono a capital fijo", "Cuota creciente",
            "Cuota decreciente personalizada", "Pago único",
        ), "Cuota fija")
        self._choice(right, "Momento del pago", "moment", ("Vencido", "Anticipado"), "Vencido")

        grace_section = self._section(
            self.advanced_frame, "04  ·  Diferimiento y cuotas especiales",
            "La primera cuota diferida y la gracia total capitalizan intereses; la gracia de capital paga intereses sin amortizar.",
        )
        left, right = self._two_columns(grace_section)
        self._choice(left, "Periodo de gracia", "grace", (
            "Sin diferimiento", "Gracia de capital", "Gracia total",
        ), "Sin diferimiento")
        self._field(left, "Periodos de gracia o diferimiento", "grace_periods", "0",
                    hint="Se aplica cuando seleccionas una opción de gracia.")
        self._field(right, "Crecimiento o disminución por cuota (%)", "growth", "2",
                    hint="Se usa en cuotas crecientes o decrecientes.")

        rates = self._section(self.advanced_frame, "05  ·  Comportamiento de las tasas",
                              "Define una tasa fija o una tasa escalonada programada. Formato: periodo:porcentaje; por ejemplo, 7:20;13:22.")
        left, right = self._two_columns(rates)
        self._choice(left, "Tipo de tasa", "rate_type",
                     ("Fija", "Escalonada"), "Fija")
        self._field(right, "Cambios de tasa (opcional)", "rate_changes", "",
                    hint="El porcentaje usa la misma unidad elegida arriba.")

        extras = self._section(self.advanced_frame, "06  ·  Pagos extraordinarios",
                               "Puedes agregar varios abonos indicando periodo:monto, separados por punto y coma.")
        left, right = self._two_columns(extras)
        self._field(left, "Abonos extraordinarios", "extras", "",
                    hint="Ejemplo: 6:1000000;12:500000.")
        self._choice(right, "Efecto de los abonos", "extra_strategy",
                     ("Reducir plazo", "Reducir cuota"), "Reducir plazo")
        self.compatibility_note = ttk.Label(
            extras, text="", style="Muted.TLabel", wraplength=860,
        )
        self.compatibility_note.pack(anchor="w", padx=8, pady=(8, 0))

        buttons = ttk.Frame(page.content, style="Page.TFrame")
        buttons.pack(fill="x", padx=28, pady=22)
        self.loan_buttons = buttons
        self._rounded_button(
            buttons, text="← Volver al perfil", command=lambda: self.show_page("Perfil"),
        ).pack(side="left")
        self._rounded_button(
            buttons, text="Calcular simulación  →", style="Primary.TButton",
            command=self._run_simulation,
        ).pack(side="right")

        self._vars["grace"].trace_add("write", lambda *_: self._update_dynamic_fields())
        self._vars["amortization"].trace_add("write", lambda *_: self._update_dynamic_fields())
        self._vars["rate_type"].trace_add("write", lambda *_: self._update_dynamic_fields())
        self._vars["moment"].trace_add("write", lambda *_: self._update_dynamic_fields())
        self._vars["extra_strategy"].trace_add("write", lambda *_: self._update_dynamic_fields())
        self._update_dynamic_fields()

    def _toggle_advanced(self) -> None:
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.advanced_frame.pack(fill="x", before=self.loan_buttons)
            self.advanced_toggle.set_text("−  Ocultar ajustes avanzados")
        else:
            self.advanced_frame.pack_forget()
            self.advanced_toggle.set_text("＋  Ajustes avanzados")
            self._reset_advanced_settings()

    def _reset_advanced_settings(self) -> None:
        for key, value in (
            ("amortization", "Cuota fija"),
            ("moment", "Vencido"),
            ("grace", "Sin diferimiento"),
            ("grace_periods", "0"),
            ("growth", "2"),
            ("rate_type", "Fija"),
            ("rate_changes", ""),
            ("extras", ""),
            ("extra_strategy", "Reducir plazo"),
        ):
            self._vars[key].set(value)

    def _update_dynamic_fields(self) -> None:
        amortization = self._vars["amortization"].get()
        grace = self._vars["grace"].get()
        strategy = self._vars["extra_strategy"].get()

        if amortization == "Pago único":
            self._vars["moment"].set("Vencido")
        elif amortization == "Abono a capital fijo" and strategy == "Reducir cuota":
            self._vars["extra_strategy"].set("Reducir plazo")
        if amortization == "Pago único" and strategy != "Reducir cuota":
            self._vars["extra_strategy"].set("Reducir cuota")

        if grace == "Sin diferimiento" and self._vars["grace_periods"].get() != "0":
            self._vars["grace_periods"].set("0")
        self._controls["moment"].configure(
            state="disabled" if amortization == "Pago único" else "readonly"
        )
        self._controls["extras"].configure(state="normal")
        strategy_values = ("Reducir cuota",) if amortization == "Pago único" else (
            ("Reducir plazo",) if amortization == "Abono a capital fijo" else
            ("Reducir plazo", "Reducir cuota")
        )
        self._controls["extra_strategy"].configure(
            values=strategy_values,
            state="disabled" if amortization == "Pago único" else "readonly",
        )
        if amortization == "Pago único":
            self.compatibility_label.configure(
                text="El pago único vence al final del plazo: no admite pagos anticipados ni abonos extraordinarios."
            )
            self.compatibility_note.configure(
                text="Esta modalidad no admite abonos extraordinarios."
            )
        elif amortization == "Abono a capital fijo":
            self.compatibility_label.configure(
                text="Con abono a capital fijo, un abono extraordinario puede reducir el plazo; la cuota no se recalcula."
            )
            self.compatibility_note.configure(
                text="Esta modalidad permite reducir plazo; reducir cuota no es compatible con el capital fijo."
            )
        else:
            self.compatibility_label.configure(text="")
            self.compatibility_note.configure(text="")
        if grace != "Sin diferimiento" and self._vars["extra_strategy"].get() == "Reducir plazo":
            self.compatibility_note.configure(
                text="Con «Reducir plazo», programa los abonos después de los periodos de gracia."
            )
        if self._vars["rate_type"].get() == "Escalonada":
            self._field_hints["rate_changes"].configure(
                text="Obligatorio. Ejemplo: 7:20;13:22. Usa los periodos y unidad de tasa del crédito."
            )
        else:
            self._field_hints["rate_changes"].configure(
                text="Se usa con tasas escalonadas programadas."
            )
        self._controls["grace_periods"].configure(
            state="disabled" if grace == "Sin diferimiento" else "normal"
        )
        self._set_field_visible("grace_periods", grace != "Sin diferimiento")
        self._controls["growth"].configure(
            state="normal" if amortization in (
                "Cuota creciente", "Cuota decreciente personalizada"
            ) else "disabled"
        )
        self._set_field_visible(
            "growth", amortization in ("Cuota creciente", "Cuota decreciente personalizada")
        )
        self._controls["rate_changes"].configure(
            state="disabled" if self._vars["rate_type"].get() == "Fija" else "normal"
        )
        self._set_field_visible("rate_changes", self._vars["rate_type"].get() != "Fija")

    def _set_field_visible(self, key: str, visible: bool) -> None:
        frame = self._field_frames[key]
        if visible and not frame.winfo_manager():
            frame.pack(fill="x", padx=8, pady=7)
        elif not visible and frame.winfo_manager():
            frame.pack_forget()

    def _parse_float(self, key: str, label: str, percent: bool = False) -> float:
        raw = self._vars[key].get().strip().replace(",", "")
        try:
            value = float(raw)
        except ValueError as exc:
            raise ValueError(f"Revisa el campo «{label}»: debe ser numérico.") from exc
        if not math.isfinite(value):
            raise ValueError(f"El campo «{label}» debe ser un número finito.")
        return value / 100 if percent else value

    def _parse_changes(self) -> tuple[tuple[int, float], ...]:
        raw = self._vars["rate_changes"].get().strip()
        if not raw:
            return ()
        changes: list[tuple[int, float]] = []
        try:
            for item in raw.split(";"):
                period_text, rate_text = item.strip().split(":")
                changes.append((int(period_text.strip()), float(rate_text.strip()) / 100))
        except (ValueError, TypeError) as exc:
            raise ValueError("Cambios de tasa inválidos. Usa el formato periodo:porcentaje; por ejemplo 7:20;13:22.") from exc
        return tuple(changes)

    def _parse_extras(self) -> tuple[ExtraPayment, ...]:
        raw = self._vars["extras"].get().strip()
        if not raw:
            return ()
        items: list[ExtraPayment] = []
        try:
            for item in raw.split(";"):
                period_text, amount_text = item.strip().split(":")
                items.append(ExtraPayment(int(period_text.strip()), float(amount_text.strip().replace(",", ""))))
        except (ValueError, TypeError) as exc:
            raise ValueError("Abonos inválidos. Usa periodo:monto; por ejemplo 6:1000000;12:500000.") from exc
        return tuple(items)

    def _config_from_form(self) -> LoanConfig:
        unit = {
            "Efectiva anual (EA)": "EA",
            "Efectiva mensual (EM)": "EM",
            "Efectiva por periodo (EP)": "EP",
        }[self._vars["rate_unit"].get()]
        frequency = {
            "Mensual": 1, "Bimestral": 2, "Trimestral": 3,
            "Cuatrimestral": 4, "Semestral": 6, "Anual": 12,
        }[self._vars["frequency"].get()]
        amortization = {
            "Cuota fija": "fixed",
            "Abono a capital fijo": "constant_principal",
            "Cuota creciente": "growing",
            "Cuota decreciente personalizada": "custom_decreasing",
            "Pago único": "bullet",
        }[self._vars["amortization"].get() if self.advanced_visible else "Cuota fija"]
        grace = {
            "Sin diferimiento": "none",
            "Gracia de capital": "principal",
            "Gracia total": "total",
        }[self._vars["grace"].get() if self.advanced_visible else "Sin diferimiento"]
        rate_type = self._vars["rate_type"].get() if self.advanced_visible else "Fija"
        try:
            periods = int(self._vars["periods"].get().strip())
            grace_count = (
                int(self._vars["grace_periods"].get().strip() or "0")
                if self.advanced_visible and grace != "none" else 0
            )
            principal = self._parse_float("principal", "Monto solicitado")
            rate = self._parse_float("rate", "Tasa de referencia", percent=True)
            growth = (
                self._parse_float("growth", "Crecimiento por cuota", percent=True)
                if self.advanced_visible and amortization in ("growing", "custom_decreasing")
                else 0.0
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        moment = (
            self._vars["moment"].get()
            if self.advanced_visible and amortization != "bullet" else "Vencido"
        )
        return LoanConfig(
            principal=principal,
            periods=periods,
            annual_rate=rate,
            rate_unit=unit,
            frequency_months=frequency,
            amortization=amortization,  # type: ignore[arg-type]
            payment_moment="advance" if moment == "Anticipado" else "arrears",
            grace=grace,  # type: ignore[arg-type]
            grace_periods=grace_count,
            growth_rate=growth,
            rate_changes=(
                self._parse_changes()
                if self.advanced_visible and rate_type == "Escalonada" else ()
            ),
            extra_payments=self._parse_extras() if self.advanced_visible else (),
            extra_strategy=(
                "installment"
                if self.advanced_visible and amortization != "bullet"
                and self._vars["extra_strategy"].get() == "Reducir cuota"
                else "term"
            ),
        )

    def _run_simulation(self) -> None:
        try:
            age = int(self._vars["age"].get().strip())
            occupation = self._vars["occupation"].get().strip()
            if not 1 <= age <= 120:
                raise ValueError("La edad debe estar entre 1 y 120 años.")
            if not occupation:
                raise ValueError("Indica tu ocupación o actividad laboral.")
            income = self._parse_float("income", "Ingresos mensuales")
            expenses_text = self._vars["expenses"].get().strip()
            expenses = self._parse_float("expenses", "Gastos mensuales") if expenses_text else 0
            if income < 0 or expenses < 0:
                raise ValueError("Ingresos y gastos no pueden ser negativos.")
            config = self._config_from_form()
            rate_type = self._vars["rate_type"].get() if self.advanced_visible else "Fija"
            validate_compatibility(config, rate_type)
            self.result = simulate(config)
            self._render_results(config)
        except (ValueError, OverflowError) as exc:
            messagebox.showerror("No se pudo calcular", str(exc), parent=self)
            return
        self.show_page("Resultados")

    @staticmethod
    def _money(value: float) -> str:
        return f"$ {value:,.0f}".replace(",", ".")

    def _build_results_page(self) -> None:
        page = ScrollableFrame(self.page_host)
        self._register_page("Resultados", page)
        self.results_content = page.content

    def _clear_results(self) -> None:
        for child in self.results_content.winfo_children():
            child.destroy()

    def _render_results(self, config: LoanConfig) -> None:
        assert self.result is not None
        result = self.result
        self._clear_results()
        intro = ttk.Frame(self.results_content, style="Page.TFrame")
        intro.pack(fill="x", padx=28, pady=(22, 0))
        ttk.Label(intro, text="Resumen del escenario", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(intro, text=f"{self._vars['occupation'].get().strip()} · {self._vars['age'].get()} años · "
                  f"{config.periods} periodos · tasa {config.annual_rate:.2%} {config.rate_unit} · "
                  f"{config.frequency_months} mes(es) por pago",
                  foreground=MUTED).pack(anchor="w", pady=(4, 0))

        cards = ttk.Frame(self.results_content, style="Page.TFrame")
        cards.pack(fill="x", padx=20, pady=(16, 0))
        income = self._parse_profile_value("income")
        available = max(0.0, income - self._parse_profile_value("expenses"))
        period_months = config.frequency_months
        monthly_installment = result.initial_payment / period_months
        ratio = monthly_installment / income if income > 0 else None
        first_metric = "PAGO ÚNICO (FINAL)" if config.amortization == "bullet" else "CUOTA INICIAL"
        metrics = (
            (first_metric, self._money(result.initial_payment), BLUE),
            ("INTERESES TOTALES", self._money(result.total_interest), ORANGE),
            ("TOTAL PAGADO", self._money(result.total_paid), TEAL),
            ("SALDO PENDIENTE", self._money(result.final_balance), NAVY),
        )
        metric_cards: list[ttk.Frame] = []
        for title, value, accent in metrics:
            card = self._card(cards, padding=16)
            metric_cards.append(card)
            tk.Frame(card, bg=accent, height=3).pack(fill="x", pady=(0, 12))
            ttk.Label(card, text=title, style="CardTitle.TLabel").pack(anchor="w")
            ttk.Label(card, text=value, style="CardValue.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(
            self.results_content,
            text=f"Monto solicitado: {self._money(config.principal)}  ·  "
                 f"Cuota final: {self._money(result.final_payment)}",
            foreground=MUTED,
        ).pack(anchor="w", padx=32, pady=(8, 0))

        capacity = self._card(self.results_content)
        capacity.pack(fill="x", padx=28, pady=(16, 0))
        ttk.Label(capacity, text="Capacidad de pago orientativa", style="Section.TLabel").pack(anchor="w")
        if ratio is None:
            payment_ratio_text = "Ingresa un ingreso mensual para calcular la relación cuota/ingreso."
        else:
            payment_ratio_text = (
                f"La cuota equivale aproximadamente al {ratio:.1%} de tus ingresos mensuales. "
                f"Ingreso disponible estimado después de gastos: {self._money(available)}."
            )
        ttk.Label(capacity, text=payment_ratio_text, style="Muted.TLabel", wraplength=1000).pack(
            anchor="w", pady=(8, 2)
        )
        ttk.Label(capacity, text="Indicador educativo; no constituye una recomendación ni aprobación de crédito.",
                  style="Muted.TLabel", font=(FONT, 9)).pack(anchor="w")

        charts = ttk.Frame(self.results_content, style="Page.TFrame")
        charts.pack(fill="x", padx=20, pady=(16, 0))
        balance_card = self._card(charts, padding=14)
        balance_card.pack(side="left", fill="both", expand=True, padx=8)
        ttk.Label(balance_card, text="EVOLUCIÓN DEL SALDO", style="CardTitle.TLabel").pack(anchor="w")
        balance_canvas = tk.Canvas(balance_card, height=200, bg=WHITE, highlightthickness=0)
        balance_canvas.pack(fill="x", pady=(7, 0))
        self._draw_line_chart(balance_canvas, [row.closing_balance for row in result.rows], BLUE, currency=True)
        balance_canvas.bind("<Configure>", lambda _event: self._draw_line_chart(
            balance_canvas, [row.closing_balance for row in result.rows], BLUE, currency=True
        ))

        split_card = self._card(charts, padding=14)
        split_card.pack(side="left", fill="both", expand=True, padx=8)
        ttk.Label(split_card, text="CAPITAL E INTERESES POR PERIODO", style="CardTitle.TLabel").pack(anchor="w")
        split_canvas = tk.Canvas(split_card, height=200, bg=WHITE, highlightthickness=0)
        split_canvas.pack(fill="x", pady=(7, 0))
        self._draw_split_chart(split_canvas, result.rows)
        split_canvas.bind("<Configure>", lambda _event: self._draw_split_chart(
            split_canvas, result.rows
        ))

        payment_charts = ttk.Frame(self.results_content, style="Page.TFrame")
        payment_charts.pack(fill="x", padx=20, pady=(12, 0))
        payment_card = self._card(payment_charts, padding=14)
        payment_card.pack(side="left", fill="both", expand=True, padx=8)
        ttk.Label(payment_card, text="EVOLUCIÓN DEL VALOR DE LOS PAGOS", style="CardTitle.TLabel").pack(anchor="w")
        payment_canvas = tk.Canvas(payment_card, height=180, bg=WHITE, highlightthickness=0)
        payment_canvas.pack(fill="x", pady=(7, 0))
        self._draw_line_chart(payment_canvas, [row.payment for row in result.rows], TEAL)
        payment_canvas.bind("<Configure>", lambda _event: self._draw_line_chart(
            payment_canvas, [row.payment for row in result.rows], TEAL
        ))

        table_card = self._card(self.results_content, padding=16)
        table_card.pack(fill="both", padx=28, pady=(16, 0))
        table_header = ttk.Frame(table_card, style="Card.TFrame")
        table_header.pack(fill="x", pady=(0, 12))
        ttk.Label(table_header, text="Tabla de amortización", style="Section.TLabel").pack(side="left")
        self._rounded_button(
            table_header, text="Exportar CSV", command=self._export_csv,
        ).pack(side="right")
        container = ttk.Frame(table_card, style="Card.TFrame")
        container.pack(fill="both", expand=True)
        columns = ("period", "opening", "interest", "principal", "extra", "payment", "closing", "note")
        tree = ttk.Treeview(container, columns=columns, show="headings", height=11)
        labels = ("Periodo", "Saldo inicial", "Interés", "Abono a capital", "Abono extra", "Pago total", "Saldo final", "Detalle")
        widths = (72, 120, 110, 125, 110, 110, 120, 205)
        for column, label, width in zip(columns, labels, widths):
            tree.heading(column, text=label)
            tree.column(column, width=width, minwidth=65, anchor="e" if column not in ("note",) else "w")
        yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(table_card, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(fill="x")
        for index, row in enumerate(result.rows):
            tree.insert("", "end", values=(
                row.period, self._money(row.opening_balance), self._money(row.interest),
                self._money(row.principal_paid), self._money(row.extra_payment),
                self._money(row.payment), self._money(row.closing_balance), row.note,
            ), tags=("even" if index % 2 == 0 else "odd",))
        tree.tag_configure("even", background=WHITE)
        tree.tag_configure("odd", background="#F6F9FC")
        footer = ttk.Frame(self.results_content, style="Page.TFrame")
        footer.pack(fill="x", padx=28, pady=20)
        self._rounded_button(
            footer, text="← Ajustar condiciones", command=lambda: self.show_page("Crédito"),
        ).pack(side="left")
        self._rounded_button(
            footer, text="Nueva simulación", style="Primary.TButton", command=self._reset,
        ).pack(side="right")
        self._layout_metric_cards(cards, metric_cards)
        cards.bind(
            "<Configure>",
            lambda event: self._layout_metric_cards(cards, metric_cards, event.width),
        )
        self._render_recommendations(config)

    def _layout_metric_cards(
        self,
        parent: ttk.Frame,
        cards: list[ttk.Frame],
        width: int | None = None,
    ) -> None:
        columns = 2 if (width or parent.winfo_width()) < 880 else 4
        if parent.__dict__.get("_metric_columns") == columns:
            return
        for card in cards:
            card.grid_forget()
        for index, card in enumerate(cards):
            card.grid(row=index // columns, column=index % columns, sticky="nsew", padx=8, pady=5)
        for column in range(4):
            parent.columnconfigure(column, weight=1 if column < columns else 0)
        parent.__dict__["_metric_columns"] = columns

    def _render_recommendations(self, config: LoanConfig) -> None:
        growth_rate = (
            config.growth_rate
            if config.amortization in ("growing", "custom_decreasing")
            else 0.02
        )
        section = self._card(self.results_content, padding=20)
        section.pack(fill="x", padx=28, pady=(4, 18))
        ttk.Label(section, text="Recomendaciones", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            section,
            text=(
                f"Alternativas simuladas con {self._money(config.principal)}, "
                f"{config.periods} periodos totales y la tasa ingresada "
                f"({config.annual_rate:.2%} {config.rate_unit}). Se comparan alternativas compatibles, "
                "conservando los cambios de tasa, las condiciones de gracia y los abonos configurados. "
                "Las tasas se convierten a su equivalente EA y los cambios permanecen en el mismo número "
                f"de periodo; las cuotas crecientes/decrecientes usan {growth_rate:.1%} por periodo."
            ),
            style="Muted.TLabel", wraplength=1000,
        ).pack(anchor="w", pady=(6, 12))
        try:
            recommendations = recommend_loans(config)
        except (ValueError, OverflowError) as exc:
            ttk.Label(
                section, text=f"No fue posible generar recomendaciones: {exc}",
                style="Muted.TLabel", wraplength=1000,
            ).pack(anchor="w")
            return

        amortization_labels = {
            "fixed": "Cuota fija",
            "constant_principal": "Abono a capital fijo",
            "growing": "Cuota creciente",
            "custom_decreasing": "Cuota decreciente personalizada",
            "bullet": "Pago único",
        }
        frequency_labels = {
            1: "Mensual", 2: "Bimestral", 3: "Trimestral",
            4: "Cuatrimestral", 6: "Semestral", 12: "Anual",
        }
        explanations = {
            "Menor costo": "Es la alternativa con menor total pagado entre los planes simulados.",
            "Menor tiempo": "Es la alternativa que termina antes, considerando los meses reales entre pagos.",
            "Equilibrada": "Balancea costo y duración frente al conjunto de alternativas simuladas.",
        }
        cards = ttk.Frame(section, style="Card.TFrame")
        cards.pack(fill="x")
        for recommendation in recommendations:
            candidate = recommendation.config
            result = recommendation.result
            card = self._card(cards, padding=14)
            card.pack(fill="x", pady=5)
            heading = ttk.Frame(card, style="Card.TFrame")
            heading.pack(fill="x")
            ttk.Label(
                heading, text=recommendation.category, style="Section.TLabel",
            ).pack(side="left")
            ttk.Label(
                heading, text=explanations[recommendation.category],
                style="Muted.TLabel", wraplength=700,
            ).pack(side="left", padx=(14, 0))
            setup = (
                f"{amortization_labels[candidate.amortization]} · "
                f"{frequency_labels[candidate.frequency_months]} · "
                f"{'Anticipado' if candidate.payment_moment == 'advance' else 'Vencido'} · "
                f"{candidate.periods} periodos totales · tasa base {candidate.annual_rate:.2%} EA"
            )
            if candidate.amortization in ("growing", "custom_decreasing"):
                setup += f" · variación {candidate.growth_rate:.1%} por periodo"
            if candidate.grace != "none":
                grace_labels = {
                    "principal": "Gracia de capital",
                    "total": "Gracia total",
                }
                grace_unit = "periodo" if candidate.grace_periods == 1 else "periodos"
                setup += (
                    f" · {grace_labels[candidate.grace]}: "
                    f"{candidate.grace_periods} {grace_unit}"
                )
            if candidate.rate_changes:
                changes = "; ".join(
                    f"{period}:{rate:.2%} EA"
                    for period, rate in candidate.rate_changes
                )
                setup += f" · tasas escalonadas {changes}"
            ttk.Label(card, text=setup, style="Muted.TLabel", wraplength=1000).pack(
                anchor="w", pady=(7, 5)
            )
            if candidate.extra_payments:
                extras = "; ".join(
                    f"{extra.period}: {self._money(extra.amount)}"
                    for extra in candidate.extra_payments
                )
                strategy = (
                    "reducir cuota" if candidate.extra_strategy == "installment"
                    else "reducir plazo"
                )
                ttk.Label(
                    card,
                    text=f"Abonos extraordinarios: {extras} · Estrategia: {strategy}.",
                    style="Muted.TLabel", wraplength=1000,
                ).pack(anchor="w", pady=(0, 5))
            duration = (
                f"{recommendation.elapsed_months} meses"
                if recommendation.elapsed_months != 1
                else "1 mes"
            )
            payment_label = (
                "Pago único final" if candidate.amortization == "bullet"
                else "Cuota inicial de amortización"
            )
            ttk.Label(
                card,
                text=(
                    f"Total pagado: {self._money(result.total_paid)}   ·   "
                    f"Intereses: {self._money(result.total_interest)}   ·   "
                    f"Duración estimada: {duration}   ·   "
                    f"{payment_label}: {self._money(result.initial_payment)}"
                ),
                style="Muted.TLabel", wraplength=1000,
            ).pack(anchor="w")

    def _parse_profile_value(self, key: str) -> float:
        try:
            value = float(self._vars[key].get().strip().replace(",", "") or "0")
            return value if math.isfinite(value) else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _draw_line_chart(canvas: tk.Canvas, values: list[float], color: str,
                         currency: bool = False) -> None:
        canvas.delete("all")
        width = max(canvas.winfo_width(), 360)
        height = 190
        pad = 28
        if not values:
            return
        maximum = max(values + [1])
        points: list[float] = []
        for index, value in enumerate(values):
            x = pad + index * (width - 2 * pad) / max(1, len(values) - 1)
            y = height - pad - value / maximum * (height - 2 * pad)
            points.extend((x, y))
        for grid in range(3):
            y = pad + grid * (height - 2 * pad) / 2
            canvas.create_line(pad, y, width - pad, y, fill=LINE)
        if len(points) >= 4:
            canvas.create_line(*points, fill=color, width=3, smooth=True)
            canvas.create_oval(points[-2] - 4, points[-1] - 4, points[-2] + 4,
                               points[-1] + 4, fill=color, outline=WHITE, width=2)
        canvas.create_text(pad, height - 8, text="Inicio", anchor="w", fill=MUTED,
                           font=(FONT, 9))
        canvas.create_text(width - pad, height - 8, text="Fin", anchor="e", fill=MUTED,
                           font=(FONT, 9))

    @staticmethod
    def _draw_split_chart(canvas: tk.Canvas, rows: tuple) -> None:
        canvas.delete("all")
        width = max(canvas.winfo_width(), 360)
        height = 190
        pad = 24
        if not rows:
            return
        sample_count = min(len(rows), 30)
        indexes = [round(index * (len(rows) - 1) / max(1, sample_count - 1))
                   for index in range(sample_count)]
        max_value = max((rows[index].principal_paid + rows[index].interest for index in indexes), default=1) or 1
        slot = (width - 2 * pad) / sample_count
        for position, row_index in enumerate(indexes):
            row = rows[row_index]
            x = pad + position * slot
            capital_h = row.principal_paid / max_value * (height - 2 * pad)
            interest_h = row.interest / max_value * (height - 2 * pad)
            canvas.create_rectangle(x + 2, height - pad - capital_h, x + slot - 2,
                                    height - pad, fill=BLUE, outline="")
            canvas.create_rectangle(x + 2, height - pad - capital_h - interest_h,
                                    x + slot - 2, height - pad - capital_h,
                                    fill=ORANGE, outline="")
        canvas.create_rectangle(pad, 8, pad + 10, 18, fill=BLUE, outline="")
        canvas.create_text(pad + 15, 13, text="Capital", anchor="w", fill=MUTED, font=(FONT, 9))
        canvas.create_rectangle(pad + 80, 8, pad + 90, 18, fill=ORANGE, outline="")
        canvas.create_text(pad + 95, 13, text="Interés", anchor="w", fill=MUTED, font=(FONT, 9))

    def _export_csv(self) -> None:
        if self.result is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self, title="Exportar tabla de amortización",
            defaultextension=".csv", filetypes=(("Archivo CSV", "*.csv"),),
            initialfile="simulacion_credito.csv",
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file, delimiter=";")
                writer.writerow(("Periodo", "Saldo inicial", "Interés", "Abono a capital",
                                 "Abono extraordinario", "Pago total", "Saldo final", "Detalle"))
                for row in self.result.rows:
                    writer.writerow((
                        row.period, f"{row.opening_balance:.2f}", f"{row.interest:.2f}",
                        f"{row.principal_paid:.2f}", f"{row.extra_payment:.2f}",
                        f"{row.payment:.2f}", f"{row.closing_balance:.2f}", row.note,
                    ))
        except OSError as exc:
            messagebox.showerror("No se pudo exportar", f"No fue posible escribir el archivo:\n{exc}", parent=self)
            return
        messagebox.showinfo("Exportación completa", "La tabla de amortización se exportó correctamente.", parent=self)

    def _reset(self) -> None:
        self.result = None
        if self.advanced_visible:
            self._toggle_advanced()
        for key, value in (
            ("principal", "25000000"), ("periods", "24"), ("rate", "18"),
            ("rate_unit", "Efectiva anual (EA)"), ("frequency", "Mensual"),
            ("amortization", "Cuota fija"), ("moment", "Vencido"),
            ("grace", "Sin diferimiento"), ("grace_periods", "0"), ("growth", "2"),
            ("rate_type", "Fija"), ("rate_changes", ""), ("extras", ""),
            ("extra_strategy", "Reducir plazo"),
        ):
            self._vars[key].set(value)
        for key, value in (("age", "30"), ("occupation", "Empleado"),
                           ("income", "4500000"), ("expenses", "1800000")):
            self._vars[key].set(value)
        self.show_page("Perfil")


if __name__ == "__main__":
    CreditSimulator().mainloop()
