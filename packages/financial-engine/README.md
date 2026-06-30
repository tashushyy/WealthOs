# WealthOS Financial Engine

Pure, dependency-free financial calculations for WealthOS.

**Rule:** modules here contain business logic only — no database, HTTP, or
framework code. They take plain values in and return plain values out, so the
math can be tested in isolation and reused by the API, background jobs, and
reports without dragging in side effects.

## Modules

| Module   | Status | Purpose                                              |
| -------- | ------ | ---------------------------------------------------- |
| `xirr`   | ✅     | Annualized money-weighted return on irregular dates. |
| `cagr`   | ⏳     | Compound annual growth rate.                         |
| `fire`   | ⏳     | Lean / Coast / Regular / Fat / Barista FIRE.         |
| `swp`    | ⏳     | Systematic withdrawal plan + corpus survival.        |
| ...      | ⏳     | See roadmap.                                         |

## XIRR

XIRR finds the discount rate `r` where the net present value of all cash flows
is zero:

```
NPV(r) = Σ amount_i / (1 + r) ^ (days_i / 365) = 0
```

Day count is actual days over a fixed 365-day year, matching spreadsheet
`XIRR`. Sign convention: money **out** is negative, money **in** is positive.

```python
from datetime import date
from financial_engine import Cashflow, xirr

flows = [
    Cashflow(date(2008, 1, 1), -10000),
    Cashflow(date(2008, 3, 1), 2750),
    Cashflow(date(2008, 10, 30), 4250),
    Cashflow(date(2009, 2, 15), 3250),
    Cashflow(date(2009, 4, 1), 2750),
]
xirr(flows)  # -> 0.373362535
```

The solver runs Newton-Raphson and falls back to bracketing bisection when
Newton leaves the valid domain (`r > -1`) or fails to converge, so the result
is independent of the initial `guess`.

### Errors

- `InvalidCashflowsError` — fewer than two flows, or no sign change (a series
  with no money in *or* no money out has no return).
- `ConvergenceError` — no real rate could be bracketed/found.

## Development

```bash
cd packages/financial-engine
pip install -e ".[dev]"

pytest            # tests + coverage (fails under 80%)
ruff check .      # lint
black --check .   # format check
isort --check .   # import order
```

Every module ships with reference-value tests (validated against a known-good
external implementation), edge-case tests, and property-based tests
(Hypothesis) that assert mathematical invariants such as *NPV is zero at the
solution*, *scale invariance*, and *date-shift invariance*.
