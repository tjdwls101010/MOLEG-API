from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from importlib.metadata import PackageNotFoundError, version as _dist_version
from typing import Any

from ..errors import (
    AmbiguousLawError,
    AsOfBeforeCoverageError,
    MolegApiError,
    NoResultError,
    ParseFailureError,
    RateLimitError,
    RetryExhaustedError,
    UnsupportedFormatError,
)
from ..laws import MolegApi
from ..models import DeferredLookup


def _pkg_version() -> str:
    try:
        return _dist_version("moleg-api")
    except PackageNotFoundError:
        return "unknown"

__all__ = [name for name in globals() if not name.startswith("__")]
