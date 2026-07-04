"""Query-expansion candidate normalization."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.models import LegalArticleCandidate, LegalLawCandidate, LegalTermCandidate

from .row_format import article_label_from_parts
from .primitives import compact_date, first_value, string_or_none

def normalize_term_candidate(
    row: dict[str, Any],
    *,
    source_type: str,
    source_target: str,
) -> LegalTermCandidate | None:
    if source_type == "everyday_term":
        term = first_value(row, "일상용어명", "법령용어명", "법령용어명_한글")
    else:
        term = first_value(row, "법령용어명", "법령용어명_한글", "일상용어명")
    if not term:
        return None
    return LegalTermCandidate(
        term=str(term),
        source_type=source_type,
        source_target=source_target,
        term_id=string_or_none(
            first_value(
                row,
                "법령용어 id",
                "법령용어ID",
                "법령용어 일련번호",
                "일상용어 id",
                "연계용어 id",
            )
        ),
        relation=string_or_none(first_value(row, "용어관계", "용어구분")),
        note=string_or_none(first_value(row, "비고", "동음이의어 내용")),
        definition=string_or_none(first_value(row, "법령용어정의")),
        source_title=string_or_none(first_value(row, "출처")),
        raw=row,
    )


def normalize_related_article_candidate(
    row: dict[str, Any],
    *,
    source_target: str,
) -> LegalArticleCandidate | None:
    law_name = string_or_none(first_value(row, "법령명", "행정규칙명"))
    text = string_or_none(first_value(row, "조문내용"))
    title = string_or_none(first_value(row, "조문제목"))
    article = article_label_from_parts(
        first_value(row, "조문번호", "조번호"),
        first_value(row, "조문가지번호", "조가지번호"),
    )
    if not law_name and not text and not title:
        return None
    return LegalArticleCandidate(
        law_name=law_name,
        law_id=string_or_none(first_value(row, "법령ID", "행정규칙ID")),
        article=article,
        title=title,
        text=text,
        source_target=source_target,
        term=string_or_none(first_value(row, "법령용어명", "일상용어명")),
        raw=row,
    )


def normalize_related_law_candidate(
    row: dict[str, Any],
    *,
    source_target: str,
) -> LegalLawCandidate | None:
    name = first_value(row, "관련법령명", "법령명", "행정규칙명")
    if not name:
        return None
    source_type = "administrative_rule" if first_value(row, "행정규칙ID", "행정규칙명") else "law"
    return LegalLawCandidate(
        name=str(name),
        law_id=string_or_none(first_value(row, "관련법령ID", "법령ID", "행정규칙ID")),
        mst=string_or_none(first_value(row, "MST", "법령일련번호", "lsi_seq")),
        source_type=source_type,
        source_target=source_target,
        relation=string_or_none(first_value(row, "법령간관계", "제개정구분명", "행정규칙 종류명")),
        article=article_label_from_parts(
            first_value(row, "조문번호", "조번호"),
            first_value(row, "조문가지번호", "조가지번호"),
        ),
        article_title=string_or_none(first_value(row, "조문제목")),
        promulgation_date=string_or_none(compact_date(first_value(row, "공포일자"))),
        effective_date=string_or_none(compact_date(first_value(row, "시행일자"))),
        promulgation_number=string_or_none(first_value(row, "공포번호")),
        law_type=string_or_none(first_value(row, "법령종류명", "법령구분명")),
        ministry=string_or_none(first_value(row, "소관부처명", "소관부처")),
        raw=row,
    )
