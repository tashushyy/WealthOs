"""Wealth projection: future value of a lump sum plus a monthly SIP.

Projects how an initial principal and an ongoing monthly contribution grow over
time at an assumed annual return. The monthly contribution can step up once a
year (a common SIP feature where you raise the amount with your income).

Model:
  * The annual return is converted to an *effective* monthly rate, so that
    twelve months of compounding reproduces the annual figure exactly:
    ``r_month = (1 + annual_return) ** (1/12) - 1``.
  * Contributions are made at the **end** of each month (an ordinary annuity):
    each month the balance first grows, then the contribution is added.
  * The contribution amount is multiplied by ``(1 + annual_step_up)`` after
    every twelfth month.

The calculation is done with an explicit month-by-month loop rather than a
closed-form annuity formula. It is exact for the step-up case (which has no
simple closed form), avoids the divide-by-zero a closed form hits at zero
return, and naturally produces a year-by-year schedule for charting.
"""

from __future__ import annotations

from dataclasses import dataclass

from financial_engine.errors import InvalidParameterError

MONTHS_PER_YEAR: int = 12

__all__ = [
    "InvalidParameterError",
    "YearSnapshot",
    "future_value",
    "projection_schedule",
]


@dataclass(frozen=True)
class YearSnapshot:
    """End-of-year state of a projection.

    Attributes:
        year: Year number, 1-based (1 = after the first 12 months).
        contributed: Cumulative contributions paid in by this point
            (excludes the starting principal).
        value: Total portfolio value at the end of the year.
    """

    year: int
    contributed: float
    value: float


def _monthly_rate(annual_return: float) -> float:
    """Effective monthly rate equivalent to ``annual_return`` per year."""
    return (1.0 + annual_return) ** (1.0 / MONTHS_PER_YEAR) - 1.0


def _validate(
    principal: float,
    monthly_contribution: float,
    annual_return: float,
    years: int,
    annual_step_up: float,
) -> None:
    if principal < 0:
        raise InvalidParameterError("principal must be non-negative.")
    if monthly_contribution < 0:
        raise InvalidParameterError("monthly_contribution must be non-negative.")
    if annual_return <= -1.0:
        raise InvalidParameterError("annual_return must be greater than -100%.")
    if years <= 0:
        raise InvalidParameterError("years must be a positive whole number.")
    if annual_step_up < 0:
        raise InvalidParameterError("annual_step_up must be non-negative.")


def projection_schedule(
    principal: float,
    monthly_contribution: float,
    annual_return: float,
    years: int,
    annual_step_up: float = 0.0,
) -> list[YearSnapshot]:
    """Year-by-year projection of portfolio value.

    Args:
        principal: Starting lump sum (>= 0).
        monthly_contribution: Amount invested at the end of each month (>= 0).
        annual_return: Expected annual return as a decimal (> -1), e.g. 0.12.
        years: Whole number of years to project (> 0).
        annual_step_up: Fractional annual increase applied to the monthly
            contribution after each year (>= 0), e.g. 0.10 for +10% a year.

    Returns:
        One :class:`YearSnapshot` per projected year, in order.

    Raises:
        InvalidParameterError: Any argument is outside its valid domain.
    """
    _validate(principal, monthly_contribution, annual_return, years, annual_step_up)

    rate = _monthly_rate(annual_return)
    balance = principal
    contribution = monthly_contribution
    contributed_total = 0.0
    schedule: list[YearSnapshot] = []

    for year in range(1, years + 1):
        for _ in range(MONTHS_PER_YEAR):
            balance = balance * (1.0 + rate) + contribution
            contributed_total += contribution
        schedule.append(YearSnapshot(year=year, contributed=contributed_total, value=balance))
        contribution *= 1.0 + annual_step_up

    return schedule


def future_value(
    principal: float,
    monthly_contribution: float,
    annual_return: float,
    years: int,
    annual_step_up: float = 0.0,
) -> float:
    """Projected portfolio value at the end of the period.

    Convenience wrapper over :func:`projection_schedule` returning only the
    final value. See that function for argument and error details.
    """
    schedule = projection_schedule(
        principal, monthly_contribution, annual_return, years, annual_step_up
    )
    return schedule[-1].value
