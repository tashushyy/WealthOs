"""Paytm Money portfolio import (scaffold — needs your API credentials).

Uses the official Paytm Money Open API via the ``pyPMClient`` SDK. Auth is
completed by *you* in the browser; the app only ever holds tokens in memory for
the duration of a request.

Setup (one-time):
  1. Register an app at https://developer.paytmmoney.com/ to get an API key and
     secret (requires a KYC-ready Paytm Money trading account).
  2. Install the SDK. It is distributed as a repo, e.g.:
         pip install git+https://github.com/paytmmoney/pyPMClient.git
     (or clone it and add it to the backend's environment).
  3. Export credentials before starting the backend:
         export PAYTM_API_KEY=your_key
         export PAYTM_API_SECRET=your_secret

Flow:
  * GET  /api/paytm/status      -> is this configured / SDK available?
  * GET  /api/paytm/login-url   -> open it, log in, copy the request_token from
                                   the redirected URL.
  * POST /api/paytm/holdings    -> exchange request_token, fetch holdings.

The holdings response schema is not assumed: the endpoint returns Paytm's raw
payload alongside a best-effort mapping, so the mapping can be corrected once a
real response is seen.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/paytm", tags=["paytm"])

_STATE_KEY = "wealthos"

# In-memory credentials set at runtime (e.g. from the frontend). Convenient for a
# personal, local app; NOT for public deployment — a browser-supplied secret is
# transmitted and held in server memory. For anything public, use env vars / a
# secrets manager and remove the /config endpoint. Cleared on backend restart.
_RUNTIME_CREDS: dict[str, str] = {}


class HoldingsImportRequest(BaseModel):
    request_token: str


class PaytmConfig(BaseModel):
    api_key: str
    api_secret: str


def _credentials() -> tuple[str, str]:
    api_key = _RUNTIME_CREDS.get("api_key") or os.environ.get("PAYTM_API_KEY")
    api_secret = _RUNTIME_CREDS.get("api_secret") or os.environ.get("PAYTM_API_SECRET")
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=501,
            detail=(
                "Paytm Money is not configured. Provide an API key and secret "
                "(via the frontend, or PAYTM_API_KEY / PAYTM_API_SECRET env vars)."
            ),
        )
    return api_key, api_secret


@router.post("/config")
def set_config(config: PaytmConfig) -> dict[str, bool]:
    """Store API credentials in memory for this session (personal/local use)."""
    _RUNTIME_CREDS["api_key"] = config.api_key
    _RUNTIME_CREDS["api_secret"] = config.api_secret
    return {"configured": True}


def _make_client() -> Any:
    """Import the SDK lazily and build a client, with clear errors if missing."""
    api_key, api_secret = _credentials()
    try:
        from pyPMClient import PMClient  # type: ignore
    except ImportError:
        try:
            from pmClient import PMClient  # type: ignore
        except ImportError as exc:
            raise HTTPException(
                status_code=501,
                detail=(
                    "Paytm SDK not installed. Install it with "
                    "'pip install git+https://github.com/paytmmoney/pyPMClient.git'."
                ),
            ) from exc
    return PMClient(api_secret=api_secret, api_key=api_key)


@router.get("/status")
def status() -> dict[str, bool]:
    """Report whether credentials and the SDK are available (no network call)."""
    configured = bool(
        (_RUNTIME_CREDS.get("api_key") or os.environ.get("PAYTM_API_KEY"))
        and (_RUNTIME_CREDS.get("api_secret") or os.environ.get("PAYTM_API_SECRET"))
    )
    sdk = True
    try:  # pragma: no cover - depends on optional dependency
        import pyPMClient  # type: ignore  # noqa: F401
    except ImportError:
        try:
            import pmClient  # type: ignore  # noqa: F401
        except ImportError:
            sdk = False
    return {"configured": configured, "sdk_installed": sdk}


@router.get("/login-url")
def login_url() -> dict[str, str]:
    """Return the Paytm Money login URL to open in a browser."""
    client = _make_client()
    try:
        url = client.login(_STATE_KEY)
    except Exception as exc:  # surface any SDK error to the user
        raise HTTPException(status_code=502, detail=f"Paytm login-url error: {exc}") from exc
    return {"url": str(url)}


def _map_holdings(raw: Any) -> list[dict[str, float | str]]:
    """Best-effort map of Paytm holdings to {name, amount}. Adjusted once a real
    response is available."""
    rows = raw.get("data", raw) if isinstance(raw, dict) else raw
    if not isinstance(rows, list):
        return []

    mapped: list[dict[str, float | str]] = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        name = (
            item.get("display_name")
            or item.get("name")
            or item.get("symbol")
            or str(item.get("security_id", "Holding"))
        )
        amount = (
            item.get("value")
            or item.get("holding_value")
            or (float(item.get("quantity", 0) or 0) * float(item.get("last_price", 0) or 0))
        )
        try:
            mapped.append({"name": str(name), "amount": float(amount or 0)})
        except (TypeError, ValueError):
            continue
    return mapped


@router.post("/holdings")
def import_holdings(request: HoldingsImportRequest) -> dict[str, Any]:
    """Exchange the request token and return holdings (raw + best-effort mapped)."""
    client = _make_client()
    try:
        client.generate_session(request_token=request.request_token)
        raw = client.user_holdings_data()
    except Exception as exc:  # surface any SDK/network error
        raise HTTPException(status_code=502, detail=f"Paytm holdings error: {exc}") from exc
    return {"holdings": _map_holdings(raw), "raw": raw}
