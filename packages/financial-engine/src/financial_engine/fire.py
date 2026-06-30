"""FIRE — Financial Independence, Retire Early.

Helpers for the corpus targets behind the common FIRE variants and for tracking
progress toward them. All figures are in the same currency and are real or
nominal consistently with whatever return/expense assumptions the caller feeds
in (the module does not itself adjust for inflation).

Variants, and how they map to the functions here:

  * Lean / Regular / Fat FIRE differ only in the assumed annual expenses, so
    all three are :func:`fire_number` called with a lower, baseline, or higher
    expense figure.
  * Coast FIRE — the amount needed *today* that, with no further contributions,
    compounds to a full FIRE number by retirement: :func:`coast_fire_number`.
  * Barista FIRE — a smaller corpus that only needs to cover the expenses not
    met by ongoing part-time income: :func:`barista_fire_number`.

The 4% "safe withdrawal rate" is the conventional default and corresponds to the
familiar 25x-annual-expenses target; it is an assumption, not a guarantee.
"""

from __future__ import annotations

from financial_engine.errors import InvalidParameterError
from financial_engine.projection import projection_schedule

DEFAULT_WITHDRAWAL_RATE: float = 0.04
"""The conventional 4% safe withdrawal rate (the '25x expenses' rule)."""

DEFAULT_MAX_YEARS: int = 100
"""Default horizon cap for :func:`years_to_target`."""


def fire_number(
    annual_expenses: float,
    withdrawal_rate: float = DEFAULT_WITHDRAWAL_RATE,
) -> float:
    """Corpus required to sustain ``annual_expenses`` at ``withdrawal_rate``.

    At the default 4% rate this is ``annual_expenses * 25``. Lean, Regular, and
    Fat FIRE are just this function with smaller or larger expense figures.

    Args:
        annual_expenses: Yearly spending to support (>= 0).
        withdrawal_rate: Fraction of the corpus withdrawn per year (0 < r <= 1).

    Returns:
        The required corpus.

    Raises:
        InvalidParameterError: Negative expenses or a withdrawal rate outside
            ``(0, 1]``.
    """
    if annual_expenses < 0:
        raise InvalidParameterError("annual_expenses must be non-negative.")
    if not 0.0 < withdrawal_rate <= 1.0:
        raise InvalidParameterError("withdrawal_rate must be in the interval (0, 1].")
    return annual_expenses / withdrawal_rate


def coast_fire_number(
    fire_target: float,
    annual_return: float,
    years_to_retirement: float,
) -> float:
    """Amount needed today to reach ``fire_target`` with no further saving.

    It is the present value of the target: ``fire_target / (1+r)**years``.

    Args:
        fire_target: Full FIRE corpus to reach by retirement (>= 0).
        annual_return: Expected annual return as a decimal (> -1).
        years_to_retirement: Years until retirement (>= 0).

    Returns:
        The corpus that, left to compound, grows to ``fire_target``.

    Raises:
        InvalidParameterError: Negative target, return <= -100%, or negative
            years.
    """
    if fire_target < 0:
        raise InvalidParameterError("fire_target must be non-negative.")
    if annual_return <= -1.0:
        raise InvalidParameterError("annual_return must be greater than -100%.")
    if years_to_retirement < 0:
        raise InvalidParameterError("years_to_retirement must be non-negative.")
    return fire_target / (1.0 + annual_return) ** years_to_retirement


def barista_fire_number(
    annual_expenses: float,
    part_time_income: float,
    withdrawal_rate: float = DEFAULT_WITHDRAWAL_RATE,
) -> float:
    """Corpus needed to cover only the expenses not met by part-time income.

    Args:
        annual_expenses: Total yearly spending (>= 0).
        part_time_income: Yearly income that continues in semi-retirement
            (>= 0). Income at or above expenses yields a zero corpus.
        withdrawal_rate: Fraction of the corpus withdrawn per year (0 < r <= 1).

    Returns:
        The required corpus for the uncovered portion of expenses.

    Raises:
        InvalidParameterError: Negative inputs or a withdrawal rate outside
            ``(0, 1]``.
    """
    if annual_expenses < 0:
        raise InvalidParameterError("annual_expenses must be non-negative.")
    if part_time_income < 0:
        raise InvalidParameterError("part_time_income must be non-negative.")
    if not 0.0 < withdrawal_rate <= 1.0:
        raise InvalidParameterError("withdrawal_rate must be in the interval (0, 1].")
    uncovered = max(annual_expenses - part_time_income, 0.0)
    return uncovered / withdrawal_rate


def fire_progress(current_corpus: float, target_corpus: float) -> float:
    """Fraction of the way to a FIRE target.

    Args:
        current_corpus: Current portfolio value (>= 0).
        target_corpus: Target corpus (> 0).

    Returns:
        ``current_corpus / target_corpus`` (1.0 means the target is met; values
        above 1.0 mean it is exceeded).

    Raises:
        InvalidParameterError: Negative current corpus or non-positive target.
    """
    if current_corpus < 0:
        raise InvalidParameterError("current_corpus must be non-negative.")
    if target_corpus <= 0:
        raise InvalidParameterError("target_corpus must be strictly positive.")
    return current_corpus / target_corpus


def years_to_target(
    current_corpus: float,
    monthly_contribution: float,
    annual_return: float,
    target_corpus: float,
    max_years: int = DEFAULT_MAX_YEARS,
) -> int | None:
    """Whole years until contributions + growth reach ``target_corpus``.

    Projects ``current_corpus`` forward with a monthly contribution (see
    :func:`financial_engine.projection.projection_schedule`) and returns the
    first year-end at which the value meets or exceeds the target.

    Args:
        current_corpus: Starting portfolio value (>= 0).
        monthly_contribution: Monthly contribution (>= 0).
        annual_return: Expected annual return as a decimal (> -1).
        target_corpus: Corpus to reach (>= 0).
        max_years: Horizon cap to search (> 0).

    Returns:
        ``0`` if the target is already met, the year it is first reached, or
        ``None`` if it is not reached within ``max_years``.

    Raises:
        InvalidParameterError: Negative target, non-positive ``max_years``, or
            any invalid projection input.
    """
    if target_corpus < 0:
        raise InvalidParameterError("target_corpus must be non-negative.")
    if max_years <= 0:
        raise InvalidParameterError("max_years must be a positive whole number.")
    if current_corpus >= target_corpus:
        return 0

    schedule = projection_schedule(current_corpus, monthly_contribution, annual_return, max_years)
    for snapshot in schedule:
        if snapshot.value >= target_corpus:
            return snapshot.year
    return None
