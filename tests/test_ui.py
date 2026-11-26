import tkinter as tk
import tkinter.font as tkfont
import unittest
from tkinter import ttk

from finance import recommend_loans, simulate, validate_compatibility
from main import CreditSimulator


class CreditSimulatorUiTests(unittest.TestCase):
    def setUp(self):
        try:
            self.app = CreditSimulator()
        except tk.TclError as exc:
            self.skipTest(f"Tk no está disponible en este entorno: {exc}")
        self.app.withdraw()

    def tearDown(self):
        app = getattr(self, "app", None)
        if app is not None:
            app.destroy()

    def test_window_has_a_smaller_resizable_minimum(self):
        self.app.geometry("860x600")
        self.assertEqual(self.app.minsize(), (860, 600))
        self.assertEqual(self.app.resizable(), (True, True))

    def test_closing_advanced_settings_resets_and_disables_their_values(self):
        self.app.advanced_toggle.invoke()
        for key, value in (
            ("amortization", "Pago único"),
            ("moment", "Vencido"),
            ("grace", "Gracia total"),
            ("grace_periods", "2"),
            ("growth", "8"),
            ("rate_type", "Escalonada"),
            ("rate_changes", "4:20"),
            ("extras", "5:1000000"),
            ("extra_strategy", "Reducir plazo"),
        ):
            self.app._vars[key].set(value)

        self.app.advanced_toggle.invoke()
        self.assertFalse(self.app.advanced_visible)
        expected = {
            "amortization": "Cuota fija",
            "moment": "Vencido",
            "grace": "Sin diferimiento",
            "grace_periods": "0",
            "growth": "2",
            "rate_type": "Fija",
            "rate_changes": "",
            "extras": "",
            "extra_strategy": "Reducir plazo",
        }
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(self.app._vars[key].get(), value)

        config = self.app._config_from_form()
        self.assertEqual(config.amortization, "fixed")
        self.assertEqual(config.grace, "none")
        self.assertFalse(config.rate_changes)
        self.assertFalse(config.extra_payments)

        self.app.advanced_toggle.invoke()
        for key, value in expected.items():
            with self.subTest(reopened_key=key):
                self.assertEqual(self.app._vars[key].get(), value)

    def test_disabled_advanced_values_do_not_affect_the_config(self):
        self.app.advanced_toggle.invoke()
        self.app._vars["rate_type"].set("Fija")
        self.app._vars["rate_changes"].set("not a rate schedule")
        self.app._vars["amortization"].set("Cuota fija")
        self.app._vars["growth"].set("not a percentage")
        self.app._vars["grace"].set("Sin diferimiento")
        self.app._vars["grace_periods"].set("not a period count")

        config = self.app._config_from_form()
        self.assertEqual(config.rate_changes, ())
        self.assertEqual(config.growth_rate, 0)
        self.assertEqual(config.grace, "none")
        self.assertEqual(config.grace_periods, 0)

        self.app._vars["amortization"].set("Pago único")
        bullet_config = self.app._config_from_form()
        self.assertEqual(bullet_config.payment_moment, "arrears")
        self.assertEqual(bullet_config.extra_strategy, "term")

    def test_entry_and_advanced_button_use_rounded_surfaces(self):
        entry_surface = self.app._field_frames["principal"].winfo_children()[1]
        self.assertEqual(entry_surface.type(1), "polygon")
        self.assertEqual(self.app.advanced_toggle.type(1), "polygon")
        self.assertIn("Trebuchet MS", str(self.app.style.lookup(".", "font")))
        self.assertEqual(
            tuple(self.app._controls["grace"].cget("values")),
            ("Sin diferimiento", "Gracia de capital", "Gracia total"),
        )
        self.assertEqual(
            tuple(self.app._controls["rate_type"].cget("values")),
            ("Fija", "Escalonada"),
        )

    def test_initial_profile_shows_institution_and_team(self):
        labels = []

        def collect(widget):
            if isinstance(widget, (tk.Label, ttk.Label)):
                labels.append(widget.cget("text"))
            for child in widget.winfo_children():
                collect(child)

        collect(self.app.pages["Perfil"])
        self.assertEqual(self.app.page_title.cget("text"), "Cuéntanos un poco de ti")
        for expected in (
            "Universidad Distrital Francisco José de Caldas",
            "Proyecto académico — 2026",
            "Harold Mateus",
            "202626780XX",
            "Santiago Castiblanco",
            "Erick Lemus",
            "20262678012",
            "Camilo Ocampo",
            "20262678061",
        ):
            with self.subTest(text=expected):
                self.assertIn(expected, labels)

    def test_button_width_fits_its_text_after_a_label_change(self):
        button = self.app._rounded_button(
            self.app,
            text="Continuar a configurar el crédito  →",
            command=lambda: None,
            style="Primary.TButton",
        )
        self.app.update_idletasks()
        self.assertGreaterEqual(
            button.winfo_reqwidth() - 16,
            button.button.winfo_reqwidth(),
        )
        button.set_text("Calcular simulación  →")
        self.app.update_idletasks()
        self.assertGreaterEqual(
            button.winfo_reqwidth() - 16,
            button.button.winfo_reqwidth(),
        )
        font = tkfont.Font(self.app, font=self.app.style.lookup(".", "font"))
        self.assertEqual(font.cget("size"), 10)

    def test_form_fields_stack_at_the_minimum_window_width(self):
        self.app.geometry("860x600")
        self.app.deiconify()
        self.app.update()
        self.app.show_page("Crédito")
        self.app.update()
        for key in ("principal", "periods", "rate", "rate_unit"):
            with self.subTest(field=key):
                self.assertGreater(self.app._controls[key].winfo_width(), 300)

    def test_recommendations_render_the_active_advanced_configuration(self):
        self.app.advanced_toggle.invoke()
        for key, value in (
            ("principal", "100000"),
            ("periods", "8"),
            ("rate", "1"),
            ("rate_unit", "Efectiva por periodo (EP)"),
            ("frequency", "Bimestral"),
            ("amortization", "Cuota creciente"),
            ("moment", "Anticipado"),
            ("grace", "Gracia de capital"),
            ("grace_periods", "1"),
            ("growth", "3"),
            ("rate_type", "Escalonada"),
            ("rate_changes", "4:1.5"),
            ("extras", "3:5000"),
            ("extra_strategy", "Reducir cuota"),
        ):
            self.app._vars[key].set(value)

        config = self.app._config_from_form()
        validate_compatibility(config, "Escalonada")
        self.app.result = simulate(config)
        recommendations = recommend_loans(config)
        self.app.geometry("1100x800")
        self.app.deiconify()
        self.app._render_results(config)
        self.app.show_page("Resultados")
        self.app.update()

        labels = []

        def collect(widget):
            if isinstance(widget, (tk.Label, ttk.Label)):
                labels.append(widget.cget("text"))
            for child in widget.winfo_children():
                collect(child)

        collect(self.app.pages["Resultados"])
        rendered_metrics = [text for text in labels if "Total pagado:" in text]
        self.assertEqual(len(rendered_metrics), len(recommendations))
        for item in recommendations:
            with self.subTest(category=item.category):
                self.assertIn(item.category, labels)
                self.assertTrue(any(
                    f"Total pagado: {self.app._money(item.result.total_paid)}" in text
                    and f"Intereses: {self.app._money(item.result.total_interest)}" in text
                    and f"Duración estimada: {item.elapsed_months}" in text
                    for text in rendered_metrics
                ))
        self.assertTrue(any("Gracia de capital: 1 periodo" in text for text in labels))
        self.assertTrue(any("tasas escalonadas" in text for text in labels))
        self.assertTrue(any("Abonos extraordinarios: 3:" in text for text in labels))
        self.assertTrue(any("variación 3.0% por periodo" in text for text in labels))


if __name__ == "__main__":
    unittest.main()
