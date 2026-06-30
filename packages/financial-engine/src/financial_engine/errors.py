"""Shared exception hierarchy for the financial engine.

Every module raises errors that derive from :class:`FinancialEngineError`, so
callers can catch all engine-level problems with a single ``except`` while still
being able to target a specific failure (e.g. ``InvalidCashflowsError``).
``FinancialEngineError`` itself subclasses :class:`ValueError`, so existing code
that catches ``ValueError`` keeps working.
"""

from __future__ import annotations


class FinancialEngineError(ValueError):
    """Base class for all errors raised by the financial engine."""


class InvalidParameterError(FinancialEngineError):
    """A numeric parameter is outside its valid domain.

    Shared by modules whose inputs are simple scalars (e.g. projection, fire,
    swp), so callers see one error type for "you passed a bad value". Modules
    with domain-specific failure modes (e.g. XIRR's cash-flow shape) keep their
    own error types.
    """
