"""Law history event normalization."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.errors import ParseFailureError
from moleg_api.models import HistoryEvent, LawIdentity

from .identities import normalize_law_identity
from .primitives import compact_date, compact_promulgation_number, first_value, mask_oc_param, string_or_none
from .row_format import article_label_from_parts, collect_rows

def normalize_history_events(
    payload: dict[str, Any],
    identity: LawIdentity,
    *,
    article_text_map: dict[str, str | None] | None = None,
    bill_id_map: dict[tuple[str, str, str], str] | None = None,
) -> list[HistoryEvent]:
    rows = collect_rows(
        payload,
        "law",
        "법령",
        "조문변경이력",
        "조문변경이력목록",
        "lsJoHstInf",
        "lsHstInf",
        "lsHistory",
    )
    events: list[HistoryEvent] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # The article-scoped (lsJoHstInf) payload nests fields under 조문정보
        # /법령정보; the whole-law (lsHistory HTML) payload is already flat.
        # Merge both so the flat first_value reads below work on either shape —
        # otherwise the article path loses changed_date/effective_date/revision
        # _type/reason and lets `article` fall through to a dict-repr string.
        jo = row.get("조문정보") if isinstance(row.get("조문정보"), dict) else {}
        li = row.get("법령정보") if isinstance(row.get("법령정보"), dict) else {}
        lookup = {**row, **jo, **li} if (jo or li) else row
        try:
            row_identity = normalize_law_identity(row, basis=identity.basis)
        except ParseFailureError:
            row_identity = identity
        changed_date = string_or_none(compact_date(first_value(lookup, "조문변경일", "조문개정일", "regDt", "공포일자")))
        effective_date = string_or_none(compact_date(first_value(lookup, "조문시행일", "시행일자")))
        article_text = history_event_article_text(
            lookup,
            changed_date=changed_date,
            effective_date=effective_date,
            article_text_map=article_text_map,
        )
        promulgation_law_name = string_or_none(
            first_value(lookup, "법령명한글", "법령명_한글", "법령명")
        ) or row_identity.name
        promulgation_date = string_or_none(compact_date(first_value(lookup, "공포일자")))
        promulgation_number = compact_promulgation_number(first_value(lookup, "공포번호"))
        event = HistoryEvent(
            identity=row_identity,
            changed_date=changed_date,
            effective_date=effective_date,
            promulgation_law_name=promulgation_law_name,
            promulgation_date=promulgation_date,
            promulgation_number=promulgation_number,
            bill_id=history_event_bill_id(
                bill_id_map,
                law_name=promulgation_law_name,
                promulgation_number=promulgation_number,
                promulgation_date=promulgation_date,
            ),
            revision_type=string_or_none(first_value(lookup, "제개정구분명", "제개정구분")),
            article=article_label_from_parts(
                first_value(lookup, "조문번호", "JO"),
                first_value(lookup, "조문가지번호", "조가지번호"),
            ),
            article_text=article_text,
            article_link=mask_oc_param(string_or_none(first_value(lookup, "조문링크"))),
            reason=string_or_none(first_value(lookup, "변경사유")),
            raw=row,
        )
        events.append(event)
    return events


def history_event_article_text(
    row: dict[str, Any],
    *,
    changed_date: str | None,
    effective_date: str | None,
    article_text_map: dict[str, str | None] | None,
) -> str | None:
    source_text = string_or_none(first_value(row, "조문내용", "조문본문", "현행조문내용", "개정조문내용"))
    if source_text:
        return source_text
    if not article_text_map:
        return None
    for key in (effective_date, changed_date):
        if key and key in article_text_map:
            return article_text_map[key]
    return None


def history_event_bill_id(
    bill_id_map: dict[tuple[str, str, str], str] | None,
    *,
    law_name: str | None,
    promulgation_number: str | None,
    promulgation_date: str | None,
) -> str | None:
    if not bill_id_map or not law_name or not promulgation_number or not promulgation_date:
        return None
    return bill_id_map.get((law_name, promulgation_number, promulgation_date))
