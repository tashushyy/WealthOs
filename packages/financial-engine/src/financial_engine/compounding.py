"""Shared compounding helpers.

Small primitives used by any module that compounds monthly (projection, swp,
...). Centralized so the annual-to-monthly rate convention is defined once.
"""

from __future__ import annotations

MONTHS_PER_YEAR: int = 12


def effective_monthly_rate(annual_return: float) -> float:
    """Monthly rate equivalent to ``annual_return`` per year.

    Defined so that twelve months of compounding reproduce the annual figure
    exactly: ``(1 + monthly) ** 12 == 1 + annual_return``.

    Args:
        annual_return: Annual return as a decimal (must be > -1).

    Returns:
        The effective monthly rate as a decimal.
    """
    return (1.0 + annual_return) ** (1.0 / MONTHS_PER_YEAR) - 1.0
