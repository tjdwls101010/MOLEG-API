"""Primitive normalization values and scalar helpers."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

LAW_SEARCH_ENVELOPES = ("LawSearch", "lawSearch", "LawSearchService")
ARTICLE_REFERENCE_RE = re.compile(r"제\s*(?P<number>\d+)\s*조(?:\s*의\s*(?P<branch>\d+))?")
LAW_NAME_RE = re.compile(
    r"[가-힣A-Za-z0-9ㆍ·().\s]+(?:법률|시행령|시행규칙|법|령|규칙|조례|고시|예규|훈령|규정|지침)"
)
MAX_EXPANDED_ARTICLE_RANGE = 100

ADMINISTRATIVE_RULE_SOURCE_LAW_ID_KEYS = (
    "위임법령ID",
    "위임법령 ID",
    "위임 법령ID",
    "위임 법령 ID",
    "근거법령ID",
    "근거법령 ID",
    "근거 법령ID",
    "근거 법령 ID",
    "수권법령ID",
    "수권법령 ID",
    "수권 법령ID",
    "수권 법령 ID",
    "상위법령ID",
    "상위법령 ID",
    "상위 법령ID",
    "상위 법령 ID",
    "모법령ID",
    "모법령 ID",
    "모법 ID",
    "법적근거법령ID",
    "법적근거 법령ID",
)

ADMINISTRATIVE_RULE_SOURCE_LAW_NAME_KEYS = (
    "위임법령명",
    "위임법령",
    "위임 법령명",
    "위임 법령",
    "근거법령명",
    "근거법령",
    "근거 법령명",
    "근거 법령",
    "수권법령명",
    "수권법령",
    "수권 법령명",
    "수권 법령",
    "상위법령명",
    "상위법령",
    "상위 법령명",
    "상위 법령",
    "모법령명",
    "모법령",
    "모법명",
    "모법",
    "법적근거법령명",
    "법적근거법령",
    "법적근거 법령명",
    "법적근거 법령",
)

ADMINISTRATIVE_RULE_SOURCE_ARTICLE_KEYS = (
    "위임조문번호",
    "위임조문",
    "위임 조문번호",
    "위임 조문",
    "위임근거조문",
    "위임근거 조문",
    "근거조문번호",
    "근거조문",
    "근거 조문번호",
    "근거 조문",
    "수권조문번호",
    "수권조문",
    "수권 조문번호",
    "수권 조문",
    "상위조문번호",
    "상위조문",
    "상위 조문번호",
    "상위 조문",
    "모법령조문",
    "모법조문",
    "법적근거조문",
    "법적근거 조문",
)

ADMINISTRATIVE_RULE_SOURCE_ARTICLE_BRANCH_KEYS = (
    "위임조문가지번호",
    "위임 조문가지번호",
    "위임 조문 가지번호",
    "위임근거조문가지번호",
    "위임근거 조문가지번호",
    "위임근거 조문 가지번호",
    "근거조문가지번호",
    "근거 조문가지번호",
    "근거 조문 가지번호",
    "수권조문가지번호",
    "수권 조문가지번호",
    "수권 조문 가지번호",
    "상위조문가지번호",
    "상위 조문가지번호",
    "상위 조문 가지번호",
    "모법령조문가지번호",
    "모법령 조문가지번호",
    "모법령 조문 가지번호",
    "모법조문가지번호",
    "모법 조문가지번호",
    "모법 조문 가지번호",
    "법적근거조문가지번호",
    "법적근거 조문가지번호",
    "법적근거 조문 가지번호",
)

ADMINISTRATIVE_RULE_SOURCE_ARTICLE_TITLE_KEYS = (
    "위임조문제목",
    "위임 조문제목",
    "위임 조문 제목",
    "근거조문제목",
    "근거 조문제목",
    "근거 조문 제목",
    "수권조문제목",
    "수권 조문제목",
    "상위조문제목",
    "상위 조문제목",
    "모법령조문제목",
    "모법조문제목",
    "법적근거조문제목",
)

ADMINISTRATIVE_RULE_SOURCE_BASIS_KEYS = (
    "위임근거",
    "위임 근거",
    "근거",
    "법적근거",
    "법적 근거",
    "수권근거",
    "수권 근거",
)

ADMINISTRATIVE_RULE_SOURCE_KEYS = (
    *ADMINISTRATIVE_RULE_SOURCE_LAW_ID_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_LAW_NAME_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_BRANCH_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_TITLE_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_BASIS_KEYS,
)
AI_ROW_KEYS = ("법령조문", "법령별표서식", "행정규칙조문", "행정규칙별표서식")


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def compact_date(value: str | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().strftime("%Y%m%d")
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    if not text:
        return None
    dotted = re.fullmatch(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", text)
    if dotted:
        year, month, day = dotted.groups()
        return f"{year}{int(month):02d}{int(day):02d}"
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return digits
    return text

def compact_promulgation_number(value: Any) -> str | None:
    text = string_or_none(value)
    if text is None:
        return None
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^제", "", text)
    text = re.sub(r"호$", "", text)
    return text or None


def first_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return content_value(value)
    return None


def content_value(value: Any) -> Any:
    if isinstance(value, dict) and "content" in value:
        return value.get("content")
    return value


def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", "", text)


def yes_no_or_none(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    normalized = str(value).strip().upper()
    if normalized in {"Y", "YES", "TRUE", "1"}:
        return True
    if normalized in {"N", "NO", "FALSE", "0"}:
        return False
    return None


def is_deleted_article(
    text: str,
    *,
    title: str | None = None,
    revision_type: str | None = None,
) -> bool:
    if revision_type and "삭제" in revision_type:
        return True
    if title and title.strip() == "삭제":
        return True
    return article_text_marks_deleted(text)


def article_text_marks_deleted(text: str) -> bool:
    compact = compact_whitespace(text)
    return bool(
        re.fullmatch(
            r"제\d+조(?:의\d+)?(?:\([^)]*\))?삭제(?:[<［【(].*)?",
            compact,
        )
    )


def mask_oc_param(link: str | None) -> str | None:
    """Mask the OC credential in a law.go.kr link before it is surfaced."""
    if not link:
        return link
    return re.sub(r"(OC=)[^&]*", r"\1***", link)

def _digits(value: Any) -> str:
    return "".join(ch for ch in str(value) if ch.isdigit())


def string_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
