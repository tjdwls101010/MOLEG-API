"""Article and supplementary-provision extraction."""

from __future__ import annotations

from typing import Any, Literal

from moleg_api.models import AdministrativeRuleArticleText, AdministrativeRuleIdentity, ArticleText, LawIdentity, SupplementaryProvision

from .article_units import normalize_administrative_rule_article, normalize_article
from .primitives import compact_date, compact_promulgation_number, ensure_list, first_value, string_or_none
from .row_format import article_label_from_parts

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


def extract_supplementary_provisions(
    raw_source: dict[str, Any],
    source_type: Literal["law", "administrative_rule"],
) -> list[SupplementaryProvision]:
    """Extract 부칙 rows from law or administrative-rule detail payloads."""

    rows: list[Any] = []
    top_level_text = first_value(raw_source, "부칙내용", "부칙")
    top_level_has_supplement = (
        top_level_text is not None
        and not isinstance(top_level_text, (dict, list))
    ) or any(first_value(raw_source, key) is not None for key in ("부칙공포일자", "부칙공포번호"))
    if top_level_has_supplement:
        rows.append(raw_source)
    else:
        rows.extend(supplementary_rows(raw_source.get("부칙")))
        rows.extend(supplementary_rows(raw_source.get("부칙단위")))

    provisions: list[SupplementaryProvision] = []
    for row in rows:
        if isinstance(row, dict):
            text = first_value(row, "부칙내용", "부칙", "내용", "text")
            if text is None or isinstance(text, (dict, list)):
                continue
            provisions.append(
                SupplementaryProvision(
                    source_type=source_type,
                    title=string_or_none(first_value(row, "부칙제목", "제목")),
                    text=str(text),
                    promulgation_date=string_or_none(compact_date(first_value(row, "부칙공포일자"))),
                    promulgation_number=compact_promulgation_number(first_value(row, "부칙공포번호")),
                    raw=row,
                )
            )
        elif row not in (None, ""):
            provisions.append(
                SupplementaryProvision(
                    source_type=source_type,
                    text=str(row),
                )
            )
    return provisions


def supplementary_rows(value: Any) -> list[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if any(key in value for key in ("부칙내용", "부칙공포일자", "부칙공포번호")):
            return [value]
        for key in ("부칙단위", "부칙"):
            if key in value:
                return supplementary_rows(value[key])
        return [value]
    return [value]


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
                article=article_label_from_parts(
                    first_value(raw_rule, "조문번호", "조번호"),
                    first_value(raw_rule, "조문가지번호", "조가지번호"),
                ),
                title=string_or_none(first_value(raw_rule, "조문제목", "제목")),
                text=str(flat_text),
                effective_date=string_or_none(compact_date(first_value(raw_rule, "시행일자"))),
                source_law_id=identity.source_law_id,
                source_law_name=identity.source_law_name,
                source_article=identity.source_article,
                source_article_title=identity.source_article_title,
                raw=raw_rule,
            )
        )
    return articles
