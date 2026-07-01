"""Market-data endpoints (best-effort).

Search for instruments and estimate an expected return from trailing history.

Data sources (both free, no API key, and both **unofficial** — they can change,
rate-limit, or break):
  * Mutual funds (India): https://www.mfapi.in (wraps AMFI NAV data).
  * Stocks / ETFs / commodities: Yahoo Finance query endpoints.

"Expected return" here is the trailing CAGR over the available window (up to ~5
years). That is *past performance*, not a forecast — the frontend labels it as
such, and the user can always override it or enter a holding manually.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx
from fastapi import APIRouter, HTTPException, Query
from financial_engine import cagr_between
from financial_engine.errors import FinancialEngineError

from app.schemas import InstrumentResult, QuoteResult

router = APIRouter(prefix="/api/instruments", tags=["market"])

_TIMEOUT = httpx.Timeout(8.0)
_HEADERS = {"User-Agent": "Mozilla/5.0 (WealthOS)"}
_MFAPI = "https://api.mfapi.in"
_YAHOO = "https://query1.finance.yahoo.com"
_YAHOO_SEARCH = "https://query2.finance.yahoo.com"

_YAHOO_KIND = {
    "EQUITY": "stock",
    "ETF": "etf",
    "MUTUALFUND": "mutual_fund",
    "FUTURE": "commodity",
    "INDEX": "index",
    "CURRENCY": "currency",
    "CRYPTOCURRENCY": "crypto",
}


def _trailing_cagr(begin_value: float, end_value: float, start: date, end: date) -> float | None:
    """CAGR between two dated prices, or None if it is not computable."""
    try:
        return cagr_between(begin_value, end_value, start, end)
    except FinancialEngineError:
        return None


def _search_mutual_funds(query: str) -> list[InstrumentResult]:
    resp = httpx.get(f"{_MFAPI}/mf/search", params={"q": query}, timeout=_TIMEOUT)
    resp.raise_for_status()
    results: list[InstrumentResult] = []
    for item in resp.json()[:15]:
        code = item.get("schemeCode")
        name = item.get("schemeName")
        if code and name:
            results.append(InstrumentResult(id=f"mf:{code}", name=name, kind="mutual_fund"))
    return results


def _search_yahoo(query: str) -> list[InstrumentResult]:
    resp = httpx.get(
        f"{_YAHOO_SEARCH}/v1/finance/search",
        params={"q": query, "quotesCount": 15, "newsCount": 0},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    results: list[InstrumentResult] = []
    for quote in resp.json().get("quotes", []):
        symbol = quote.get("symbol")
        if not symbol:
            continue
        name = quote.get("shortname") or quote.get("longname") or symbol
        kind = _YAHOO_KIND.get(quote.get("quoteType", ""), "other")
        results.append(InstrumentResult(id=f"yahoo:{symbol}", name=name, kind=kind, symbol=symbol))
    return results


@router.get("/search", response_model=list[InstrumentResult])
def search_instruments(
    q: str = Query(min_length=1, description="Search text."),
    kind: str = Query("all", description="all | mf | market"),
) -> list[InstrumentResult]:
    """Search mutual funds and/or stocks/ETFs/commodities."""
    try:
        results: list[InstrumentResult] = []
        if kind in ("all", "mf"):
            results += _search_mutual_funds(q)
        if kind in ("all", "market"):
            results += _search_yahoo(q)
        return results
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Search provider error: {exc}") from exc


def _quote_mutual_fund(code: str) -> QuoteResult:
    resp = httpx.get(f"{_MFAPI}/mf/{code}", timeout=_TIMEOUT)
    resp.raise_for_status()
    payload = resp.json()
    data = payload.get("data", [])
    name = payload.get("meta", {}).get("scheme_name", code)
    if not data:
        return QuoteResult(id=f"mf:{code}", name=name, price=None)

    latest = data[0]
    price = float(latest["nav"])
    end_dt = datetime.strptime(latest["date"], "%d-%m-%Y").date()

    cutoff = end_dt - timedelta(days=5 * 365)
    begin = data[-1]
    for row in data:
        row_dt = datetime.strptime(row["date"], "%d-%m-%Y").date()
        if row_dt <= cutoff:
            begin = row
            break
    begin_dt = datetime.strptime(begin["date"], "%d-%m-%Y").date()
    begin_nav = float(begin["nav"])

    expected = _trailing_cagr(begin_nav, price, begin_dt, end_dt)
    window = (end_dt - begin_dt).days / 365.0
    return QuoteResult(
        id=f"mf:{code}",
        name=name,
        price=price,
        expected_return=expected,
        window_years=round(window, 1) if window > 0 else None,
        as_of=end_dt.isoformat(),
    )


def _quote_yahoo(symbol: str) -> QuoteResult:
    resp = httpx.get(
        f"{_YAHOO}/v8/finance/chart/{symbol}",
        params={"range": "5y", "interval": "1mo"},
        headers=_HEADERS,
        timeout=_TIMEOUT,
    )
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    meta = result.get("meta", {})
    timestamps = result.get("timestamp", []) or []
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", []) or []

    series = [(ts, c) for ts, c in zip(timestamps, closes, strict=False) if c is not None]
    price = meta.get("regularMarketPrice")
    name = meta.get("longName") or meta.get("shortName") or symbol
    if len(series) < 2:
        return QuoteResult(id=f"yahoo:{symbol}", name=name, price=price)

    begin_ts, begin_price = series[0]
    end_ts, end_price = series[-1]
    begin_dt = date.fromtimestamp(begin_ts)
    end_dt = date.fromtimestamp(end_ts)
    expected = _trailing_cagr(float(begin_price), float(end_price), begin_dt, end_dt)
    window = (end_dt - begin_dt).days / 365.0
    return QuoteResult(
        id=f"yahoo:{symbol}",
        name=name,
        price=price if price is not None else float(end_price),
        expected_return=expected,
        window_years=round(window, 1) if window > 0 else None,
        as_of=end_dt.isoformat(),
    )


@router.get("/quote", response_model=QuoteResult)
def quote_instrument(id: str = Query(description="Instrument id from search.")) -> QuoteResult:
    """Latest price and trailing-CAGR expected return for one instrument."""
    try:
        prefix, _, value = id.partition(":")
        if prefix == "mf" and value:
            return _quote_mutual_fund(value)
        if prefix == "yahoo" and value:
            return _quote_yahoo(value)
        raise HTTPException(status_code=400, detail=f"Unrecognized instrument id: {id}")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Quote provider error: {exc}") from exc
    except (KeyError, ValueError, IndexError) as exc:
        raise HTTPException(status_code=502, detail=f"Unexpected provider response: {exc}") from exc
