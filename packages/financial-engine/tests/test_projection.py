"""Tests for the projection module.

Three layers, mirroring the other engine modules:
  1. Reference values — hand-computable results.
  2. Edge cases and error handling.
  3. Property-based tests — invariants that hold for any valid input.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from financial_engine.projection import (
    InvalidParameterError,
    future_value,
    projection_schedule,
)

# --- 1. Reference values -----------------------------------------------------


def test_contributions_only_zero_return() -> None:
    # 100/month for 12 months, no growth -> 1200.
    assert future_value(0.0, 100.0, 0.0, 1) == pytest.approx(1200.0, abs=1e-9)


def test_lump_sum_only_grows_at_annual_rate() -> None:
    # Twelve months of effective monthly compounding reproduces +10% a year.
    assert future_value(1000.0, 0.0, 0.10, 1) == pytest.approx(1100.0, abs=1e-6)


def test_step_up_reference() -> None:
    # Year 1: 12 * 100 = 1200. Year 2 contribution steps to 110: 12 * 110 = 1320.
    # Zero return, so the total is just the contributions: 2520.
    assert future_value(0.0, 100.0, 0.0, 2, annual_step_up=0.10) == pytest.approx(2520.0, abs=1e-9)


def test_everything_zero_is_zero() -> None:
    assert future_value(0.0, 0.0, 0.05, 10) == 0.0


# --- 2. Edge cases and errors ------------------------------------------------


def test_rejects_negative_principal() -> None:
    with pytest.raises(InvalidParameterError):
        future_value(-1.0, 100.0, 0.1, 1)


def test_rejects_negative_contribution() -> None:
    with pytest.raises(InvalidParameterError):
        future_value(1000.0, -1.0, 0.1, 1)


def test_rejects_return_at_or_below_minus_one() -> None:
    with pytest.raises(InvalidParameterError):
        future_value(1000.0, 0.0, -1.0, 1)


def test_rejects_non_positive_years() -> None:
    with pytest.raises(InvalidParameterError):
        future_value(1000.0, 0.0, 0.1, 0)


def test_rejects_negative_step_up() -> None:
    with pytest.raises(InvalidParameterError):
        future_value(1000.0, 100.0, 0.1, 5, annual_step_up=-0.1)


def test_schedule_has_one_entry_per_year() -> None:
    schedule = projection_schedule(1000.0, 100.0, 0.1, 5)
    assert [s.year for s in schedule] == [1, 2, 3, 4, 5]


# --- 3. Property-based tests -------------------------------------------------

_principal = st.floats(min_value=0.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False)
_contribution = st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False)
_return = st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)
_years = st.integers(min_value=1, max_value=40)
_step_up = st.floats(min_value=0.0, max_value=0.25, allow_nan=False, allow_infinity=False)


@given(principal=_principal, contribution=_contribution, years=_years)
@settings(max_examples=200, deadline=None)
def test_zero_return_is_just_money_in(principal: float, contribution: float, years: int) -> None:
    """With no growth, value == principal + every contribution made."""
    value = future_value(principal, contribution, 0.0, years)
    expected = principal + contribution * 12 * years
    assert value == pytest.approx(expected, rel=1e-9, abs=1e-6)


@given(
    principal=_principal,
    contribution=_contribution,
    years=_years,
    step_up=_step_up,
    low=_return,
    delta=st.floats(min_value=0.0, max_value=0.5),
)
@settings(max_examples=200, deadline=None)
def test_monotonic_in_return(
    principal: float, contribution: float, years: int, step_up: float, low: float, delta: float
) -> None:
    """A higher return never produces a lower value."""
    high = low + delta
    fv_low = future_value(principal, contribution, low, years, step_up)
    fv_high = future_value(principal, contribution, high, years, step_up)
    assert fv_high >= fv_low - 1e-6


@given(
    principal=_principal,
    contribution=_contribution,
    years=_years,
    annual_return=_return,
    extra=st.floats(min_value=0.0, max_value=100_000.0),
)
@settings(max_examples=200, deadline=None)
def test_monotonic_in_contribution(
    principal: float, contribution: float, years: int, annual_return: float, extra: float
) -> None:
    """Contributing more never produces a lower value."""
    fv_base = future_value(principal, contribution, annual_return, years)
    fv_more = future_value(principal, contribution + extra, annual_return, years)
    assert fv_more >= fv_base - 1e-6


@given(
    principal=_principal,
    contribution=_contribution,
    annual_return=_return,
    years=_years,
    step_up=_step_up,
)
@settings(max_examples=200, deadline=None)
def test_schedule_last_matches_future_value(
    principal: float, contribution: float, annual_return: float, years: int, step_up: float
) -> None:
    """The schedule's final value equals future_value, and contributions
    accumulate monotonically."""
    schedule = projection_schedule(principal, contribution, annual_return, years, step_up)
    fv = future_value(principal, contribution, annual_return, years, step_up)
    assert schedule[-1].value == pytest.approx(fv, rel=1e-12)
    contributed = [s.contributed for s in schedule]
    assert contributed == sorted(contributed)
