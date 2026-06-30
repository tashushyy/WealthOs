"""Tests for the XIRR module.

Three layers:
  1. Reference values — match a known-good external implementation
     (Microsoft Excel's XIRR documentation example).
  2. Edge cases and error handling.
  3. Property-based tests — invariants that must hold for *any* valid input.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from financial_engine.xirr import (
    Cashflow,
    ConvergenceError,
    InvalidCashflowsError,
    _npv,
    _solve_bisection,
    _year_fractions,
    xirr,
)

# --- 1. Reference values -----------------------------------------------------


def test_matches_excel_documentation_example() -> None:
    """Microsoft's published XIRR example returns 0.373362535."""
    flows = [
        Cashflow(date(2008, 1, 1), -10000),
        Cashflow(date(2008, 3, 1), 2750),
        Cashflow(date(2008, 10, 30), 4250),
        Cashflow(date(2009, 2, 15), 3250),
        Cashflow(date(2009, 4, 1), 2750),
    ]
    assert xirr(flows) == pytest.approx(0.373362535, abs=1e-6)


def test_exact_one_year_double_digit() -> None:
    """-100 today, +110 in exactly 365 days -> 10% annualized."""
    flows = [
        Cashflow(date(2024, 1, 1), -100.0),
        Cashflow(date(2024, 12, 31), 110.0),  # 365 days (2024 is a leap year)
    ]
    assert xirr(flows) == pytest.approx(0.10, abs=1e-6)


def test_loss_produces_negative_rate() -> None:
    flows = [
        Cashflow(date(2023, 1, 1), -1000.0),
        Cashflow(date(2024, 1, 1), 900.0),  # 365 days, lost 10%
    ]
    rate = xirr(flows)
    assert rate == pytest.approx(-0.10, abs=1e-6)


# --- 2. Edge cases and errors ------------------------------------------------


def test_order_does_not_matter() -> None:
    forward = [
        Cashflow(date(2020, 1, 1), -5000),
        Cashflow(date(2021, 6, 1), 2000),
        Cashflow(date(2022, 1, 1), 4000),
    ]
    reverse = list(reversed(forward))
    assert xirr(forward) == pytest.approx(xirr(reverse), abs=1e-9)


def test_requires_two_cashflows() -> None:
    with pytest.raises(InvalidCashflowsError):
        xirr([Cashflow(date(2024, 1, 1), -100.0)])


def test_requires_a_sign_change() -> None:
    with pytest.raises(InvalidCashflowsError):
        xirr(
            [
                Cashflow(date(2024, 1, 1), -100.0),
                Cashflow(date(2025, 1, 1), -50.0),
            ]
        )


def test_unsolvable_series_raises_convergence_error() -> None:
    """All money out then a positive smaller than rounding can't bracket."""
    # Construct a pathological series with the same date so every discount
    # factor is 1 and NPV is constant (= sum of amounts) -> no root.
    flows = [
        Cashflow(date(2024, 1, 1), -100.0),
        Cashflow(date(2024, 1, 1), 50.0),
    ]
    with pytest.raises(ConvergenceError):
        xirr(flows)


def test_extreme_short_horizon_raises() -> None:
    """A multi-fold gain over a single day implies an annualized rate whose
    (1 + r) exceeds float64 range; we surface that as ConvergenceError rather
    than returning a meaningless number."""
    flows = [
        Cashflow(date(2024, 1, 1), -1.0),
        Cashflow(date(2024, 1, 2), 7.0),  # ~7x in one day
    ]
    with pytest.raises(ConvergenceError):
        xirr(flows)


def test_large_loss_reference() -> None:
    """A 95% loss over exactly one year annualizes to -95%.

    This pins the large-loss boundary: the rate is close to -1 but still
    comfortably representable, so the result stays accurate.
    """
    flows = [
        Cashflow(date(2023, 1, 1), -1000.0),
        Cashflow(date(2024, 1, 1), 50.0),  # 365 days, kept 5%
    ]
    assert xirr(flows) == pytest.approx(-0.95, abs=1e-6)


