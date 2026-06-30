"""Extended Internal Rate of Return (XIRR).

XIRR is the annualized, money-weighted return of a series of cash flows that
occur on *irregular* dates. It is the discount rate ``r`` that makes the net
present value of all cash flows equal to zero::

    NPV(r) = sum( amount_i / (1 + r) ** (days_i / 365) ) = 0

where ``days_i`` is the number of days between cash flow ``i`` and the first
cash flow. This matches the convention used by spreadsheet ``XIRR`` functions
(actual days, 365-day year).

Sign convention: money leaving the investor (deposits, purchases) is negative;
money returning to the investor (withdrawals, redemptions, current value) is
positive. A valid series therefore needs at least one negative and one
positive cash flow.

The solver uses Newton-Raphson for speed and falls back to a bracketing
bisection search when Newton leaves the valid domain or fails to converge,
which makes it robust to poor initial guesses and unusual cash-flow shapes.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

# --- Numerical constants (no magic numbers in the algorithm below) -----------

DAYS_PER_YEAR: float = 365.0
"""Day-count denominator. Spreadsheet XIRR uses a fixed 365-day year."""

DEFAULT_GUESS: float = 0.1
"""Initial annualized-rate guess (10%) for Newton-Raphson."""

CONVERGENCE_TOLERANCE: float = 1e-9
"""Stop when the step size (in log-rate space) falls below this threshold."""

MAX_NEWTON_ITERATIONS: int = 100
"""Cap on Newton-Raphson iterations before falling back to bisection."""

MAX_BISECTION_ITERATIONS: int = 200
"""Cap on bisection iterations in the fallback solver."""

# A discount rate of -100% (r = -1) makes the discount factor undefined, so the
# search domain is open at the bottom. We stay just above it.
MIN_RATE: float = -0.999_999
"""Lower bound of the search domain for the discount rate."""

# The bisection fallback searches in log-rate space, x = ln(1 + r), so the
# discount factor exp(-x * t) is numerically stable even for enormous rates
# (e.g. a near-instant doubling implies a colossal *annualized* return). The
# bounds below span r ~ -1 up to r ~ exp(700), comfortably wider than any
# economically meaningful figure while staying inside float range.
# Bisection runs in log-rate space x = ln(1 + r). float64 represents (1 + r)
# for x roughly in [-745, 709.78]; we stay just inside both ends. The high end
# bounds enormous gains (e.g. a multi-fold return over one day); the low end
# bounds near-total losses, where r approaches -1 from above. Rates outside
# this representable band surface as ConvergenceError rather than a wrong
# number.
_LOG_RATE_LOW: float = -700.0
_LOG_RATE_HIGH: float = 709.0

# Largest / smallest exponent that math.exp can take without overflow/underflow
# to a non-finite or zero result. Used only to keep the *sign* of NPV correct
# at the extreme bracket ends; near the actual root the exponent is moderate
# and never clamped, so the solved rate is unaffected.
_EXP_MAX: float = 709.0
_EXP_MIN: float = -745.0

_DERIVATIVE_EPSILON: float = 1e-12
"""Below this derivative magnitude Newton's step is unstable; bail out."""


# --- Public types ------------------------------------------------------------


class XirrError(ValueError):
    """Base class for all XIRR errors."""


class InvalidCashflowsError(XirrError):
    """The cash-flow series cannot have an XIRR (bad shape or sign)."""


class ConvergenceError(XirrError):
    """No discount rate could be found within the configured iteration caps."""


@dataclass(frozen=True)
class Cashflow:
    """A single dated cash flow.

    Attributes:
        on: Calendar date the cash flow occurred.
        amount: Signed amount. Negative = money out (invested),
            positive = money in (returned).
    """

    on: date
    amount: float


# --- Internal helpers --------------------------------------------------------


def _year_fractions(dates: Sequence[date]) -> list[float]:
    """Return each date's offset from the earliest date, in years."""
    base = min(dates)
    return [(d - base).days / DAYS_PER_YEAR for d in dates]


def _npv(rate: float, amounts: Sequence[float], years: Sequence[float]) -> float:
    """Net present value of the cash flows at ``rate``."""
    base = 1.0 + rate
    return sum(amount / base**t for amount, t in zip(amounts, years, strict=True))


def _validate(cashflows: Sequence[Cashflow]) -> None:
    """Reject series that provably have no XIRR."""
    if len(cashflows) < 2:
        raise InvalidCashflowsError("At least two cash flows are required.")

    amounts = [cf.amount for cf in cashflows]
    has_negative = any(a < 0 for a in amounts)
    has_positive = any(a > 0 for a in amounts)
    if not (has_negative and has_positive):
        raise InvalidCashflowsError(
            "Cash flows must contain at least one negative (money out) and one "
            "positive (money in) amount."
        )


