"""API tests for the FIRE and SWP endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_fire_target_and_progress() -> None:
    response = client.post(
        "/api/fire",
        json={
            "annual_expenses": 40000,
            "withdrawal_rate": 0.04,
            "current_corpus": 250000,
            "monthly_contribution": 10000,
            "annual_return": 0.10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fire_number"] == 1_000_000.0  # 25x expenses
    assert body["progress"] == 0.25
    assert isinstance(body["years_to_fire"], int)


def test_fire_rejects_bad_withdrawal_rate() -> None:
    response = client.post(
        "/api/fire",
        json={
            "annual_expenses": 40000,
            "withdrawal_rate": 1.5,
            "current_corpus": 0,
            "monthly_contribution": 0,
            "annual_return": 0.1,
        },
    )
    assert response.status_code == 422


def test_swp_survival_and_schedule() -> None:
    response = client.post(
        "/api/swp",
        json={
            "corpus": 1200,
            "monthly_withdrawal": 100,
            "annual_return": 0.0,
            "annual_inflation": 0.0,
            "years": 1,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["survival_months"] == 12
    assert len(body["points"]) == 1
    assert body["sustainable_monthly"] > 0


def test_swp_reports_sustainable_none_when_perpetual() -> None:
    response = client.post(
        "/api/swp",
        json={
            "corpus": 1000000,
            "monthly_withdrawal": 100,
            "annual_return": 0.10,
            "annual_inflation": 0.0,
            "years": 30,
        },
    )
    assert response.status_code == 200
    body = response.json()
    # Tiny withdrawal against strong growth never depletes.
    assert body["survival_months"] is None


def test_swp_rejects_return_below_minus_one() -> None:
    response = client.post(
        "/api/swp",
        json={
            "corpus": 1000,
            "monthly_withdrawal": 50,
            "annual_return": -1.5,
            "annual_inflation": 0.0,
            "years": 10,
        },
    )
    assert response.status_code == 422
