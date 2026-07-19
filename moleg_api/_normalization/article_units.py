"""Article unit normalization."""

from __future__ import annotations

import re
from typing import Any, Literal

from moleg_api.models import AdministrativeRuleArticleText, AdministrativeRuleIdentity, ArticleText, LawIdentity

from .row_format import article_label, article_label_from_parts
from .primitives import compact_date, content_value, ensure_list, first_value, string_or_none
from .source_refs import administrative_rule_source_reference

def normalize_article(row: dict[str, Any], identity: LawIdentity) -> ArticleText | None:
    number = first_value(row, "조문번호", "조번호", "JO")
    branch = first_value(row, "조문가지번호", "조가지번호")
    text = first_value(row, "조문내용", "조문본문", "내용")
    title = first_value(row, "조문제목", "제목")
    if number is None and text is None and title is None:
        return None
    return ArticleText(
        identity=identity,
        article=article_label_from_parts(number, branch) or "",
        title=string_or_none(title),
        text=join_article_text(row, article_text_value(text)),
        effective_date=string_or_none(compact_date(first_value(row, "조문시행일자", "시행일자"))),
        article_kind=string_or_none(first_value(row, "조문여부")),
        revision_type=string_or_none(first_value(row, "조문제개정유형", "제개정유형")),
        moved_from=article_label(first_value(row, "조문이동이전", "조문이동이전번호")),
        moved_to=article_label(first_value(row, "조문이동이후", "조문이동이후번호")),
        has_changes=yes_no_or_none(first_value(row, "조문변경여부")),
        is_deleted=is_deleted_article(
            article_text_value(text),
            title=string_or_none(title),
            revision_type=string_or_none(first_value(row, "조문제개정유형", "제개정유형")),
        ),
        raw=row,
    )


def normalize_administrative_rule_article(
    row: dict[str, Any],
    identity: AdministrativeRuleIdentity,
) -> AdministrativeRuleArticleText | None:
    number = first_value(row, "조문번호", "조번호", "JO")
    branch = first_value(row, "조문가지번호", "조가지번호")
    text = first_value(row, "조문내용", "조문본문", "내용", "content")
    title = first_value(row, "조문제목", "제목", "title")
    if number is None and text is None and title is None:
        return None
    source_reference = administrative_rule_source_reference(row)
    if not any(source_reference.values()):
        source_reference = {
            "source_law_id": identity.source_law_id,
            "source_law_name": identity.source_law_name,
            "source_article": identity.source_article,
            "source_article_title": identity.source_article_title,
        }
    else:
        source_reference = {
            "source_law_id": source_reference["source_law_id"] or identity.source_law_id,
            "source_law_name": source_reference["source_law_name"] or identity.source_law_name,
            "source_article": source_reference["source_article"],
            "source_article_title": source_reference["source_article_title"],
        }
    return AdministrativeRuleArticleText(
        identity=identity,
        article=article_label_from_parts(number, branch),
        title=string_or_none(title),
        text=join_article_text(row, article_text_value(text)),
        effective_date=string_or_none(compact_date(first_value(row, "조문시행일자", "시행일자"))),
        article_kind=string_or_none(first_value(row, "조문여부")),
        revision_type=string_or_none(first_value(row, "조문제개정유형", "제개정유형")),
        moved_from=article_label(first_value(row, "조문이동이전", "조문이동이전번호")),
        moved_to=article_label(first_value(row, "조문이동이후", "조문이동이후번호")),
        has_changes=yes_no_or_none(first_value(row, "조문변경여부")),
        is_deleted=is_deleted_article(
            article_text_value(text),
            title=string_or_none(title),
            revision_type=string_or_none(first_value(row, "조문제개정유형", "제개정유형")),
        ),
        **source_reference,
        raw=row,
    )


def article_text_value(value: Any) -> str:
    """Flatten 조문내용 into text, whatever nesting law.go.kr wrapped it in.

    A row carrying both a 장 and a 절 heading returns them as a nested array, and
    `str()` on that yields a Python repr — `[['제3장 …', '제1절 …']]` — which then
    travels as if it were the statute's own wording. Rare enough to survive this
    long, wrong in a way a reader cannot detect from the output.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        parts = [article_text_value(item) for item in value]
        return "\n".join(part for part in parts if part.strip())
    return "" if value is None else str(value)


def join_article_text(row: dict[str, Any], base_text: str) -> str:
    lines: list[str] = []
    if base_text:
        lines.append(base_text)
    for line in nested_article_lines(row):
        if line and not article_line_already_present(line, lines):
            lines.append(line)
    return "\n".join(lines)


def article_line_already_present(line: str, lines: list[str]) -> bool:
    compact_line = compact_whitespace(line)
    return any(compact_line in compact_whitespace(existing) for existing in lines)


def nested_article_lines(row: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.extend(nested_unit_lines(row, *PARAGRAPH_SPEC))
    lines.extend(nested_unit_lines(row, *SUBPARAGRAPH_SPEC))
    lines.extend(nested_unit_lines(row, *ITEM_SPEC))
    return lines


NestedSpec = tuple[tuple[str, ...], tuple[str, ...], "NestedSpec | None"]
ITEM_SPEC: NestedSpec = (("목", "목단위"), ("목내용",), None)
SUBPARAGRAPH_SPEC: NestedSpec = (("호", "호단위"), ("호내용",), ITEM_SPEC)
PARAGRAPH_SPEC: NestedSpec = (("항", "항단위"), ("항내용",), SUBPARAGRAPH_SPEC)


def nested_unit_lines(
    row: dict[str, Any],
    container_keys: tuple[str, ...],
    text_keys: tuple[str, ...],
    child_spec: NestedSpec | None,
) -> list[str]:
    lines: list[str] = []
    for unit in child_rows(row, container_keys):
        line = string_or_none(first_value(unit, *text_keys, "내용", "content", "text"))
        if line:
            lines.append(line)
        if child_spec:
            lines.extend(nested_unit_lines(unit, *child_spec))
    return lines


def child_rows(row: dict[str, Any], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in keys:
        rows.extend(child_rows_from_container(row.get(key), keys))
    return rows


def child_rows_from_container(value: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    content = content_value(value)
    if isinstance(content, dict) and any(key in content for key in keys):
        return child_rows(content, keys)
    rows: list[dict[str, Any]] = []
    for item in ensure_list(content):
        if isinstance(item, dict):
            rows.append(item)
    return rows


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
