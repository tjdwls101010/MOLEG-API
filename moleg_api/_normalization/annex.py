"""Annex and form identity normalization."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.errors import ParseFailureError
from moleg_api.models import AnnexFormIdentity

from .row_format import annex_number_from_parts
from .primitives import compact_date, compact_promulgation_number, first_value, string_or_none

def normalize_annex_form_identity(
    row: dict[str, Any],
    *,
    source_type: str,
    source_target: str,
) -> AnnexFormIdentity:
    info = row.get("기본정보") if isinstance(row.get("기본정보"), dict) else row
    title = first_value(info, "별표명", "별표서식명", "LM")
    if not title:
        raise ParseFailureError("Annex/form identity is missing a title")

    raw_keys = {
        key: info.get(key)
        for key in (
            "licbyl id",
            "admrulbyl id",
            "별표일련번호",
            "별표가지번호",
            "별표서식 가지번호",
            "관련법령일련번호",
            "관련행정규칙 일련번호",
            "관련행정규칙일련번호",
            "관련법령ID",
            "별표법령 상세링크",
            "별표행정규칙 상세링크",
            "별표행정규칙상세링크",
        )
        if info.get(key) not in (None, "")
    }
    return AnnexFormIdentity(
        annex_id=string_or_none(first_value(info, "licbyl id", "admrulbyl id", "별표일련번호", "ID")),
        title=str(title),
        source_type=source_type,
        source_target=source_target,
        related_name=string_or_none(first_value(info, "관련법령명", "관련행정규칙명", "관련자치법규명")),
        related_id=string_or_none(first_value(info, "관련법령ID", "관련행정규칙ID", "관련자치법규ID")),
        related_serial_id=string_or_none(
            first_value(
                info,
                "관련법령일련번호",
                "관련행정규칙 일련번호",
                "관련행정규칙일련번호",
                "관련자치법규일련번호",
            )
        ),
        annex_number=annex_number_from_parts(
            first_value(info, "별표번호"),
            first_value(info, "별표가지번호", "별표서식 가지번호"),
        ),
        annex_type=string_or_none(first_value(info, "별표종류")),
        ministry=string_or_none(first_value(info, "소관부처명", "소관부처")),
        promulgation_date=string_or_none(compact_date(first_value(info, "공포일자"))),
        promulgation_number=string_or_none(first_value(info, "공포번호")),
        issued_on=string_or_none(compact_date(first_value(info, "발령일자"))),
        issuing_number=string_or_none(first_value(info, "발령번호")),
        revision_type=string_or_none(first_value(info, "제개정구분명")),
        law_type=string_or_none(first_value(info, "법령종류", "법령구분명")),
        rule_type=string_or_none(first_value(info, "행정규칙종류", "행정규칙 종류명")),
        file_link=string_or_none(first_value(info, "별표서식 파일링크", "별표서식파일링크")),
        pdf_link=string_or_none(first_value(info, "별표서식 PDF파일링크", "별표서식PDF파일링크")),
        detail_link=string_or_none(
            first_value(
                info,
                "별표법령 상세링크",
                "별표법령상세링크",
                "별표행정규칙 상세링크",
                "별표행정규칙상세링크",
                "별표자치법규 상세링크",
                "별표자치법규상세링크",
            )
        ),
        raw_keys=raw_keys,
    )
