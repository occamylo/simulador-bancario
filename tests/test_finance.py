import unittest

from finance import (
    ExtraPayment,
    LoanConfig,
    periodic_rate,
    recommend_loans,
    simulate,
    validate_compatibility,
)


class InterestConversionTests(unittest.TestCase):
    def test_effective_annual_rate_converts_compoundingly(self):
        self.assertAlmostEqual(periodic_rate(0.1268250301, "EA", 1), 0.01, places=8)

    def test_effective_monthly_rate_converts_to_quarterly(self):
        self.assertAlmostEqual(periodic_rate(0.01, "EM", 3), 0.030301, places=9)

    def test_effective_period_rate_is_not_divided(self):
        self.assertEqual(periodic_rate(0.04, "EP", 6), 0.04)


class AmortizationTests(unittest.TestCase):
    def test_fixed_arrears_payment_and_balances(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=2, annual_rate=0.10, rate_unit="EP",
        ))
        self.assertAlmostEqual(result.initial_payment, 57_619.047619, places=5)
        self.assertAlmostEqual(result.rows[0].interest, 10_000, places=6)
        self.assertAlmostEqual(result.final_balance, 0, places=6)
        self.assertAlmostEqual(result.total_paid, 115_238.095238, places=5)

    def test_advance_payment_reduces_interest(self):
        arrears = simulate(LoanConfig(
            principal=100_000, periods=3, annual_rate=0.10, rate_unit="EP",
        ))
        advance = simulate(LoanConfig(
            principal=100_000, periods=3, annual_rate=0.10, rate_unit="EP",
            payment_moment="advance",
        ))
        self.assertEqual(advance.rows[0].interest, 0)
        self.assertLess(advance.total_interest, arrears.total_interest)
        self.assertAlmostEqual(advance.final_balance, 0, places=6)

    def test_advance_payment_handles_rate_changes_consistently(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=4, annual_rate=0.10, rate_unit="EP",
            payment_moment="advance", rate_changes=((3, 0.20),),
        ))
        self.assertAlmostEqual(result.final_balance, 0, places=5)
        self.assertEqual(result.rows[2].rate, 0.20)

    def test_constant_principal_has_decreasing_payments(self):
        result = simulate(LoanConfig(
            principal=90_000, periods=3, annual_rate=0.10, rate_unit="EP",
            amortization="constant_principal",
        ))
        self.assertEqual([round(row.principal_paid) for row in result.rows], [30_000] * 3)
        self.assertGreater(result.rows[0].payment, result.rows[1].payment)
        self.assertGreater(result.rows[1].payment, result.rows[2].payment)
        self.assertAlmostEqual(result.final_balance, 0, places=6)

    def test_bullet_capitalizes_compound_interest(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=2, annual_rate=0.10, rate_unit="EP",
            amortization="bullet",
        ))
        self.assertAlmostEqual(result.final_payment, 121_000, places=6)
        self.assertAlmostEqual(result.total_interest, 21_000, places=6)
        self.assertAlmostEqual(result.final_balance, 0, places=6)

    def test_total_grace_capitalizes_interest_then_amortizes(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=4, annual_rate=0.10, rate_unit="EP",
            grace="total", grace_periods=2,
        ))
        self.assertAlmostEqual(result.rows[1].closing_balance, 121_000, places=6)
        self.assertEqual(result.rows[0].payment, 0)
        self.assertAlmostEqual(result.final_balance, 0, places=6)
        self.assertEqual(len(result.rows), 4)

    def test_extra_payment_during_grace_reduces_capitalized_balance(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=4, annual_rate=0.10, rate_unit="EP",
            grace="total", grace_periods=2,
            extra_payments=(ExtraPayment(1, 10_000),),
            extra_strategy="installment",
        ))
        self.assertAlmostEqual(result.rows[0].closing_balance, 100_000, places=6)
        self.assertEqual(result.rows[0].extra_payment, 10_000)
        self.assertAlmostEqual(result.final_balance, 0, places=6)

    def test_principal_grace_pays_interest_without_reducing_balance(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=3, annual_rate=0.10, rate_unit="EP",
            grace="principal", grace_periods=1,
        ))
        self.assertAlmostEqual(result.rows[0].payment, 10_000, places=6)
        self.assertAlmostEqual(result.rows[0].closing_balance, 100_000, places=6)
        self.assertAlmostEqual(result.final_balance, 0, places=6)

    def test_variable_rates_and_extra_principal_payment(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=6, annual_rate=0.10, rate_unit="EP",
            rate_changes=((4, 0.05),),
            extra_payments=(ExtraPayment(2, 20_000),),
        ))
        self.assertEqual(result.rows[3].rate, 0.05)
        self.assertEqual(result.rows[1].extra_payment, 20_000)
        self.assertLessEqual(result.final_balance, 0.01)

    def test_extra_payment_recalculates_future_installment_when_selected(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=6, annual_rate=0.10, rate_unit="EP",
            extra_payments=(ExtraPayment(2, 20_000),),
            extra_strategy="installment",
        ))
        self.assertEqual(result.rows[1].extra_payment, 20_000)
        self.assertLess(result.rows[2].payment, result.rows[1].payment)
        self.assertAlmostEqual(result.final_balance, 0, places=5)

    def test_extra_payment_after_early_payoff_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "después de que el crédito ya se liquida"):
            simulate(LoanConfig(
                principal=100_000, periods=3, annual_rate=0, rate_unit="EP",
                extra_payments=(ExtraPayment(1, 100_000), ExtraPayment(3, 1_000)),
            ))

    def test_growing_and_custom_decreasing_payments_amortize(self):
        for mode, growth in (("growing", 0.05), ("custom_decreasing", 0.05)):
            with self.subTest(mode=mode):
                result = simulate(LoanConfig(
                    principal=50_000, periods=5, annual_rate=0.08, rate_unit="EP",
                    amortization=mode, growth_rate=growth,
                ))
                self.assertAlmostEqual(result.final_balance, 0, places=5)

    def test_summary_totals_reconcile_with_amortization_rows(self):
        result = simulate(LoanConfig(
            principal=123_456, periods=8, annual_rate=0.14, rate_unit="EA",
            frequency_months=3, grace="principal", grace_periods=2,
            extra_payments=(ExtraPayment(4, 2_500),),
        ))
        self.assertAlmostEqual(sum(row.interest for row in result.rows),
                               result.total_interest, places=6)
        self.assertAlmostEqual(sum(row.payment for row in result.rows),
                               result.total_paid, places=6)
        self.assertAlmostEqual(result.rows[-1].closing_balance,
                               result.final_balance, places=6)

    def test_invalid_rate_change_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "dentro del plazo"):
            simulate(LoanConfig(
                principal=1000, periods=3, annual_rate=0.1, rate_unit="EP",
                rate_changes=((4, 0.2),),
            ))


