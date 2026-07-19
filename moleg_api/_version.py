"""Single source of truth for the package version.

Deliberately a literal in the package rather than a lookup through
``importlib.metadata``: metadata describes the *installed distribution*, but the
code that actually runs may come from somewhere else entirely. A checkout on
``sys.path`` shadows site-packages, so ``python -m moleg_api`` silently executes
checkout code while the distribution metadata still reports the installed
release — the exact skew that made "which version answered me?" unanswerable.
A literal travels with the code, so the version an envelope reports is always the
version that produced it.

``pyproject.toml`` reads this attribute (``[tool.setuptools.dynamic]``), so the
build and the runtime can never disagree.
"""

from __future__ import annotations

__version__ = "0.3.0"
