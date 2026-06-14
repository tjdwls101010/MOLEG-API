"""Normalization helpers for MOLEG source payloads."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from .errors import ParseFailureError
from .models import (
    AdministrativeRuleArticleText,
    AdministrativeRuleIdentity,
    ArticleText,
    Basis,
    DelegatedRule,
    HistoryEvent,
    LawDiffChange,
    LawIdentity,
)


LAW_SEARCH_ENVELOPES = ("LawSearch", "lawSearch", "LawSearchService")


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
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return digits
    return text


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
        promulgation_number=string_or_none(first_value(info, "공포번호", "prom_no")),
        law_type=string_or_none(first_value(info, "법종구분", "법령구분명")),
        ministry=string_or_none(first_value(info, "소관부처", "소관부처명")),
        raw_keys=raw_keys,
    )


def normalize_administrative_rule_identity(row: dict[str, Any]) -> AdministrativeRuleIdentity:
    info = row.get("기본정보") if isinstance(row.get("기본정보"), dict) else row
    name = first_value(info, "행정규칙명", "신구법명", "LM")
    if not name:
        raise ParseFailureError("Administrative-rule identity is missing a name")

    raw_keys = {
        key: info.get(key)
        for key in (
            "행정규칙 일련번호",
            "행정규칙일련번호",
            "행정규칙ID",
            "ID",
            "LID",
            "행정규칙 상세링크",
            "신구법 상세링크",
        )
        if info.get(key) not in (None, "")
    }
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
        raw_keys=raw_keys,
    )


def unwrap_search_laws(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for envelope in LAW_SEARCH_ENVELOPES:
        if isinstance(payload.get(envelope), dict):
            rows = payload[envelope].get("law")
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = payload.get("law")
    return [row for row in ensure_list(rows) if isinstance(row, dict)]


def unwrap_search_administrative_rules(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for envelope in ("AdmRulSearch", "admrulSearch", "AdmrulSearch", "AdmRulSearchService"):
        if isinstance(payload.get(envelope), dict):
            rows = payload[envelope].get("admrul")
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = payload.get("admrul")
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    return collect_rows(payload, "admrul")


def unwrap_service_payload(payload: dict[str, Any], target: str) -> dict[str, Any]:
    if isinstance(payload.get(target), dict):
        return payload[target]
    if len(payload) == 1:
        only = next(iter(payload.values()))
        if isinstance(only, dict):
            return only
    if "기본정보" in payload or "조문" in payload:
        return payload
    raise ParseFailureError(f"Could not unwrap service payload for target {target}")


def extract_articles(raw_law: dict[str, Any], identity: LawIdentity) -> list[ArticleText]:
    article_container = raw_law.get("조문")
    rows: list[Any]
    if isinstance(article_container, dict):
        rows = ensure_list(
            article_container.get("조문단위")
            or article_container.get("조문")
            or article_container
        )
    else:
        rows = ensure_list(article_container)

    articles: list[ArticleText] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        article = normalize_article(row, identity)
        if article:
            articles.append(article)
    return articles


def extract_administrative_rule_articles(
    raw_rule: dict[str, Any],
    identity: AdministrativeRuleIdentity,
) -> list[AdministrativeRuleArticleText]:
    article_container = raw_rule.get("조문")
    if isinstance(article_container, dict):
        rows = ensure_list(
            article_container.get("조문단위")
            or article_container.get("조문")
            or article_container
        )
    else:
        rows = ensure_list(article_container)

    articles: list[AdministrativeRuleArticleText] = []
    for row in rows:
        if isinstance(row, dict):
            article = normalize_administrative_rule_article(row, identity)
            if article:
                articles.append(article)

    if articles:
        return articles

    flat_text = first_value(raw_rule, "조문내용", "본문", "내용")
    if flat_text:
        articles.append(
            AdministrativeRuleArticleText(
                identity=identity,
                article=article_label(first_value(raw_rule, "조문번호", "조번호")),
                title=string_or_none(first_value(raw_rule, "조문제목", "제목")),
                text=str(flat_text),
                effective_date=string_or_none(compact_date(first_value(raw_rule, "시행일자"))),
                raw=raw_rule,
            )
        )
    return articles


def normalize_article(row: dict[str, Any], identity: LawIdentity) -> ArticleText | None:
    number = first_value(row, "조문번호", "조번호", "JO")
    text = first_value(row, "조문내용", "조문본문", "내용")
    title = first_value(row, "조문제목", "제목")
    if number is None and text is None and title is None:
        return None
    article = f"제{number}조" if number not in (None, "") and not str(number).startswith("제") else str(number or "")
    return ArticleText(
        identity=identity,
        article=article,
        title=string_or_none(title),
        text=str(text or ""),
        effective_date=string_or_none(compact_date(first_value(row, "조문시행일자", "시행일자"))),
        raw=row,
    )


def normalize_administrative_rule_article(
    row: dict[str, Any],
    identity: AdministrativeRuleIdentity,
) -> AdministrativeRuleArticleText | None:
    number = first_value(row, "조문번호", "조번호", "JO")
    text = first_value(row, "조문내용", "조문본문", "내용", "content")
    title = first_value(row, "조문제목", "제목", "title")
    if number is None and text is None and title is None:
        return None
    return AdministrativeRuleArticleText(
        identity=identity,
        article=article_label(number),
        title=string_or_none(title),
        text=str(text or ""),
        effective_date=string_or_none(compact_date(first_value(row, "조문시행일자", "시행일자"))),
        raw=row,
    )


def normalize_history_events(payload: dict[str, Any], identity: LawIdentity) -> list[HistoryEvent]:
    rows = collect_rows(
        payload,
        "law",
        "법령",
        "조문변경이력",
        "조문변경이력목록",
        "lsJoHstInf",
        "lsHstInf",
    )
    events: list[HistoryEvent] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            row_identity = normalize_law_identity(row, basis=identity.basis)
        except ParseFailureError:
            row_identity = identity
        event = HistoryEvent(
            identity=row_identity,
            changed_date=string_or_none(compact_date(first_value(row, "조문변경일", "조문개정일", "regDt"))),
            effective_date=string_or_none(compact_date(first_value(row, "조문시행일", "시행일자"))),
            promulgation_date=string_or_none(compact_date(first_value(row, "공포일자"))),
            promulgation_number=string_or_none(first_value(row, "공포번호")),
            revision_type=string_or_none(first_value(row, "제개정구분명", "제개정구분")),
            article=article_label(first_value(row, "조문번호", "조문정보", "JO")),
            reason=string_or_none(first_value(row, "변경사유")),
            raw=row,
        )
        events.append(event)
    return events


def normalize_diff_changes(payload: dict[str, Any], *, article: str | int | None = None) -> list[LawDiffChange]:
    before_rows = article_rows_from_diff(payload, "구조문목록")
    after_rows = article_rows_from_diff(payload, "신조문목록")
    wanted = article_label(article) if article is not None else None

    before_by_no = {article_key(row): row for row in before_rows}
    after_by_no = {article_key(row): row for row in after_rows}
    keys = sorted(set(before_by_no) | set(after_by_no))
    changes: list[LawDiffChange] = []
    for key in keys:
        before_row = before_by_no.get(key, {})
        after_row = after_by_no.get(key, {})
        label = article_label(key) or key
        if wanted and label != wanted and key != wanted:
            continue
        changes.append(
            LawDiffChange(
                article=label,
                title=string_or_none(first_value(after_row, "title", "조문제목") or first_value(before_row, "title", "조문제목")),
                before_text=str(first_value(before_row, "content", "조문내용", "text") or ""),
                after_text=str(first_value(after_row, "content", "조문내용", "text") or ""),
                raw={"before": before_row, "after": after_row},
            )
        )
    return changes


def normalize_delegated_rules(payload: dict[str, Any]) -> list[DelegatedRule]:
    rows = collect_rows(payload, "위임조문정보", "위임법령", "위임행정규칙", "위임자치법규")
    rules: list[DelegatedRule] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if "위임정보" in row or "조정보" in row:
            source = row.get("조정보") if isinstance(row.get("조정보"), dict) else {}
            info = row.get("위임정보") if isinstance(row.get("위임정보"), dict) else {}
        else:
            source = row
            info = row
        rule = DelegatedRule(
            source_article=article_label(first_value(source, "조문번호", "조번호", "조항호목")),
            source_article_title=string_or_none(first_value(source, "조문제목", "조제목")),
            delegated_type=string_or_none(first_value(info, "위임구분", "법종구분")),
            delegated_name=string_or_none(
                first_value(info, "위임법령제목", "위임행정규칙제목", "위임자치법규제목", "위임행정규칙명", "법령명")
            ),
            delegated_law_id=string_or_none(first_value(info, "법령ID", "위임법령ID")),
            delegated_mst=string_or_none(first_value(info, "위임법령일련번호", "위임행정규칙일련번호", "위임자치법규일련번호", "법령일련번호")),
            delegated_article=article_label(first_value(info, "위임법령조문번호", "위임행정규칙조번호")),
            text=string_or_none(first_value(info, "라인텍스트", "조내용", "링크텍스트")),
            raw=row,
        )
        if rule.delegated_name or rule.text:
            rules.append(rule)
    return rules


def collect_rows(obj: Any, *keys: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(obj, list):
        for item in obj:
            rows.extend(collect_rows(item, *keys))
    elif isinstance(obj, dict):
        for key in keys:
            value = obj.get(key)
            if isinstance(value, list):
                rows.extend([item for item in value if isinstance(item, dict)])
            elif isinstance(value, dict):
                if any(isinstance(value.get(k), (list, dict)) for k in keys):
                    rows.extend(collect_rows(value, *keys))
                else:
                    rows.append(value)
        if not rows:
            for value in obj.values():
                if isinstance(value, (list, dict)):
                    rows.extend(collect_rows(value, *keys))
    return rows


def article_rows_from_diff(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    container = payload.get(key)
    if isinstance(container, dict):
        return [row for row in ensure_list(container.get("조문")) if isinstance(row, dict)]
    return []


def article_key(row: dict[str, Any]) -> str:
    value = first_value(row, "no", "조문번호", "JO")
    return str(value or "")


def article_label(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value)
    if text.startswith("제"):
        return text
    if text.isdigit():
        return f"제{int(text)}조"
    return text


def format_article_jo(article: str | int) -> str:
    if isinstance(article, int):
        return f"{article:04d}00"
    text = str(article).strip()
    if re.fullmatch(r"\d{6}", text):
        return text
    match = re.search(r"제?\s*(\d+)\s*조(?:\s*의\s*(\d+))?", text)
    if match:
        main = int(match.group(1))
        branch = int(match.group(2) or 0)
        return f"{main:04d}{branch:02d}"
    if text.isdigit():
        return f"{int(text):04d}00"
    raise ParseFailureError(f"Unsupported article notation: {article}")


def string_or_none(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