class CompatibilityTests(unittest.TestCase):
    def test_amortization_frequency_grace_and_payment_moment_matrix(self):
        amortizations = ("fixed", "constant_principal", "growing", "custom_decreasing", "bullet")
        for amortization in amortizations:
            for frequency in (1, 2, 3, 4, 6, 12):
                for grace in ("none", "principal", "total"):
                    for moment in ("arrears", "advance"):
                        with self.subTest(
                            amortization=amortization, frequency=frequency,
                            grace=grace, moment=moment,
                        ):
                            config = LoanConfig(
                                principal=100_000, periods=4, annual_rate=0.1,
                                frequency_months=frequency, amortization=amortization,
                                payment_moment=moment, grace=grace,
                                grace_periods=0 if grace == "none" else 1,
                            )
                            if amortization == "bullet" and moment == "advance":
                                with self.assertRaisesRegex(ValueError, "al vencimiento"):
                                    validate_compatibility(config)
                            else:
                                validate_compatibility(config)

    def test_amortization_and_extra_payment_strategy_matrix(self):
        for amortization in ("fixed", "constant_principal", "growing", "custom_decreasing", "bullet"):
            for strategy in ("term", "installment"):
                with self.subTest(amortization=amortization, strategy=strategy):
                    config = LoanConfig(
                        principal=100_000, periods=4, annual_rate=0.1,
                        amortization=amortization, extra_strategy=strategy,
                        extra_payments=(ExtraPayment(3, 1_000),),
                    )
                    incompatible = (
                        amortization == "bullet"
                        or (amortization == "constant_principal" and strategy == "installment")
                    )
                    if incompatible:
                        with self.assertRaises(ValueError):
                            validate_compatibility(config)
                    else:
                        validate_compatibility(config)

    def test_grace_period_extra_payment_requires_installment_reduction(self):
        config = LoanConfig(
            principal=100_000, periods=5, annual_rate=0.1,
            grace="total", grace_periods=2,
            extra_payments=(ExtraPayment(2, 1_000),),
        )
        with self.assertRaisesRegex(ValueError, "durante la gracia"):
            validate_compatibility(config)
        validate_compatibility(
            LoanConfig(
                principal=100_000, periods=5, annual_rate=0.1,
                grace="total", grace_periods=2,
                extra_payments=(ExtraPayment(2, 1_000),), extra_strategy="installment",
            )
        )

    def test_rate_type_requires_compatible_rate_changes(self):
        config = LoanConfig(
            principal=100_000, periods=4, annual_rate=0.1,
            rate_changes=((3, 0.12),),
        )
        with self.assertRaisesRegex(ValueError, "tasa fija"):
            validate_compatibility(config, "Fija")
        with self.assertRaisesRegex(ValueError, "Agrega al menos un cambio"):
            validate_compatibility(
                LoanConfig(principal=100_000, periods=4, annual_rate=0.1), "Escalonada"
            )
        with self.assertRaisesRegex(ValueError, "tipo de tasa"):
            validate_compatibility(config, "Variable")
        validate_compatibility(config, "Escalonada")


