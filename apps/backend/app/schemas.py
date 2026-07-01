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
