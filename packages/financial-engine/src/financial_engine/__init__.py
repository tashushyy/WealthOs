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
from financial_engine.errors import FinancialEngineError
from financial_engine.projection import (
    InvalidParameterError,
    ProjectionError,
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
    "ProjectionError",
    "XirrError",
    "YearSnapshot",
    "cagr",
    "cagr_between",
    "future_value",
    "projection_schedule",
    "xirr",
]