def test_bisection_fallback_agrees_with_reference() -> None:
    """The bisection fallback (used when Newton fails) must independently
    reproduce the reference result and zero out NPV."""
    flows = [
        Cashflow(date(2008, 1, 1), -10000),
        Cashflow(date(2008, 3, 1), 2750),
        Cashflow(date(2008, 10, 30), 4250),
        Cashflow(date(2009, 2, 15), 3250),
        Cashflow(date(2009, 4, 1), 2750),
    ]
    amounts = [cf.amount for cf in flows]
    years = _year_fractions([cf.on for cf in flows])
    rate = _solve_bisection(amounts, years)
    assert rate == pytest.approx(0.373362535, abs=1e-6)
    assert _npv(rate, amounts, years) == pytest.approx(0.0, abs=1e-3)


# --- 3. Property-based tests -------------------------------------------------

# A realistic investment series: one upfront outflow followed by later positive
# inflows on distinct, increasing dates.
# Economically meaningful, precision-safe domain. Two boundaries are excluded
# deliberately and covered by explicit edge-case tests instead:
#   * holding periods >= 90 days — sub-week horizons with large multiples imply
#     annualized rates beyond float64 range (test_extreme_short_horizon_raises).
#   * inflows of 5%..150% of the outflow each — keeps the implied rate away from
#     r = -1, where 1 + r loses precision to catastrophic cancellation
#     (test_large_loss_reference pins that boundary down directly).
_outflows = st.floats(min_value=100.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False)
_inflow_fraction = st.floats(min_value=0.05, max_value=1.5, allow_nan=False, allow_infinity=False)
_day_offsets = st.integers(min_value=90, max_value=3650)


@st.composite
def investment_series(draw: st.DrawFn) -> list[Cashflow]:
    start = date(2000, 1, 1)
    outflow = draw(_outflows)
    n_inflows = draw(st.integers(min_value=1, max_value=6))
    offsets = sorted(
        draw(st.lists(_day_offsets, min_size=n_inflows, max_size=n_inflows, unique=True))
    )
    fractions = [draw(_inflow_fraction) for _ in offsets]
    flows = [Cashflow(start, -outflow)]
    flows += [
        Cashflow(start + timedelta(days=o), outflow * f)
        for o, f in zip(offsets, fractions, strict=True)
    ]
    return flows


@given(flows=investment_series())
@settings(max_examples=200, deadline=None)
def test_npv_is_zero_at_solution(flows: list[Cashflow]) -> None:
    """The defining property: NPV at the returned rate is ~0.

    NPV has units of money, so the residual is normalized by the gross cash
    flow to get a dimensionless, scale-independent measure of accuracy.
    """
    rate = xirr(flows)
    amounts = [cf.amount for cf in flows]
    years = _year_fractions([cf.on for cf in flows])
    gross = sum(abs(a) for a in amounts)
    assert _npv(rate, amounts, years) / gross == pytest.approx(0.0, abs=1e-6)


@given(flows=investment_series(), scale=st.floats(min_value=0.01, max_value=1000.0))
@settings(max_examples=100, deadline=None)
def test_scale_invariance(flows: list[Cashflow], scale: float) -> None:
    """Multiplying every amount by k>0 must not change the rate."""
    scaled = [Cashflow(cf.on, cf.amount * scale) for cf in flows]
    assert xirr(scaled) == pytest.approx(xirr(flows), abs=1e-6, rel=1e-6)


@given(flows=investment_series(), shift=st.integers(min_value=-3000, max_value=3000))
@settings(max_examples=100, deadline=None)
def test_date_shift_invariance(flows: list[Cashflow], shift: float) -> None:
    """Shifting every date by the same offset must not change the rate."""
    shifted = [Cashflow(cf.on + timedelta(days=shift), cf.amount) for cf in flows]
    assert xirr(shifted) == pytest.approx(xirr(flows), abs=1e-6, rel=1e-6)
