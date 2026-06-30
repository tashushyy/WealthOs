"""Compound Annual Growth Rate (CAGR).

CAGR is the constant annual rate that grows a starting value to an ending value
over a given period::

    CAGR = (end / begin) ** (1 / years) - 1

Unlike XIRR it ignores the timing and size of intermediate cash flows — it only
considers the first value, the last value, and the elapsed time. Use it for the
smoothed, headline "what annual return would have produced this growth" figure;
use XIRR when contributions and withdrawals along the way matter.

A total loss (``end == 0``) yields a CAGR of -1.0 (-100%). Values must be
non-negative with a strictly positive starting value, because a negative
portfolio value has no real growth rate.
"""

from __future__ import annotations

from datetime import date

DAYS_PER_YEAR: float = 365.0
"""Day-count denominator, consistent with the XIRR module."""

_TOTAL_LOSS_RATE: float = -1.0
"""CAGR when the ending value is zero (a 100% loss)."""


class CagrError(ValueError):
    """Base class for all CAGR errors."""


class InvalidValueError(CagrError):
    """A value or period is outside the domain where CAGR is defined."""


def cagr(begin_value: float, end_value: float, years: float) -> float:
    """Compound annual growth rate over a period expressed in years.

    Args:
        begin_value: Starting value. Must be strictly positive.
        end_value: Ending value. Must be non-negative.
        years: Length of the period in years. Must be strictly positive.

    Returns:
        The constant annual growth rate as a decimal (e.g. ``0.12`` = 12%).
        Returns ``-1.0`` when ``end_value`` is zero (a total loss).

    Raises:
        InvalidValueError: ``begin_value <= 0``, ``end_value < 0``, or
            ``years <= 0``.

    Example:
        >>> round(cagr(1000.0, 2000.0, 2.0), 6)  # doubled over two years
        0.414214
    """
    if begin_value <= 0:
        raise InvalidValueError("begin_value must be strictly positive.")
    if end_value < 0:
        raise InvalidValueError("end_value must be non-negative.")
    if years <= 0:
        raise InvalidValueError("years must be strictly positive.")

    if end_value == 0:
        return _TOTAL_LOSS_RATE
    return (end_value / begin_value) ** (1.0 / years) - 1.0


def cagr_between(
    begin_value: float,
    end_value: float,
    start: date,
    end: date,
) -> float:
    """CAGR between two dates, using an actual/365 day count.

    Args:
        begin_value: Value on ``start``. Must be strictly positive.
        end_value: Value on ``end``. Must be non-negative.
        start: Start date.
        end: End date. Must be strictly after ``start``.

    Returns:
        The annual growth rate as a decimal.

    Raises:
        InvalidValueError: Invalid values, or ``end`` is not after ``start``.
    """
    days = (end - start).days
    if days <= 0:
        raise InvalidValueError("end date must be strictly after start date.")
    return cagr(begin_value, end_value, days / DAYS_PER_YEAR)
