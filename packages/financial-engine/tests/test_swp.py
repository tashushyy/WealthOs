"""Tests for the SWP module.

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
from financial_engine.swp import (
    corpus_survival,
    sustainable_withdrawal,
    swp_schedule,
)

# --- 1. Reference values -----------------------------------------------------


def test_survival_no_growth_no_inflation() -> None:
    # 1200 corpus, 100/month, no growth -> exactly 12 monthly withdrawals.
    assert corpus_survival(1200.0, 100.0, 0.0) == 12


def test_survival_simple_ratio() -> None:
    assert corpus_survival(1000.0, 50.0, 0.0) == 20


def test_survival_returns_none_when_sustainable() -> None:
    # Tiny withdrawal against strong growth never depletes.
    assert corpus_survival(1_000_000.0, 100.0, 0.10) is None


def test_zero_withdrawal_never_depletes() -> None:
    assert corpus_survival(1000.0, 0.0, 0.0) is None


def test_schedule_depletes_in_one_year() -> None:
    schedule = swp_schedule(1200.0, 100.0, 0.0, 0.0, 1)
    assert len(schedule) == 1
    assert schedule[0].withdrawn == pytest.approx(1200.0, abs=1e-9)
    assert schedule[0].balance == pytest.approx(0.0, abs=1e-9)


def test_sustainable_no_growth() -> None:
    # 12000 over 10 years (120 months), no growth/inflation -> 100/month.
    assert sustainable_withdrawal(12000.0, 0.0, 0.0, 10) == pytest.approx(100.0, abs=1e-6)


def test_sustainable_zero_corpus_is_zero() -> None:
    assert sustainable_withdrawal(0.0, 0.05, 0.02, 30) == 0.0


# --- 2. Edge cases and errors ------------------------------------------------


def test_rejects_negative_corpus() -> None:
    with pytest.raises(InvalidParameterError):
        corpus_survival(-1.0, 100.0, 0.05)


def test_rejects_negative_withdrawal() -> None:
    with pytest.raises(InvalidParameterError):
        corpus_survival(1000.0, -1.0, 0.05)


def test_rejects_return_at_or_below_minus_one() -> None:
    with pytest.raises(InvalidParameterError):
        corpus_survival(1000.0, 100.0, -1.0)


def test_rejects_inflation_at_or_below_minus_one() -> None:
    with pytest.raises(InvalidParameterError):
        corpus_survival(1000.0, 100.0, 0.05, annual_inflation=-1.0)


def test_survival_rejects_non_positive_max_years() -> None:
    with pytest.raises(InvalidParameterError):
        corpus_survival(1000.0, 100.0, 0.05, max_years=0)


def test_schedule_rejects_non_positive_years() -> None:
    with pytest.raises(InvalidParameterError):
        swp_schedule(1000.0, 100.0, 0.05, 0.0, 0)


def test_sustainable_rejects_non_positive_years() -> None:
    with pytest.raises(InvalidParameterError):
        sustainable_withdrawal(1000.0, 0.05, 0.02, 0)


# --- 3. Property-based tests -------------------------------------------------

_corpus = st.floats(min_value=1.0, max_value=10_000_000.0, allow_nan=False, allow_infinity=False)
_withdrawal = st.floats(min_value=0.0, max_value=100_000.0, allow_nan=False, allow_infinity=False)
_return = st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False)
_inflation = st.floats(min_value=0.0, max_value=0.1, allow_nan=False, allow_infinity=False)
_years = st.integers(min_value=1, max_value=50)

_INFINITY = float("inf")


@given(
    corpus=_corpus,
    withdrawal=_withdrawal,
    annual_return=_return,
    inflation=_inflation,
    extra=st.floats(min_value=0.0, max_value=100_000.0),
)
@settings(max_examples=200, deadline=None)
def test_higher_withdrawal_never_lasts_longer(
    corpus: float, withdrawal: float, annual_return: float, inflation: float, extra: float
) -> None:
    """Withdrawing more never extends survival."""
    low = corpus_survival(corpus, withdrawal, annual_return, inflation)
    high = corpus_survival(corpus, withdrawal + extra, annual_return, inflation)
    low_val = _INFINITY if low is None else low
    high_val = _INFINITY if high is None else high
    assert high_val <= low_val


@given(corpus=_corpus, annual_return=_return, inflation=_inflation, years=_years)
@settings(max_examples=200, deadline=None)
def test_sustainable_withdrawal_depletes_corpus(
    corpus: float, annual_return: float, inflation: float, years: int
) -> None:
    """Withdrawing the sustainable amount leaves ~0 at the horizon."""
    monthly = sustainable_withdrawal(corpus, annual_return, inflation, years)
    schedule = swp_schedule(corpus, monthly, annual_return, inflation, years)
    # Balance is floored at zero in the schedule; the residual should be a
    # negligible fraction of the starting corpus.
    assert schedule[-1].balance <= corpus * 1e-6


@given(corpus=_corpus, annual_return=_return, inflation=_inflation, years=_years, extra=_corpus)
@settings(max_examples=150, deadline=None)
def test_sustainable_increases_with_corpus(
    corpus: float, annual_return: float, inflation: float, years: int, extra: float
) -> None:
    """A larger corpus supports at least as large a sustainable withdrawal."""
    base = sustainable_withdrawal(corpus, annual_return, inflation, years)
    more = sustainable_withdrawal(corpus + extra, annual_return, inflation, years)
    assert more >= base - 1e-6


@given(
    corpus=_corpus,
    withdrawal=_withdrawal,
    annual_return=_return,
    inflation=_inflation,
    years=_years,
)
@settings(max_examples=150, deadline=None)
def test_schedule_is_consistent(
    corpus: float, withdrawal: float, annual_return: float, inflation: float, years: int
) -> None:
    """Schedule has one entry per year, withdrawals accumulate, balance >= 0."""
    schedule = swp_schedule(corpus, withdrawal, annual_return, inflation, years)
    assert [s.year for s in schedule] == list(range(1, years + 1))
    withdrawn = [s.withdrawn for s in schedule]
    assert withdrawn == sorted(withdrawn)
    assert all(s.balance >= 0.0 for s in schedule)
