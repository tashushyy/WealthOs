# WealthOS Financial Engine

Pure, dependency-free financial calculations for WealthOS.

**Rule:** modules here contain business logic only — no database, HTTP, or
framework code. They take plain values in and return plain values out, so the
math can be tested in isolation and reused by the API, background jobs, and
reports without dragging in side effects.

## Modules

| Module   | Status | Purpose                                              |
| -------- | ------ | ---------------------------------------------------- |
| `xirr`       | ✅ | Annualized money-weighted return on irregular dates.   |
| `cagr`       | ✅ | Compound annual growth rate (smoothed, first-to-last). |
| `projection` | ✅ | Future value of a lump sum + monthly SIP (with step-up).|
| `fire`       | ✅ | FIRE targets (Lean/Regular/Fat/Coast/Barista) + progress.|
| `swp`        | ⏳ | Systematic withdrawal plan + corpus survival.          |
| ...          | ⏳ | See roadmap.                                            |

All modules raise errors deriving from `FinancialEngineError` (itself a
`ValueError`), so callers can catch engine problems broadly or by specific type.

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

## CAGR

CAGR is the smoothed annual rate from a first value to a last value, ignoring
the timing of anything in between:

```
CAGR = (end / begin) ^ (1 / years) - 1
```

Reach for CAGR for the headline "what steady annual return matches this growth"
figure, and for XIRR when intermediate contributions and withdrawals matter.

```python
from datetime import date
from financial_engine import cagr, cagr_between

cagr(1000.0, 2000.0, 2.0)                                   # -> 0.414214 (doubled in 2y)
cagr_between(1000.0, 1200.0, date(2023, 1, 1), date(2024, 1, 1))  # actual/365 day count
```

A total loss (`end == 0`) returns `-1.0`. `InvalidValueError` is raised for a
non-positive `begin`, a negative `end`, a non-positive `years`, or end-not-after
-start dates.

## Projection

Future value of a starting lump sum plus a monthly SIP, with an optional annual
step-up of the contribution. The annual return is converted to an effective
monthly rate, contributions are end-of-month, and the math is an exact
month-by-month loop (correct even at zero return and for the step-up case).

```python
from financial_engine import future_value, projection_schedule

future_value(100_000, 10_000, 0.12, 20, annual_step_up=0.10)  # final value
schedule = projection_schedule(100_000, 10_000, 0.12, 20)     # per-year snapshots
schedule[-1].value, schedule[-1].contributed                  # for growth charts
```

`InvalidParameterError` is raised for a negative principal/contribution/step-up,
an annual return at or below -100%, or a non-positive number of years.

## FIRE

Corpus targets for the FIRE variants and progress tracking. The 4% safe
withdrawal rate (the 25x-expenses rule) is the default assumption.

```python
from financial_engine import (
    fire_number, coast_fire_number, barista_fire_number,
    fire_progress, years_to_target,
)

fire_number(40_000)                       # 1_000_000  (Regular; Lean/Fat = lower/higher expenses)
coast_fire_number(1_000_000, 0.07, 30)    # amount needed today to coast to the target
barista_fire_number(40_000, 20_000)       # corpus for expenses not met by part-time income
fire_progress(250_000, 1_000_000)         # 0.25
years_to_target(250_000, 10_000, 0.10, 1_000_000)  # whole years to reach it (built on projection)
```

Lean, Regular, and Fat FIRE are `fire_number` with lower, baseline, or higher
expense figures. `years_to_target` returns `0` if already met, the year the
target is first reached, or `None` if not reached within `max_years`.
`InvalidParameterError` covers negative inputs, a withdrawal rate outside
`(0, 1]`, and a return at or below -100%.

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
