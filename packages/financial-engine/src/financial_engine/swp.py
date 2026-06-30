"""Systematic Withdrawal Plan (SWP).

The decumulation counterpart to :mod:`financial_engine.projection`. Given a
retirement corpus and a monthly withdrawal, it answers:

  * :func:`corpus_survival` — how many months of withdrawals the corpus funds.
  * :func:`swp_schedule` — the year-by-year balance and amount withdrawn.
  * :func:`sustainable_withdrawal` — the starting monthly withdrawal that
    exactly depletes the corpus over a chosen horizon.

Model (consistent with the projection module):
  * The annual return becomes an effective monthly rate.
  * Each month the balance grows, then the withdrawal is taken (end-of-month).
  * Withdrawals are inflation-adjusted once a year: the monthly amount is
    multiplied by ``(1 + annual_inflation)`` after every twelfth month, so
    spending keeps pace with prices.

Tax is intentionally out of scope here: modelling it correctly needs cost-basis
and capital-gains rules that belong above this layer. Callers that withdraw a
net amount under a flat tax ``t`` should pass a gross withdrawal of
``net / (1 - t)``.
"""

from __future__ import annotations

from dataclasses import dataclass

from financial_engine.compounding import MONTHS_PER_YEAR, effective_monthly_rate
from financial_engine.errors import InvalidParameterError

DEFAULT_MAX_YEARS: int = 100
"""Default horizon cap for :func:`corpus_survival`."""

_BISECTION_ITERATIONS: int = 200
"""Iterations for the sustainable-withdrawal solver (ample for float precision)."""

_MAX_BRACKET_EXPANSIONS: int = 60
"""Cap on doublings while bracketing the sustainable-withdrawal root."""

__all__ = [
    "InvalidParameterError",
    "SwpYearSnapshot",
    "corpus_survival",
    "sustainable_withdrawal",
    "swp_schedule",
]


@dataclass(frozen=True)
class SwpYearSnapshot:
    """End-of-year state of a withdrawal plan.

    Attributes:
        year: Year number, 1-based.
        withdrawn: Cumulative amount actually withdrawn by this point.
        balance: Remaining corpus at the end of the year (never negative).
    """

    year: int
    withdrawn: float
    balance: float


def _validate(
    corpus: float,
    monthly_withdrawal: float,
    annual_return: float,
    annual_inflation: float,
) -> None:
    if corpus < 0:
        raise InvalidParameterError("corpus must be non-negative.")
    if monthly_withdrawal < 0:
        raise InvalidParameterError("monthly_withdrawal must be non-negative.")
    if annual_return <= -1.0:
        raise InvalidParameterError("annual_return must be greater than -100%.")
    if annual_inflation <= -1.0:
        raise InvalidParameterError("annual_inflation must be greater than -100%.")


def corpus_survival(
    corpus: float,
    monthly_withdrawal: float,
    annual_return: float,
    annual_inflation: float = 0.0,
    max_years: int = DEFAULT_MAX_YEARS,
) -> int | None:
    """Number of monthly withdrawals the corpus can fully fund.

    Args:
        corpus: Starting corpus (>= 0).
        monthly_withdrawal: Initial monthly withdrawal (>= 0).
        annual_return: Expected annual return as a decimal (> -1).
        annual_inflation: Annual increase applied to the withdrawal (> -1).
        max_years: Horizon to simulate before giving up (> 0).

    Returns:
        The count of months fully funded, or ``None`` if the corpus still funds
        withdrawals after ``max_years`` (effectively sustainable).

    Raises:
        InvalidParameterError: Any argument is outside its valid domain.
    """
    _validate(corpus, monthly_withdrawal, annual_return, annual_inflation)
    if max_years <= 0:
        raise InvalidParameterError("max_years must be a positive whole number.")

    rate = effective_monthly_rate(annual_return)
    balance = corpus
    withdrawal = monthly_withdrawal

    # Every month before the first shortfall is fully funded, so the count of
    # funded months equals (month - 1) at the point a withdrawal can't be met.
    for month in range(1, max_years * MONTHS_PER_YEAR + 1):
        available = balance * (1.0 + rate)
        if available < withdrawal:
            return month - 1
        balance = available - withdrawal
        if month % MONTHS_PER_YEAR == 0:
            withdrawal *= 1.0 + annual_inflation

    return None


