"""WealthOS financial engine.

Pure, dependency-free financial calculations. Modules in this package must
never import framework, database, or I/O code — they take plain values in and
return plain values out, so they can be tested in isolation and reused across
the API, background jobs, and reports.
"""

from financial_engine.cagr import (
    CagrError,
    InvalidValueError,
    cagr,
    cagr_between,
)
from financial_engine.errors import FinancialEngineError, InvalidParameterError
from financial_engine.fire import (
    barista_fire_number,
    coast_fire_number,
    fire_number,
    fire_progress,
    years_to_target,
)
from financial_engine.projection import (
    YearSnapshot,
    future_value,
    projection_schedule,
)
from financial_engine.xirr import (
    Cashflow,
    ConvergenceError,
    InvalidCashflowsError,
    XirrError,
    xirr,
)

__all__ = [
    "CagrError",
    "Cashflow",
    "ConvergenceError",
    "FinancialEngineError",
    "InvalidCashflowsError",
    "InvalidParameterError",
    "InvalidValueError",
    "XirrError",
    "YearSnapshot",
    "barista_fire_number",
    "cagr",
    "cagr_between",
    "coast_fire_number",
    "fire_number",
    "fire_progress",
    "future_value",
    "projection_schedule",
    "xirr",
    "years_to_target",
]
