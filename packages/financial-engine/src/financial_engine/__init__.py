"""WealthOS financial engine.

Pure, dependency-free financial calculations. Modules in this package must
never import framework, database, or I/O code — they take plain values in and
return plain values out, so they can be tested in isolation and reused across
the API, background jobs, and reports.
"""

from financial_engine.xirr import (
    Cashflow,
    ConvergenceError,
    InvalidCashflowsError,
    XirrError,
    xirr,
)

__all__ = [
    "Cashflow",
    "ConvergenceError",
    "InvalidCashflowsError",
    "XirrError",
    "xirr",
]
