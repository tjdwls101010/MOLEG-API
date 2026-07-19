"""Normalization for committee decisions and administrative appeals.

Twelve committees and five appeal tribunals each name the same concepts
differently — a decision's gist is 결정요지 at 개인정보보호위원회, 판단요지 at
국가인권위원회, 판정요지 at 노동위원회, 재결요지 at every 심판기관. Left raw, a
consumer would have to learn all seventeen vocabularies to ask one question, and
would silently get None from the sixteen it did not know about.
"""

from __future__ import annotations

from typing import Any

from moleg_api.models import AdjudicationIdentity, AdjudicationText

from .primitives import compact_date, ensure_list, first_value, string_or_none

# Ordered by specificity: the first key present wins, so a body that carries both
# a precise and a generic field is read the precise way.
_ID_KEYS = ("결정문일련번호", "행정심판례일련번호", "행정심판재결례일련번호", "특별행정심판재결례일련번호")
_TITLE_KEYS = ("사건명", "안건명", "제목", "소청사례명", "민원표시명", "사건")
_CASE_NO_KEYS = ("사건번호", "의안번호", "의결번호", "안건번호", "청구번호", "재결번호", "결정번호")
_DECIDED_KEYS = ("의결일자", "의결일", "결정일자", "의결연월일", "등록일", "데이터기준일시")
_DISPOSITION_DATE_KEYS = ("처분일자",)
_AGENCY_KEYS = ("기관명", "위원회명", "재결위원회")
_REVIEW_AGENCY_KEYS = ("재결청",)
_RESPONDENT_AGENCY_KEYS = ("처분청", "원처분기관", "상위처분청", "관계기관")
_CATEGORY_KEYS = ("결정구분명", "재결구분명", "결정구분", "재결례유형명", "결정유형", "의결서종류", "의결서유형", "회의종류")
_LINK_KEYS = ("결정문상세링크", "행정심판례상세링크", "행정심판재결례상세링크", "바로보기URL")

_SUMMARY_KEYS = ("결정요지", "재결요지", "판단요지", "판정요지", "주문요지", "쟁점")
_DISPOSITION_KEYS = ("주문", "결정", "조치내용", "판정결과", "판단")
_REASONING_KEYS = ("이유", "조치이유", "내용", "평가의견", "판정사항", "관련법리")
_CLAIM_KEYS = ("청구취지",)
_BACKGROUND_KEYS = ("개요", "사건의개요", "배경", "주요내용", "분쟁의경과", "사실조사결과", "처분요지", "원처분")
_APPLICANT_KEYS = ("신청인", "청구인", "소청인", "피해자")
_RESPONDENT_KEYS = ("피신청인", "피청구인", "피심인", "피소청인", "피조사자", "조치대상자의인적사항", "피심정보", "해양사고관련자")
_RELATED_LAW_KEYS = ("관계법령", "관련법령", "세목", "사건의분류", "분류명")


def adjudication_rows(payload: dict[str, Any], target: str) -> list[dict[str, Any]]:
    """Pull the row list out of a search envelope.

    Matched by shape, not by name: the four special tribunals answer a request for
    `acrSpecialDecc` with rows keyed `decc`, so keying on the requested target
    would return nothing and read as "this tribunal has no records".
    """
    for container in (payload, *(v for v in payload.values() if isinstance(v, dict))):
        if not isinstance(container, dict):
            continue
        for key in (target, "decc", *container):
            value = container.get(key)
            if isinstance(value, list) and value:
                return [row for row in value if isinstance(row, dict)]
    return []


def adjudication_detail(payload: dict[str, Any]) -> dict[str, Any]:
    """Unwrap a detail response, through the 의결서 wrapper some bodies add."""
    body = payload
    for _ in range(3):
        if len(body) == 1:
            only = next(iter(body.values()))
            if isinstance(only, dict):
                body = only
                continue
        break
    return body


