"""Normalization helpers for MOLEG source payloads."""

from __future__ import annotations

import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any, Literal
from urllib.parse import parse_qs, urlparse

from .errors import NoResultError, ParseFailureError
from .models import (
    AdministrativeRuleArticleText,
    AdministrativeRuleIdentity,
    AnnexFormIdentity,
    ArticleReference,
    ArticleText,
    Basis,
    DelegatedRule,
    HistoryEvent,
    InterpretationIdentity,
    InterpretationText,
    JudicialDecisionIdentity,
    JudicialDecisionText,
    LegalArticleCandidate,
    LegalLawCandidate,
    LegalTermCandidate,
    LawDiffChange,
    LawIdentity,
    LawStructure,
    LawStructureNode,
    SupplementaryProvision,
)


LAW_SEARCH_ENVELOPES = ("LawSearch", "lawSearch", "LawSearchService")
ARTICLE_REFERENCE_RE = re.compile(r"제\s*(?P<number>\d+)\s*조(?:\s*의\s*(?P<branch>\d+))?")
LAW_NAME_RE = re.compile(
    r"[가-힣A-Za-z0-9ㆍ·().\s]+(?:법률|시행령|시행규칙|법|령|규칙|조례|고시|예규|훈령|규정|지침)"
)
MAX_EXPANDED_ARTICLE_RANGE = 100

ADMINISTRATIVE_RULE_SOURCE_LAW_ID_KEYS = (
    "위임법령ID",
    "위임법령 ID",
    "위임 법령ID",
    "위임 법령 ID",
    "근거법령ID",
    "근거법령 ID",
    "근거 법령ID",
    "근거 법령 ID",
    "수권법령ID",
    "수권법령 ID",
    "수권 법령ID",
    "수권 법령 ID",
    "상위법령ID",
    "상위법령 ID",
    "상위 법령ID",
    "상위 법령 ID",
    "모법령ID",
    "모법령 ID",
    "모법 ID",
    "법적근거법령ID",
    "법적근거 법령ID",
)

ADMINISTRATIVE_RULE_SOURCE_LAW_NAME_KEYS = (
    "위임법령명",
    "위임법령",
    "위임 법령명",
    "위임 법령",
    "근거법령명",
    "근거법령",
    "근거 법령명",
    "근거 법령",
    "수권법령명",
    "수권법령",
    "수권 법령명",
    "수권 법령",
    "상위법령명",
    "상위법령",
    "상위 법령명",
    "상위 법령",
    "모법령명",
    "모법령",
    "모법명",
    "모법",
    "법적근거법령명",
    "법적근거법령",
    "법적근거 법령명",
    "법적근거 법령",
)

ADMINISTRATIVE_RULE_SOURCE_ARTICLE_KEYS = (
    "위임조문번호",
    "위임조문",
    "위임 조문번호",
    "위임 조문",
    "위임근거조문",
    "위임근거 조문",
    "근거조문번호",
    "근거조문",
    "근거 조문번호",
    "근거 조문",
    "수권조문번호",
    "수권조문",
    "수권 조문번호",
    "수권 조문",
    "상위조문번호",
    "상위조문",
    "상위 조문번호",
    "상위 조문",
    "모법령조문",
    "모법조문",
    "법적근거조문",
    "법적근거 조문",
)

ADMINISTRATIVE_RULE_SOURCE_ARTICLE_BRANCH_KEYS = (
    "위임조문가지번호",
    "위임 조문가지번호",
    "위임 조문 가지번호",
    "위임근거조문가지번호",
    "위임근거 조문가지번호",
    "위임근거 조문 가지번호",
    "근거조문가지번호",
    "근거 조문가지번호",
    "근거 조문 가지번호",
    "수권조문가지번호",
    "수권 조문가지번호",
    "수권 조문 가지번호",
    "상위조문가지번호",
    "상위 조문가지번호",
    "상위 조문 가지번호",
    "모법령조문가지번호",
    "모법령 조문가지번호",
    "모법령 조문 가지번호",
    "모법조문가지번호",
    "모법 조문가지번호",
    "모법 조문 가지번호",
    "법적근거조문가지번호",
    "법적근거 조문가지번호",
    "법적근거 조문 가지번호",
)

