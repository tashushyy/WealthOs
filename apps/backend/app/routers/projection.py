"""Projection endpoint.

A thin adapter: validate the request, delegate to the financial engine, map the
result (and any domain error) onto HTTP. No business logic lives here.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from financial_engine import projection_schedule
from financial_engine.errors import FinancialEngineError

from app.schemas import ProjectionRequest, ProjectionResponse, YearPoint

router = APIRouter(prefix="/api", tags=["projection"])


@router.post("/projection", response_model=ProjectionResponse)
def compute_projection(request: ProjectionRequest) -> ProjectionResponse:
    """Project portfolio value year by year from a lump sum and monthly SIP."""
    try:
        schedule = projection_schedule(
            request.principal,
            request.monthly_contribution,
            request.annual_return,
            request.years,
            request.annual_step_up,
        )
    except FinancialEngineError as exc:
        # Engine domain errors are client input problems, not server faults.
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    points = [
        YearPoint(year=item.year, contributed=item.contributed, value=item.value)
        for item in schedule
    ]
    return ProjectionResponse(
        points=points,
        final_value=points[-1].value,
        total_contributed=points[-1].contributed,
    )
