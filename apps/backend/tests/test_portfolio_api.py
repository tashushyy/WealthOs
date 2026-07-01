"""API tests for the portfolio endpoint.

The market-data endpoints (/api/instruments/*) hit live third-party services,
so they are exercised manually rather than in this offline test suite.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_portfolio_blends_returns() -> None:
    response = client.post(
        "/api/portfolio",
        json={
            "holdings": [
                {"name": "Equity Fund", "amount": 6000, "expected_return": 0.10},
                {"name": "Debt Fund", "amount": 4000, "expected_return": 0.20},
            ]
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_invested"] == 10000
    assert body["blended_return"] == 0.14
    assert body["blended_volatility"] is None
    assert [round(w["weight"], 2) for w in body["weights"]] == [0.6, 0.4]


def test_portfolio_blends_volatility_when_all_present() -> None:
    response = client.post(
        "/api/portfolio",
        json={
            "holdings": [
                {"name": "A", "amount": 5000, "expected_return": 0.10, "volatility": 0.20},
                {"name": "B", "amount": 5000, "expected_return": 0.10, "volatility": 0.10},
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["blended_volatility"] == pytest.approx(0.15)


def test_portfolio_requires_at_least_one_holding() -> None:
    response = client.post("/api/portfolio", json={"holdings": []})
    assert response.status_code == 422


def test_portfolio_rejects_zero_total() -> None:
    response = client.post(
        "/api/portfolio",
        json={"holdings": [{"name": "A", "amount": 0, "expected_return": 0.1}]},
    )
    assert response.status_code == 422