def normalize_adjudication_identity(row: dict[str, Any], *, spec: dict[str, str]) -> AdjudicationIdentity:
    return AdjudicationIdentity(
        decision_id=str(first_value(row, *_ID_KEYS) or "").strip(),
        body=spec["code"],
        body_name=spec["name"],
        source_type=spec["source_type"],
        source_authority=spec["authority"],
        title=_clean(first_value(row, *_TITLE_KEYS)),
        case_number=_clean(first_value(row, *_CASE_NO_KEYS)),
        decided_on=_adjudication_date(first_value(row, *_DECIDED_KEYS)),
        disposition_date=_adjudication_date(first_value(row, *_DISPOSITION_DATE_KEYS)),
        agency=_clean(first_value(row, *_AGENCY_KEYS)) or spec["name"],
        review_agency=_clean(first_value(row, *_REVIEW_AGENCY_KEYS)),
        respondent_agency=_clean(first_value(row, *_RESPONDENT_AGENCY_KEYS)),
        decision_category=_clean(first_value(row, *_CATEGORY_KEYS)),
        detail_link=_clean(first_value(row, *_LINK_KEYS)),
        raw=row,
    )


def normalize_adjudication_text(body: dict[str, Any], identity: AdjudicationIdentity) -> AdjudicationText:
    disposition = _flatten(first_value(body, *_DISPOSITION_KEYS))
    summary = _flatten(first_value(body, *_SUMMARY_KEYS))
    reasoning = _flatten(first_value(body, *_REASONING_KEYS))
    claim = _flatten(first_value(body, *_CLAIM_KEYS))
    background = _flatten(first_value(body, *_BACKGROUND_KEYS))
    sections = [
        ("주문", disposition),
        ("요지", summary),
        ("청구취지", claim),
        ("개요", background),
        ("이유", reasoning),
    ]
    return AdjudicationText(
        identity=identity,
        disposition=disposition,
        summary=summary,
        reasoning=reasoning,
        claim=claim,
        background=background,
        applicant=_flatten(first_value(body, *_APPLICANT_KEYS)),
        respondent=_flatten(first_value(body, *_RESPONDENT_KEYS)),
        related_laws=_flatten(first_value(body, *_RELATED_LAW_KEYS)),
        text="\n\n".join(f"{label}\n{value}" for label, value in sections if value),
        raw=body,
    )


def _adjudication_date(value: Any) -> str | None:
    """Normalize the dotted, unpadded dates these bodies write.

    Committees emit `2020.6.8.` — trailing dot, no zero padding — which the shared
    `compact_date` passes through untouched because it expects `2017.07.31`. An
    un-normalized date sorts and compares wrong, and in an oversight question the
    date *is* the finding: when the regulator knew, and how long it then took.
    """
    text = _flatten(value)
    if not text:
        return None
    parts = [p for p in text.replace("-", ".").split(".") if p.strip()]
    if len(parts) >= 3 and all(p.strip().isdigit() for p in parts[:3]):
        year, month, day = (p.strip() for p in parts[:3])
        if len(year) == 4:
            return f"{year}{month.zfill(2)}{day.zfill(2)}"
    return string_or_none(compact_date(text))


def _clean(value: Any) -> str | None:
    text = _flatten(value)
    # "null" arrives as a literal four-character string on several targets; kept
    # as-is it would render as a real case number or title in an answer.
    return None if text in (None, "", "null") else text


def _flatten(value: Any) -> str | None:
    """Render a field to text, whatever nesting the body wrapped it in.

    Committee payloads mix bare strings, string arrays, and single-key objects
    for the same concept across bodies. `str()` on those yields a Python repr
    that then travels as if it were the agency's own wording.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        parts = [p for p in (_flatten(v) for v in value.values()) if p]
        return "\n".join(parts) or None
    if isinstance(value, (list, tuple)):
        parts = [p for p in (_flatten(v) for v in ensure_list(value)) if p]
        return "\n".join(parts) or None
    return str(value).strip() or None

__all__ = [name for name in globals() if not name.startswith("_")]
