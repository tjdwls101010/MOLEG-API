"""Article reference parsing."""

from __future__ import annotations

import re

from moleg_api.models import ArticleReference

from .primitives import ARTICLE_REFERENCE_RE, LAW_NAME_RE, MAX_EXPANDED_ARTICLE_RANGE

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
    # '및'/'또는' are ambiguous: name-internal (부정청탁 및 …에 관한 법률) OR a
    # separator between statutes (제15조 및 데이터기본법). Splitting on them chops
    # the internal case; not splitting keeps a leading separator glued on. Resolve
    # by not splitting but stripping only a LEADING 및/또는 from the candidate. Also
    # drop a trailing promulgation parenthetical ("(2015. 3. 27. 법률 제…호…)") so
    # LAW_NAME_RE doesn't consume it as the name.
    pieces = re.split(r"[:;,\n/]", segment)
    for piece in reversed(pieces):
        candidate = piece.strip(" \t\r\n,.;[]{}「」『』\"'")
        candidate = re.sub(r"^(?:및|또는)\s+", "", candidate)
        candidate = re.split(r"\(\s*\d{4}\.", candidate)[0].strip()
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
