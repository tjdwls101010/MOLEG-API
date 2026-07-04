"""MOLEG-API error model."""

from __future__ import annotations

from typing import Any


class MolegApiError(Exception):
    """Base error for MOLEG-API public-interface failures."""


class NoResultError(MolegApiError):
    """The source API returned no usable result for the requested legal task."""


class AmbiguousLawError(MolegApiError):
    """The request matched multiple plausible law identities."""

    def __init__(
        self,
        message: str,
        *,
        kind: str | None = None,
        candidates: list[Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.candidates = list(candidates or [])


class UnsupportedFormatError(MolegApiError):
    """The source endpoint cannot provide a supported response format."""


class SourceApiError(MolegApiError):
    """The source law.go.kr API failed or returned an invalid response."""


class RateLimitError(SourceApiError):
    """The source law.go.kr API rate limited the request."""


class RetryExhaustedError(SourceApiError):
    """Retryable source failures continued through all allowed attempts."""


class ParseFailureError(MolegApiError):
    """A source response could not be normalized into the public model."""


class AsOfBeforeCoverageError(MolegApiError):
    """The requested as_of date predates law.go.kr's consolidated-version coverage.

    A valid identifier and a well-formed date, but no consolidated version text
    exists at (or before) that date — a permanent coverage-floor condition, not a
    transient source failure. Carries the earliest available version date so the
    caller can steer to amendment history instead of retrying.
    """

    def __init__(
        self,
        message: str,
        *,
        law_id: str | None = None,
        earliest_available: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.law_id = law_id
        self.earliest_available = earliest_available
