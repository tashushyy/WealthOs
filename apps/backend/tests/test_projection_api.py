"""API tests for the projection endpoint, using FastAPI's TestClient."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_projection_happy_path() -> None:
    response = client.post(
        "/api/projection",
        json={
            "principal": 0,
            "monthly_contribution": 100,
            "annual_return": 0.0,
            "years": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["points"]) == 1
    # No growth, 100/month for 12 months -> 1200.
    assert body["final_value"] == 1200.0
    assert body["total_contributed"] == 1200.0


def test_projection_returns_one_point_per_year() -> None:
    response = client.post(
        "/api/projection",
        json={
            "principal": 100000,
            "monthly_contribution": 10000,
            "annual_return": 0.12,
            "years": 20,
            "annual_step_up": 0.10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert [p["year"] for p in body["points"]] == list(range(1, 21))
    assert body["final_value"] > body["total_contributed"]  # growth happened


def test_projection_rejects_return_below_minus_one() -> None:
    response = client.post(
        "/api/projection",
        json={
            "principal": 1000,
            "monthly_contribution": 0,
            "annual_return": -1.5,
            "years": 5,
        },
    )
    assert response.status_code == 422


def test_projection_rejects_zero_years() -> None:
    response = client.post(
        "/api/projection",
        json={
            "principal": 1000,
            "monthly_contribution": 0,
            "annual_return": 0.1,
            "years": 0,
        },
    )
    assert response.status_code == 422
