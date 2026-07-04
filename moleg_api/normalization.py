"""Normalization helpers for MOLEG source payloads."""

from __future__ import annotations

from ._normalization import *
from ._normalization.authority import _DISPOSITION_RULES
from ._normalization.delegation import _DELEGATION_TARGET_KEYS, _transpose_delegation_info
from ._normalization.history_html import _diff_article_header, _diff_row_has_real_article
from ._normalization.primitives import _digits
