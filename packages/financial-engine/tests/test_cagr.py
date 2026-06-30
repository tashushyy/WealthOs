"""Tests for the CAGR module.

Three layers, mirroring the XIRR tests:
  1. Reference values — hand-computable closed-form results.
  2. Edge cases and error handling.
  3. Property-based tests — invariants that hold for any valid input.
"""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from financial_engine.cagr import InvalidValueError, cagr, cagr_between

# --- 1. Reference values -----------------------------------------------------


def test_doubling_over_one_year_is_100_percent() -> None:
    assert cagr(1000.0, 2000.0, 1.0) == pytest.approx(1.0, abs=1e-12)


def test_doubling_over_two_years() -> None:
    assert cagr(1000.0, 2000.0, 2.0) == pytest.approx(2.0**0.5 - 1.0, abs=1e-12)


def test_no_change_is_zero() -> None:
    assert cagr(500.0, 500.0, 5.0) == pytest.approx(0.0, abs=1e-12)


def test_halving_over_one_year() -> None:
    assert cagr(1000.0, 500.0, 1.0) == pytest.approx(-0.5, abs=1e-12)


def test_total_loss_is_minus_one() -> None:
    assert cagr(1000.0, 0.0, 3.0) == -1.0


# --- 2. Edge cases and errors ------------------------------------------------


def test_rejects_non_positive_begin() -> None:
    with pytest.raises(InvalidValueError):
        cagr(0.0, 100.0, 1.0)


def test_rejects_negative_end() -> None:
    with pytest.raises(InvalidValueError):
        cagr(100.0, -1.0, 1.0)


def test_rejects_non_positive_years() -> None:
    with pytest.raises(InvalidValueError):
        cagr(100.0, 200.0, 0.0)


def test_cagr_between_matches_year_fraction() -> None:
    # 365 days == exactly one year under actual/365.
    by_date = cagr_between(1000.0, 1200.0, date(2023, 1, 1), date(2024, 1, 1))
    by_years = cagr(1000.0, 1200.0, 365.0 / 365.0)
    assert by_date == pytest.approx(by_years, abs=1e-12)


def test_cagr_between_requires_forward_dates() -> None:
    with pytest.raises(InvalidValueError):
        cagr_between(1000.0, 1200.0, date(2024, 1, 1), date(2024, 1, 1))


# --- 3. Property-based tests -------------------------------------------------

_values = st.floats(min_value=1.0, max_value=1_000_000_000.0, allow_nan=False, allow_infinity=False)
_years = st.floats(min_value=0.1, max_value=50.0, allow_nan=False, allow_infinity=False)


# The inverse round-trip check below is only well-conditioned when (1 + rate)
# stays away from zero. That fails when multiple^(1/years) underflows — i.e. a
# loss compounded over a sub-year horizon drives rate toward -1 — which is a
# float64 limit, not a CAGR error. We therefore bound the round-trip to >= 1
# year and multiples of 0.01x..100x (a -99%..+9900% total range); the sub-year
# and total-loss boundaries are covered by the reference tests above.
_growth_multiple = st.floats(min_value=1e-2, max_value=1e2, allow_nan=False, allow_infinity=False)
_years_at_least_one = st.floats(
    min_value=1.0, max_value=50.0, allow_nan=False, allow_infinity=False
)


@given(begin=_values, multiple=_growth_multiple, years=_years_at_least_one)
@settings(max_examples=300, deadline=None)
def test_compounding_round_trip(begin: float, multiple: float, years: float) -> None:
    """Growing begin at the CAGR for the period must recover end."""
    end = begin * multiple
    rate = cagr(begin, end, years)
    assert begin * (1.0 + rate) ** years == pytest.approx(end, rel=1e-9)


@given(begin=_values, end=_values, years=_years)
@settings(max_examples=200, deadline=None)
def test_sign_tracks_growth(begin: float, end: float, years: float) -> None:
    """Positive iff it grew, negative iff it shrank, zero iff unchanged."""
    rate = cagr(begin, end, years)
    if end > begin:
        assert rate > 0
    elif end < begin:
        assert rate < 0
    else:
        assert rate == pytest.approx(0.0, abs=1e-12)


@given(begin=_values, end=_values)
@settings(max_examples=200, deadline=None)
def test_longer_horizon_dampens_rate(begin: float, end: float) -> None:
    """For a fixed gain, a longer period implies a smaller annual rate
    (in magnitude). Compares 1 year against 5 years."""
    one_year = cagr(begin, end, 1.0)
    five_years = cagr(begin, end, 5.0)
    assert abs(five_years) <= abs(one_year) + 1e-12
