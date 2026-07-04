"""HTML history and diff normalization."""

from __future__ import annotations

from typing import Any, Literal

import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

from moleg_api.errors import ParseFailureError
from moleg_api.models import LawDiffChange, LawIdentity

from .history_events import normalize_history_events
from .primitives import _digits, compact_date, first_value, string_or_none
from .row_format import article_key, article_label, article_rows_from_diff

def parse_law_history_html(html: str) -> list[dict[str, Any]]:
    parser = LawHistoryTableParser()
    parser.feed(html)
    data_rows = [row for row in parser.rows if row]
    # A results table has 9-column rows; a "no results" page carries a single
    # message cell. Treat 1-column rows as non-data (empty result), but a row
    # that looks like data with the wrong width is a genuine parse breakage.
    structured = [row for row in data_rows if len(row) == 9]
    suspicious = [row for row in data_rows if len(row) not in (1, 9)]
    if suspicious:
        raise ParseFailureError("Could not parse lsHistory HTML table: unexpected column count")
    rows: list[dict[str, Any]] = []
    for row in structured:
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
    # An empty result (no structured rows) is a legitimate "no history" page,
    # not a parse failure — let the caller surface NoResultError instead.
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


def _diff_article_header(text: str) -> str | None:
    """The real 제N조[의M] label from the start of a diff row's content, if any."""
    match = re.match(r"\s*제\s*(\d+)\s*조(?:\s*의\s*(\d+))?", text or "")
    if not match:
        return None
    main = int(match.group(1))
    branch = int(match.group(2) or 0)
    return f"제{main}조의{branch}" if branch else f"제{main}조"


def _diff_row_has_real_article(row: dict[str, Any]) -> bool:
    """True when a diff row carries a genuine article identifier (제N조 in `no`, a
    6-digit 조문번호, or explicit 조문번호/조가지번호 fields) rather than a bare
    running row index — the latter must not be treated as an article number."""
    no = str(first_value(row, "no") or "").strip()
    if no.startswith("제") or "조" in no or re.fullmatch(r"\d{6}", no):
        return True
    return first_value(row, "조문번호", "조가지번호", "조문가지번호") not in (None, "")


def normalize_diff_changes(payload: dict[str, Any], *, article: str | int | None = None) -> list[LawDiffChange]:
    before_rows = article_rows_from_diff(payload, "구조문목록")
    after_rows = article_rows_from_diff(payload, "신조문목록")
    wanted = article_label(article) if article is not None else None

    before_by_no = {article_key(row): row for row in before_rows}
    after_by_no = {article_key(row): row for row in after_rows}
    # `no` is a sequential ROW index (1,2,3…), a correct index-parallel JOIN key
    # for the before/after lists — but NOT the real article number. Walk rows in
    # document order (numeric `no`) and derive the DISPLAYED article label from
    # the content's 제N조 header, carrying it forward across continuation rows
    # (항·호 fragments with no header). Never emit the sequential index as 제N조.
    keys = sorted(set(before_by_no) | set(after_by_no), key=lambda k: int(_digits(k) or "0"))
    changes: list[LawDiffChange] = []
    current_article: str | None = None
    for key in keys:
        before_row = before_by_no.get(key, {})
        after_row = after_by_no.get(key, {})
        before_text = str(first_value(before_row, "content", "조문내용", "text") or "")
        after_text = str(first_value(after_row, "content", "조문내용", "text") or "")
        header = _diff_article_header(after_text) or _diff_article_header(before_text)
        if header:
            current_article = header
        elif (_diff_row_has_real_article(after_row) or _diff_row_has_real_article(before_row)) and key:
            # The row carries a genuine article number (not the sequential index).
            current_article = key
        label = current_article
        if wanted and label != wanted:
            continue
        changes.append(
            LawDiffChange(
                article=label,
                title=string_or_none(first_value(after_row, "title", "조문제목") or first_value(before_row, "title", "조문제목")),
                before_text=before_text,
                after_text=after_text,
                raw={"before": before_row, "after": after_row},
            )
        )
    return changes
