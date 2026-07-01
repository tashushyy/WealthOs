"""Portfolio blending.

Combine several holdings (stocks, mutual funds, gold, ...) into one portfolio
and summarize it: the amount-weighted expected return, each holding's weight,
and an optional blended volatility.

Two honesty notes baked into the design:

  * Expected return is whatever the caller supplies per holding. This module
    does not forecast — a portfolio's expected return is the amount-weighted
    average of its holdings' expected returns, and that is all this computes.
  * The blended volatility here is the amount-weighted average of the holdings'
    volatilities. That is an **upper bound** on real portfolio risk: because
    holdings are not perfectly correlated, actual volatility is usually lower
    (this is the diversification benefit). Computing the true figure needs a
    covariance matrix, which this module deliberately does not take.
"""

from __future__ import annotations

from dataclasses import dataclass

from financial_engine.errors import InvalidParameterError


@dataclass(frozen=True)
class Holding:
    """One position in the portfolio.

    Attributes:
        name: Display label (e.g. a fund or ticker).
        amount: Money allocated to this holding (> 0 in aggregate; >= 0 each).
        expected_return: Expected annual return as a decimal, e.g. 0.12.
        volatility: Optional annual volatility (std. dev.) as a decimal.
    """

    name: str
    amount: float
    expected_return: float
    volatility: float | None = None


@dataclass(frozen=True)
class Weight:
    """A holding's share of the portfolio."""

    name: str
    weight: float


@dataclass(frozen=True)
class PortfolioSummary:
    """The blended view of a set of holdings."""

    total_invested: float
    blended_return: float
    weights: list[Weight]
    blended_volatility: float | None


def summarize(holdings: list[Holding]) -> PortfolioSummary:
    """Blend holdings into a portfolio summary.

    Args:
        holdings: One or more holdings. Amounts must be non-negative and sum to
            a positive total; each expected return must be greater than -100%.

    Returns:
        A :class:`PortfolioSummary` with total invested, the amount-weighted
        expected return, per-holding weights, and (only if *every* holding has a
        volatility) the amount-weighted volatility.

    Raises:
        InvalidParameterError: No holdings, a negative amount, a zero total, an
            expected return <= -1, or a negative volatility.
    """
    if not holdings:
        raise InvalidParameterError("At least one holding is required.")

    for holding in holdings:
        if holding.amount < 0:
            raise InvalidParameterError(f"{holding.name}: amount must be non-negative.")
        if holding.expected_return <= -1.0:
            raise InvalidParameterError(f"{holding.name}: expected_return must be > -100%.")
        if holding.volatility is not None and holding.volatility < 0:
            raise InvalidParameterError(f"{holding.name}: volatility must be non-negative.")

    total = sum(holding.amount for holding in holdings)
    if total <= 0:
        raise InvalidParameterError("Total invested must be positive.")

    weights = [Weight(name=h.name, weight=h.amount / total) for h in holdings]
    blended_return = sum(h.amount / total * h.expected_return for h in holdings)

    if all(h.volatility is not None for h in holdings):
        blended_volatility: float | None = sum(
            h.amount / total * float(h.volatility) for h in holdings
        )
    else:
        blended_volatility = None

    return PortfolioSummary(
        total_invested=total,
        blended_return=blended_return,
        weights=weights,
        blended_volatility=blended_volatility,
    )