class RecommendationTests(unittest.TestCase):
    def test_three_recommendations_are_real_valid_simulations(self):
        config = LoanConfig(
            principal=100_000, periods=12, annual_rate=0.12, rate_unit="EA",
        )
        original_result = simulate(config)
        recommendations = recommend_loans(config)
        self.assertEqual([item.category for item in recommendations], [
            "Menor costo", "Menor tiempo", "Equilibrada",
        ])
        for item in recommendations:
            with self.subTest(category=item.category):
                self.assertEqual(item.result, simulate(item.config))
                self.assertAlmostEqual(item.result.final_balance, 0, places=2)
                self.assertEqual(item.config.rate_unit, "EA")
                self.assertEqual(item.config.grace, config.grace)
                self.assertEqual(item.config.extra_payments, config.extra_payments)
        self.assertEqual(simulate(config), original_result)
        cheapest_key = (
            recommendations[0].config.amortization,
            recommendations[0].config.frequency_months,
            recommendations[0].config.payment_moment,
        )
        fastest_key = (
            recommendations[1].config.amortization,
            recommendations[1].config.frequency_months,
            recommendations[1].config.payment_moment,
        )
        balanced_key = (
            recommendations[2].config.amortization,
            recommendations[2].config.frequency_months,
            recommendations[2].config.payment_moment,
        )
        if cheapest_key == fastest_key:
            self.assertEqual(balanced_key, cheapest_key)

    def test_recommendation_categories_match_cost_and_calendar_time(self):
        principal, periods, annual_rate = 25_000_000, 24, 0.18
        reference_config = LoanConfig(
            principal=principal, periods=periods, annual_rate=annual_rate,
        )
        recommendations = recommend_loans(reference_config)
        candidates = []
        amortizations = ("fixed", "constant_principal", "growing", "custom_decreasing", "bullet")
        for frequency in (1, 2, 3, 4, 6, 12):
            for amortization in amortizations:
                moments = ("arrears",) if amortization == "bullet" else ("arrears", "advance")
                for moment in moments:
                    config = LoanConfig(
                        principal=principal, periods=periods, annual_rate=annual_rate,
                        frequency_months=frequency, amortization=amortization,
                        payment_moment=moment, growth_rate=0.02,
                    )
                    try:
                        result = simulate(config)
                    except (ValueError, OverflowError):
                        continue
                    if result.final_balance > max(0.01, principal * 1e-10):
                        continue
                    elapsed = result.actual_periods * frequency
                    if moment == "advance":
                        elapsed = max(0, elapsed - frequency)
                    candidates.append((config, result, elapsed))
        cheapest = min(candidates, key=lambda item: (item[1].total_paid, item[2]))
        fastest = min(candidates, key=lambda item: (item[2], item[1].total_paid))
        self.assertEqual(recommendations[0].config, cheapest[0])
        self.assertEqual(recommendations[1].config, fastest[0])
        self.assertAlmostEqual(recommendations[0].result.total_paid, cheapest[1].total_paid)
        self.assertEqual(recommendations[1].elapsed_months, fastest[2])
        minimum_cost = min(item[1].total_paid for item in candidates)
        maximum_cost = max(item[1].total_paid for item in candidates)
        minimum_time = min(item[2] for item in candidates)
        maximum_time = max(item[2] for item in candidates)

        def balance_score(item):
            cost_range = maximum_cost - minimum_cost
            time_range = maximum_time - minimum_time
            cost_score = (item[1].total_paid - minimum_cost) / cost_range if cost_range else 0
            time_score = (item[2] - minimum_time) / time_range if time_range else 0
            return (cost_score + time_score) / 2, item[1].total_paid, item[2]

        balanced = min(candidates, key=balance_score)
        self.assertEqual(recommendations[2].config, balanced[0])
        self.assertEqual(recommendations[0].config, recommendations[1].config)
        self.assertEqual(recommendations[1].config, recommendations[2].config)

    def test_period_rate_recommendations_preserve_effective_annual_rate(self):
        rate = 0.01
        annual_equivalent = (1 + rate) ** 12 - 1
        from_period_rate = recommend_loans(LoanConfig(
            100_000, 8, rate, rate_unit="EP", frequency_months=1,
        ))
        from_annual_rate = recommend_loans(LoanConfig(
            100_000, 8, annual_equivalent, rate_unit="EA", frequency_months=1,
        ))
        self.assertEqual(
            [(item.config, item.result.total_paid) for item in from_period_rate],
            [(item.config, item.result.total_paid) for item in from_annual_rate],
        )

    def test_recommendations_preserve_advanced_settings_and_simulation_metrics(self):
        config = LoanConfig(
            principal=100_000,
            periods=8,
            annual_rate=0.01,
            rate_unit="EP",
            frequency_months=2,
            amortization="growing",
            payment_moment="advance",
            grace="principal",
            grace_periods=1,
            growth_rate=0.03,
            rate_changes=((4, 0.015),),
            extra_payments=(ExtraPayment(3, 5_000),),
            extra_strategy="installment",
        )
        original_result = simulate(config)
        recommendations = recommend_loans(config)
        expected_annual_change = (1 + 0.015) ** 6 - 1

        for item in recommendations:
            candidate = item.config
            with self.subTest(category=item.category):
                self.assertEqual(candidate.grace, "principal")
                self.assertEqual(candidate.grace_periods, 1)
                self.assertEqual(candidate.growth_rate, 0.03)
                self.assertEqual(candidate.rate_changes, ((4, expected_annual_change),))
                self.assertEqual(candidate.extra_payments, config.extra_payments)
                self.assertEqual(candidate.extra_strategy, "installment")
                self.assertEqual(candidate.rate_unit, "EA")
                self.assertNotEqual(candidate.amortization, "bullet")
                self.assertNotEqual(candidate.amortization, "constant_principal")
                self.assertEqual(item.result, simulate(candidate))
                expected_elapsed = item.result.actual_periods * candidate.frequency_months
                if candidate.payment_moment == "advance":
                    expected_elapsed = max(0, expected_elapsed - candidate.frequency_months)
                self.assertEqual(item.elapsed_months, expected_elapsed)
        self.assertEqual(simulate(config), original_result)

    def test_initial_installment_excludes_extra_payment(self):
        result = simulate(LoanConfig(
            principal=100_000, periods=6, annual_rate=0.10, rate_unit="EP",
            extra_payments=(ExtraPayment(1, 20_000),),
        ))
        self.assertAlmostEqual(
            result.initial_payment,
            result.rows[0].payment - result.rows[0].extra_payment,
            places=6,
        )


if __name__ == "__main__":
    unittest.main()