def swp_schedule(
    corpus: float,
    monthly_withdrawal: float,
    annual_return: float,
    annual_inflation: float,
    years: int,
) -> list[SwpYearSnapshot]:
    """Year-by-year balance and cumulative withdrawals over ``years``.

    Once the corpus is exhausted, later months withdraw whatever remains (down
    to zero) and the balance stays at zero.

    Args:
        corpus: Starting corpus (>= 0).
        monthly_withdrawal: Initial monthly withdrawal (>= 0).
        annual_return: Expected annual return as a decimal (> -1).
        annual_inflation: Annual increase applied to the withdrawal (> -1).
        years: Whole number of years to simulate (> 0).

    Returns:
        One :class:`SwpYearSnapshot` per year, in order.

    Raises:
        InvalidParameterError: Any argument is outside its valid domain.
    """
    _validate(corpus, monthly_withdrawal, annual_return, annual_inflation)
    if years <= 0:
        raise InvalidParameterError("years must be a positive whole number.")

    rate = effective_monthly_rate(annual_return)
    balance = corpus
    withdrawal = monthly_withdrawal
    withdrawn_total = 0.0
    schedule: list[SwpYearSnapshot] = []

    for year in range(1, years + 1):
        for _ in range(MONTHS_PER_YEAR):
            available = balance * (1.0 + rate)
            taken = min(available, withdrawal)
            balance = available - taken
            withdrawn_total += taken
        schedule.append(SwpYearSnapshot(year=year, withdrawn=withdrawn_total, balance=balance))
        withdrawal *= 1.0 + annual_inflation

    return schedule


def _balance_after(
    corpus: float,
    monthly_withdrawal: float,
    rate: float,
    annual_inflation: float,
    months: int,
) -> float:
    """Final balance after ``months``, allowing it to go negative.

    Unfloored on purpose: the sign change is what the root finder needs.
    """
    balance = corpus
    withdrawal = monthly_withdrawal
    for month in range(1, months + 1):
        balance = balance * (1.0 + rate) - withdrawal
        if month % MONTHS_PER_YEAR == 0:
            withdrawal *= 1.0 + annual_inflation
    return balance


def sustainable_withdrawal(
    corpus: float,
    annual_return: float,
    annual_inflation: float,
    years: int,
) -> float:
    """Starting monthly withdrawal that exactly depletes the corpus.

    Solves for the initial monthly withdrawal whose inflation-adjusted stream
    leaves a zero balance after ``years``. Withdrawing this amount sustains
    spending for exactly the horizon; less leaves a surplus, more runs out
    early.

    Args:
        corpus: Starting corpus (>= 0).
        annual_return: Expected annual return as a decimal (> -1).
        annual_inflation: Annual increase applied to the withdrawal (> -1).
        years: Whole number of years the corpus must last (> 0).

    Returns:
        The sustainable initial monthly withdrawal (``0.0`` for a zero corpus).

    Raises:
        InvalidParameterError: Any argument is outside its valid domain.
    """
    _validate(corpus, 0.0, annual_return, annual_inflation)
    if years <= 0:
        raise InvalidParameterError("years must be a positive whole number.")
    if corpus == 0:
        return 0.0

    rate = effective_monthly_rate(annual_return)
    months = years * MONTHS_PER_YEAR

    # Bracket the root: balance_after decreases monotonically in the withdrawal.
    low = 0.0
    high = max(corpus, 1.0)
    for _ in range(_MAX_BRACKET_EXPANSIONS):
        if _balance_after(corpus, high, rate, annual_inflation, months) < 0:
            break
        high *= 2.0

    for _ in range(_BISECTION_ITERATIONS):
        mid = (low + high) / 2.0
        if _balance_after(corpus, mid, rate, annual_inflation, months) > 0:
            low = mid
        else:
            high = mid

    return (low + high) / 2.0
