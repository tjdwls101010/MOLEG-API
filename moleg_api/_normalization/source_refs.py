from __future__ import annotations

import re
from typing import Any

from .primitives import (
    ADMINISTRATIVE_RULE_SOURCE_ARTICLE_BRANCH_KEYS,
    ADMINISTRATIVE_RULE_SOURCE_ARTICLE_KEYS,
    ADMINISTRATIVE_RULE_SOURCE_ARTICLE_TITLE_KEYS,
    ADMINISTRATIVE_RULE_SOURCE_BASIS_KEYS,
    ADMINISTRATIVE_RULE_SOURCE_LAW_ID_KEYS,
    ADMINISTRATIVE_RULE_SOURCE_LAW_NAME_KEYS,
    first_value,
    string_or_none,
)
from .row_format import article_label_from_parts


def administrative_rule_source_reference(row: dict[str, Any]) -> dict[str, str | None]:
    basis_text = string_or_none(first_value(row, *ADMINISTRATIVE_RULE_SOURCE_BASIS_KEYS))
    return {
        "source_law_id": string_or_none(first_value(row, *ADMINISTRATIVE_RULE_SOURCE_LAW_ID_KEYS)),
        "source_law_name": string_or_none(
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_LAW_NAME_KEYS)
        )
        or quoted_law_name(basis_text),
        "source_article": article_label_from_parts(
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_KEYS),
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_BRANCH_KEYS),
        )
        or article_from_source_basis(basis_text),
        "source_article_title": string_or_none(
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_TITLE_KEYS)
        ),
    }


def quoted_law_name(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"[「『](.+?)[」』]", text)
    if not match:
        return None
    return match.group(1).strip() or None


def article_from_source_basis(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(
        r"제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?",
        text,
    )
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(0))
