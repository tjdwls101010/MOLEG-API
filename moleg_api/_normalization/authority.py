"""Legal interpretation and judicial decision normalization."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Literal

from moleg_api.errors import ParseFailureError
from moleg_api.models import InterpretationIdentity, InterpretationText, JudicialDecisionIdentity, JudicialDecisionText

from .primitives import compact_date, first_value, string_or_none
from .references import parse_article_references

def normalize_interpretation_identity(
    row: dict[str, Any],
    *,
    source_type: str,
    source_target: str,
    ministry: str | None = None,
) -> InterpretationIdentity:
    info = row.get("기본정보") if isinstance(row.get("기본정보"), dict) else row
    title = first_value(info, "안건명", "법령해석례명", "법령해석명", "LM")
    if not title:
        raise ParseFailureError("Interpretation identity is missing a title")

    raw_keys = {
        key: info.get(key)
        for key in (
            "법령해석례일련번호",
            "법령해석일련번호",
            "ID",
            "expc id",
            "법령해석례 상세링크",
            "법령해석 상세링크",
        )
        if info.get(key) not in (None, "")
    }
    return InterpretationIdentity(
        interpretation_id=string_or_none(first_value(info, "법령해석례일련번호", "법령해석일련번호", "ID", "expc id")),
        title=str(title),
        source_type=source_type,
        source_target=source_target,
        case_number=string_or_none(first_value(info, "안건번호")),
        interpretation_date=string_or_none(compact_date(first_value(info, "해석일자", "회신일자"))),
        reply_agency=string_or_none(first_value(info, "회신기관명", "해석기관명")),
        reply_agency_code=string_or_none(first_value(info, "회신기관코드", "해석기관코드")),
        inquiry_agency=string_or_none(first_value(info, "질의기관명")),
        inquiry_agency_code=string_or_none(first_value(info, "질의기관코드")),
        ministry=ministry,
        data_timestamp=string_or_none(first_value(info, "데이터기준일시", "등록일시")),
        raw_keys=raw_keys,
    )


def normalize_interpretation_text(
    row: dict[str, Any],
    *,
    source_type: str,
    source_target: str,
    ministry: str | None = None,
) -> InterpretationText:
    identity = normalize_interpretation_identity(
        row,
        source_type=source_type,
        source_target=source_target,
        ministry=ministry,
    )
    question = string_or_none(first_value(row, "질의요지", "질의"))
    answer = string_or_none(first_value(row, "회답", "답변", "해석"))
    reason = string_or_none(first_value(row, "이유", "해석이유"))
    related_laws = string_or_none(first_value(row, "관련법령", "관련 법령"))
    parts = []
    if question:
        parts.append(f"질의요지\n{question}")
    if answer:
        parts.append(f"회답\n{answer}")
    if reason:
        parts.append(f"이유\n{reason}")
    if related_laws:
        parts.append(f"관련법령\n{related_laws}")
    return InterpretationText(
        identity=identity,
        question=question,
        answer=answer,
        reason=reason,
        related_laws=related_laws,
        referenced_articles=parse_article_references(related_laws),
        text="\n\n".join(parts),
        raw=row,
    )


def normalize_judicial_decision_identity(
    row: dict[str, Any],
    *,
    source_type: str,
    source_target: str,
) -> JudicialDecisionIdentity:
    info = row.get("기본정보") if isinstance(row.get("기본정보"), dict) else row
    title = first_value(info, "사건명", "판례명", "헌재결정례명", "LM")
    if not title:
        raise ParseFailureError("Judicial decision identity is missing a title")

    raw_keys = {
        key: info.get(key)
        for key in (
            "판례일련번호",
            "판례정보일련번호",
            "헌재결정례일련번호",
            "ID",
            "판례상세링크",
            "헌재결정례 상세링크",
        )
        if info.get(key) not in (None, "")
    }
    return JudicialDecisionIdentity(
        decision_id=string_or_none(first_value(info, "판례일련번호", "판례정보일련번호", "헌재결정례일련번호", "ID")),
        title=str(title),
        source_type=source_type,
        source_target=source_target,
        case_number=string_or_none(first_value(info, "사건번호")),
        decision_date=string_or_none(compact_date(first_value(info, "선고일자", "종국일자"))),
        court=string_or_none(first_value(info, "법원명")),
        court_type_code=string_or_none(first_value(info, "법원종류코드", "재판부구분코드")),
        case_type=string_or_none(first_value(info, "사건종류명")),
        decision_type=string_or_none(first_value(info, "판결유형", "선고")),
        data_source=string_or_none(first_value(info, "데이터출처명")),
        raw_keys=raw_keys,
    )


_DISPOSITION_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("헌법불합치", (r"헌법에\s*합치되지\s*아니한다", r"헌법불합치")),
    ("한정위헌", (r"한정위헌",)),
    ("한정합헌", (r"한정합헌",)),
    ("합헌", (r"헌법에\s*위반되지\s*아니한다", r"헌법에\s*위배되지\s*아니한다")),
    ("위헌", (r"위반된다",)),
    ("각하", (r"각하한다",)),
    ("기각", (r"기각한다",)),
    ("인용", (r"인용한다", r"취소한다")),
)


def parse_constitutional_disposition(full_text: str | None) -> str | None:
    """Disposition(s) (합헌/위헌/헌법불합치/각하/기각 …) from the 주문 of a 헌재
    decision's 전문. Scans ONLY the 주문 slice — the 이유 section repeats these
    verbs (dissents) and would mislabel. Returns None when the 주문 is absent."""
    if not full_text:
        return None
    marker = re.search(r"[【\[]\s*주\s*문\s*[】\]]", full_text)
    if not marker:
        return None
    rest = full_text[marker.end():]
    reason = re.search(r"[【\[]\s*이\s*유", rest)
    section = rest[: reason.start()] if reason else rest[:2000]
    found: list[str] = []
    for label, patterns in _DISPOSITION_RULES:
        if label not in found and any(re.search(p, section) for p in patterns):
            found.append(label)
    return " ".join(found) if found else None


def normalize_judicial_decision_text(
    row: dict[str, Any],
    *,
    source_type: str,
    source_target: str,
) -> JudicialDecisionText:
    identity = normalize_judicial_decision_identity(
        row,
        source_type=source_type,
        source_target=source_target,
    )
    holdings = string_or_none(first_value(row, "판시사항"))
    summary = string_or_none(first_value(row, "판결요지", "결정요지"))
    full_text = string_or_none(first_value(row, "판례내용", "전문"))
    # 헌재 detail carries no 판결유형/선고 key, so decision_type is always null —
    # recover the disposition from the 주문 so 각하/기각 aren't mistaken for merits.
    if source_target == "detc" and not identity.decision_type:
        disposition = parse_constitutional_disposition(full_text)
        if disposition:
            identity = replace(identity, decision_type=disposition)
    referenced_statutes = string_or_none(first_value(row, "참조조문"))
    reviewed_statutes = string_or_none(first_value(row, "심판대상조문"))
    referenced_cases = string_or_none(first_value(row, "참조판례"))
    parts = []
    if holdings:
        parts.append(f"판시사항\n{holdings}")
    if summary:
        parts.append(f"요지\n{summary}")
    if referenced_statutes:
        parts.append(f"참조조문\n{referenced_statutes}")
    if reviewed_statutes:
        parts.append(f"심판대상조문\n{reviewed_statutes}")
    if referenced_cases:
        parts.append(f"참조판례\n{referenced_cases}")
    if full_text:
        parts.append(f"전문\n{full_text}")
    return JudicialDecisionText(
        identity=identity,
        holdings=holdings,
        summary=summary,
        full_text=full_text,
        referenced_statutes=referenced_statutes,
        reviewed_statutes=reviewed_statutes,
        referenced_cases=referenced_cases,
        referenced_articles=parse_article_references(referenced_statutes),
        reviewed_articles=parse_article_references(reviewed_statutes),
        text="\n\n".join(parts),
        raw=row,
    )
