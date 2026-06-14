"""MOLEG-API error model."""


class MolegApiError(Exception):
    """Base error for MOLEG-API public-interface failures."""


class NoResultError(MolegApiError):
    """The source API returned no usable result for the requested legal task."""


class AmbiguousLawError(MolegApiError):
    """The request matched multiple plausible law identities."""


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
