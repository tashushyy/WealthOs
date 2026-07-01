"""SWP endpoint.

Thin adapter over the engine's withdrawal helpers: how long the corpus lasts at
the requested withdrawal, the sustainable withdrawal for the horizon, and the
year-by-year balance series.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from financial_engine import corpus_survival, sustainable_withdrawal, swp_schedule
from financial_engine.errors import FinancialEngineError

from app.schemas import SwpRequest, SwpResponse, SwpYearPoint

router = APIRouter(prefix="/api", tags=["swp"])


@router.post("/swp", response_model=SwpResponse)
def compute_swp(request: SwpRequest) -> SwpResponse:
    """Compute corpus survival, a sustainable withdrawal, and the yearly series."""
    try:
        survival = corpus_survival(
            request.corpus,
            request.monthly_withdrawal,
            request.annual_return,
            request.annual_inflation,
        )
        sustainable = sustainable_withdrawal(
            request.corpus,
            request.annual_return,
            request.annual_inflation,
            request.years,
        )
        schedule = swp_schedule(
            request.corpus,
            request.monthly_withdrawal,
            request.annual_return,
            request.annual_inflation,
            request.years,
        )
    except FinancialEngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    points = [
        SwpYearPoint(year=item.year, withdrawn=item.withdrawn, balance=item.balance)
        for item in schedule
    ]
    return SwpResponse(
        survival_months=survival,
        sustainable_monthly=sustainable,
        points=points,
    )
