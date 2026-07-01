"""Tests for the portfolio module."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from financial_engine.errors import InvalidParameterError
from financial_engine.portfolio import Holding, summarize

# --- 1. Reference values -----------------------------------------------------


def test_blended_return_is_amount_weighted() -> None:
    holdings = [
        Holding("A", amount=6000, expected_return=0.10),
        Holding("B", amount=4000, expected_return=0.20),
    ]
    summary = summarize(holdings)
    # 0.6*0.10 + 0.4*0.20 = 0.14
    assert summary.blended_return == pytest.approx(0.14, abs=1e-12)
    assert summary.total_invested == 10000
    assert [round(w.weight, 4) for w in summary.weights] == [0.6, 0.4]


def test_single_holding_returns_its_own_numbers() -> None:
    summary = summarize([Holding("Only", amount=500, expected_return=0.11, volatility=0.18)])
    assert summary.blended_return == pytest.approx(0.11)
    assert summary.weights[0].weight == 1.0
    assert summary.blended_volatility == pytest.approx(0.18)


def test_blended_volatility_only_when_all_present() -> None:
    with_all = summarize(
        [
            Holding("A", 5000, 0.10, volatility=0.20),
            Holding("B", 5000, 0.10, volatility=0.10),
        ]
    )
    assert with_all.blended_volatility == pytest.approx(0.15)  # 0.5*0.2 + 0.5*0.1

    missing_one = summarize(
        [
            Holding("A", 5000, 0.10, volatility=0.20),
            Holding("B", 5000, 0.10),  # no volatility
        ]
    )
    assert missing_one.blended_volatility is None


# --- 2. Edge cases and errors ------------------------------------------------


def test_rejects_empty() -> None:
    with pytest.raises(InvalidParameterError):
        summarize([])


def test_rejects_negative_amount() -> None:
    with pytest.raises(InvalidParameterError):
        summarize([Holding("A", -1, 0.1)])


def test_rejects_zero_total() -> None:
    with pytest.raises(InvalidParameterError):
        summarize([Holding("A", 0, 0.1), Holding("B", 0, 0.1)])


def test_rejects_return_at_or_below_minus_one() -> None:
    with pytest.raises(InvalidParameterError):
        summarize([Holding("A", 100, -1.0)])


def test_rejects_negative_volatility() -> None:
    with pytest.raises(InvalidParameterError):
        summarize([Holding("A", 100, 0.1, volatility=-0.1)])


# --- 3. Property-based tests -------------------------------------------------

_amount = st.floats(min_value=1.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False)
_return = st.floats(min_value=-0.5, max_value=0.5, allow_nan=False, allow_infinity=False)


@st.composite
def holdings(draw: st.DrawFn) -> list[Holding]:
    n = draw(st.integers(min_value=1, max_value=8))
    return [Holding(f"H{i}", draw(_amount), draw(_return)) for i in range(n)]


@given(items=holdings())
@settings(max_examples=200, deadline=None)
def test_weights_sum_to_one(items: list[Holding]) -> None:
    summary = summarize(items)
    assert sum(w.weight for w in summary.weights) == pytest.approx(1.0, abs=1e-9)


@given(items=holdings())
@settings(max_examples=200, deadline=None)
def test_blended_return_within_holding_bounds(items: list[Holding]) -> None:
    """The blend can never exceed the best or trail the worst holding."""
    summary = summarize(items)
    lo = min(h.expected_return for h in items)
    hi = max(h.expected_return for h in items)
    assert lo - 1e-9 <= summary.blended_return <= hi + 1e-9


@given(items=holdings(), scale=st.floats(min_value=0.01, max_value=1000.0))
@settings(max_examples=100, deadline=None)
def test_scaling_all_amounts_keeps_blend(items: list[Holding], scale: float) -> None:
    """Weights and blended return depend only on relative amounts."""
    scaled = [Holding(h.name, h.amount * scale, h.expected_return) for h in items]
    assert summarize(scaled).blended_return == pytest.approx(
        summarize(items).blended_return, rel=1e-9, abs=1e-12
    )
