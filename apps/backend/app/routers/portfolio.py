"""Portfolio endpoint.

Thin adapter over the engine's portfolio blending: amount-weighted expected
return, per-holding weights, and (if every holding has one) a blended
volatility.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from financial_engine import Holding, summarize
from financial_engine.errors import FinancialEngineError

from app.schemas import PortfolioRequest, PortfolioResponse, WeightOut

router = APIRouter(prefix="/api", tags=["portfolio"])


@router.post("/portfolio", response_model=PortfolioResponse)
def compute_portfolio(request: PortfolioRequest) -> PortfolioResponse:
    """Blend holdings into a portfolio summary."""
    try:
        summary = summarize(
            [
                Holding(
                    name=h.name,
                    amount=h.amount,
                    expected_return=h.expected_return,
                    volatility=h.volatility,
                )
                for h in request.holdings
            ]
        )
    except FinancialEngineError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PortfolioResponse(
        total_invested=summary.total_invested,
        blended_return=summary.blended_return,
        blended_volatility=summary.blended_volatility,
        weights=[WeightOut(name=w.name, weight=w.weight) for w in summary.weights],
    )