ADMINISTRATIVE_RULE_SOURCE_ARTICLE_TITLE_KEYS = (
    "위임조문제목",
    "위임 조문제목",
    "위임 조문 제목",
    "근거조문제목",
    "근거 조문제목",
    "근거 조문 제목",
    "수권조문제목",
    "수권 조문제목",
    "상위조문제목",
    "상위 조문제목",
    "모법령조문제목",
    "모법조문제목",
    "법적근거조문제목",
)

ADMINISTRATIVE_RULE_SOURCE_BASIS_KEYS = (
    "위임근거",
    "위임 근거",
    "근거",
    "법적근거",
    "법적 근거",
    "수권근거",
    "수권 근거",
)

ADMINISTRATIVE_RULE_SOURCE_KEYS = (
    *ADMINISTRATIVE_RULE_SOURCE_LAW_ID_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_LAW_NAME_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_BRANCH_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_TITLE_KEYS,
    *ADMINISTRATIVE_RULE_SOURCE_BASIS_KEYS,
)
AI_ROW_KEYS = ("법령조문", "법령별표서식", "행정규칙조문", "행정규칙별표서식")


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
    dotted = re.fullmatch(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", text)
    if dotted:
        year, month, day = dotted.groups()
        return f"{year}{int(month):02d}{int(day):02d}"
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return digits
    return text


def parse_article_references(text: str | None) -> list[ArticleReference]:
    """Parse conservative law-name/article references from Korean source text."""

    if not text:
        return []
    source_text = re.sub(r"\s+", " ", str(text)).strip()
    if not source_text:
        return []

    references: list[ArticleReference] = []
    current_law_name: str | None = None
    previous_end = 0
    matches = list(ARTICLE_REFERENCE_RE.finditer(source_text))
    index = 0
    while index < len(matches):
        match = matches[index]
        law_name = law_name_before_article(source_text[previous_end : match.start()])
        if law_name:
            current_law_name = law_name
        article = article_label_from_reference_match(match)

        if not current_law_name:
            previous_end = match.end()
            index += 1
            continue

        if index + 1 < len(matches):
            next_match = matches[index + 1]
            delimiter = source_text[match.end() : next_match.start()]
            if is_article_range_delimiter(delimiter):
                for expanded in expand_article_range(article, article_label_from_reference_match(next_match)):
                    references.append(ArticleReference(law_name=current_law_name, article=expanded))
                previous_end = next_match.end()
                index += 2
                continue

        references.append(ArticleReference(law_name=current_law_name, article=article))
        previous_end = match.end()
        index += 1

    return dedupe_article_references(references)


def law_name_before_article(segment: str) -> str | None:
    pieces = re.split(r"[:;,\n/]|(?:\s및\s)|(?:\s또는\s)", segment)
    for piece in reversed(pieces):
        candidate = piece.strip(" \t\r\n,.;()[]{}「」『』\"'")
        if not candidate:
            continue
        matches = list(LAW_NAME_RE.finditer(candidate))
        if matches:
            return re.sub(r"\s+", " ", matches[-1].group(0)).strip()
    return None


def article_label_from_reference_match(match: re.Match[str]) -> str:
    number = int(match.group("number"))
    branch = match.group("branch")
    if branch is not None:
        return f"제{number}조의{int(branch)}"
    return f"제{number}조"


def is_article_range_delimiter(delimiter: str) -> bool:
    compacted = re.sub(r"\s+", "", delimiter)
    return compacted in {"~", "-", "부터", "내지"}


def expand_article_range(start: str, end: str) -> list[str]:
    start_parts = article_label_parts(start)
    end_parts = article_label_parts(end)
    if not start_parts or not end_parts:
        return [start, end]

    start_number, start_branch = start_parts
    end_number, end_branch = end_parts
    if start_branch is None and end_branch is None:
        if start_number <= end_number <= start_number + MAX_EXPANDED_ARTICLE_RANGE:
            return [f"제{number}조" for number in range(start_number, end_number + 1)]
        return [start, end]
    if start_number == end_number and start_branch is not None and end_branch is not None:
        if start_branch <= end_branch <= start_branch + MAX_EXPANDED_ARTICLE_RANGE:
            return [f"제{start_number}조의{branch}" for branch in range(start_branch, end_branch + 1)]
    return [start, end]


def article_label_parts(article: str) -> tuple[int, int | None] | None:
    match = re.fullmatch(r"제(\d+)조(?:의(\d+))?", article)
    if not match:
        return None
    branch = match.group(2)
    return int(match.group(1)), int(branch) if branch is not None else None


def dedupe_article_references(references: list[ArticleReference]) -> list[ArticleReference]:
    seen: set[tuple[str, str, str | None]] = set()
    deduped: list[ArticleReference] = []
    for reference in references:
        key = (reference.law_name, reference.article, reference.law_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(reference)
    return deduped


def compact_promulgation_number(value: Any) -> str | None:
    text = string_or_none(value)
    if text is None:
        return None
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"^제", "", text)
    text = re.sub(r"호$", "", text)
    return text or None


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


def administrative_rule_source_reference(row: dict[str, Any]) -> dict[str, str | None]:
    basis_text = string_or_none(first_value(row, *ADMINISTRATIVE_RULE_SOURCE_BASIS_KEYS))
    return {
        "source_law_id": string_or_none(first_value(row, *ADMINISTRATIVE_RULE_SOURCE_LAW_ID_KEYS)),
        "source_law_name": string_or_none(
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_LAW_NAME_KEYS)
        )
        or quoted_law_name(basis_text),
        "source_article": article_label_from_parts(
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_KEYS),
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_BRANCH_KEYS),
        )
        or article_from_source_basis(basis_text),
        "source_article_title": string_or_none(
            first_value(row, *ADMINISTRATIVE_RULE_SOURCE_ARTICLE_TITLE_KEYS)
        ),
    }


