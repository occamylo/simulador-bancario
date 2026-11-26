"""Financial calculations for the bank-credit simulator."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
import math
from typing import Literal


Frequency = Literal[1, 2, 3, 4, 6, 12]
Amortization = Literal["fixed", "constant_principal", "growing", "custom_decreasing", "bullet"]
PaymentMoment = Literal["arrears", "advance"]
Grace = Literal["none", "principal", "total"]
ExtraStrategy = Literal["term", "installment"]


def validate_compatibility(config: LoanConfig, rate_type: str | None = None) -> None:
    """Reject combinations whose selected behavior is not represented by the model."""
    if rate_type is not None and rate_type not in ("Fija", "Escalonada"):
        raise ValueError("El tipo de tasa seleccionado no es válido.")
    if rate_type == "Fija" and config.rate_changes:
        raise ValueError("Una tasa fija no admite cambios programados.")
    if rate_type == "Escalonada" and not config.rate_changes:
        raise ValueError("Agrega al menos un cambio de tasa para una tasa escalonada.")
    if config.amortization == "bullet":
        if config.payment_moment == "advance":
            raise ValueError("El pago único se realiza al vencimiento; no admite pagos anticipados.")
        if config.extra_payments:
            raise ValueError("El pago único no admite abonos extraordinarios ni estrategias de reducción.")
    if config.amortization == "constant_principal" and config.extra_strategy == "installment":
        if config.extra_payments:
            raise ValueError("El abono a capital fijo no admite reducción de cuota; selecciona reducir plazo.")
    if config.grace != "none" and config.extra_strategy == "term":
        if any(extra.period <= config.grace_periods for extra in config.extra_payments):
            raise ValueError(
                "Un abono durante la gracia modifica el saldo antes de iniciar las cuotas. "
                "Selecciona «Reducir cuota» o programa el abono después de la gracia."
            )


@dataclass(frozen=True)
class ExtraPayment:
    period: int
    amount: float


@dataclass(frozen=True)
class LoanConfig:
    principal: float
    periods: int
    annual_rate: float
    rate_unit: str = "EA"
    frequency_months: Frequency = 1
    amortization: Amortization = "fixed"
    payment_moment: PaymentMoment = "arrears"
    grace: Grace = "none"
    grace_periods: int = 0
    growth_rate: float = 0.0
    rate_changes: tuple[tuple[int, float], ...] = ()
    extra_payments: tuple[ExtraPayment, ...] = ()
    extra_strategy: ExtraStrategy = "term"


@dataclass(frozen=True)
class AmortizationRow:
    period: int
    opening_balance: float
    interest: float
    principal_paid: float
    payment: float
    extra_payment: float
    closing_balance: float
    rate: float
    note: str = ""


@dataclass(frozen=True)
class SimulationResult:
    rows: tuple[AmortizationRow, ...]
    initial_payment: float
    final_payment: float
    total_interest: float
    total_paid: float
    final_balance: float
    effective_periodic_rate: float
    actual_periods: int


@dataclass(frozen=True)
class LoanRecommendation:
    category: str
    config: LoanConfig
    result: SimulationResult
    elapsed_months: int


def _validate(config: LoanConfig) -> None:
    if not math.isfinite(config.principal) or config.principal <= 0:
        raise ValueError("El monto del crédito debe ser mayor que cero.")
    if not isinstance(config.periods, int) or config.periods < 1:
        raise ValueError("El plazo debe ser de al menos un periodo.")
    if config.frequency_months not in (1, 2, 3, 4, 6, 12):
        raise ValueError("La periodicidad seleccionada no es válida.")
    if config.rate_unit not in ("EA", "EM", "EP"):
        raise ValueError("La unidad de tasa debe ser EA, EM o EP.")
    if not math.isfinite(config.annual_rate) or config.annual_rate <= -1:
        raise ValueError("La tasa debe ser un valor finito superior a -100%.")
    if config.amortization not in ("fixed", "constant_principal", "growing", "custom_decreasing", "bullet"):
        raise ValueError("La modalidad de amortización no es válida.")
    if config.grace not in ("none", "principal", "total"):
        raise ValueError("El tipo de diferimiento no es válido.")
    if config.payment_moment not in ("arrears", "advance"):
        raise ValueError("El momento del pago no es válido.")
    if config.grace == "none" and config.grace_periods != 0:
        raise ValueError("No indique periodos de gracia si no hay diferimiento.")
    if config.grace != "none" and not 1 <= config.grace_periods < config.periods:
        raise ValueError("El diferimiento debe ser menor que el plazo.")
    if not math.isfinite(config.growth_rate) or not 0 <= config.growth_rate < 1:
        raise ValueError("El cambio por cuota debe estar entre 0% y 99,9%.")
    for start_period, rate in config.rate_changes:
        if not isinstance(start_period, int) or not 1 <= start_period <= config.periods:
            raise ValueError("Los cambios de tasa deben indicar periodos dentro del plazo.")
        if not math.isfinite(rate) or rate <= -1:
            raise ValueError("Cada tasa debe ser finita y superior a -100%.")
    if len({period for period, _ in config.rate_changes}) != len(config.rate_changes):
        raise ValueError("No puede definir más de una tasa para el mismo periodo.")
    for extra in config.extra_payments:
        if not isinstance(extra.period, int) or not 1 <= extra.period <= config.periods:
            raise ValueError("Cada abono extraordinario debe estar dentro del plazo.")
        if not math.isfinite(extra.amount) or extra.amount <= 0:
            raise ValueError("Los abonos extraordinarios deben ser mayores que cero.")
    validate_compatibility(config)


def periodic_rate(rate: float, unit: str, frequency_months: int) -> float:
    """Convert an effective annual, monthly, or loan-period rate."""
    if unit == "EA":
        return (1 + rate) ** (frequency_months / 12) - 1
    if unit == "EM":
        return (1 + rate) ** frequency_months - 1
    if unit == "EP":
        return rate
    raise ValueError("Unidad de tasa no reconocida.")


def _annual_equivalent_rate(rate: float, unit: str, frequency_months: int) -> float:
    if unit == "EA":
        return rate
    if unit == "EM":
        return (1 + rate) ** 12 - 1
    if unit == "EP":
        return (1 + rate) ** (12 / frequency_months) - 1
    raise ValueError("Unidad de tasa no reconocida.")


def _period_rates(config: LoanConfig) -> list[float]:
    base = periodic_rate(config.annual_rate, config.rate_unit, config.frequency_months)
    changes = sorted(config.rate_changes)
    rates: list[float] = []
    current = base
    change_index = 0
    for period in range(1, config.periods + 1):
        while change_index < len(changes) and changes[change_index][0] == period:
            current = periodic_rate(changes[change_index][1], config.rate_unit, config.frequency_months)
            change_index += 1
        rates.append(current)
    return rates


def _payment_sequence(base: float, count: int, config: LoanConfig) -> list[float]:
    if config.amortization == "growing":
        factor = 1 + config.growth_rate
        return [base * factor**index for index in range(count)]
    if config.amortization == "custom_decreasing":
        factor = 1 - config.growth_rate
        return [base * factor**index for index in range(count)]
    return [base] * count


def _simulate_level_payments(
    balance: float,
    rates: list[float],
    config: LoanConfig,
    base_payment: float,
) -> float:
    payments = _payment_sequence(base_payment, len(rates), config)
    total = balance
    for index, rate in enumerate(rates):
        if config.payment_moment == "arrears":
            total *= 1 + rate
        elif index > 0:
            total *= 1 + rates[index - 1]
        total -= payments[index]
    return total


def _solve_payment(balance: float, rates: list[float], config: LoanConfig) -> float:
    if balance <= 0 or not rates:
        return 0.0
    if config.amortization == "bullet":
        return 0.0
    if config.amortization == "constant_principal":
        return balance / len(rates)

    low, high = 0.0, max(balance, 1.0)
    while _simulate_level_payments(balance, rates, config, high) > 0:
        high *= 2
        if high > balance * 1e12:
            raise ValueError("No fue posible encontrar una cuota que amortice el crédito.")
    for _ in range(100):
        middle = (low + high) / 2
        if _simulate_level_payments(balance, rates, config, middle) > 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def simulate(config: LoanConfig) -> SimulationResult:
    """Simulate a loan and return a complete amortization table."""
    _validate(config)
    rates = _period_rates(config)
    grace_count = config.grace_periods if config.grace != "none" else 0
    payment_count = config.periods - grace_count
    balance = config.principal
    rows: list[AmortizationRow] = []
    total_interest = 0.0
    total_paid = 0.0
    extras: dict[int, float] = {}
    for extra in config.extra_payments:
        extras[extra.period] = extras.get(extra.period, 0.0) + extra.amount

    for period in range(1, grace_count + 1):
        opening = balance
        interest = balance * rates[period - 1]
        total_interest += interest
        if config.grace == "principal":
            payment = interest
            principal_paid = 0.0
            note = "Gracia de capital"
        else:
            balance += interest
            payment = 0.0
            principal_paid = 0.0
            note = "Diferimiento; interés capitalizado"
        extra = min(extras.get(period, 0.0), balance)
        balance = max(balance - extra, 0.0)
        principal_paid += extra
        payment += extra
        if extra > 0:
            note += " · abono extraordinario"
        total_paid += payment
        rows.append(AmortizationRow(
            period, opening, interest, principal_paid, payment, extra,
            max(balance, 0.0), rates[period - 1], note,
        ))

    remaining_rates = rates[grace_count:]
    scheduled_payment = _solve_payment(balance, remaining_rates, config)
    scheduled_payments = _payment_sequence(scheduled_payment, payment_count, config)
    initial_payment = 0.0
    actual_periods = 0

    if config.amortization == "bullet":
        for index, rate in enumerate(remaining_rates):
            period = grace_count + index + 1
            opening = balance
            interest = balance * rate
            total_interest += interest
            balance += interest
            is_final = index == len(remaining_rates) - 1
            payment = balance if is_final else 0.0
            principal_paid = max(payment - interest, 0.0)
            balance = max(balance - payment, 0.0)
            extra = min(extras.get(period, 0.0), balance)
            balance -= extra
            total_paid += payment + extra
            actual_periods = period
            if not initial_payment and payment:
                initial_payment = payment
            rows.append(AmortizationRow(
                period, opening, interest, principal_paid, payment + extra, extra,
                balance, rate, "Pago único" if is_final else "Capitalización compuesta",
            ))
    else:
        for index, rate in enumerate(remaining_rates):
            period = grace_count + index + 1
            if balance <= 0.005:
                break

            opening = balance
            if config.payment_moment == "arrears":
                interest = balance * rate
            elif index == 0:
                interest = 0.0
            else:
                interest = balance * remaining_rates[index - 1]
            total_interest += interest
            balance += interest

            if config.amortization == "constant_principal":
                principal_target = opening / max(1, len(remaining_rates) - index)
                regular_payment = min(balance, interest + principal_target)
            else:
                regular_payment = scheduled_payments[index]
            regular_payment = min(regular_payment, balance)
            principal_paid = max(regular_payment - interest, 0.0)
            balance = max(balance - regular_payment, 0.0)

            extra_requested = extras.get(period, 0.0)
            extra = min(extra_requested, balance)
            balance = max(balance - extra, 0.0)
            payment = regular_payment + extra
            total_paid += payment
            actual_periods = period
            if initial_payment == 0.0 and regular_payment > 0:
                initial_payment = regular_payment
            note = ""
            if extra > 0:
                note = "Abono extraordinario"
                if config.extra_strategy == "installment" and balance > 0.005:
                    next_count = len(remaining_rates) - index - 1
                    rate_start = index if config.payment_moment == "advance" else index + 1
                    future_rates = remaining_rates[rate_start:rate_start + next_count]
                    future_config = replace(config, payment_moment="arrears")
                    scheduled_payment = _solve_payment(balance, future_rates, future_config)
                    payment_count = len(future_rates)
                    for future_index, future_payment in enumerate(
                        _payment_sequence(scheduled_payment, payment_count, config),
                        start=index + 1,
                    ):
                        scheduled_payments[future_index] = future_payment
            rows.append(AmortizationRow(
                period, opening, interest, principal_paid, payment, extra,
                balance, rate, note,
            ))

    recorded_periods = {row.period for row in rows}
    unapplied_periods = sorted(period for period in extras if period not in recorded_periods)
    if unapplied_periods:
        raise ValueError(
            "Un abono extraordinario está programado después de que el crédito ya se liquida "
            f"(periodo {unapplied_periods[0]}). Ajusta el periodo del abono."
        )

    final_payment = next((row.payment for row in reversed(rows) if row.payment > 0), 0.0)
    final_balance = max(balance, 0.0)
    tolerance = max(0.01, config.principal * 1e-10)
    if final_balance > tolerance and config.extra_strategy == "installment" and extras:
        raise ValueError("Los abonos no alcanzan a amortizar el saldo dentro del plazo.")

    return SimulationResult(
        tuple(rows), initial_payment, final_payment, total_interest, total_paid,
        final_balance, rates[0], actual_periods,
    )


def recommend_loans(
    reference_config: LoanConfig,
) -> tuple[LoanRecommendation, ...]:
    """Compare valid schedules while preserving the configured advanced settings."""
    _validate(reference_config)
    annual_rate = _annual_equivalent_rate(
        reference_config.annual_rate,
        reference_config.rate_unit,
        reference_config.frequency_months,
    )
    annual_rate_changes = tuple(
        (
            period,
            _annual_equivalent_rate(
                rate, reference_config.rate_unit, reference_config.frequency_months,
            ),
        )
        for period, rate in reference_config.rate_changes
    )
    if not math.isfinite(annual_rate) or any(
        not math.isfinite(rate) for _, rate in annual_rate_changes
    ):
        raise ValueError("Una tasa equivalente anual para las recomendaciones no es finita.")

    candidates: list[LoanRecommendation] = []
    amortizations = (
        "fixed", "constant_principal", "growing", "custom_decreasing", "bullet",
    )
    growth_rate = (
        reference_config.growth_rate
        if reference_config.amortization in ("growing", "custom_decreasing")
        else 0.02
    )
    for frequency in (1, 2, 3, 4, 6, 12):
        for amortization in amortizations:
            moments = ("arrears",) if amortization == "bullet" else ("arrears", "advance")
            for moment in moments:
                config = LoanConfig(
                    principal=reference_config.principal,
                    periods=reference_config.periods,
                    annual_rate=annual_rate,
                    rate_unit="EA",
                    frequency_months=frequency,
                    amortization=amortization,  # type: ignore[arg-type]
                    payment_moment=moment,  # type: ignore[arg-type]
                    grace=reference_config.grace,
                    grace_periods=reference_config.grace_periods,
                    growth_rate=growth_rate,
                    rate_changes=annual_rate_changes,
                    extra_payments=reference_config.extra_payments,
                    extra_strategy=reference_config.extra_strategy,
                )
                try:
                    result = simulate(config)
                except (ValueError, OverflowError):
                    continue
                if result.final_balance > max(0.01, reference_config.principal * 1e-10):
                    continue
                elapsed_months = result.actual_periods * frequency
                if moment == "advance":
                    elapsed_months = max(0, elapsed_months - frequency)
                candidates.append(LoanRecommendation(
                    "", config, result, elapsed_months,
                ))

    if not candidates:
        raise ValueError("No se encontraron configuraciones válidas para recomendar con estos datos.")

    cheapest = min(candidates, key=lambda item: (item.result.total_paid, item.elapsed_months))
    fastest = min(candidates, key=lambda item: (item.elapsed_months, item.result.total_paid))

    minimum_cost = min(item.result.total_paid for item in candidates)
    maximum_cost = max(item.result.total_paid for item in candidates)
    minimum_time = min(item.elapsed_months for item in candidates)
    maximum_time = max(item.elapsed_months for item in candidates)
    cost_range = maximum_cost - minimum_cost
    time_range = maximum_time - minimum_time

    def balance_score(item: LoanRecommendation) -> tuple[float, float, int]:
        cost_score = (
            (item.result.total_paid - minimum_cost) / cost_range if cost_range else 0.0
        )
        time_score = (
            (item.elapsed_months - minimum_time) / time_range if time_range else 0.0
        )
        return (cost_score + time_score) / 2, item.result.total_paid, item.elapsed_months

    balanced = min(candidates, key=balance_score)
    return (
        LoanRecommendation("Menor costo", cheapest.config, cheapest.result, cheapest.elapsed_months),
        LoanRecommendation("Menor tiempo", fastest.config, fastest.result, fastest.elapsed_months),
        LoanRecommendation("Equilibrada", balanced.config, balanced.result, balanced.elapsed_months),
    )
