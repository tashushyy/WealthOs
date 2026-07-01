"""WealthOS API entry point.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import fire, market, paytm, portfolio, projection, swp

app = FastAPI(title="WealthOS API", version="0.1.0")

# The Next.js dev server runs on :3000; allow it to call the API in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projection.router)
app.include_router(fire.router)
app.include_router(swp.router)
app.include_router(portfolio.router)
app.include_router(market.router)
app.include_router(paytm.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
