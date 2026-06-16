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
