"""Delegated-rule normalization."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.models import DelegatedRule

from .primitives import first_value, string_or_none
from .row_format import article_label_from_parts, collect_rows

_DELEGATION_TARGET_KEYS = (
    "위임구분", "법종구분",
    "위임법령제목", "위임행정규칙제목", "위임자치법규제목", "위임행정규칙명", "법령명",
    "법령ID", "위임법령ID",
    "위임법령일련번호", "위임행정규칙일련번호", "위임자치법규일련번호", "법령일련번호",
    "위임법령조문번호", "위임행정규칙조번호",
    "라인텍스트", "조내용", "링크텍스트",
)


def _transpose_delegation_info(info: dict[str, Any]) -> list[dict[str, Any]]:
    """A single 위임정보 dict can carry parallel lists (one article delegating to
    N targets). Transpose into N per-target dicts (scalars broadcast); otherwise
    return it unchanged. Prevents delegated_type/name/mst from serializing as a
    stringified list and recovers every collapsed multi-target delegation."""
    lengths = [len(info[k]) for k in _DELEGATION_TARGET_KEYS if isinstance(info.get(k), list)]
    if not lengths:
        return [info]
    n = max(lengths)
    out: list[dict[str, Any]] = []
    for i in range(n):
        item = dict(info)
        for key, value in info.items():
            if isinstance(value, list):
                item[key] = value[i] if i < len(value) else None
        out.append(item)
    return out


def normalize_delegated_rules(payload: dict[str, Any]) -> list[DelegatedRule]:
    rows = collect_rows(payload, "위임조문정보", "위임법령", "위임행정규칙", "위임자치법규")
    rules: list[DelegatedRule] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "위임정보" in row or "조정보" in row:
            source = row.get("조정보") if isinstance(row.get("조정보"), dict) else {}
            raw_info = row.get("위임정보")
            # 위임정보 has three shapes when one article delegates to several
            # targets: a list of dicts, OR a single dict whose target fields are
            # parallel lists. Both must emit one rule per target — collapsing to
            # {} (or a single dict) drops/ stringifies multi-target delegations.
            if isinstance(raw_info, list):
                infos = [item for item in raw_info if isinstance(item, dict)]
            elif isinstance(raw_info, dict):
                infos = _transpose_delegation_info(raw_info)
            else:
                infos = [{}]
        else:
            source = row
            infos = [row]
        for info in infos:
            rule = DelegatedRule(
                source_article=article_label_from_parts(
                    first_value(source, "조문번호", "조번호", "조항호목"),
                    first_value(source, "조문가지번호", "조가지번호"),
                ),
                source_article_title=string_or_none(first_value(source, "조문제목", "조제목")),
                delegated_type=string_or_none(first_value(info, "위임구분", "법종구분")),
                delegated_name=string_or_none(
                    first_value(info, "위임법령제목", "위임행정규칙제목", "위임자치법규제목", "위임행정규칙명", "법령명")
                ),
                delegated_law_id=string_or_none(first_value(info, "법령ID", "위임법령ID")),
                delegated_mst=string_or_none(first_value(info, "위임법령일련번호", "위임행정규칙일련번호", "위임자치법규일련번호", "법령일련번호")),
                delegated_article=article_label_from_parts(
                    first_value(info, "위임법령조문번호", "위임행정규칙조번호"),
                    first_value(
                        info,
                        "위임법령조문가지번호",
                        "위임행정규칙조가지번호",
                        "위임행정규칙조문가지번호",
                    ),
                ),
                text=string_or_none(first_value(info, "라인텍스트", "조내용", "링크텍스트")),
                raw=row,
            )
            if rule.delegated_name or rule.text:
                rules.append(rule)
    return rules
