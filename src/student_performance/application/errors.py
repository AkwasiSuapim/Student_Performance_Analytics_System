"""Domain-level errors raised by the application service."""

from __future__ import annotations


class AnalysisError(Exception):
    """An expected, user-explainable failure with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