def quoted_law_name(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(r"[「『](.+?)[」』]", text)
    if not match:
        return None
    return match.group(1).strip() or None


def article_from_source_basis(text: str | None) -> str | None:
    if not text:
        return None
    match = re.search(
        r"제\s*\d+\s*조(?:\s*의\s*\d+)?(?:\s*제\s*\d+\s*항)?(?:\s*제\s*\d+\s*호)?",
        text,
    )
    if not match:
        return None
    return re.sub(r"\s+", "", match.group(0))


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


def normalize_law_structure(raw_structure: dict[str, Any], *, max_depth: int = 0) -> LawStructure:
    if not isinstance(raw_structure, dict):
        raise ParseFailureError("Law structure payload must be an object")
    root_info = raw_structure.get("기본정보")
    if not isinstance(root_info, dict):
        raise ParseFailureError("Law structure payload is missing 기본정보")
    hierarchy = raw_structure.get("상하위법")
    if hierarchy in (None, ""):
        hierarchy = {}
    if not isinstance(hierarchy, dict):
        raise ParseFailureError("Law structure 상하위법 must be an object")

    root_identity = normalize_law_identity(root_info, basis="effective")
    root_node = structure_root_node(hierarchy, root_identity)
    instruments = law_structure_children(root_node, depth_remaining=max_depth)
    return LawStructure(identity=root_identity, instruments=instruments, raw=raw_structure)


def structure_root_node(hierarchy: dict[str, Any], root_identity: LawIdentity) -> dict[str, Any]:
    for value in hierarchy.values():
        for node in structure_node_values(value):
            info = node.get("기본정보") if isinstance(node, dict) else None
            if isinstance(info, dict):
                identity = normalize_law_identity(info, basis="effective")
                if (
                    identity.law_id == root_identity.law_id
                    or identity.mst == root_identity.mst
                    or identity.name == root_identity.name
                ):
                    return node
    for value in hierarchy.values():
        for node in structure_node_values(value):
            if isinstance(node, dict) and isinstance(node.get("기본정보"), dict):
                return node
    return {}


def law_structure_children(container: dict[str, Any], *, depth_remaining: int) -> list[LawStructureNode]:
    if not isinstance(container, dict):
        raise ParseFailureError("Law structure node must be an object")
    children: list[LawStructureNode] = []
    for key, value in container.items():
        if key in {"기본정보", "자치법규"}:
            continue
        if key in {"시행령", "시행규칙", "법률"}:
            children.extend(law_structure_law_nodes(value, key, depth_remaining=depth_remaining))
        elif key == "행정규칙":
            children.extend(law_structure_administrative_nodes(value))
    return children


def law_structure_law_nodes(value: Any, key: str, *, depth_remaining: int) -> list[LawStructureNode]:
    nodes: list[LawStructureNode] = []
    for node in structure_node_values(value):
        info = node.get("기본정보")
        if not isinstance(info, dict):
            raise ParseFailureError(f"Law structure {key} node is missing 기본정보")
        identity = normalize_law_identity(info, basis="effective")
        children = law_structure_children(node, depth_remaining=depth_remaining - 1) if depth_remaining > 0 else []
        nodes.append(
            LawStructureNode(
                name=identity.name,
                source_type="law",
                instrument_type=instrument_type_for_law_node(key, identity.law_type),
                law_id=identity.law_id,
                mst=identity.mst,
                law_type=identity.law_type,
                effective_date=identity.effective_date,
                promulgation_date=identity.promulgation_date,
                promulgation_number=identity.promulgation_number,
                ministry=identity.ministry,
                detail_link=string_or_none(first_value(info, "본문상세링크", "법령상세링크")),
                children=children,
                raw=node,
            )
        )
    return nodes


def law_structure_administrative_nodes(value: Any) -> list[LawStructureNode]:
    if value in (None, ""):
        return []
    if not isinstance(value, dict):
        raise ParseFailureError("Law structure 행정규칙 must be an object")
    nodes: list[LawStructureNode] = []
    for rule_type, rule_value in value.items():
        for node in structure_node_values(rule_value):
            info = node.get("기본정보")
            if not isinstance(info, dict):
                raise ParseFailureError(f"Law structure {rule_type} node is missing 기본정보")
            identity = normalize_administrative_rule_identity(info)
            nodes.append(
                LawStructureNode(
                    name=identity.name,
                    source_type="administrative_rule",
                    instrument_type=instrument_type_for_admin_rule(rule_type),
                    serial_id=identity.serial_id,
                    rule_id=identity.rule_id,
                    law_type=identity.rule_type,
                    effective_date=identity.effective_date,
                    issuing_date=identity.issuing_date,
                    issuing_number=identity.issuing_number,
                    ministry=identity.ministry,
                    detail_link=string_or_none(first_value(info, "본문상세링크", "행정규칙 상세링크")),
                    raw=node,
                )
            )
    return nodes


def structure_node_values(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        if not all(isinstance(item, dict) for item in value):
            raise ParseFailureError("Law structure node list contains non-object entries")
        return value
    if isinstance(value, dict):
        if "기본정보" in value:
            return [value]
        nodes: list[dict[str, Any]] = []
        for child in value.values():
            nodes.extend(structure_node_values(child))
        return nodes
    raise ParseFailureError("Law structure node must be an object or list")


def instrument_type_for_law_node(key: str, law_type: str | None) -> str:
    if key == "시행령":
        return "enforcement_decree"
    if key == "시행규칙":
        return "enforcement_rule"
    if key == "법률":
        return "related_law"
    if law_type:
        return law_type
    return key


def instrument_type_for_admin_rule(rule_type: str) -> str:
    return {
        "고시": "notice",
        "훈령": "directive",
        "예규": "established_rule",
    }.get(rule_type, rule_type)


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


def unwrap_search_interpretations(payload: dict[str, Any], target: str) -> list[dict[str, Any]]:
    row_keys = tuple(dict.fromkeys((target, "expc", "cgmExpc")))
    for envelope in (
        "ExpcSearch",
        "expcSearch",
        "Expc",
        "expc",
        "CgmExpcSearch",
        "cgmExpcSearch",
        "CgmExpc",
        "cgmExpc",
    ):
        if isinstance(payload.get(envelope), dict):
            rows = next((payload[envelope].get(key) for key in row_keys if key in payload[envelope]), None)
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = next((payload.get(key) for key in row_keys if key in payload), None)
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    return collect_rows(payload, *row_keys)


def unwrap_search_judicial_decisions(payload: dict[str, Any], target: str) -> list[dict[str, Any]]:
    for envelope in ("PrecSearch", "precSearch", "DetcSearch", "detcSearch"):
        if isinstance(payload.get(envelope), dict):
            rows = payload[envelope].get(target)
            return [row for row in ensure_list(rows) if isinstance(row, dict)]
    rows = payload.get(target)
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    return collect_rows(payload, target)


def unwrap_target_rows(payload: dict[str, Any], target: str) -> list[dict[str, Any]]:
    if target in ("aiSearch", "aiRltLs"):
        rows = collect_rows(payload, *AI_ROW_KEYS)
        if rows or isinstance(payload.get(target), dict):
            return rows
    rows = payload.get(target)
    if rows is not None:
        return [row for row in ensure_list(rows) if isinstance(row, dict)]
    for value in payload.values():
        if isinstance(value, dict):
            nested = value.get(target)
            if nested is not None:
                return [row for row in ensure_list(nested) if isinstance(row, dict)]
    return collect_rows(payload, target)


def unwrap_service_payload(payload: dict[str, Any], target: str) -> dict[str, Any]:
    if isinstance(payload.get(target), dict):
        return payload[target]
    if len(payload) == 1:
        only = next(iter(payload.values()))
        if isinstance(only, dict):
            return only
        if is_no_result_message(only):
            raise NoResultError(str(only))
    if "기본정보" in payload or "조문" in payload:
        return payload
    raise ParseFailureError(f"Could not unwrap service payload for target {target}")


def is_no_result_message(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return "일치하는" in value and "없습니다" in value


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
        text=join_article_text(row, str(text or "")),
        effective_date=string_or_none(compact_date(first_value(row, "조문시행일자", "시행일자"))),
        article_kind=string_or_none(first_value(row, "조문여부")),
        revision_type=string_or_none(first_value(row, "조문제개정유형", "제개정유형")),
        moved_from=article_label(first_value(row, "조문이동이전", "조문이동이전번호")),
        moved_to=article_label(first_value(row, "조문이동이후", "조문이동이후번호")),
        has_changes=yes_no_or_none(first_value(row, "조문변경여부")),
        is_deleted=is_deleted_article(
            str(text or ""),
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
        text=join_article_text(row, str(text or "")),
        effective_date=string_or_none(compact_date(first_value(row, "조문시행일자", "시행일자"))),
        article_kind=string_or_none(first_value(row, "조문여부")),
        revision_type=string_or_none(first_value(row, "조문제개정유형", "제개정유형")),
        moved_from=article_label(first_value(row, "조문이동이전", "조문이동이전번호")),
        moved_to=article_label(first_value(row, "조문이동이후", "조문이동이후번호")),
        has_changes=yes_no_or_none(first_value(row, "조문변경여부")),
        is_deleted=is_deleted_article(
            str(text or ""),
            title=string_or_none(title),
            revision_type=string_or_none(first_value(row, "조문제개정유형", "제개정유형")),
        ),
        **source_reference,
        raw=row,
    )


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
        try:
            row_identity = normalize_law_identity(row, basis=identity.basis)
        except ParseFailureError:
            row_identity = identity
        changed_date = string_or_none(compact_date(first_value(row, "조문변경일", "조문개정일", "regDt", "공포일자")))
        effective_date = string_or_none(compact_date(first_value(row, "조문시행일", "시행일자")))
        article_text = history_event_article_text(
            row,
            changed_date=changed_date,
            effective_date=effective_date,
            article_text_map=article_text_map,
        )
        promulgation_law_name = string_or_none(
            first_value(row, "법령명한글", "법령명_한글", "법령명")
        ) or row_identity.name
        promulgation_date = string_or_none(compact_date(first_value(row, "공포일자")))
        promulgation_number = compact_promulgation_number(first_value(row, "공포번호"))
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
            revision_type=string_or_none(first_value(row, "제개정구분명", "제개정구분")),
            article=article_label_from_parts(
                first_value(row, "조문번호", "조문정보", "JO"),
                first_value(row, "조문가지번호", "조가지번호"),
            ),
            article_text=article_text,
            reason=string_or_none(first_value(row, "변경사유")),
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


def parse_law_history_html(html: str) -> list[dict[str, Any]]:
    parser = LawHistoryTableParser()
    parser.feed(html)
    data_rows = [row for row in parser.rows if row]
    malformed = [row for row in data_rows if len(row) != 9]
    if malformed:
        raise ParseFailureError("Could not parse lsHistory HTML table: unexpected column count")
    rows: list[dict[str, Any]] = []
    for row in data_rows:
        href = row[1]["href"]
        link_params = parse_link_params(href)
        mst = first_query_value(link_params, "MST")
        rows.append(
            {
                "순번": row[0]["text"],
                "법령명한글": row[1]["text"],
                "소관부처명": row[2]["text"],
                "제개정구분명": row[3]["text"],
                "법령구분명": row[4]["text"],
                "공포번호": row[5]["text"],
                "공포일자": row[6]["text"],
                "시행일자": row[7]["text"],
                "현행연혁구분": row[8]["text"],
                "MST": mst,
                "법령일련번호": mst,
                "법령상세링크": href,
            }
        )
    if not rows and "법령 연혁정보 목록" in html:
        raise ParseFailureError("Could not parse lsHistory HTML table rows")
    return rows


def parse_law_history_total_count(html: str) -> int | None:
    match = re.search(r"총\s*<strong>\s*([0-9,]+)\s*</strong>\s*건", html)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def parse_link_params(href: str | None) -> dict[str, list[str]]:
    if not href:
        return {}
    return parse_qs(urlparse(href).query)


def first_query_value(params: dict[str, list[str]], key: str) -> str | None:
    values = params.get(key)
    if not values:
        return None
    return values[0]


class LawHistoryTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[dict[str, str | None]]] = []
        self._current_row: list[dict[str, str | None]] | None = None
        self._current_cell_text: list[str] | None = None
        self._current_cell_href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._current_row = []
            return
        if tag == "td" and self._current_row is not None:
            self._current_cell_text = []
            self._current_cell_href = None
            return
        if tag == "a" and self._current_cell_text is not None:
            attr_map = dict(attrs)
            self._current_cell_href = attr_map.get("href")

    def handle_data(self, data: str) -> None:
        if self._current_cell_text is not None:
            self._current_cell_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self._current_row is not None and self._current_cell_text is not None:
            text = re.sub(r"\s+", " ", "".join(self._current_cell_text)).strip()
            self._current_row.append({"text": text, "href": self._current_cell_href})
            self._current_cell_text = None
            self._current_cell_href = None
            return
        if tag == "tr" and self._current_row is not None:
            if self._current_row:
                self.rows.append(self._current_row)
            self._current_row = None


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
    return article_label_from_parts(
        first_value(row, "no", "조문번호", "JO"),
        first_value(row, "조문가지번호", "조가지번호"),
    ) or ""


def article_label(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.startswith("제"):
        return text
    if re.fullmatch(r"\d{6}", text):
        main = int(text[:4])
        branch = int(text[4:])
        return f"제{main}조의{branch}" if branch else f"제{main}조"
    match = re.fullmatch(r"(\d+)\s*조(?:\s*의\s*(\d+))?", text)
    if match:
        main = int(match.group(1))
        branch = int(match.group(2) or 0)
        return f"제{main}조의{branch}" if branch else f"제{main}조"
    if text.isdigit():
        return f"제{int(text)}조"
    return text


def annex_number_from_parts(number: Any, branch: Any = None) -> str | None:
    if number in (None, ""):
        return None
    text = str(number).strip()
    branch_text = str(branch or "").strip()
    if not branch_text or not branch_text.isdigit() or int(branch_text) == 0:
        return text
    if re.search(r"의\s*\d+", text):
        return text
    return f"{text}의{int(branch_text)}"


def article_label_from_parts(number: Any, branch: Any = None) -> str | None:
    if number in (None, ""):
        return None
    text = str(number).strip()
    branch_text = str(branch or "").strip()
    branch_number = int(branch_text) if branch_text.isdigit() and int(branch_text) != 0 else None
    if branch_number is None and re.fullmatch(r"\d{6}", text):
        main = int(text[:4])
        source_branch = int(text[4:])
        return f"제{main}조의{source_branch}" if source_branch else f"제{main}조"
    if text.startswith("제"):
        if branch_number is not None:
            match = re.fullmatch(r"제\s*(\d+)\s*조", text)
            if match:
                return f"제{int(match.group(1))}조의{branch_number}"
        return text
    if not text.isdigit():
        return text
    main = int(text)
    if branch_number is not None:
        return f"제{main}조의{branch_number}"
    return f"제{main}조"


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