def _npv_logspace(x: float, amounts: Sequence[float], years: Sequence[float]) -> float:
    """NPV expressed in log-rate space, where ``x = ln(1 + r)``.

    NPV = sum( amount * exp(-x * t) ). The exponent is clamped to float's
    representable range so extreme bracket ends never overflow; the clamp only
    affects regions far from the root, never the converged value.
    """
    total = 0.0
    for amount, t in zip(amounts, years, strict=True):
        exponent = max(_EXP_MIN, min(_EXP_MAX, -x * t))
        total += amount * math.exp(exponent)
    return total


def _dnpv_logspace(x: float, amounts: Sequence[float], years: Sequence[float]) -> float:
    """Derivative of :func:`_npv_logspace` with respect to ``x``.

    d/dx [ a * exp(-x * t) ] = -t * a * exp(-x * t).
    """
    total = 0.0
    for amount, t in zip(amounts, years, strict=True):
        exponent = max(_EXP_MIN, min(_EXP_MAX, -x * t))
        total += -t * amount * math.exp(exponent)
    return total


def _solve_newton(amounts: Sequence[float], years: Sequence[float], guess: float) -> float | None:
    """Newton-Raphson in log-rate space. Returns the rate, or None on failure.

    Working in ``x = ln(1 + r)`` keeps convergence meaningful across the whole
    domain — including near total losses, where ``r`` crowds against -1 and an
    absolute step tolerance in ``r`` would stop far too early. The step is
    invariant to scaling all cash flows by a constant, so the result is
    independent of their magnitude.
    """
    x = math.log1p(guess) if guess > MIN_RATE else 0.0
    for _ in range(MAX_NEWTON_ITERATIONS):
        derivative = _dnpv_logspace(x, amounts, years)
        if abs(derivative) < _DERIVATIVE_EPSILON:
            return None

        step = _npv_logspace(x, amounts, years) / derivative
        next_x = x - step
        if not (_LOG_RATE_LOW < next_x < _LOG_RATE_HIGH):
            return None
        if abs(next_x - x) < CONVERGENCE_TOLERANCE:
            return math.expm1(next_x)
        x = next_x
    return None


def _solve_bisection(amounts: Sequence[float], years: Sequence[float]) -> float:
    """Bracketing bisection fallback in log-rate space.

    Robust but slower than Newton; resolves both ordinary returns and extreme
    (but representable) annualized rates that arise from very short horizons.
    """
    low, high = _LOG_RATE_LOW, _LOG_RATE_HIGH
    npv_low = _npv_logspace(low, amounts, years)
    npv_high = _npv_logspace(high, amounts, years)

    if npv_low * npv_high > 0:
        raise ConvergenceError(
            "Could not bracket a root: the cash flows may have no real XIRR, a "
            "rate outside float's representable range, or multiple sign changes "
            "that the solver cannot resolve."
        )

    # Convergence is measured on the bracket width in log-rate space, which is
    # independent of the cash-flow magnitudes (unlike a raw |NPV| threshold).
    mid = (low + high) / 2.0
    for _ in range(MAX_BISECTION_ITERATIONS):
        mid = (low + high) / 2.0
        if (high - low) < CONVERGENCE_TOLERANCE:
            break
        if npv_low * _npv_logspace(mid, amounts, years) < 0:
            high = mid
        else:
            low = mid
            npv_low = _npv_logspace(low, amounts, years)

    return math.expm1(mid)


# --- Public API --------------------------------------------------------------


def xirr(cashflows: Sequence[Cashflow], guess: float = DEFAULT_GUESS) -> float:
    """Compute the Extended Internal Rate of Return.

    Args:
        cashflows: Two or more dated cash flows, with at least one negative and
            one positive amount. Order does not matter; dates may repeat.
        guess: Initial annualized-rate guess for Newton-Raphson. Only affects
            speed, not the result, because of the bisection fallback.

    Returns:
        The annualized rate as a decimal (e.g. ``0.1234`` for 12.34%).

    Raises:
        InvalidCashflowsError: Fewer than two cash flows, or missing a sign.
        ConvergenceError: No rate could be found.

    Example:
        >>> from datetime import date
        >>> flows = [
        ...     Cashflow(date(2008, 1, 1), -10000),
        ...     Cashflow(date(2008, 3, 1), 2750),
        ...     Cashflow(date(2008, 10, 30), 4250),
        ...     Cashflow(date(2009, 2, 15), 3250),
        ...     Cashflow(date(2009, 4, 1), 2750),
        ... ]
        >>> round(xirr(flows), 6)
        0.373362
    """
    _validate(cashflows)

    amounts = [cf.amount for cf in cashflows]
    years = _year_fractions([cf.on for cf in cashflows])

    result = _solve_newton(amounts, years, guess)
    if result is not None:
        return result
    return _solve_bisection(amounts, years)
