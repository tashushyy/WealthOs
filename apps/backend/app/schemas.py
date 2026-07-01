"""Request and response models for the API.

These are the HTTP contract. They validate shape and basic ranges; the
financial engine remains the single source of truth for the calculation and its
own domain rules.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectionRequest(BaseModel):
    """Inputs for a wealth projection."""

    principal: float = Field(ge=0, description="Starting lump sum.")
    monthly_contribution: float = Field(ge=0, description="Amount invested each month.")
    annual_return: float = Field(gt=-1, description="Expected annual return, e.g. 0.12 for 12%.")
    years: int = Field(gt=0, le=100, description="Whole years to project.")
    annual_step_up: float = Field(
        default=0.0, ge=0, description="Yearly increase applied to the monthly contribution."
    )


class YearPoint(BaseModel):
    """One year of the projection, for plotting."""

    year: int
    contributed: float
    value: float


class ProjectionResponse(BaseModel):
    """A projection result: the full series plus headline totals."""

    points: list[YearPoint]
    final_value: float
    total_contributed: float


class FireRequest(BaseModel):
    """Inputs for a FIRE (Financial Independence) calculation."""

    annual_expenses: float = Field(ge=0, description="Yearly spending to support.")
    withdrawal_rate: float = Field(
        default=0.04, gt=0, le=1, description="Safe withdrawal rate, e.g. 0.04 for 4%."
    )
    current_corpus: float = Field(ge=0, description="Current portfolio value.")
    monthly_contribution: float = Field(ge=0, description="Amount invested each month.")
    annual_return: float = Field(gt=-1, description="Expected annual return, e.g. 0.12.")


class FireResponse(BaseModel):
    """A FIRE result: the target, how far along, and time to reach it."""

    fire_number: float
    progress: float
    years_to_fire: int | None


class SwpRequest(BaseModel):
    """Inputs for a systematic withdrawal plan."""

    corpus: float = Field(ge=0, description="Starting corpus.")
    monthly_withdrawal: float = Field(ge=0, description="Initial monthly withdrawal.")
    annual_return: float = Field(gt=-1, description="Expected annual return, e.g. 0.08.")
    annual_inflation: float = Field(
        default=0.0, gt=-1, description="Annual increase applied to the withdrawal."
    )
    years: int = Field(gt=0, le=100, description="Whole years to simulate.")


class SwpYearPoint(BaseModel):
    """One year of a withdrawal plan, for plotting."""

    year: int
    withdrawn: float
    balance: float


class SwpResponse(BaseModel):
    """An SWP result: survival, a sustainable amount, and the yearly series."""

    survival_months: int | None
    sustainable_monthly: float
    points: list[SwpYearPoint]


class HoldingInput(BaseModel):
    """One position in a portfolio."""

    name: str = Field(min_length=1, description="Fund/ticker/label.")
    amount: float = Field(ge=0, description="Money allocated to this holding.")
    expected_return: float = Field(gt=-1, description="Expected annual return, e.g. 0.12.")
    volatility: float | None = Field(default=None, ge=0, description="Annual volatility, decimal.")


class PortfolioRequest(BaseModel):
    """A set of holdings to blend into one portfolio."""

    holdings: list[HoldingInput] = Field(min_length=1)


class WeightOut(BaseModel):
    """A holding's share of the portfolio."""

    name: str
    weight: float


class PortfolioResponse(BaseModel):
    """The blended portfolio summary."""

    total_invested: float
    blended_return: float
    blended_volatility: float | None
    weights: list[WeightOut]


class InstrumentResult(BaseModel):
    """A search hit the user can add to their portfolio."""

    id: str = Field(description="Opaque id, e.g. 'mf:118834' or 'yahoo:RELIANCE.NS'.")
    name: str
    kind: str = Field(description="mutual_fund | stock | etf | commodity | index | other")
    symbol: str | None = None


class QuoteResult(BaseModel):
    """Latest price and a trailing-CAGR estimate of expected return."""

    id: str
    name: str
    price: float | None
    expected_return: float | None = Field(
        default=None, description="Trailing CAGR over the window; past performance, not a forecast."
    )
    window_years: float | None = None
    as_of: str | None = None
