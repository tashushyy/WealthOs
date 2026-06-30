"""Tests for the FIRE module.

Three layers, mirroring the other engine modules:
  1. Reference values — hand-computable results.
  2. Edge cases and error handling.
  3. Property-based tests — invariants that hold for any valid input.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from financial_engine.errors import InvalidParameterError
from financial_engine.fire import (
    barista_fire_number,
    coast_fire_number,
    fire_number,
    fire_progress,
    years_to_target,
)
from financial_engine.projection import projection_schedule

# --- 1. Reference values -----------------------------------------------------


def test_fire_number_is_25x_at_4_percent() -> None:
    assert fire_number(40_000.0) == pytest.approx(1_000_000.0, abs=1e-6)


def test_fire_number_default_matches_explicit() -> None:
    assert fire_number(40_000.0) == fire_number(40_000.0, 0.04)


def test_fire_number_scales_with_withdrawal_rate() -> None:
    assert fire_number(40_000.0, 0.05) == pytest.approx(800_000.0, abs=1e-6)


def test_coast_discounts_to_present_value() -> None:
    # 121 needed in 2 years at 10% -> 121 / 1.21 = 100 today.
    assert coast_fire_number(121.0, 0.10, 2.0) == pytest.approx(100.0, abs=1e-9)


def test_coast_with_no_growth_equals_target() -> None:
    assert coast_fire_number(1000.0, 0.0, 10.0) == pytest.approx(1000.0, abs=1e-9)


def test_barista_covers_only_the_gap() -> None:
    # 40k expenses, 20k from part-time, 4% -> 20k / 0.04 = 500k.
    assert barista_fire_number(40_000.0, 20_000.0, 0.04) == pytest.approx(500_000.0, abs=1e-6)


def test_barista_is_zero_when_income_covers_expenses() -> None:
    assert barista_fire_number(30_000.0, 40_000.0) == 0.0


def test_progress_is_ratio() -> None:
    assert fire_progress(250_000.0, 1_000_000.0) == pytest.approx(0.25, abs=1e-12)


def test_years_to_target_already_met_is_zero() -> None:
    assert years_to_target(1000.0, 0.0, 0.05, 1000.0) == 0


def test_years_to_target_reaches_in_one_year() -> None:
    # No growth, 100/month for a year = 1200 -> hits 1200 target at year 1.
    assert years_to_target(0.0, 100.0, 0.0, 1200.0) == 1


def test_years_to_target_unreachable_returns_none() -> None:
    # No contributions and no growth never reaches a positive target.
    assert years_to_target(0.0, 0.0, 0.0, 100.0, max_years=10) is None


# --- 2. Edge cases and errors ------------------------------------------------


def test_fire_number_rejects_negative_expenses() -> None:
    with pytest.raises(InvalidParameterError):
        fire_number(-1.0)


def test_fire_number_rejects_bad_withdrawal_rate() -> None:
    with pytest.raises(InvalidParameterError):
        fire_number(40_000.0, 0.0)
    with pytest.raises(InvalidParameterError):
        fire_number(40_000.0, 1.5)


def test_coast_rejects_negative_target() -> None:
    with pytest.raises(InvalidParameterError):
        coast_fire_number(-1.0, 0.05, 5.0)


def test_coast_rejects_return_at_or_below_minus_one() -> None:
    with pytest.raises(InvalidParameterError):
        coast_fire_number(1000.0, -1.0, 5.0)


def test_barista_rejects_negative_expenses() -> None:
    with pytest.raises(InvalidParameterError):
        barista_fire_number(-1.0, 1000.0)


def test_barista_rejects_bad_withdrawal_rate() -> None:
    with pytest.raises(InvalidParameterError):
        barista_fire_number(40_000.0, 20_000.0, 1.5)


def test_progress_rejects_negative_current() -> None:
    with pytest.raises(InvalidParameterError):
        fire_progress(-1.0, 1000.0)


def test_years_to_target_rejects_negative_target() -> None:
    with pytest.raises(InvalidParameterError):
        years_to_target(0.0, 100.0, 0.05, -1.0)


def test_coast_rejects_negative_years() -> None:
    with pytest.raises(InvalidParameterError):
        coast_fire_number(1000.0, 0.05, -1.0)


def test_barista_rejects_negative_income() -> None:
    with pytest.raises(InvalidParameterError):
        barista_fire_number(40_000.0, -1.0)


def test_progress_rejects_non_positive_target() -> None:
    with pytest.raises(InvalidParameterError):
        fire_progress(100.0, 0.0)


def test_years_to_target_rejects_non_positive_max_years() -> None:
    with pytest.raises(InvalidParameterError):
        years_to_target(0.0, 100.0, 0.05, 1000.0, max_years=0)


# --- 3. Property-based tests -------------------------------------------------

_money = st.floats(min_value=0.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False)
_positive_money = st.floats(
    min_value=1.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False
)
_withdrawal = st.floats(min_value=0.01, max_value=1.0, allow_nan=False, allow_infinity=False)
_return = st.floats(min_value=-0.3, max_value=0.3, allow_nan=False, allow_infinity=False)
_years = st.floats(min_value=0.0, max_value=40.0, allow_nan=False, allow_infinity=False)


@given(expenses=_money, rate=_withdrawal, factor=st.floats(min_value=0.0, max_value=10.0))
@settings(max_examples=200, deadline=None)
def test_fire_number_is_linear_in_expenses(expenses: float, rate: float, factor: float) -> None:
    """Scaling expenses scales the corpus by the same factor."""
    assert fire_number(expenses * factor, rate) == pytest.approx(
        fire_number(expenses, rate) * factor, rel=1e-9, abs=1e-6
    )


@given(target=_positive_money, annual_return=_return, years=_years)
@settings(max_examples=200, deadline=None)
def test_coast_round_trip(target: float, annual_return: float, years: float) -> None:
    """The coast number compounded forward recovers the target."""
    coast = coast_fire_number(target, annual_return, years)
    assert coast * (1.0 + annual_return) ** years == pytest.approx(target, rel=1e-9)


@given(expenses=_positive_money, income=_money, rate=_withdrawal, extra=_money)
@settings(max_examples=200, deadline=None)
def test_barista_decreases_with_income(
    expenses: float, income: float, rate: float, extra: float
) -> None:
    """More part-time income never increases the required corpus."""
    base = barista_fire_number(expenses, income, rate)
    more = barista_fire_number(expenses, income + extra, rate)
    assert more <= base + 1e-6


@given(
    current=_money,
    contribution=st.floats(min_value=0.0, max_value=100_000.0),
    annual_return=_return,
    target=_positive_money,
)
@settings(max_examples=200, deadline=None)
def test_years_to_target_actually_reaches(
    current: float, contribution: float, annual_return: float, target: float
) -> None:
    """When a year is returned, the projection at that year meets the target."""
    year = years_to_target(current, contribution, annual_return, target, max_years=80)
    if year is None or year == 0:
        return
    schedule = projection_schedule(current, contribution, annual_return, year)
    assert schedule[-1].value >= target
