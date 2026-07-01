"""FIRE endpoint.

Thin adapter over the engine's FIRE helpers: compute the target corpus, how far
the current corpus is toward it, and how many years of contributions reach it.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from financial_engine import fire_number, fire_progress, years_to_target
from financial_engine.errors import FinancialEngineError

from app.schemas import FireRequest, FireResponse

router = APIRouter(prefix="/api", tags=["fire"])


@router.post("/fire", response_model=FireResponse)
def compute_fire(request: FireRequest) -> FireResponse:
    """Compute a FIRE target, progress toward it, and years to reach it."""
    try:
        target = fire_number(request.annual_expenses, request.withdrawal_rate)
        if target == 0:
            # Zero expenses means already financially independent.
            return FireResponse(fire_number=0.0, progress=1.0, years_to_fire=0)

        progress = fire_progress(request.current_corpus, target)
        years = years_to_target(
            request.current_corpus,
            request.monthly_contribution,
            request.annual_return,
            target,
        )
    except FinancialEngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return FireResponse(fire_number=target, progress=progress, years_to_fire=years)
