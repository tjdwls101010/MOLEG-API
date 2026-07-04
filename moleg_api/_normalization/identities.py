"""Law and administrative-rule identity normalization."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.errors import ParseFailureError
from moleg_api.models import AdministrativeRuleIdentity, Basis, LawIdentity

from .primitives import (
    ADMINISTRATIVE_RULE_SOURCE_KEYS,
    compact_date,
    compact_promulgation_number,
    first_value,
    string_or_none,
)
from .source_refs import administrative_rule_source_reference

def normalize_law_identity(row: dict[str, Any], *, basis: Basis) -> LawIdentity:
    info = row.get("기본정보") if isinstance(row.get("기본정보"), dict) else row
    name = first_value(info, "법령명_한글", "법령명한글", "법령명", "법령명약칭")
    if not name:
        raise ParseFailureError("Law identity is missing a law name")

    raw_keys = {
        key: info.get(key)
        for key in (
            "법령ID",
            "ID",
            "MST",
            "LID",
            "법령일련번호",
            "lsi_seq",
            "법령상세링크",
        )
        if info.get(key) not in (None, "")
    }
    return LawIdentity(
        law_id=string_or_none(first_value(info, "법령ID", "ID")),
        mst=string_or_none(first_value(info, "MST", "법령일련번호", "lsi_seq")),
        lid=string_or_none(first_value(info, "LID")),
        name=str(name),
        basis=basis,
        promulgation_date=string_or_none(compact_date(first_value(info, "공포일자"))),
        effective_date=string_or_none(compact_date(first_value(info, "시행일자"))),
        promulgation_number=compact_promulgation_number(first_value(info, "공포번호", "prom_no")),
        law_type=string_or_none(first_value(info, "법종구분", "법령구분명")),
        ministry=string_or_none(first_value(info, "소관부처", "소관부처명")),
        raw_keys=raw_keys,
    )


def normalize_administrative_rule_identity(row: dict[str, Any]) -> AdministrativeRuleIdentity:
    if isinstance(row.get("기본정보"), dict):
        info = row["기본정보"]
    elif isinstance(row.get("행정규칙기본정보"), dict):
        info = row["행정규칙기본정보"]
    else:
        info = row
    source_info = {**row, **info} if info is not row else info
    name = first_value(info, "행정규칙명", "신구법명", "LM")
    if not name:
        raise ParseFailureError("Administrative-rule identity is missing a name")

    raw_keys = {
        key: source_info.get(key)
        for key in (
            "행정규칙 일련번호",
            "행정규칙일련번호",
            "행정규칙ID",
            "ID",
            "LID",
            "행정규칙 상세링크",
            "신구법 상세링크",
            *ADMINISTRATIVE_RULE_SOURCE_KEYS,
        )
        if source_info.get(key) not in (None, "")
    }
    source_reference = administrative_rule_source_reference(source_info)
    return AdministrativeRuleIdentity(
        serial_id=string_or_none(first_value(info, "행정규칙 일련번호", "행정규칙일련번호", "ID", "admrul id")),
        rule_id=string_or_none(first_value(info, "행정규칙ID", "LID")),
        name=str(name),
        rule_type=string_or_none(first_value(info, "행정규칙종류", "법령구분명")),
        issuing_date=string_or_none(compact_date(first_value(info, "발령일자"))),
        issuing_number=string_or_none(first_value(info, "발령번호")),
        effective_date=string_or_none(compact_date(first_value(info, "시행일자"))),
        ministry=string_or_none(first_value(info, "소관부처명")),
        ministry_code=string_or_none(first_value(info, "소관부처코드")),
        current_status=string_or_none(first_value(info, "현행여부", "현행연혁구분")),
        revision_type=string_or_none(first_value(info, "제개정구분명")),
        **source_reference,
        raw_keys=raw_keys,
    )
